"""
Generate Summary Function
Uses Amazon Bedrock to create multi-level summaries
"""

import json
import boto3
import os
from datetime import datetime
import hashlib
import time
import logging
from typing import Dict, Any, Optional, List
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
bedrock_model_id = os.environ.get('BEDROCK_MODEL_ID', 'amazon.nova-lite-v1:0')

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
        Generate text with retry logic
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens in response
            
        Returns:
            Generated text or None
        """
        for attempt in range(self.max_retries):
            try:
                result = self._generate(prompt, max_tokens)
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
    
    @tracer.capture_method
    def _generate(self, prompt: str, max_tokens: int = 500) -> str:
        """
        Generate text using Amazon Nova Lite
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens in response
            
        Returns:
            Generated text
        """
        request_body = {
            "schemaVersion": "messages",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            "inferenceConfig": {
                "max_new_tokens": max_tokens,
                "temperature": 0.7,
                "top_p": 0.9,
                "stopSequences": []
            }
        }
        
        try:
            start_time = time.time()
            
            response = bedrock.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )
            
            latency = time.time() - start_time
            metrics.add_metric(name="BedrockLatency", unit=MetricUnit.Seconds, value=latency)
            
            response_body = json.loads(response['body'].read())
            
            # Extract text from response (Nova format)
            output = response_body.get('output', {})
            message = output.get('message', {})
            content = message.get('content', [])
            
            if content and len(content) > 0:
                return content[0].get('text', '')
            
            return "Summary generation failed - no content in response."
            
        except Exception as e:
            logger.error(f"Bedrock API error: {str(e)}")
            metrics.add_metric(name="BedrockError", unit=MetricUnit.Count, value=1)
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
- Use clear, plain language suitable for patients
- Avoid technical jargon
- Be accurate to the original research

Summary:"""
        
        result = self.generate_with_retry(prompt, 150)
        return result or "Unable to generate short summary."
    
    @tracer.capture_method
    def generate_medium_summary(self, abstract: str) -> str:
        """Generate paragraph-length summary"""
        prompt = f"""Write a clear, professional summary of this medical abstract for healthcare professionals.

Abstract:
{abstract}

Format your summary with these sections clearly marked:
**Objective**: What did the study aim to investigate?
**Methods**: Brief overview of study design and key methods
**Results**: Main findings with key data points
**Conclusion**: Clinical implications

Requirements:
- One coherent paragraph with clear section markers
- Include key statistics if available in the abstract
- Professional tone, but accessible
- Approximately 150-200 words
- Maintain scientific accuracy

Summary:"""
        
        result = self.generate_with_retry(prompt, 300)
        return result or "Unable to generate medium summary."
    
    @tracer.capture_method
    def generate_long_summary(self, abstract: str) -> str:
        """Generate detailed comprehensive summary"""
        prompt = f"""Create a detailed, structured analysis of this medical abstract.

Abstract:
{abstract}

Provide a comprehensive summary with the following structure:

## Background and Rationale
- What gap in knowledge does this address?
- Why was this study needed?
- What were the researchers' hypotheses?

## Study Design and Methods
- Study type (RCT, cohort, case-control, etc.)
- Population characteristics (size, demographics, inclusion/exclusion)
- Key interventions or exposures
- Primary and secondary outcomes measured
- Statistical methods used

## Key Results
- Primary outcome results with effect sizes and confidence intervals
- Secondary outcomes and subgroup analyses
- Important negative or null findings
- Absolute and relative risks if applicable

## Limitations
- Methodological limitations
- Generalizability concerns
- Potential biases
- Confounding factors not addressed

## Clinical Implications
- How should this change clinical practice?
- What questions remain unanswered?
- Recommendations for implementation
- Cost-effectiveness considerations (if mentioned)

Requirements:
- Comprehensive but concise
- Include specific numbers/statistics from the abstract
- Critical evaluation where appropriate
- Approximately 400-500 words
- Use markdown formatting for readability

Analysis:"""
        
        result = self.generate_with_retry(prompt, 600)
        return result or "Unable to generate detailed summary."

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
        summary_type = body.get('type', 'all')  # short, medium, long, or all
        regenerate = body.get('regenerate', False)  # Force regeneration
        
        if not pmid:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'PMID required',
                    'message': 'Please provide a PubMed ID'
                })
            }
        
        # Check if summaries already exist (unless regenerate is True)
        if not regenerate:
            try:
                existing = summaries_table.query(
                    IndexName='by-pmid',
                    KeyConditionExpression='pmid = :pmid',
                    ExpressionAttributeValues={':pmid': pmid},
                    Limit=1,
                    ScanIndexForward=False  # Get most recent first
                )
                
                if existing.get('Items'):
                    latest = existing['Items'][0]
                    logger.info(f"Found existing summaries for PMID {pmid}")
                    return {
                        'statusCode': 200,
                        'headers': {
                            'Content-Type': 'application/json',
                            'Access-Control-Allow-Origin': '*'
                        },
                        'body': json.dumps({
                            'summaryId': latest['summaryId'],
                            'pmid': pmid,
                            'summaries': {
                                'short': latest.get('short', ''),
                                'medium': latest.get('medium', ''),
                                'long': latest.get('long', '')
                            },
                            'created_at': latest.get('created_at'),
                            'cached': True,
                            'model': latest.get('model')
                        })
                    }
            except Exception as e:
                logger.warning(f"Error checking existing summaries: {str(e)}")
        
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
                'body': json.dumps({
                    'error': 'Database error',
                    'message': 'Error accessing paper data'
                })
            }
        
        # Initialize summarizer
        summarizer = BedrockSummarizer()
        
        # Generate summaries based on requested type
        summaries = {}
        
        try:
            if summary_type in ['short', 'all']:
                summaries['short'] = summarizer.generate_short_summary(paper['abstract'])
                logger.info("Generated short summary")
                metrics.add_metric(name="ShortSummaryGenerated", unit=MetricUnit.Count, value=1)
            
            if summary_type in ['medium', 'all']:
                summaries['medium'] = summarizer.generate_medium_summary(paper['abstract'])
                logger.info("Generated medium summary")
                metrics.add_metric(name="MediumSummaryGenerated", unit=MetricUnit.Count, value=1)
            
            if summary_type in ['long', 'all']:
                summaries['long'] = summarizer.generate_long_summary(paper['abstract'])
                logger.info("Generated long summary")
                metrics.add_metric(name="LongSummaryGenerated", unit=MetricUnit.Count, value=1)
                
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
                    'message': 'AI service temporarily unavailable'
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
            'summary_type': summary_type,
            'paper_title': paper.get('title', '')
        }
        
        # Store in DynamoDB
        try:
            summaries_table.put_item(Item=summary_record)
            logger.info(f"Stored summary {summary_id}")
        except Exception as e:
            logger.error(f"Error storing summary: {str(e)}")
            # Continue even if storage fails
        
        # Prepare response
        response_data = {
            'summaryId': summary_id,
            'pmid': pmid,
            'summaries': summaries,
            'created_at': summary_record['created_at'],
            'cached': False,
            'model': bedrock_model_id
        }
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(response_data)
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
                'message': 'An unexpected error occurred'
            })
        }