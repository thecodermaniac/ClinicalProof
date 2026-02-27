"""
Common utilities shared across Lambda functions
Complete version with all helper functions
"""

import json
import hashlib
import hmac
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
import boto3
from botocore.exceptions import ClientError
import uuid
import re
import base64
import zlib
from decimal import Decimal
import time
import random
import string

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class DynamoDBClient:
    """Wrapper for DynamoDB operations"""
    
    def __init__(self, table_name: str, region: str = 'us-east-1'):
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        self.table = self.dynamodb.Table(table_name)
        self.table_name = table_name
    
    def get_item(self, key: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get item by key"""
        try:
            response = self.table.get_item(Key=key)
            return response.get('Item')
        except ClientError as e:
            logger.error(f"Error getting item from {self.table_name}: {e}")
            return None
    
    def put_item(self, item: Dict[str, Any]) -> bool:
        """Put item in table"""
        try:
            self.table.put_item(Item=item)
            return True
        except ClientError as e:
            logger.error(f"Error putting item in {self.table_name}: {e}")
            return False
    
    def update_item(self, key: Dict[str, Any], update_expr: str, expr_attrs: Dict[str, Any]) -> bool:
        """Update item"""
        try:
            self.table.update_item(
                Key=key,
                UpdateExpression=update_expr,
                ExpressionAttributeValues=expr_attrs
            )
            return True
        except ClientError as e:
            logger.error(f"Error updating item in {self.table_name}: {e}")
            return False
    
    def delete_item(self, key: Dict[str, Any]) -> bool:
        """Delete item"""
        try:
            self.table.delete_item(Key=key)
            return True
        except ClientError as e:
            logger.error(f"Error deleting item from {self.table_name}: {e}")
            return False
    
    def query(self, index_name: str, key_condition: str, expr_attrs: Dict[str, Any], 
              limit: int = 10, scan_forward: bool = True) -> List[Dict[str, Any]]:
        """Query table with index"""
        try:
            response = self.table.query(
                IndexName=index_name,
                KeyConditionExpression=key_condition,
                ExpressionAttributeValues=expr_attrs,
                Limit=limit,
                ScanIndexForward=scan_forward
            )
            return response.get('Items', [])
        except ClientError as e:
            logger.error(f"Error querying table {self.table_name}: {e}")
            return []
    
    def scan(self, filter_expr: Optional[str] = None, expr_attrs: Optional[Dict[str, Any]] = None,
             limit: int = 100) -> List[Dict[str, Any]]:
        """Scan table with optional filter"""
        try:
            params = {'Limit': limit}
            if filter_expr and expr_attrs:
                params['FilterExpression'] = filter_expr
                params['ExpressionAttributeValues'] = expr_attrs
            
            response = self.table.scan(**params)
            return response.get('Items', [])
        except ClientError as e:
            logger.error(f"Error scanning table {self.table_name}: {e}")
            return []
    
    def batch_write(self, items: List[Dict[str, Any]]) -> bool:
        """Batch write items"""
        try:
            with self.table.batch_writer() as batch:
                for item in items:
                    batch.put_item(Item=item)
            return True
        except ClientError as e:
            logger.error(f"Error batch writing to {self.table_name}: {e}")
            return False
    
    def increment_counter(self, key: Dict[str, Any], counter_field: str, increment: int = 1) -> Optional[int]:
        """Increment a counter field"""
        try:
            response = self.table.update_item(
                Key=key,
                UpdateExpression=f"ADD {counter_field} :inc",
                ExpressionAttributeValues={':inc': increment},
                ReturnValues="UPDATED_NEW"
            )
            return response.get('Attributes', {}).get(counter_field)
        except ClientError as e:
            logger.error(f"Error incrementing counter in {self.table_name}: {e}")
            return None

class HashGenerator:
    """Generate and verify hashes"""
    
    @staticmethod
    def generate_sha256(data: str) -> str:
        """Generate SHA-256 hash"""
        return hashlib.sha256(data.encode('utf-8')).hexdigest()
    
    @staticmethod
    def generate_sha512(data: str) -> str:
        """Generate SHA-512 hash"""
        return hashlib.sha512(data.encode('utf-8')).hexdigest()
    
    @staticmethod
    def generate_md5(data: str) -> str:
        """Generate MD5 hash (not for security)"""
        return hashlib.md5(data.encode('utf-8')).hexdigest()
    
    @staticmethod
    def generate_hmac(data: str, key: str, algorithm: str = 'sha256') -> str:
        """Generate HMAC with specified algorithm"""
        algorithms = {
            'sha256': hashlib.sha256,
            'sha512': hashlib.sha512,
            'sha1': hashlib.sha1,
            'md5': hashlib.md5
        }
        hash_func = algorithms.get(algorithm, hashlib.sha256)
        
        return hmac.new(
            key.encode('utf-8'),
            data.encode('utf-8'),
            hash_func
        ).hexdigest()
    
    @staticmethod
    def verify_hash(data: str, expected_hash: str, key: Optional[str] = None, 
                    algorithm: str = 'sha256') -> bool:
        """Verify hash"""
        if key:
            computed = HashGenerator.generate_hmac(data, key, algorithm)
        else:
            computed = HashGenerator.generate_sha256(data)
        
        # Constant-time comparison
        return hmac.compare_digest(computed, expected_hash)
    
    @staticmethod
    def generate_hash_from_dict(data: Dict[str, Any], exclude_keys: List[str] = None) -> str:
        """Generate hash from dictionary"""
        if exclude_keys is None:
            exclude_keys = []
        
        # Create sorted copy excluding specified keys
        filtered = {k: v for k, v in data.items() if k not in exclude_keys}
        
        # Convert to canonical JSON string
        canonical = json.dumps(filtered, sort_keys=True, default=str)
        
        return HashGenerator.generate_sha256(canonical)
    
    @staticmethod
    def generate_hash_from_file(file_content: bytes) -> str:
        """Generate hash from file content"""
        return hashlib.sha256(file_content).hexdigest()

class CryptoUtils:
    """Cryptographic utilities"""
    
    @staticmethod
    def encrypt_data(data: str, key: str) -> str:
        """Simple XOR encryption (not for production)"""
        # This is a simple implementation - use proper encryption in production
        encrypted = []
        for i, char in enumerate(data):
            key_char = key[i % len(key)]
            encrypted_char = chr(ord(char) ^ ord(key_char))
            encrypted.append(encrypted_char)
        
        # Encode to base64 for safe transmission
        combined = ''.join(encrypted)
        return base64.b64encode(combined.encode()).decode()
    
    @staticmethod
    def decrypt_data(encrypted_data: str, key: str) -> str:
        """Simple XOR decryption"""
        # Decode from base64
        decoded = base64.b64decode(encrypted_data).decode()
        
        decrypted = []
        for i, char in enumerate(decoded):
            key_char = key[i % len(key)]
            decrypted_char = chr(ord(char) ^ ord(key_char))
            decrypted.append(decrypted_char)
        
        return ''.join(decrypted)
    
    @staticmethod
    def compress_data(data: str) -> str:
        """Compress string data"""
        compressed = zlib.compress(data.encode('utf-8'))
        return base64.b64encode(compressed).decode()
    
    @staticmethod
    def decompress_data(compressed_data: str) -> str:
        """Decompress string data"""
        compressed = base64.b64decode(compressed_data)
        decompressed = zlib.decompress(compressed)
        return decompressed.decode('utf-8')
    
    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """Generate cryptographically secure random token"""
        return secrets.token_hex(length // 2)  # hex string of specified length
    
    @staticmethod
    def generate_api_key() -> str:
        """Generate API key"""
        prefix = "mk_"  # MedHash Key
        random_part = secrets.token_urlsafe(32)
        return f"{prefix}{random_part}"

class ResponseBuilder:
    """Build standardized API responses"""
    
    @staticmethod
    def success(data: Any = None, message: str = "Success", status_code: int = 200) -> Dict[str, Any]:
        """Build success response"""
        body = {
            'success': True,
            'message': message,
            'timestamp': datetime.utcnow().isoformat()
        }
        if data is not None:
            body['data'] = data
        
        return create_response(status_code, body)
    
    @staticmethod
    def error(message: str, error_code: str = None, status_code: int = 400, 
              details: Any = None) -> Dict[str, Any]:
        """Build error response"""
        body = {
            'success': False,
            'message': message,
            'timestamp': datetime.utcnow().isoformat()
        }
        if error_code:
            body['error_code'] = error_code
        if details:
            body['details'] = details
        
        return create_response(status_code, body)
    
    @staticmethod
    def not_found(resource: str = "Resource") -> Dict[str, Any]:
        """Build not found response"""
        return ResponseBuilder.error(
            message=f"{resource} not found",
            error_code="NOT_FOUND",
            status_code=404
        )
    
    @staticmethod
    def validation_error(errors: List[str]) -> Dict[str, Any]:
        """Build validation error response"""
        return ResponseBuilder.error(
            message="Validation failed",
            error_code="VALIDATION_ERROR",
            status_code=400,
            details={'errors': errors}
        )
    
    @staticmethod
    def server_error(error_id: str = None) -> Dict[str, Any]:
        """Build server error response"""
        body = {
            'success': False,
            'message': "Internal server error",
            'timestamp': datetime.utcnow().isoformat()
        }
        if error_id:
            body['error_id'] = error_id
        
        return create_response(500, body)

def create_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """Create standardized API response"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Credentials': 'true',
            'Access-Control-Max-Age': '600'
        },
        'body': json.dumps(body, default=json_serializer)
    }

