"""
Create Hash Function
Generates SHA-256 hash of paper + summary for blockchain verification
"""

import json
import boto3
import os
import hashlib
import hmac
from datetime import datetime
import time
import logging
from typing import Dict, Any, Optional
import secrets
import traceback
from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext

# Configure Powertools
logger = Logger(service="medhash-create-hash")
tracer = Tracer(service="medhash-create-hash")
metrics = Metrics(namespace="MedHash", service="create-hash")

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb')
verifications_table_name = os.environ.get('VERIFICATIONS_TABLE', 'medhash-verifications-dev')
verifications_table = dynamodb.Table(verifications_table_name)

class HashGenerator:
    """Handles cryptographic hash generation"""
    
    @staticmethod
    def generate_sha256(data: str) -> str:
        """
        Generate SHA-256 hash
        
        Args:
            data: Input string to hash
            
        Returns:
            Hexadecimal hash string
        """
        return hashlib.sha256(data.encode('utf-8')).hexdigest()
    
    @staticmethod
    def generate_hmac(data: str, key: str) -> str:
        """
        Generate HMAC-SHA256
        
        Args:
            data: Input string to hash
            key: Secret key for HMAC
            
        Returns:
            Hexadecimal HMAC string
        """
        return hmac.new(
            key.encode('utf-8'),
            data.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    @staticmethod
    def generate_hash(paper_data: Dict[str, Any], summary_text: str, secret_key: Optional[str] = None) -> str:
        """
        Generate hash from paper and summary
        
        Args:
            paper_data: Dictionary with paper metadata
            summary_text: Summary text to include
            secret_key: Optional secret key for HMAC
            
        Returns:
            Generated hash
        """
        # Create canonical representation
        components = [
            paper_data.get('pmid', ''),
            paper_data.get('title', ''),
            paper_data.get('doi', ''),
            paper_data.get('pubdate', ''),
            summary_text.strip()
        ]
        
        # Join with separator
        combined = '|'.join(components)
        
        # Generate hash
        if secret_key:
            return HashGenerator.generate_hmac(combined, secret_key)
        else:
            return HashGenerator.generate_sha256(combined)
    
    @staticmethod
    def verify_hash(data: str, expected_hash: str, key: Optional[str] = None) -> bool:
        """
        Verify hash matches data
        
        Args:
            data: Original data
            expected_hash: Hash to verify against
            key: Secret key if HMAC was used
            
        Returns:
            True if hash matches
        """
        if key:
            computed = HashGenerator.generate_hmac(data, key)
        else:
            computed = HashGenerator.generate_sha256(data)
        
        # Constant-time comparison to prevent timing attacks
        return hmac.compare_digest(computed, expected_hash)

class BlockchainSimulator:
    """Simulates blockchain interactions (for hackathon)"""
    
    @staticmethod
    def create_transaction(hash_value: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulate blockchain transaction
        
        Args:
            hash_value: Hash to store
            metadata: Additional metadata
            
        Returns:
            Simulated blockchain transaction data
        """
        return {
            'network': 'Ethereum Sepolia Testnet',
            'transactionHash': f"0x{hash_value[:64]}",
            'blockNumber': int(time.time()) % 1000000,
            'timestamp': datetime.utcnow().isoformat(),
            'from': '0x' + secrets.token_hex(20),
            'to': '0x' + secrets.token_hex(20),
            'gasUsed': '21000',
            'status': 'success',
            'note': 'SIMULATED FOR HACKATHON - Not a real blockchain transaction'
        }

@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics
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
    metrics.add_metric(name="InvocationCount", unit=MetricUnit.Count, value=1)
    
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
        
        # Extract required fields
        pmid = body.get('pmid')
        summary_id = body.get('summaryId')
        title = body.get('title', '')
        summary_text = body.get('summary', '')
        secret_key = body.get('secretKey')  # Optional
        store_on_chain = body.get('storeOnChain', True)  # Whether to simulate blockchain
        
        # Validate required fields
        missing_fields = []
        if not pmid:
            missing_fields.append('pmid')
        if not summary_id:
            missing_fields.append('summaryId')
        if not summary_text:
            missing_fields.append('summary')
        
        if missing_fields:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Missing required fields',
                    'missing_fields': missing_fields,
                    'message': f"Please provide: {', '.join(missing_fields)}"
                })
            }
        
        # Prepare paper data
        paper_data = {
            'pmid': pmid,
            'title': title,
            'doi': body.get('doi', ''),
            'pubdate': body.get('pubdate', '')
        }
        
        # Generate hash
        hash_value = HashGenerator.generate_hash(paper_data, summary_text, secret_key)
        logger.info(f"Generated hash: {hash_value}")
        metrics.add_metric(name="HashGenerated", unit=MetricUnit.Count, value=1)
        
        # Check for duplicate hash
        try:
            existing = verifications_table.get_item(Key={'hash': hash_value})
            if 'Item' in existing:
                logger.warning(f"Hash already exists: {hash_value}")
                # Still return success, but note it's a duplicate
        except Exception as e:
            logger.warning(f"Error checking duplicate: {str(e)}")
        
        # Simulate blockchain transaction if requested
        blockchain_data = None
        if store_on_chain:
            blockchain_data = BlockchainSimulator.create_transaction(hash_value, {
                'pmid': pmid,
                'summaryId': summary_id
            })
            logger.info("Simulated blockchain transaction")
            metrics.add_metric(name="BlockchainSimulated", unit=MetricUnit.Count, value=1)
        
        # Create verification record
        verification_record = {
            'hash': hash_value,
            'pmid': pmid,
            'summaryId': summary_id,
            'paper_title': title,
            'created_at': datetime.utcnow().isoformat(),
            'timestamp': int(time.time()),
            'verification_count': 0,
            'last_verified': None,
            'metadata': {
                'has_secret': secret_key is not None,
                'store_on_chain': store_on_chain
            }
        }
        
        # Add blockchain data if available
        if blockchain_data:
            verification_record['blockchain'] = blockchain_data
        
        # Store in DynamoDB
        try:
            verifications_table.put_item(Item=verification_record)
            logger.info(f"Stored verification record for hash {hash_value}")
            metrics.add_metric(name="RecordStored", unit=MetricUnit.Count, value=1)
        except Exception as e:
            logger.error(f"Error storing in DynamoDB: {str(e)}")
            # Continue even if storage fails
        
        # Prepare response
        response = {
            'hash': hash_value,
            'pmid': pmid,
            'summaryId': summary_id,
            'created_at': verification_record['created_at'],
            'verification_url': f"/verify/{hash_value}",
            'api_url': f"https://api.medhash.com/verify/{hash_value}"  # Update with your domain
        }
        
        # Include blockchain data if available
        if blockchain_data:
            response['blockchain'] = blockchain_data
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(response)
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
                'error': 'Internal server error',
                'message': 'An unexpected error occurred while creating hash'
            })
        }