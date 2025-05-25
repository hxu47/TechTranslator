# main lambda - FIXED VERSION
import json
import boto3
import os
import uuid
from datetime import datetime
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients  
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
lambda_client = boto3.client('lambda')
sagemaker_runtime = boto3.client('sagemaker-runtime')

# Get environment variables
VECTOR_TABLE = os.environ.get('VECTOR_TABLE')
KNOWLEDGE_BUCKET = os.environ.get('KNOWLEDGE_BUCKET')
CONVERSATION_FUNCTION = os.environ.get('CONVERSATION_FUNCTION')
SAGEMAKER_ENDPOINT = os.environ.get('SAGEMAKER_ENDPOINT')

# CORS headers for API Gateway integration
CORS_HEADERS = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET',
    'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'
}

def lambda_handler(event, context):
    """Main Lambda function - Enhanced with better context handling"""
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Parse request body
        body = json.loads(event.get('body', '{}')) if event.get('body') else {}
        query = body.get('query', '')
        conversation_id = body.get('conversation_id')
        
        # Extract user ID from Cognito authorizer if available
        user_id = 'anonymous'
        if event.get('requestContext') and event.get('requestContext').get('authorizer'):
            user_id = event.get('requestContext').get('authorizer').get('claims', {}).get('sub', 'anonymous')
        
        if not query:
            return {
                'statusCode': 400,
                'headers': CORS_HEADERS,
                'body': json.dumps({'error': 'Query is required'})
            }
        
        logger.info(f"Processing query: {query} for user: {user_id}")
        
        # Check if SageMaker endpoint is configured
        if not SAGEMAKER_ENDPOINT or SAGEMAKER_ENDPOINT in ['', 'NOT_CONFIGURED', 'PLACEHOLDER']:
            logger.error("SageMaker endpoint not configured")
            return {
                'statusCode': 503,
                'headers': CORS_HEADERS,
                'body': json.dumps({
                    'error': 'AI service temporarily unavailable',
                    'message': 'SageMaker endpoint not configured. Please deploy the model first.',
                    'concept': 'unknown',
                    'audience': 'general'
                })
            }
        
        # Get conversation history to check for context
        conversation_context = get_conversation_context(user_id, conversation_id) if conversation_id else None
        logger.info(f"Conversation context: {conversation_context}")
        
        # Determine if this is a follow-up question
        is_follow_up = is_follow_up_question(query, conversation_context)
        logger.info(f"Is follow-up question: {is_follow_up}")
        
        # Extract concept and audience
        if is_follow_up and conversation_context:
            # For follow-up questions, preserve the previous context
            concept = conversation_context.get('concept', 'unknown')
            audience = conversation_context.get('audience', 'general')
            logger.info(f"Using preserved context - Concept: {concept}, Audience: {audience}")
        else:
            # For new questions, extract concept and audience
            concept_and_audience = extract_concept_and_audience(query)
            concept = concept_and_audience['concept']
            audience = concept_and_audience['audience']
            logger.info(f"Extracted new context - Concept: {concept}, Audience: {audience}")
        
        # Skip processing if concept is unknown and it's not in our knowledge base
        if concept == 'unknown':
            return {
                'statusCode': 200,
                'headers': CORS_HEADERS,
                'body': json.dumps({
                    'query': query,
                    'response': "I'm sorry, but I can only explain data science and machine learning concepts related to insurance, such as R-squared, loss ratio, and predictive models. Could you please ask about one of these topics?",
                    'concept': 'unknown',
                    'audience': audience,
                    'conversation_id': conversation_id or str(uuid.uuid4())
                })
            }
        
        # Get relevant context from DynamoDB
        relevant_chunks = get_relevant_context(concept, audience)
        logger.info(f"Retrieved {len(relevant_chunks)} relevant chunks")
        
        # Generate response using SageMaker
        response = generate_response_with_sagemaker(query, {'concept': concept, 'audience': audience}, relevant_chunks, is_follow_up)
        logger.info("Generated response using SageMaker")
        
        # Store conversation
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
        
        store_conversation(user_id, conversation_id, query, response, concept, audience)
        logger.info(f"Stored conversation: {conversation_id}")
        
        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': json.dumps({
                'query': query,
                'response': response,
                'concept': concept,
                'audience': audience,
                'conversation_id': conversation_id
            })
        }
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': CORS_HEADERS,
            'body': json.dumps({'error': f'Internal server error: {str(e)}'})
        }

def extract_concept_and_audience(query):
    """Extract concept and audience from user query - IMPROVED"""
    query_lower = query.lower()
    
    # Concept mapping - more comprehensive
    concept_keywords = {
        'r-squared': ['r squared', 'r-squared', 'r2', 'coefficient of determination', 'r square'],
        'loss-ratio': ['loss ratio', 'claims ratio', 'incurred losses', 'loss ratios'],
        'predictive-model': ['predictive model', 'prediction model', 'machine learning', 'ml model', 'models', 'modeling', 'algorithm']
    }
    
    detected_concept = None
    for concept_id, keywords in concept_keywords.items():
        if any(keyword in query_lower for keyword in keywords):
            detected_concept = concept_id
            break
    
    # IMPORTANT: Don't default to anything - return 'unknown' if no match
    if not detected_concept:
        detected_concept = 'unknown'
    
    # Audience mapping - more comprehensive
    audience_keywords = {
        'underwriter': ['underwriter', 'underwriting', 'underwriters'],
        'actuary': ['actuary', 'actuarial', 'actuaries'],
        'executive': ['executive', 'ceo', 'manager', 'leadership', 'executives', 'management']
    }
    
    detected_audience = None
    for audience_id, keywords in audience_keywords.items():
        if any(keyword in query_lower for keyword in keywords):
            detected_audience = audience_id
            break
    
    if not detected_audience:
        detected_audience = 'general'
    
    return {'concept': detected_concept, 'audience': detected_audience}

def is_follow_up_question(query, conversation_context):
    """Determine if this is a follow-up question"""
    if not conversation_context:
        return False
    
    query_lower = query.lower()
    
    # Follow-up indicators
    follow_up_patterns = [
        'example', 'more', 'explain', 'tell me more', 'what about', 'can you', 'how about',
        'why', 'how', 'when', 'where', 'give me', 'show me', 'another', 'different',
        'what if', 'suppose', 'imagine', 'consider', 'think about', 'elaborate',
        'important', 'matter', 'significant', 'relevant', 'useful', 'helpful'
    ]
    
    # Check if query contains follow-up patterns and is relatively short
    has_follow_up_pattern = any(pattern in query_lower for pattern in follow_up_patterns)
    is_short = len(query.split()) <= 10  # Short questions are more likely to be follow-ups
    
    # Check if query does NOT contain concept keywords (strong indicator of follow-up)
    concept_keywords = ['r squared', 'r-squared', 'loss ratio', 'predictive model', 'machine learning']
    has_concept_keywords = any(keyword in query_lower for keyword in concept_keywords)
    
    return has_follow_up_pattern and (is_short or not has_concept_keywords)

