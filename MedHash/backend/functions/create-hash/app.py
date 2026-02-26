import json
import boto3
import os
import hashlib
import hmac
from datetime import datetime
import time

dynamodb = boto3.resource('dynamodb')
verifications_table = dynamodb.Table(os.environ['VERIFICATIONS_TABLE'])

def generate_hash(paper_data, summary_data, secret_key=None):
    """
    Generate SHA-256 hash of paper + summary
    
    This creates a fingerprint that can be verified later
    """
    # Create combined string
    combined = f"{paper_data['pmid']}:{paper_data['title']}:{summary_data}"
    
    if secret_key:
        # Use HMAC if secret key provided
        h = hmac.new(
            secret_key.encode(),
            combined.encode(),
            hashlib.sha256
        )
        return h.hexdigest()
    else:
        # Simple SHA-256
        return hashlib.sha256(combined.encode()).hexdigest()

def lambda_handler(event, context):
    try:
        # Parse request
        body = json.loads(event.get('body', '{}'))
        pmid = body.get('pmid')
        summary_id = body.get('summaryId')
        title = body.get('title', '')
        summary_text = body.get('summary', '')
        secret_key = body.get('secretKey')  # Optional
        
        if not all([pmid, summary_id, summary_text]):
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing required fields'})
            }
        
        # Generate hash
        paper_data = {
            'pmid': pmid,
            'title': title
        }
        
        hash_value = generate_hash(paper_data, summary_text, secret_key)
        
        # Store verification record
        verification_record = {
            'hash': hash_value,
            'pmid': pmid,
            'summaryId': summary_id,
            'created_at': datetime.utcnow().isoformat(),
            'timestamp': int(time.time()),
            'verifications': 0,
            'metadata': {
                'has_secret': secret_key is not None,
                'title': title
            }
        }
        
        verifications_table.put_item(Item=verification_record)
        
        # Blockchain simulation (for hackathon demo)
        blockchain_ref = {
            'network': 'Ethereum Testnet (Simulated)',
            'transactionId': f"0x{hash_value[:64]}",
            'blockTimestamp': datetime.utcnow().isoformat(),
            'note': 'Simulated for hackathon - real implementation would call actual blockchain'
        }
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'hash': hash_value,
                'pmid': pmid,
                'summaryId': summary_id,
                'blockchain': blockchain_ref,
                'verificationUrl': f"/verify/{hash_value}"
            })
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }