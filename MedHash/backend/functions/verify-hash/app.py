import json
import boto3
import os
from datetime import datetime
import logging
from typing import Dict, Any, Optional
import traceback
from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext
from decimal import Decimal

# Configure Powertools
logger = Logger(service="medhash-verify-hash")
tracer = Tracer(service="medhash-verify-hash")
metrics = Metrics(namespace="MedHash", service="verify-hash")

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb')
verifications_table_name = os.environ.get('VERIFICATIONS_TABLE', 'medhash-verifications-dev')
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
    Main Lambda handler
    """
    logger.info(f"Received event: {json.dumps(event)}")
    metrics.add_metric(name="InvocationCount", unit=MetricUnit.Count, value=1)
    
    try:
        # Get hash from path parameters
        path_params = event.get('pathParameters') or {}
        hash_value = path_params.get('hash')
        
        # Also check query parameters
        query_params = event.get('queryStringParameters') or {}
        if not hash_value:
            hash_value = query_params.get('hash')
        
        if not hash_value:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'verified': False,
                    'error': 'Hash required',
                    'message': 'Please provide a hash value to verify'
                })
            }
        
        # Clean hash value (remove any prefixes)
        hash_value = hash_value.strip()
        if hash_value.startswith('0x'):
            hash_value = hash_value[2:]
        
        logger.info(f"Verifying hash: {hash_value}")
        
        # Look up in DynamoDB
        try:
            response = verifications_table.get_item(Key={'hash': hash_value})
        except Exception as e:
            logger.error(f"DynamoDB error: {str(e)}")
            return {
                'statusCode': 503,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'verified': False,
                    'error': 'Database error',
                    'message': 'Unable to access verification database'
                })
            }
        
        if 'Item' not in response:
            logger.info(f"Hash not found: {hash_value}")
            metrics.add_metric(name="HashNotFound", unit=MetricUnit.Count, value=1)
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'verified': False,
                    'hash': hash_value,
                    'message': 'Hash not found in registry',
                    'timestamp': datetime.utcnow().isoformat()
                })
            }
        
        record = response['Item']
        logger.info(f"Found record for hash {hash_value}")
        
        # Increment verification count
        current_count = record.get('verification_count', 0)
        # Convert Decimal to int if necessary
        if isinstance(current_count, Decimal):
            current_count = int(current_count)
        new_count = current_count + 1
        
        try:
            # Update the verification count
            verifications_table.update_item(
                Key={'hash': hash_value},
                UpdateExpression='SET verification_count = :count, last_verified = :time',
                ExpressionAttributeValues={
                    ':count': new_count,
                    ':time': datetime.utcnow().isoformat()
                },
                ReturnValues='UPDATED_NEW'
            )
            logger.info(f"Incremented verification count to {new_count}")
        except Exception as e:
            logger.error(f"Error updating verification count: {str(e)}")
            # Continue even if update fails
        
        metrics.add_metric(name="HashVerified", unit=MetricUnit.Count, value=1)
        
        # Prepare response - convert any Decimal values
        response_data = {
            'verified': True,
            'hash': hash_value,
            'pmid': record.get('pmid'),
            'summaryId': record.get('summaryId'),
            'paper_title': record.get('paper_title'),
            'created_at': record.get('created_at'),
            'verification_count': new_count,
            'last_verified': datetime.utcnow().isoformat(),
            'timestamp': int(datetime.utcnow().timestamp())
        }
        
        # Include blockchain data if available
        if 'blockchain' in record:
            response_data['blockchain'] = record['blockchain']
        
        # Include metadata if available
        if 'metadata' in record:
            response_data['metadata'] = record['metadata']
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(response_data, cls=DecimalEncoder)
        }
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(traceback.format_exc())
        metrics.add_metric(name="UnhandledError", unit=MetricUnit.Count, value=1)
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'verified': False,
                'error': 'Internal server error',
                'message': 'An unexpected error occurred during verification'
            })
        }