def json_serializer(obj: Any) -> str:
    """JSON serializer for objects not serializable by default"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj) if obj % 1 else int(obj)
    if isinstance(obj, (bytes, bytearray)):
        return base64.b64encode(obj).decode()
    if hasattr(obj, 'isoformat'):  # Handle dates
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def parse_request_body(event: Dict[str, Any]) -> Dict[str, Any]:
    """Parse and validate request body"""
    try:
        if event.get('body'):
            body = event['body']
            if isinstance(body, str):
                return json.loads(body)
            return body
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        return {}

def get_path_parameter(event: Dict[str, Any], param: str) -> Optional[str]:
    """Get path parameter from event"""
    path_params = event.get('pathParameters') or {}
    return path_params.get(param)

def get_query_parameter(event: Dict[str, Any], param: str, default: Any = None) -> Optional[str]:
    """Get query parameter from event"""
    query_params = event.get('queryStringParameters') or {}
    return query_params.get(param, default)

def get_header(event: Dict[str, Any], header: str) -> Optional[str]:
    """Get header from event"""
    headers = event.get('headers') or {}
    # Case-insensitive lookup
    for key, value in headers.items():
        if key.lower() == header.lower():
            return value
    return None

def validate_pmid(pmid: str) -> bool:
    """Validate PubMed ID format"""
    return bool(pmid and pmid.isdigit() and 1 <= len(pmid) <= 20)

def validate_doi(doi: str) -> bool:
    """Validate DOI format"""
    pattern = r'^10\.\d{4,9}/[-._;()/:A-Z0-9]+$'
    return bool(re.match(pattern, doi, re.IGNORECASE))

def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_url(url: str) -> bool:
    """Validate URL format"""
    pattern = r'^https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[/\w\.-]*$'
    return bool(re.match(pattern, url))

def validate_hash(hash_value: str) -> bool:
    """Validate hash format (hex string)"""
    return bool(re.match(r'^[0-9a-fA-F]{64}$', hash_value))

def current_timestamp() -> str:
    """Get current UTC timestamp in ISO format"""
    return datetime.utcnow().isoformat()

def current_epoch() -> int:
    """Get current epoch timestamp"""
    return int(time.time())

def generate_id(prefix: str = '', length: int = 16) -> str:
    """Generate unique ID"""
    unique_id = str(uuid.uuid4()).replace('-', '')
    if length:
        unique_id = unique_id[:length]
    return f"{prefix}{unique_id}" if prefix else unique_id

def generate_short_id(length: int = 8) -> str:
    """Generate short alphanumeric ID"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def safe_json_loads(data: str, default: Any = None) -> Any:
    """Safely load JSON string"""
    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError):
        return default

