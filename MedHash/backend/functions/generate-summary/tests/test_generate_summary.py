"""
Unit tests for generate-summary function
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from app import lambda_handler, BedrockSummarizer

class TestGenerateSummary:
    
    @pytest.fixture
    def valid_event(self):
        return {
            'body': json.dumps({
                'pmid': '12345678',
                'type': 'all'
            })
        }
    
    @pytest.fixture
    def mock_paper(self):
        return {
            'Item': {
                'pmid': '12345678',
                'title': 'Test Paper',
                'abstract': 'This is a test abstract for a medical paper.'
            }
        }
    
    @patch('app.papers_table.get_item')
    def test_lambda_handler_paper_not_found(self, mock_get_item, valid_event):
        mock_get_item.return_value = {}
        
        response = lambda_handler(valid_event, None)
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert 'error' in body
    
    @patch('app.papers_table.get_item')
    @patch('app.BedrockSummarizer.generate_short_summary')
    @patch('app.BedrockSummarizer.generate_medium_summary')
    @patch('app.BedrockSummarizer.generate_long_summary')
    @patch('app.summaries_table.put_item')
    def test_generate_all_summaries(self, mock_put, mock_long, mock_medium, mock_short, mock_get, valid_event, mock_paper):
        mock_get.return_value = mock_paper
        mock_short.return_value = 'Short summary'
        mock_medium.return_value = 'Medium summary'
        mock_long.return_value = 'Long summary'
        mock_put.return_value = {}
        
        response = lambda_handler(valid_event, None)
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'summaryId' in body
        assert 'short' in body['summaries']
        assert 'medium' in body['summaries']
        assert 'long' in body['summaries']
    
    @patch('app.papers_table.get_item')
    @patch('app.BedrockSummarizer.generate_short_summary')
    def test_generate_short_only(self, mock_short, mock_get, mock_paper):
        mock_get.return_value = mock_paper
        mock_short.return_value = 'Short summary'
        
        event = {
            'body': json.dumps({
                'pmid': '12345678',
                'type': 'short'
            })
        }
        
        response = lambda_handler(event, None)
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'short' in body['summaries']
        assert 'medium' not in body['summaries']
    
    def test_bedrock_summarizer_initialization(self):
        summarizer = BedrockSummarizer()
        assert summarizer.model_id is not None
        assert summarizer.max_