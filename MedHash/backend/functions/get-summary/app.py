import json
import boto3
import os
from datetime import datetime
from decimal import Decimal
import logging
import traceback
from typing import Dict, Any, Optional  # ← THIS IS CRITICAL - adds Dict, Any, Optional

# For Lambda Powertools (if you're using them)
# from aws_lambda_powertools import Logger, Tracer, Metrics
# from aws_lambda_powertools.utilities.typing import LambdaContext

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb')
summaries_table_name = os.environ.get('SUMMARIES_TABLE', 'medhash-summaries-dev')
papers_table_name = os.environ.get('PAPERS_TABLE', 'medhash-papers-dev')
verifications_table_name = os.environ.get('VERIFICATIONS_TABLE', 'medhash-verifications-dev')

summaries_table = dynamodb.Table(summaries_table_name)
papers_table = dynamodb.Table(papers_table_name)
verifications_table = dynamodb.Table(verifications_table_name)

class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder for Decimal types"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super(DecimalEncoder, self).default(obj)

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Get a specific summary by ID
    """
    logger.info(f"Received event: {json.dumps(event)}")
    
    # Standard CORS headers
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET,OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
    }
    
    try:
        # Handle OPTIONS preflight
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': headers,
                'body': ''
            }
        
        # Get summary ID from path parameters
        path_params = event.get('pathParameters') or {}
        summary_id = path_params.get('summaryId')
        
        if not summary_id:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({
                    'error': 'Summary ID required'
                })
            }
        
        logger.info(f"Fetching summary: {summary_id}")
        
        # Get summary from DynamoDB
        response = summaries_table.get_item(Key={'summaryId': summary_id})
        
        if 'Item' not in response:
            logger.warning(f"Summary not found: {summary_id}")
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({
                    'error': 'Summary not found'
                })
            }
        
        summary = response['Item']
        logger.info(f"Found summary for PMID: {summary.get('pmid')}")
        
        # Get associated paper details
        paper_response = papers_table.get_item(Key={'pmid': summary['pmid']})
        paper = paper_response.get('Item', {})
        
        # Get blockchain verification if exists
        verification = None
        try:
            verifications = verifications_table.scan(
                FilterExpression='summaryId = :sid',
                ExpressionAttributeValues={':sid': summary_id}
            )
            if verifications.get('Items'):
                verification = verifications['Items'][0]
        except Exception as e:
            logger.warning(f"Error checking verification: {str(e)}")
        
        # Prepare response
        response_data = {
            'summary': summary,
            'paper': {
                'title': paper.get('title', ''),
                'authors': paper.get('authors', []),
                'journal': paper.get('journal', ''),
                'pubdate': paper.get('pubdate', ''),
                'doi': paper.get('doi', '')
            }
        }
        
        if verification:
            response_data['blockchain'] = {
                'hash': verification.get('hash'),
                'verified_at': verification.get('created_at'),
                'verification_count': verification.get('verification_count', 0)
            }
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(response_data, cls=DecimalEncoder)
        }
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }