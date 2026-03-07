"""
List Summaries Function
Retrieves all summaries for a user with pagination
"""

import json
import boto3
import os
from datetime import datetime
from decimal import Decimal
import logging
from typing import Dict, Any, Optional
from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext

# Configure Powertools
logger = Logger(service="medhash-list-summaries")
tracer = Tracer(service="medhash-list-summaries")
metrics = Metrics(namespace="MedHash", service="list-summaries")

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb')
summaries_table_name = os.environ.get('SUMMARIES_TABLE', 'medhash-summaries-dev')
verifications_table_name = os.environ.get('VERIFICATIONS_TABLE', 'medhash-verifications-dev')

summaries_table = dynamodb.Table(summaries_table_name)
verifications_table = dynamodb.Table(verifications_table_name)

class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder for Decimal types"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super(DecimalEncoder, self).default(obj)

@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics
def lambda_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    List all summaries with optional pagination and filtering
    """
    logger.info(f"Received event: {json.dumps(event)}")
    metrics.add_metric(name="InvocationCount", unit=MetricUnit.Count, value=1)
    
    try:
        # Get query parameters
        query_params = event.get('queryStringParameters') or {}
        
        # Pagination parameters
        limit = int(query_params.get('limit', '20'))
        last_evaluated_key = query_params.get('lastKey')
        
        # Filter parameters
        pmid_filter = query_params.get('pmid')
        date_from = query_params.get('from')
        date_to = query_params.get('to')
        
        # Build scan parameters
        scan_params = {
            'Limit': limit
        }
        
        # Add pagination if provided
        if last_evaluated_key:
            scan_params['ExclusiveStartKey'] = {'summaryId': last_evaluated_key}
        
        # Add filters if provided
        filter_expressions = []
        expr_attr_values = {}
        
        if pmid_filter:
            filter_expressions.append('pmid = :pmid')
            expr_attr_values[':pmid'] = pmid_filter
        
        if date_from or date_to:
            date_expr = []
            if date_from:
                date_expr.append('created_at >= :from')
                expr_attr_values[':from'] = date_from
            if date_to:
                date_expr.append('created_at <= :to')
                expr_attr_values[':to'] = date_to
            filter_expressions.append('(' + ' AND '.join(date_expr) + ')')
        
        if filter_expressions:
            scan_params['FilterExpression'] = ' AND '.join(filter_expressions)
            scan_params['ExpressionAttributeValues'] = expr_attr_values
        
        # Execute scan
        response = summaries_table.scan(**scan_params)
        
        items = response.get('Items', [])
        last_key = response.get('LastEvaluatedKey')
        
        # For each summary, check if it has a blockchain verification
        for item in items:
            # Check if hash exists for this summary
            try:
                # Query verifications table for this summaryId
                verifications = verifications_table.query(
                    IndexName='by-summaryId',  # You'll need to add this GSI
                    KeyConditionExpression='summaryId = :sid',
                    ExpressionAttributeValues={':sid': item['summaryId']},
                    Limit=1
                )
                
                if verifications.get('Items'):
                    item['verified_on_blockchain'] = True
                    item['blockchain_hash'] = verifications['Items'][0]['hash']
                else:
                    item['verified_on_blockchain'] = False
            except Exception as e:
                logger.warning(f"Error checking verification: {str(e)}")
                item['verified_on_blockchain'] = False
        
        # Sort by created_at descending (newest first)
        items.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET,OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'
            },
            'body': json.dumps({
                'summaries': items,
                'pagination': {
                    'lastKey': last_key.get('summaryId') if last_key else None,
                    'limit': limit,
                    'total': response.get('ScannedCount', 0)
                }
            }, cls=DecimalEncoder)
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
                'message': 'Failed to retrieve summaries'
            })
        }