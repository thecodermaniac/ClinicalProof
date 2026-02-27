"""
Fetch PubMed Function
Retrieves paper metadata and abstract from PubMed API
"""

import json
import urllib.request
import urllib.parse
import boto3
import os
from datetime import datetime
import xml.etree.ElementTree as ET
import logging
from typing import Dict, Any, Optional, List
import traceback
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

# Configure Powertools
logger = Logger(service="medhash-fetch-pubmed")
tracer = Tracer(service="medhash-fetch-pubmed")

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('TABLE_NAME', 'medhash-papers-dev')
table = dynamodb.Table(table_name)

# PubMed API Configuration
PUBMED_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
PUBMED_ESEARCH_URL = f"{PUBMED_BASE_URL}esearch.fcgi"
PUBMED_ESUMMARY_URL = f"{PUBMED_BASE_URL}esummary.fcgi"
PUBMED_EFETCH_URL = f"{PUBMED_BASE_URL}efetch.fcgi"

# Rate limiting for PubMed API (3 requests per second)
import time
_last_request_time = 0
MIN_REQUEST_INTERVAL = 0.34  # ~3 requests per second

def rate_limit():
    """Rate limit PubMed API calls"""
    global _last_request_time
    current_time = time.time()
    time_since_last = current_time - _last_request_time
    if time_since_last < MIN_REQUEST_INTERVAL:
        time.sleep(MIN_REQUEST_INTERVAL - time_since_last)
    _last_request_time = time.time()

class PubMedFetcher:
    """Handles fetching data from PubMed API"""
    
    @staticmethod
    @tracer.capture_method
    def fetch_metadata(pmid: str) -> Dict[str, Any]:
        """
        Fetch paper metadata using esummary
        
        Args:
            pmid: PubMed ID
            
        Returns:
            Dictionary with paper metadata
        """
        url = f"{PUBMED_ESUMMARY_URL}?db=pubmed&id={pmid}&retmode=json"
        
        try:
            rate_limit()
            logger.info(f"Fetching metadata for PMID {pmid}")
            
            req = urllib.request.Request(
                url,
                headers={
                    'User-Agent': 'MedHash/1.0 (mailto:contact@medhash.com)'
                }
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                
            result = data.get('result', {})
            paper_data = result.get(pmid, {})
            
            # Extract authors properly
            authors = []
            for author in paper_data.get('authors', []):
                if isinstance(author, dict):
                    name = author.get('name', '')
                    if name:
                        authors.append(name)
            
            return {
                'title': paper_data.get('title', 'Title not available'),
                'authors': authors,
                'journal': paper_data.get('fulljournalname', ''),
                'pubdate': paper_data.get('pubdate', ''),
                'doi': paper_data.get('elocationid', '').replace('doi: ', ''),
                'issn': paper_data.get('issn', ''),
                'volume': paper_data.get('volume', ''),
                'issue': paper_data.get('issue', ''),
                'pages': paper_data.get('pages', ''),
                'pmcid': paper_data.get('pmcid', '')
            }
        except urllib.error.HTTPError as e:
            logger.error(f"HTTP error fetching metadata: {e.code} - {e.reason}")
            raise
        except Exception as e:
            logger.error(f"Error fetching metadata: {str(e)}")
            raise

    @staticmethod
    @tracer.capture_method
    def fetch_abstract(pmid: str) -> str:
        """
        Fetch abstract using efetch
        
        Args:
            pmid: PubMed ID
            
        Returns:
            Abstract text
        """
        url = f"{PUBMED_EFETCH_URL}?db=pubmed&id={pmid}&retmode=xml&rettype=abstract"
        
        try:
            rate_limit()
            logger.info(f"Fetching abstract for PMID {pmid}")
            
            req = urllib.request.Request(
                url,
                headers={
                    'User-Agent': 'MedHash/1.0 (mailto:contact@medhash.com)'
                }
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                xml_data = response.read().decode()
            
            # Parse XML
            root = ET.fromstring(xml_data)
            
            # Find abstract text - handle multiple formats
            abstract_parts = []
            
            # Try different paths for abstract
            for abstract in root.findall('.//AbstractText'):
                label = abstract.get('Label', '')
                text = abstract.text or ''
                
                # Get all text including tail
                for child in abstract:
                    if child.text:
                        text += child.text
                    if child.tail:
                        text += child.tail
                
                if label:
                    abstract_parts.append(f"**{label}:** {text}")
                else:
                    abstract_parts.append(text)
            
            # Also check for OtherAbstract
            for abstract in root.findall('.//OtherAbstract/AbstractText'):
                text = abstract.text or ''
                abstract_parts.append(text)
            
            if abstract_parts:
                return '\n\n'.join(abstract_parts)
            
            # If no abstract found, check if it's a book chapter
            book_title = root.find('.//Book/BookTitle')
            if book_title is not None:
                return f"This is a book chapter from: {book_title.text}"
            
            return "Abstract not available for this article."
            
        except ET.ParseError as e:
            logger.error(f"XML parsing error: {str(e)}")
            return "Error parsing abstract XML."
        except Exception as e:
            logger.error(f"Error fetching abstract: {str(e)}")
            raise

    @staticmethod
    def validate_pmid(pmid: str) -> bool:
        """Validate PubMed ID format"""
        return bool(pmid and pmid.isdigit() and 1 <= len(pmid) <= 20)

@logger.inject_lambda_context
@tracer.capture_lambda_handler
def lambda_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Main Lambda handler
    
    Args:
        event: Lambda event object
        context: Lambda context object
        
    Returns:
        API Gateway response
    """
    logger.info(f"Received event: {json.dumps(event)}")
    
    try:
        # Parse request body
        body = {}
        if event.get('body'):
            try:
                body = json.loads(event['body'])
            except json.JSONDecodeError:
                return {
                    'statusCode': 400,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': 'Invalid JSON',
                        'message': 'Request body must be valid JSON'
                    })
                }
        
        pmid = body.get('pmid')
        
        if not pmid:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'PMID is required',
                    'message': 'Please provide a valid PubMed ID'
                })
            }
        
        # Validate PMID format
        if not PubMedFetcher.validate_pmid(pmid):
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Invalid PMID format',
                    'message': 'PMID should contain only numbers (1-20 digits)'
                })
            }
        
        # Check if already in DynamoDB
        try:
            response = table.get_item(Key={'pmid': pmid})
            
            if 'Item' in response:
                logger.info(f"Paper {pmid} found in cache")
                return {
                    'statusCode': 200,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'pmid': pmid,
                        'cached': True,
                        'data': response['Item']
                    })
                }
        except Exception as e:
            logger.warning(f"Error checking DynamoDB: {str(e)}")
            # Continue with fetch if DynamoDB fails
        
        # Fetch from PubMed
        logger.info(f"Fetching paper {pmid} from PubMed")
        
        # Get metadata
        metadata = PubMedFetcher.fetch_metadata(pmid)
        
        # Get abstract
        abstract = PubMedFetcher.fetch_abstract(pmid)
        
        # Create article record
        article = {
            'pmid': pmid,
            'title': metadata.get('title', 'Title not available'),
            'abstract': abstract,
            'authors': metadata.get('authors', []),
            'journal': metadata.get('journal', ''),
            'pubdate': metadata.get('pubdate', ''),
            'doi': metadata.get('doi', ''),
            'issn': metadata.get('issn', ''),
            'volume': metadata.get('volume', ''),
            'issue': metadata.get('issue', ''),
            'pages': metadata.get('pages', ''),
            'pmcid': metadata.get('pmcid', ''),
            'fetched_at': datetime.utcnow().isoformat(),
            'source': 'pubmed'
        }
        
        # Store in DynamoDB
        try:
            table.put_item(Item=article)
            logger.info(f"Stored paper {pmid} in DynamoDB")
        except Exception as e:
            logger.error(f"Error storing in DynamoDB: {str(e)}")
            # Continue even if storage fails - return fetched data
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'pmid': pmid,
                'cached': False,
                'data': article,
                'message': 'Paper fetched successfully'
            })
        }
        
    except urllib.error.HTTPError as e:
        logger.error(f"PubMed API error: {e.code} - {e.reason}")
        return {
            'statusCode': 502,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'PubMed API error',
                'message': f'PubMed returned error {e.code}: {e.reason}'
            })
        }
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }