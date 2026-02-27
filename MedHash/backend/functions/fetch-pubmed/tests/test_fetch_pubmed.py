"""
Unit tests for fetch-pubmed function
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from app import lambda_handler, PubMedFetcher

class TestFetchPubMed:
    
    @pytest.fixture
    def valid_event(self):
        return {
            'body': json.dumps({'pmid': '12345678'})
        }
    
    @pytest.fixture
    def invalid_event(self):
        return {
            'body': json.dumps({})
        }
    
    def test_validate_pmid_valid(self):
        assert PubMedFetcher.validate_pmid('12345678') is True
        assert PubMedFetcher.validate_pmid('1') is True
        assert PubMedFetcher.validate_pmid('12345678901234567890') is True
    
    def test_validate_pmid_invalid(self):
        assert PubMedFetcher.validate_pmid('abc') is False
        assert PubMedFetcher.validate_pmid('') is False
        assert PubMedFetcher.validate_pmid('12345abc') is False
        assert PubMedFetcher.validate_pmid('123456789012345678901') is False
    
    @patch('app.table.get_item')
    def test_lambda_handler_cached(self, mock_get_item, valid_event):
        # Mock cached item
        mock_get_item.return_value = {
            'Item': {
                'pmid': '12345678',
                'title': 'Cached Paper'
            }
        }
        
        response = lambda_handler(valid_event, None)
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['cached'] is True
        assert body['data']['pmid'] == '12345678'
    
    @patch('app.PubMedFetcher.fetch_metadata')
    @patch('app.PubMedFetcher.fetch_abstract')
    @patch('app.table.get_item')
    @patch('app.table.put_item')
    def test_lambda_handler_fetch_new(self, mock_put, mock_get, mock_abstract, mock_metadata, valid_event):
        # Mock no cached item
        mock_get.return_value = {}
        
        # Mock PubMed responses
        mock_metadata.return_value = {
            'title': 'Test Paper',
            'authors': ['Smith J'],
            'journal': 'Test Journal',
            'pubdate': '2024'
        }
        mock_abstract.return_value = 'Test abstract'
        mock_put.return_value = {}
        
        response = lambda_handler(valid_event, None)
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['cached'] is False
        assert body['data']['title'] == 'Test Paper'
    
    def test_lambda_handler_missing_pmid(self, invalid_event):
        response = lambda_handler(invalid_event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body