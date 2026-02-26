import json
import urllib.request
import urllib.parse
import boto3
import os
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_NAME'])

def lambda_handler(event, context):
    """
    Fetch PubMed article by PMID
    """
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        pmid = body.get('pmid')
        
        if not pmid:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'PMID is required'})
            }
        
        # Check if already in DynamoDB
        response = table.get_item(Key={'pmid': pmid})
        if 'Item' in response:
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
        
        # Fetch from PubMed API
        # NCBI E-utilities API
        base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
        
        # Get article metadata
        esummary_url = f"{base_url}esummary.fcgi?db=pubmed&id={pmid}&retmode=json"
        with urllib.request.urlopen(esummary_url) as response:
            summary_data = json.loads(response.read().decode())
        
        # Get abstract
        efetch_url = f"{base_url}efetch.fcgi?db=pubmed&id={pmid}&retmode=xml&rettype=abstract"
        with urllib.request.urlopen(efetch_url) as response:
            abstract_xml = response.read().decode()
        
        # Extract abstract (simplified - would need proper XML parsing)
        import re
        abstract_match = re.search(r'<AbstractText>(.*?)</AbstractText>', abstract_xml, re.DOTALL)
        abstract = abstract_match.group(1) if abstract_match else "Abstract not available"
        
        # Extract title from summary
        result = summary_data.get('result', {})
        article_data = result.get(pmid, {})
        title = article_data.get('title', 'Title not available')
        
        # Store in DynamoDB
        article = {
            'pmid': pmid,
            'title': title,
            'abstract': abstract,
            'authors': article_data.get('authors', []),
            'journal': article_data.get('fulljournalname', ''),
            'pubdate': article_data.get('pubdate', ''),
            'fetched_at': datetime.utcnow().isoformat()
        }
        
        table.put_item(Item=article)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'pmid': pmid,
                'cached': False,
                'data': article
            })
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': str(e)})
        }