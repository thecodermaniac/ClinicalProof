import json
import boto3
import os
from datetime import datetime
import hashlib
import time

dynamodb = boto3.resource('dynamodb')
bedrock = boto3.client('bedrock-runtime')

papers_table = dynamodb.Table(os.environ['PAPERS_TABLE'])
summaries_table = dynamodb.Table(os.environ['SUMMARIES_TABLE'])

def generate_with_nova(prompt, max_tokens=500):
    """Generate summary using Amazon Nova Lite [citation:8]"""
    model_id = "amazon.nova-lite-v1:0"
    
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
            "temperature": 0.7
        }
    }
    
    try:
        response = bedrock.invoke_model(
            modelId=model_id,
            body=json.dumps(request_body)
        )
        
        response_body = json.loads(response['body'].read())
        return response_body['output']['message']['content'][0]['text']
    except Exception as e:
        print(f"Bedrock error: {e}")
        return None

def generate_summary_levels(abstract):
    """Generate three levels of summaries"""
    
    # Level 1: Ultra-concise (2 sentences)
    prompt_short = f"""Provide an ultra-concise 2-sentence summary of this medical abstract:

{abstract}

Requirements:
- Exactly 2 sentences
- Include key finding and significance
- Use plain language"""
    
    # Level 2: Moderate (1 paragraph, 100 words)
    prompt_medium = f"""Provide a clear, balanced summary of this medical abstract:

{abstract}

Requirements:
- One paragraph, approximately 100 words
- Include: purpose, key methods, main finding
- Accessible to healthcare professionals"""
    
    # Level 3: Comprehensive (3 paragraphs)
    prompt_long = f"""Provide a detailed, structured summary of this medical abstract:

{abstract}

Format:
Paragraph 1: Background and purpose
Paragraph 2: Methods and key results
Paragraph 3: Conclusions and implications

Total: Approximately 300 words, professional medical tone."""
    
    # Generate all three
    short_summary = generate_with_nova(prompt_short, 100)
    medium_summary = generate_with_nova(prompt_medium, 200)
    long_summary = generate_with_nova(prompt_long, 400)
    
    return {
        'short': short_summary,
        'medium': medium_summary,
        'long': long_summary
    }

def lambda_handler(event, context):
    try:
        # Parse request
        body = json.loads(event.get('body', '{}'))
        pmid = body.get('pmid')
        
        if not pmid:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'PMID required'})
            }
        
        # Get paper from DynamoDB
        paper_response = papers_table.get_item(Key={'pmid': pmid})
        if 'Item' not in paper_response:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'Paper not found'})
            }
        
        paper = paper_response['Item']
        
        # Generate summaries
        summaries = generate_summary_levels(paper['abstract'])
        
        # Create summary record
        summary_id = hashlib.sha256(
            f"{pmid}:{time.time()}".encode()
        ).hexdigest()[:16]
        
        summary_record = {
            'summaryId': summary_id,
            'pmid': pmid,
            'short': summaries['short'],
            'medium': summaries['medium'],
            'long': summaries['long'],
            'created_at': datetime.utcnow().isoformat(),
            'model': 'nova-lite'
        }
        
        # Store in DynamoDB
        summaries_table.put_item(Item=summary_record)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'summaryId': summary_id,
                'pmid': pmid,
                'summaries': {
                    'short': summaries['short'],
                    'medium': summaries['medium'],
                    'long': summaries['long']
                }
            })
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }