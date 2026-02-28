import json
import boto3
import os
from datetime import datetime
import hashlib
import time
import logging
from typing import Dict, Any, Optional
import traceback
from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext

# Configure Powertools
logger = Logger(service="medhash-generate-summary")
tracer = Tracer(service="medhash-generate-summary")
metrics = Metrics(namespace="MedHash", service="generate-summary")

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
bedrock = boto3.client('bedrock-runtime')

# Get environment variables
papers_table_name = os.environ.get('PAPERS_TABLE', 'medhash-papers-dev')
summaries_table_name = os.environ.get('SUMMARIES_TABLE', 'medhash-summaries-dev')
bedrock_model_id = os.environ.get('BEDROCK_MODEL_ID', 'apac.amazon.nova-lite-v1:0')  # Updated default

papers_table = dynamodb.Table(papers_table_name)
summaries_table = dynamodb.Table(summaries_table_name)

class BedrockSummarizer:
    """Handles AI summary generation using Amazon Bedrock"""
    
    def __init__(self, model_id: str = bedrock_model_id):
        self.model_id = model_id
        self.max_retries = 3
        self.retry_delay = 1  # seconds
        
    @tracer.capture_method
    def generate_with_retry(self, prompt: str, max_tokens: int = 500) -> Optional[str]:
        """
        Generate text with retry logic using Converse API
        """
        for attempt in range(self.max_retries):
            try:
                result = self._generate_converse(prompt, max_tokens)
                if result:
                    metrics.add_metric(name="SuccessfulGeneration", unit=MetricUnit.Count, value=1)
                    return result
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    logger.error(f"All retries failed: {str(e)}")
                    metrics.add_metric(name="FailedGeneration", unit=MetricUnit.Count, value=1)
                    return None
        return None
    
    @tracer.capture_method
    def _generate_converse(self, prompt: str, max_tokens: int = 500) -> Optional[str]:
        """
        Generate text using Amazon Bedrock Converse API
        """
        try:
            start_time = time.time()
            
            # Prepare messages
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ]
            
            inference_config = {
                "maxTokens": max_tokens,
                "temperature": 0.7,
                "topP": 0.9
            }
            
            logger.info(f"Calling Bedrock with model: {self.model_id}")
            
            # Call Converse API
            response = bedrock.converse(
                modelId=self.model_id,
                messages=messages,
                inferenceConfig=inference_config
            )
            
            latency = time.time() - start_time
            metrics.add_metric(name="BedrockLatency", unit=MetricUnit.Seconds, value=latency)
            
            # Parse the response correctly
            if 'output' in response and 'message' in response['output']:
                message = response['output']['message']
                if 'content' in message and len(message['content']) > 0:
                    content_item = message['content'][0]
                    if 'text' in content_item:
                        return content_item['text']
            
            # Try alternative response format
            if 'results' in response:
                return response['results'][0].get('outputText', '')
            
            logger.error(f"Unexpected response format: {json.dumps(response)}")
            return None
            
        except Exception as e:
            logger.error(f"Bedrock Converse API error: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    @tracer.capture_method
    def generate_short_summary(self, abstract: str) -> str:
        """Generate 2-sentence summary"""
        prompt = f"""Provide a concise 2-sentence summary of this medical abstract. Focus on the key finding and clinical significance.

Abstract:
{abstract}

Requirements:
- Exactly 2 sentences
- First sentence: Main finding/result
- Second sentence: Clinical significance or implication
- Use clear, plain language
- Be accurate to the original research

Summary:"""
        
        result = self.generate_with_retry(prompt, 150)
        return result if result else "Unable to generate short summary."
    
    @tracer.capture_method
    def generate_medium_summary(self, abstract: str) -> str:
        """Generate paragraph-length summary"""
        prompt = f"""Write a clear, professional summary of this medical abstract.

Abstract:
{abstract}

Format your summary with these sections:
Objective: What did the study aim to investigate?
Methods: Brief overview of study design
Results: Main findings
Conclusion: Clinical implications

Requirements:
- One coherent paragraph
- Professional tone
- Approximately 150-200 words

Summary:"""
        
        result = self.generate_with_retry(prompt, 300)
        return result if result else "Unable to generate medium summary."
    
    @tracer.capture_method
    def generate_long_summary(self, abstract: str) -> str:
        """Generate detailed comprehensive summary"""
        prompt = f"""Create a detailed, structured analysis of this medical abstract.

Abstract:
{abstract}

Provide a comprehensive summary with:

Background and Rationale:
- What gap does this address?
- Why was this study needed?

Study Design and Methods:
- Study type
- Population characteristics
- Key interventions
- Primary outcomes

Key Results:
- Main findings with data
- Secondary outcomes
- Important negative findings

Limitations:
- Methodological concerns
- Generalizability issues

Clinical Implications:
- Practice recommendations
- Unanswered questions

Requirements:
- Include specific statistics
- Critical evaluation
- Approximately 400-500 words

Analysis:"""
        
        result = self.generate_with_retry(prompt, 600)
        return result if result else "Unable to generate detailed summary."

@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics
def lambda_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Main Lambda handler
    """
    logger.info(f"Received event: {json.dumps(event)}")
    metrics.add_metric(name="InvocationCount", unit=MetricUnit.Count, value=1)
    
    try:
        # Parse request
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
        
        pmid = body.get('pmid')
        summary_type = body.get('type', 'all')
        
        if not pmid:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'PMID required'})
            }
        
        # Get paper from DynamoDB
        try:
            paper_response = papers_table.get_item(Key={'pmid': pmid})
            
            if 'Item' not in paper_response:
                return {
                    'statusCode': 404,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': 'Paper not found',
                        'message': f'No paper found with PMID {pmid}. Please fetch it first.'
                    })
                }
            
            paper = paper_response['Item']
            
        except Exception as e:
            logger.error(f"Error fetching paper: {str(e)}")
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'Database error'})
            }
        
        # Initialize summarizer with correct model ID
        summarizer = BedrockSummarizer()
        
        # Generate summaries
        summaries = {}
        
        try:
            if summary_type in ['short', 'all']:
                summaries['short'] = summarizer.generate_short_summary(paper['abstract'])
                logger.info("Generated short summary")
            
            if summary_type in ['medium', 'all']:
                summaries['medium'] = summarizer.generate_medium_summary(paper['abstract'])
                logger.info("Generated medium summary")
            
            if summary_type in ['long', 'all']:
                summaries['long'] = summarizer.generate_long_summary(paper['abstract'])
                logger.info("Generated long summary")
                
        except Exception as e:
            logger.error(f"Error generating summaries: {str(e)}")
            logger.error(traceback.format_exc())
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Summary generation failed',
                    'message': f'AI service error: {str(e)}'
                })
            }
        
        # Create summary record
        summary_id = hashlib.sha256(
            f"{pmid}:{time.time()}:{paper.get('title', '')}".encode()
        ).hexdigest()[:16]
        
        summary_record = {
            'summaryId': summary_id,
            'pmid': pmid,
            'short': summaries.get('short', ''),
            'medium': summaries.get('medium', ''),
            'long': summaries.get('long', ''),
            'created_at': datetime.utcnow().isoformat(),
            'model': bedrock_model_id,
            'summary_type': summary_type
        }
        
        # Store in DynamoDB
        try:
            summaries_table.put_item(Item=summary_record)
            logger.info(f"Stored summary {summary_id}")
        except Exception as e:
            logger.error(f"Error storing summary: {str(e)}")
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'summaryId': summary_id,
                'pmid': pmid,
                'summaries': summaries,
                'created_at': summary_record['created_at'],
                'cached': False,
                'model': bedrock_model_id
            })
        }
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': 'Internal server error'})
        }