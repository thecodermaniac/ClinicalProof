"""
Unit tests for verify-hash function
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from datetime import datetime
from app import lambda_handler

class TestVerifyHash:
    
    @pytest.fixture
    def valid_event(self):
        return {
            'pathParameters': {
                'hash': 'abc123def456'
            }
        }
    
    @pytest.fixture
    def mock_record(self):
        return {
            'Item': {
                'hash': 'abc123def456',
                'pmid': '12345678',
                'summaryId': 'test123',
                'paper_title': 'Test Paper',
                'created_at': '2024-01-01T00:00:00Z',
                'verification_count': 5
            }
        }
    
    @patch('app.verifications_table.get_item')
    def test_verify_existing_hash(self, mock_get_item, valid_event, mock_record):
        mock_get_item.return_value = mock_record
        
        with patch('app.verifications_table.update_item') as mock_update:
            mock_update.return_value = {}
            
            response = lambda_handler(valid_event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['verified'] is True
            assert body['hash'] == 'abc123def456'
            assert body['verification_count'] == 6  # Incremented
    
    @patch('app.verifications_table.get_item')
    def test_verify_nonexistent_hash(self, mock_get_item, valid_event):
        mock_get_item.return_value = {}
        
        response = lambda_handler(valid_event, None)
        
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert body['verified'] is False
    
    def test_verify_missing_hash(self):
        event = {'pathParameters': {}}
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['verified'] is False
        assert 'error' in body
    
    def test_verify_with_query_param(self):
        event = {
            'queryStringParameters': {
                'hash': 'abc123'
            }
        }
        
        with patch('app.verifications_table.get_item') as mock_get:
            mock_get.return_value = {}
            
            response = lambda_handler(event, None)
            # Should return 404, but not 400
            assert response['statusCode'] == 404