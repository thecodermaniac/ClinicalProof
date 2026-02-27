"""
Pytest configuration and fixtures
Complete version with all fixtures
"""

import pytest
import boto3
import json
from datetime import datetime, timedelta
from moto import mock_dynamodb, mock_bedrock, mock_s3
import os
import sys
from typing import Dict, Any, Generator
import random
import string

# Add the layers to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../layers/common/python'))

@pytest.fixture(autouse=True)
def aws_credentials():
    """Mocked AWS Credentials for moto"""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

@pytest.fixture
def dynamodb_client(aws_credentials):
    """Create mock DynamoDB client"""
    with mock_dynamodb():
        yield boto3.client('dynamodb', region_name='us-east-1')

@pytest.fixture
def dynamodb_resource(aws_credentials):
    """Create mock DynamoDB resource"""
    with mock_dynamodb():
        yield boto3.resource('dynamodb', region_name='us-east-1')

@pytest.fixture
def s3_client(aws_credentials):
    """Create mock S3 client"""
    with mock_s3():
        yield boto3.client('s3', region_name='us-east-1')

@pytest.fixture
def bedrock_client(aws_credentials):
    """Create mock Bedrock client"""
    with mock_bedrock():
        yield boto3.client('bedrock-runtime', region_name='us-east-1')

@pytest.fixture
def papers_table(dynamodb_resource):
    """Create mock papers table"""
    table_name = 'medhash-papers-test'
    
    table = dynamodb_resource.create_table(
        TableName=table_name,
        KeySchema=[
            {'AttributeName': 'pmid', 'KeyType': 'HASH'}
        ],
        AttributeDefinitions=[
            {'AttributeName': 'pmid', 'AttributeType': 'S'}
        ],
        BillingMode='PAY_PER_REQUEST'
    )
    
    # Wait for table to be active
    table.meta.client.get_waiter('table_exists').wait(TableName=table_name)
    
    return table

@pytest.fixture
def summaries_table(dynamodb_resource):
    """Create mock summaries table"""
    table_name = 'medhash-summaries-test'
    
    table = dynamodb_resource.create_table(
        TableName=table_name,
        KeySchema=[
            {'AttributeName': 'summaryId', 'KeyType': 'HASH'}
        ],
        AttributeDefinitions=[
            {'AttributeName': 'summaryId', 'AttributeType': 'S'},
            {'AttributeName': 'pmid', 'AttributeType': 'S'}
        ],
        GlobalSecondaryIndexes=[
            {
                'IndexName': 'by-pmid',
                'KeySchema': [
                    {'AttributeName': 'pmid', 'KeyType': 'HASH'}
                ],
                'Projection': {'ProjectionType': 'ALL'}
            }
        ],
        BillingMode='PAY_PER_REQUEST'
    )
    
    table.meta.client.get_waiter('table_exists').wait(TableName=table_name)
    return table

@pytest.fixture
def verifications_table(dynamodb_resource):
    """Create mock verifications table"""
    table_name = 'medhash-verifications-test'
    
    table = dynamodb_resource.create_table(
        TableName=table_name,
        KeySchema=[
            {'AttributeName': 'hash', 'KeyType': 'HASH'}
        ],
        AttributeDefinitions=[
            {'AttributeName': 'hash', 'AttributeType': 'S'},
            {'AttributeName': 'pmid', 'AttributeType': 'S'}
        ],
        GlobalSecondaryIndexes=[
            {
                'IndexName': 'by-pmid',
                'KeySchema': [
                    {'AttributeName': 'pmid', 'KeyType': 'HASH'}
                ],
                'Projection': {'ProjectionType': 'ALL'}
            }
        ],
        BillingMode='PAY_PER_REQUEST'
    )
    
    table.meta.client.get_waiter('table_exists').wait(TableName=table_name)
    return table

@pytest.fixture
def sample_paper() -> Dict[str, Any]:
    """Sample paper data for tests"""
    return {
        'pmid': '12345678',
        'title': 'A Randomized Controlled Trial of Medical Intervention',
        'abstract': 'Background: This study aimed to evaluate the efficacy of a novel intervention. Methods: We conducted a double-blind randomized controlled trial with 500 participants. Results: The intervention showed significant improvement (p < 0.001) compared to placebo. Conclusion: This intervention is effective and safe for clinical use.',
        'authors': ['Smith J', 'Johnson M', 'Williams R'],
        'journal': 'Journal of Medical Research',
        'pubdate': '2024-01-15',
        'doi': '10.1234/jmr.2024.001',
        'volume': '42',
        'issue': '3',
        'pages': '123-135',
        'fetched_at': datetime.utcnow().isoformat()
    }

