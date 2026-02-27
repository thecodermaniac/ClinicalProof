"""
Unit tests for create-hash function
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from app import lambda_handler, HashGenerator

class TestCreateHash:
    
    @pytest.fixture
    def valid_event(self):
        return {
            'body': json.dumps({
                'pmid': '12345678',
                'summaryId': 'test123',
                'title': 'Test Paper',
                'summary': 'This is a test summary'
            })
        }
    
    def test_hash_generation_sha256(self):
        data = "test|data|123"
        hash1 = HashGenerator.generate_sha256(data)
        hash2 = HashGenerator.generate_sha256(data)
        
        assert len(hash1) == 64  # SHA-256 is 64 hex chars
        assert hash1 == hash2  # Same input should produce same hash
    
    def test_hash_generation_hmac(self):
        data = "test|data|123"
        key = "secret123"
        hash1 = HashGenerator.generate_hmac(data, key)
        hash2 = HashGenerator.generate_hmac(data, key)
        
        assert len(hash1) == 64
        assert hash1 == hash2
    
    def test_hash_verification(self):
        data = "test|data|123"
        hash_value = HashGenerator.generate_sha256(data)
        
        assert HashGenerator.verify_hash(data, hash_value) is True
        assert HashGenerator.verify_hash("wrong|data", hash_value) is False
    
    def test_hash_verification_hmac(self):
        data = "test|data|123"
        key = "secret123"
        hash_value = HashGenerator.generate_hmac(data, key)
        
        assert HashGenerator.verify_hash(data, hash_value, key) is True
        assert HashGenerator.verify_hash("wrong|data", hash_value, key) is False
        assert HashGenerator.verify_hash(data, hash_value, "wrongkey") is False
    
    @patch('app.verifications_table.put_item')
    def test_lambda_handler_success(self, mock_put, valid_event):
        mock_put.return_value = {}
        
        response = lambda_handler(valid_event, None)
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'hash' in body
        assert body['pmid'] == '12345678'
        assert 'verification_url' in body
    
    def test_lambda_handler_missing_fields(self):
        event = {
            'body': json.dumps({
                'pmid': '12345678'
                # Missing summaryId and summary
            })
        }
        
        response = lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'missing_fields' in body