def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """Split list into chunks"""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]

def extract_pmid_from_url(url: str) -> Optional[str]:
    """Extract PMID from PubMed URL"""
    patterns = [
        r'pubmed\.ncbi\.nlm\.nih\.gov/(\d+)',
        r'pubmed\.ncbi\.nlm\.nih\.gov/pubmed/(\d+)',
        r'pubmed\.ncbi\.nlm\.nih\.gov/articl/(\d+)',
        r'ncbi\.nlm\.nih\.gov/pubmed/(\d+)',
        r'pmid=(\d+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url, re.IGNORECASE)
        if match:
            return match.group(1)
    return None

def extract_doi_from_text(text: str) -> Optional[str]:
    """Extract DOI from text"""
    pattern = r'\b(10\.\d{4,9}/[-._;()/:A-Z0-9]+)\b'
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1) if match else None

def truncate_text(text: str, max_length: int = 200, suffix: str = '...') -> str:
    """Truncate text to specified length"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix

def sanitize_input(text: str) -> str:
    """Sanitize user input"""
    # Remove any non-printable characters
    text = ''.join(char for char in text if char.isprintable())
    # Remove any HTML tags (simple version)
    text = re.sub(r'<[^>]+>', '', text)
    return text.strip()

def mask_sensitive_data(data: str, visible_chars: int = 4) -> str:
    """Mask sensitive data (e.g., API keys)"""
    if len(data) <= visible_chars * 2:
        return '*' * len(data)
    
    start = data[:visible_chars]
    end = data[-visible_chars:]
    masked = '*' * (len(data) - visible_chars * 2)
    return f"{start}{masked}{end}"

def calculate_backoff(attempt: int, base_delay: float = 1.0, max_delay: float = 60.0) -> float:
    """Calculate exponential backoff with jitter"""
    delay = min(base_delay * (2 ** attempt), max_delay)
    # Add jitter (±25%)
    jitter = delay * 0.25 * (random.random() * 2 - 1)
    return max(0, delay + jitter)

def retry_with_backoff(func, max_retries: int = 3, base_delay: float = 1.0):
    """Decorator for retrying functions with exponential backoff"""
    def wrapper(*args, **kwargs):
        last_exception = None
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    delay = calculate_backoff(attempt, base_delay)
                    logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay:.2f}s: {e}")
                    time.sleep(delay)
        raise last_exception
    return wrapper

def parse_cors_headers(event: Dict[str, Any]) -> Dict[str, str]:
    """Parse CORS headers from request"""
    origin = get_header(event, 'origin')
    if origin:
        # In production, validate against allowed origins
        return {
            'Access-Control-Allow-Origin': origin,
            'Access-Control-Allow-Credentials': 'true'
        }
    return {}

def extract_client_ip(event: Dict[str, Any]) -> Optional[str]:
    """Extract client IP from event"""
    # Check CloudFront header first
    ip = get_header(event, 'cloudfront-viewer-address')
    if ip:
        return ip.split(':')[0]  # Remove port if present
    
    # Check X-Forwarded-For
    forwarded = get_header(event, 'x-forwarded-for')
    if forwarded:
        return forwarded.split(',')[0].strip()
    
    # Fallback to request context
    request_context = event.get('requestContext', {})
    identity = request_context.get('identity', {})
    return identity.get('sourceIp')

def create_error_id() -> str:
    """Create unique error ID for tracking"""
    return f"err_{generate_id(length=12)}"

def log_error_with_id(error: Exception, context: Dict[str, Any] = None) -> str:
    """Log error with unique ID and return it"""
    error_id = create_error_id()
    error_data = {
        'error_id': error_id,
        'error_type': type(error).__name__,
        'error_message': str(error),
        'timestamp': current_timestamp()
    }
    if context:
        error_data['context'] = context
    
    logger.error(f"Error {error_id}: {error_data}")
    return error_id

# Import secrets for token generation
import secrets