@pytest.fixture
def sample_summary() -> Dict[str, Any]:
    """Sample summary data for tests"""
    return {
        'summaryId': 'sum_1234567890abcdef',
        'pmid': '12345678',
        'short': 'A novel medical intervention showed significant improvement in patient outcomes.',
        'medium': 'This randomized controlled trial evaluated a new intervention in 500 patients. The treatment group showed 40% improvement compared to placebo (p<0.001), with minimal side effects.',
        'long': '## Background\nThis study addressed the need for better treatment options.\n\n## Methods\nDouble-blind RCT with 500 participants.\n\n## Results\nSignificant improvement observed.\n\n## Conclusion\nTreatment is effective and safe.',
        'created_at': datetime.utcnow().isoformat(),
        'model': 'amazon.nova-lite-v1:0'
    }

@pytest.fixture
def sample_verification() -> Dict[str, Any]:
    """Sample verification data for tests"""
    import hashlib
    hash_value = hashlib.sha256(b'test_data').hexdigest()
    
    return {
        'hash': hash_value,
        'pmid': '12345678',
        'summaryId': 'sum_1234567890abcdef',
        'paper_title': 'Test Paper',
        'created_at': datetime.utcnow().isoformat(),
        'verification_count': 5,
        'last_verified': datetime.utcnow().isoformat(),
        'metadata': {
            'has_secret': False,
            'store_on_chain': True
        }
    }

@pytest.fixture
def api_gateway_event() -> Dict[str, Any]:
    """Sample API Gateway event"""
    return {
        'httpMethod': 'POST',
        'path': '/test',
        'headers': {
            'Content-Type': 'application/json',
            'Origin': 'http://localhost:3000'
        },
        'queryStringParameters': {},
        'pathParameters': {},
        'body': json.dumps({'test': 'data'}),
        'requestContext': {
            'identity': {
                'sourceIp': '192.168.1.1'
            }
        }
    }

@pytest.fixture
def api_gateway_event_with_path(api_gateway_event) -> Dict[str, Any]:
    """API Gateway event with path parameters"""
    event = api_gateway_event.copy()
    event['pathParameters'] = {'id': 'test123'}
    return event

@pytest.fixture
def api_gateway_event_with_query(api_gateway_event) -> Dict[str, Any]:
    """API Gateway event with query parameters"""
    event = api_gateway_event.copy()
    event['queryStringParameters'] = {'page': '1', 'limit': '10'}
    return event

@pytest.fixture
def lambda_context():
    """Mock Lambda context"""
    class MockContext:
        def __init__(self):
            self.function_name = 'test-function'
            self.function_version = '$LATEST'
            self.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:test-function'
            self.memory_limit_in_mb = 512
            self.aws_request_id = 'test-request-id'
            self.log_group_name = '/aws/lambda/test-function'
            self.log_stream_name = '2024/01/01/[$LATEST]test-stream'
            
        def get_remaining_time_in_millis(self):
            return 30000
    
    return MockContext()

@pytest.fixture
def random_pmid() -> str:
    """Generate random PMID"""
    return ''.join(random.choices(string.digits, k=8))

@pytest.fixture
def random_hash() -> str:
    """Generate random hash"""
    return ''.join(random.choices(string.hexdigits, k=64)).lower()

@pytest.fixture
def sample_pubmed_response() -> Dict[str, Any]:
    """Sample PubMed API response"""
    return {
        'result': {
            '12345678': {
                'title': 'Test Medical Paper',
                'authors': [{'name': 'Smith J'}, {'name': 'Doe A'}],
                'fulljournalname': 'Test Journal',
                'pubdate': '2024 Jan',
                'elocationid': 'doi: 10.1234/test.2024.001',
                'volume': '42',
                'issue': '3',
                'pages': '123-35',
                'pmcid': 'PMC1234567'
            }
        }
    }

@pytest.fixture
def sample_pubmed_abstract_xml() -> str:
    """Sample PubMed abstract XML"""
    return '''<?xml version="1.0"?>
<!DOCTYPE PubmedArticleSet PUBLIC "-//NLM//DTD PubMedArticle 2.0//EN" "https://dtd.nlm.nih.gov/ncbi/pubmed/out/pubmed_200101.dtd">
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <Article>
        <Abstract>
          <AbstractText Label="BACKGROUND">This is the background section.</AbstractText>
          <AbstractText Label="METHODS">These are the methods.</AbstractText>
          <AbstractText Label="RESULTS">These are the results.</AbstractText>
          <AbstractText Label="CONCLUSIONS">This is the conclusion.</AbstractText>
        </Abstract>
      </Article>
    </MedlineCitation>
  </PubmedArticle>
</PubmedArticleSet>'''

@pytest.fixture
def sample_bedrock_response() -> Dict[str, Any]:
    """Sample Bedrock API response"""
    return {
        'output': {
            'message': {
                'content': [
                    {'text': 'This is a generated summary.'}
                ]
            }
        }
    }