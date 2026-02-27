"""
Integration tests for MedHash backend
Tests end-to-end workflows across multiple functions
"""

import pytest
import json
import sys
import os
from unittest.mock import patch, MagicMock
from datetime import datetime

# Add function paths to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../functions/fetch-pubmed'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../functions/generate-summary'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../functions/create-hash'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../functions/verify-hash'))

import app as fetch_app
import app as summary_app
import app as hash_app
import app as verify_app

class TestMedHashIntegration:
    """Integration tests for complete MedHash workflow"""
    
    @pytest.fixture
    def setup_tables(self, papers_table, summaries_table, verifications_table):
        """Setup all tables for testing"""
        return {
            'papers': papers_table,
            'summaries': summaries_table,
            'verifications': verifications_table
        }
    
    @patch('fetch_app.table.get_item')
    @patch('fetch_app.PubMedFetcher.fetch_metadata')
    @patch('fetch_app.PubMedFetcher.fetch_abstract')
    @patch('fetch_app.table.put_item')
    def test_complete_workflow(self, mock_put, mock_abstract, mock_metadata, 
                               mock_get, setup_tables, sample_paper):
        """Test complete workflow from fetch to verify"""
        
        # === STEP 1: Fetch Paper ===
        mock_get.return_value = {}  # No cached item
        mock_metadata.return_value = {
            'title': sample_paper['title'],
            'authors': sample_paper['authors'],
            'journal': sample_paper['journal'],
            'pubdate': sample_paper['pubdate'],
            'doi': sample_paper['doi']
        }
        mock_abstract.return_value = sample_paper['abstract']
        mock_put.return_value = {}
        
        fetch_event = {
            'body': json.dumps({'pmid': '12345678'})
        }
        
        fetch_response = fetch_app.lambda_handler(fetch_event, None)
        assert fetch_response['statusCode'] == 200
        fetch_body = json.loads(fetch_response['body'])
        assert fetch_body['pmid'] == '12345678'
        assert fetch_body['cached'] is False
        
        # === STEP 2: Generate Summary ===
        with patch('summary_app.papers_table.get_item') as mock_paper_get:
            mock_paper_get.return_value = {'Item': sample_paper}
            
            with patch('summary_app.BedrockSummarizer.generate_short_summary') as mock_short:
                mock_short.return_value = 'Short test summary'
                
                with patch('summary_app.BedrockSummarizer.generate_medium_summary') as mock_medium:
                    mock_medium.return_value = 'Medium test summary'
                    
                    with patch('summary_app.BedrockSummarizer.generate_long_summary') as mock_long:
                        mock_long.return_value = 'Long test summary'
                        
                        with patch('summary_app.summaries_table.put_item') as mock_summary_put:
                            mock_summary_put.return_value = {}
                            
                            summary_event = {
                                'body': json.dumps({
                                    'pmid': '12345678',
                                    'type': 'all'
                                })
                            }
                            
                            summary_response = summary_app.lambda_handler(summary_event, None)
                            assert summary_response['statusCode'] == 200
                            summary_body = json.loads(summary_response['body'])
                            assert 'summaryId' in summary_body
                            assert 'short' in summary_body['summaries']
                            
                            summary_id = summary_body['summaryId']
        
        # === STEP 3: Create Hash ===
        with patch('hash_app.verifications_table.put_item') as mock_hash_put:
            mock_hash_put.return_value = {}
            
            hash_event = {
                'body': json.dumps({
                    'pmid': '12345678',
                    'summaryId': summary_id,
                    'title': sample_paper['title'],
                    'summary': 'Medium test summary',
                    'storeOnChain': True
                })
            }
            
            hash_response = hash_app.lambda_handler(hash_event, None)
            assert hash_response['statusCode'] == 200
            hash_body = json.loads(hash_response['body'])
            assert 'hash' in hash_body
            assert 'verification_url' in hash_body
            
            hash_value = hash_body['hash']
        
        # === STEP 4: Verify Hash ===
        with patch('verify_app.verifications_table.get_item') as mock_verify_get:
            mock_verify_get.return_value = {
                'Item': {
                    'hash': hash_value,
                    'pmid': '12345678',
                    'summaryId': summary_id,
                    'paper_title': sample_paper['title'],
                    'created_at': datetime.utcnow().isoformat(),
                    'verification_count': 0
                }
            }
            
            with patch('verify_app.verifications_table.update_item') as mock_verify_update:
                mock_verify_update.return_value = {}
                
                verify_event = {
                    'pathParameters': {
                        'hash': hash_value
                    }
                }
                
                verify_response = verify_app.lambda_handler(verify_event, None)
                assert verify_response['statusCode'] == 200
                verify_body = json.loads(verify_response['body'])
                assert verify_body['verified'] is True
                assert verify_body['hash'] == hash_value
                assert verify_body['pmid'] == '12345678'
    
    def test_error_handling_workflow(self):
        """Test error handling across the workflow"""
        
        # Test fetch with invalid PMID
        fetch_event = {
            'body': json.dumps({'pmid': 'invalid'})
        }
        
        fetch_response = fetch_app.lambda_handler(fetch_event, None)
        assert fetch_response['statusCode'] == 400
        
        # Test generate summary without paper
        summary_event = {
            'body': json.dumps({'pmid': '99999999'})
        }
        
        with patch('summary_app.papers_table.get_item') as mock_get:
            mock_get.return_value = {}  # Paper not found
            
            summary_response = summary_app.lambda_handler(summary_event, None)
            assert summary_response['statusCode'] == 404
        
        # Test create hash with missing fields
        hash_event = {
            'body': json.dumps({'pmid': '12345678'})  # Missing summaryId and summary
        }
        
        hash_response = hash_app.lambda_handler(hash_event, None)
        assert hash_response['statusCode'] == 400
        
        # Test verify with non-existent hash
        verify_event = {
            'pathParameters': {
                'hash': 'nonexistenthash123'
            }
        }
        
        with patch('verify_app.verifications_table.get_item') as mock_get:
            mock_get.return_value = {}  # Hash not found
            
            verify_response = verify_app.lambda_handler(verify_event, None)
            assert verify_response['statusCode'] == 404
            verify_body = json.loads(verify_response['body'])
            assert verify_body['verified'] is False
    
    @patch('fetch_app.PubMedFetcher.fetch_metadata')
    @patch('fetch_app.PubMedFetcher.fetch_abstract')
    def test_pubmed_api_error_handling(self, mock_abstract, mock_metadata):
        """Test handling of PubMed API errors"""
        
        # Simulate PubMed API error
        mock_metadata.side_effect = Exception("PubMed API unavailable")
        
        fetch_event = {
            'body': json.dumps({'pmid': '12345678'})
        }
        
        with patch('fetch_app.table.get_item') as mock_get:
            mock_get.return_value = {}  # No cached item
            
            response = fetch_app.lambda_handler(fetch_event, None)
            assert response['statusCode'] == 500
    
    @patch('summary_app.BedrockSummarizer.generate_medium_summary')
    def test_bedrock_error_handling(self, mock_summary, sample_paper):
        """Test handling of Bedrock API errors"""
        
        # Simulate Bedrock error
        mock_summary.side_effect = Exception("Bedrock API error")
        
        with patch('summary_app.papers_table.get_item') as mock_get:
            mock_get.return_value = {'Item': sample_paper}
            
            summary_event = {
                'body': json.dumps({
                    'pmid': '12345678',
                    'type': 'medium'
                })
            }
            
            response = summary_app.lambda_handler(summary_event, None)
            assert response['statusCode'] == 500
    
    def test_dynamodb_error_handling(self):
        """Test handling of DynamoDB errors"""
        
        # Test fetch with DynamoDB error
        fetch_event = {
            'body': json.dumps({'pmid': '12345678'})
        }
        
        with patch('fetch_app.table.get_item') as mock_get:
            mock_get.side_effect = Exception("DynamoDB unavailable")
            
            # Should still try to fetch from PubMed
            with patch('fetch_app.PubMedFetcher.fetch_metadata') as mock_metadata:
                mock_metadata.return_value = {'title': 'Test'}
                with patch('fetch_app.PubMedFetcher.fetch_abstract') as mock_abstract:
                    mock_abstract.return_value = 'Test abstract'
                    
                    response = fetch_app.lambda_handler(fetch_event, None)
                    # Should return 200 even if DynamoDB fails
                    assert response['statusCode'] == 200
    
    def test_concurrent_requests(self):
        """Test handling of concurrent requests (simulated)"""
        
        # Simulate multiple simultaneous requests
        import concurrent.futures
        
        def make_request(pmid):
            event = {
                'body': json.dumps({'pmid': pmid})
            }
            
            with patch('fetch_app.table.get_item') as mock_get:
                mock_get.return_value = {}
                with patch('fetch_app.PubMedFetcher.fetch_metadata') as mock_metadata:
                    mock_metadata.return_value = {'title': f'Paper {pmid}'}
                    with patch('fetch_app.PubMedFetcher.fetch_abstract') as mock_abstract:
                        mock_abstract.return_value = f'Abstract {pmid}'
                        
                        return fetch_app.lambda_handler(event, None)
        
        pmids = ['11111111', '22222222', '33333333', '44444444']
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(make_request, pmid) for pmid in pmids]
            responses = [f.result() for f in futures]
        
        # All requests should succeed
        assert all(r['statusCode'] == 200 for r in responses)