def get_conversation_context(user_id, conversation_id):
    """Get the last concept/audience from conversation history"""
    if not conversation_id:
        return None
    
    try:
        # Call conversation Lambda to get history
        payload = {
            'action': 'get',
            'user_id': user_id,
            'conversation_id': conversation_id
        }
        
        response = lambda_client.invoke(
            FunctionName=CONVERSATION_FUNCTION,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        result = json.loads(response['Payload'].read())
        
        if result.get('statusCode') == 200 and result.get('conversations'):
            conversations = result['conversations']
            if conversations:
                # Get the most recent conversation entry with concept info
                for conv in sorted(conversations, key=lambda x: x.get('timestamp', ''), reverse=True):
                    if conv.get('concept') and conv.get('concept') != 'unknown':
                        return {
                            'concept': conv.get('concept'),
                            'audience': conv.get('audience', 'general')
                        }
        
        return None
        
    except Exception as e:
        logger.error(f"Error getting conversation context: {str(e)}")
        return None

def get_relevant_context(concept, audience, max_items=5):
    """Get relevant context from DynamoDB"""
    try:
        table = dynamodb.Table(VECTOR_TABLE)
        
        # Query by concept_id
        response = table.query(
            KeyConditionExpression="concept_id = :concept_id",
            ExpressionAttributeValues={":concept_id": concept},
            Limit=max_items
        )
        
        items = response.get('Items', [])
        
        # Prioritize audience-specific content
        audience_items = [item for item in items if item.get('audience') == audience]
        other_items = [item for item in items if item.get('audience') != audience]
        
        # Return audience-specific first, then others
        prioritized_items = audience_items + other_items
        
        # Convert to the format expected by generate_response_with_sagemaker
        return [{'item': item, 'similarity': 1.0} for item in prioritized_items[:max_items]]
        
    except Exception as e:
        logger.error(f"Error getting context: {str(e)}")
        return []

def generate_response_with_sagemaker(query, concept_and_audience, relevant_chunks, is_follow_up=False):
    """Generate response using SageMaker FLAN-T5 endpoint - ENHANCED"""
    try:
        concept = concept_and_audience['concept']
        audience = concept_and_audience['audience']
        
        # Create context from relevant chunks
        context_text = ""
        for chunk in relevant_chunks[:3]:  # Use top 3 chunks
            context_text += f"- {chunk['item']['text'][:300]}...\n"
        
        # Create different prompts for new questions vs follow-ups
        if is_follow_up and context_text.strip():
            # For follow-ups, be more specific about continuing the conversation
            prompt = f"""You are continuing a conversation about {concept.replace('-', ' ')} for an insurance {audience}.

Previous context:
{context_text}

Follow-up question: {query}

Provide a helpful follow-up response that builds on the previous information:"""
        elif context_text.strip():
            # For new questions with context
            prompt = f"""Based on the following information, explain {concept.replace('-', ' ')} to an insurance {audience}.

Context:
{context_text}

Question: {query}

Provide a clear, professional explanation for an insurance {audience}:"""
        else:
            # Fallback prompt if no context found
            prompt = f"""Explain {concept.replace('-', ' ')} to an insurance {audience}.

Question: {query}

Provide a clear, professional explanation:"""
        
        # Prepare payload for SageMaker
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 200,  # Increased for better responses
                "temperature": 0.7,
                "do_sample": True,
                "top_p": 0.9,
                "repetition_penalty": 1.1,
            }
        }
        
        logger.info(f"Calling SageMaker endpoint: {SAGEMAKER_ENDPOINT}")
        
        # Call SageMaker endpoint
        response = sagemaker_runtime.invoke_endpoint(
            EndpointName=SAGEMAKER_ENDPOINT,
            ContentType='application/json',
            Body=json.dumps(payload)
        )
        
        result = json.loads(response['Body'].read().decode())
        
        # Handle FLAN-T5 response format
        if isinstance(result, list) and len(result) > 0:
            if isinstance(result[0], dict):
                generated_text = result[0].get('generated_text', '')
            else:
                generated_text = str(result[0])
        elif isinstance(result, dict):
            generated_text = result.get('generated_text', '')
        else:
            generated_text = str(result)
        
        # Clean up the response
        generated_text = generated_text.strip()
        
        # Fallback if response is too short
        if not generated_text or len(generated_text) < 20:
            logger.warning("SageMaker response too short, using fallback")
            return create_fallback_response(concept_and_audience, relevant_chunks)
        
        return generated_text
        
    except Exception as e:
        logger.error(f"SageMaker generation error: {str(e)}")
        # Return fallback response
        return create_fallback_response(concept_and_audience, relevant_chunks)

def create_fallback_response(concept_and_audience, relevant_chunks):
    """Create a structured fallback response using retrieved context"""
    concept = concept_and_audience['concept'].replace('-', ' ').title()
    audience = concept_and_audience['audience']
    
    if not relevant_chunks:
        return f"I would be happy to explain {concept} for insurance {audience}s, but I could not find specific information in my knowledge base. Please try rephrasing your question."
    
    # Use the best matching chunk
    best_chunk = relevant_chunks[0]['item']
    
    response = f"**{concept} for Insurance {audience.title()}s**\n\n"
    
    # Add the most relevant information
    if best_chunk.get('audience') == audience:
        # Perfect match for audience
        response += best_chunk['text']
    else:
        # Use available information
        response += best_chunk.get('text', 'Information not available')
    
    return response

def store_conversation(user_id, conversation_id, query, response, concept, audience):
    """Store conversation in DynamoDB via the Conversation Lambda"""
    try:
        payload = {
            'action': 'store',
            'user_id': user_id,
            'conversation_id': conversation_id,
            'query': query,
            'response': response,
            'concept': concept,
            'audience': audience
        }
        
        response = lambda_client.invoke(
            FunctionName=CONVERSATION_FUNCTION,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        return json.loads(response['Payload'].read())
    except Exception as e:
        logger.error(f"Error storing conversation: {str(e)}")
        # Don't fail the main request if conversation storage fails
        return None