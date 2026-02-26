import json
import boto3
import os
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['VERIFICATIONS_TABLE'])

def lambda_handler(event, context):
    try:
        # Get hash from path parameter
        hash_value = event.get('pathParameters', {}).get('hash')
        
        if not hash_value:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Hash required'})
            }
        
        # Look up in DynamoDB
        response = table.get_item(Key={'hash': hash_value})
        
        if 'Item' not in response:
            return {
                'statusCode': 404,
                'body': json.dumps({
                    'verified': False,
                    'message': 'Hash not found in registry'
                })
            }
        
        record = response['Item']
        
        # Increment verification count (update)
        verifications = record.get('verifications', 0) + 1
        table.update_item(
            Key={'hash': hash_value},
            UpdateExpression='SET verifications = :v, last_verified = :t',
            ExpressionAttributeValues={
                ':v': verifications,
                ':t': datetime.utcnow().isoformat()
            }
        )
        
        # Prepare response
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'verified': True,
                'hash': hash_value,
                'pmid': record.get('pmid'),
                'summaryId': record.get('summaryId'),
                'created_at': record.get('created_at'),
                'verification_count': verifications,
                'blockchain': record.get('blockchain', {
                    'note': 'On-chain verification available in production'
                })
            })
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }