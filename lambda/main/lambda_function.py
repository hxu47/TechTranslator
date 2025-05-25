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


def is_follow_up_question(query, conversation_context):
    """Enhanced follow-up detection with better logic"""
    if not conversation_context:
        return False
    
    query_lower = query.lower().strip()
    
    # Strong follow-up indicators
    strong_follow_up_patterns = [
        'example', 'give me an example', 'can you give', 'show me',
        'what does it mean', 'what does that mean', 'explain that',
        'tell me more', 'more about', 'elaborate', 'expand on',
        'how about', 'what about', 'what if', 'suppose',
        'why', 'how', 'when', 'where'
    ]
    
    # Context continuation patterns
    context_patterns = [
        'if r-squared is', 'when r-squared', 'r-squared of',
        'if loss ratio', 'when loss ratio', 'loss ratio of',
        'if the model', 'when the model', 'the model',
        'that means', 'it means', 'this means'
    ]
    
    # Check for strong follow-up patterns
    has_strong_follow_up = any(pattern in query_lower for pattern in strong_follow_up_patterns)
    
    # Check for context continuation (questions that build on the topic)
    has_context_continuation = any(pattern in query_lower for pattern in context_patterns)
    
    # Check if it's a short question (likely follow-up)
    is_short_question = len(query.split()) <= 12
    
    # Check if query does NOT contain full concept keywords (strong indicator of follow-up)
    full_concept_keywords = [
        'what is r-squared', 'explain r-squared', 'r-squared for',
        'what is loss ratio', 'explain loss ratio', 'loss ratio for',
        'what is predictive model', 'explain predictive model', 'predictive model for'
    ]
    has_full_concept_intro = any(keyword in query_lower for keyword in full_concept_keywords)
    
    # Decision logic
    if has_strong_follow_up:
        return True
    elif has_context_continuation and is_short_question:
        return True
    elif is_short_question and not has_full_concept_intro:
        return True
    
    return False

def generate_response_with_sagemaker(query, concept_and_audience, relevant_chunks, is_follow_up=False):
    """Enhanced response generation with better prompting"""
    try:
        concept = concept_and_audience['concept']
        audience = concept_and_audience['audience']
        
        # Create context from relevant chunks - prioritize audience-specific content
        audience_chunks = [chunk for chunk in relevant_chunks if chunk['item'].get('audience') == audience]
        other_chunks = [chunk for chunk in relevant_chunks if chunk['item'].get('audience') != audience]
        
        prioritized_chunks = audience_chunks + other_chunks
        
        context_text = ""
        for chunk in prioritized_chunks[:3]:  # Use top 3 chunks
            context_text += f"- {chunk['item']['text'][:400]}...\n"
        
        # Create more specific prompts
        if is_follow_up and context_text.strip():
            # For follow-ups, create very specific prompts based on the question type
            if any(word in query.lower() for word in ['example', 'give me', 'show me']):
                prompt = f"""You are explaining {concept.replace('-', ' ')} to an insurance {audience}. The user is asking for an example.

Context about {concept.replace('-', ' ')}:
{context_text}

User's request: {query}

Provide a specific, practical example of {concept.replace('-', ' ')} that an insurance {audience} would encounter in their work. Include numbers and realistic scenarios:"""
            
            elif any(word in query.lower() for word in ['what does it mean', 'means', 'explain']):
                prompt = f"""You are continuing to explain {concept.replace('-', ' ')} to an insurance {audience}.

Context:
{context_text}

User's question: {query}

Provide a clear explanation that builds on what was already discussed about {concept.replace('-', ' ')} for an insurance {audience}:"""
            
            elif 'if' in query.lower() or 'when' in query.lower():
                prompt = f"""You are explaining {concept.replace('-', ' ')} scenarios to an insurance {audience}.

Context:
{context_text}

User's scenario question: {query}

Explain what this scenario means for an insurance {audience} in practical terms:"""
            
            else:
                # General follow-up
                prompt = f"""Continue explaining {concept.replace('-', ' ')} to an insurance {audience}.

Previous context:
{context_text}

Follow-up question: {query}

Provide a helpful response that builds on the previous discussion:"""
        
        elif context_text.strip():
            # For new questions with context
            prompt = f"""Explain {concept.replace('-', ' ')} to an insurance {audience} based on this information:

Context:
{context_text}

Question: {query}

Provide a clear, professional explanation tailored for an insurance {audience}:"""
        else:
            # Fallback prompt
            prompt = f"""Explain {concept.replace('-', ' ')} to an insurance {audience}.

Question: {query}

Provide a clear, professional explanation:"""
        
        # Adjust parameters for better responses
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 250,  # Increased for more detailed responses
                "temperature": 0.6,     # Slightly lower for more focused responses
                "do_sample": True,
                "top_p": 0.85,         # Slightly lower for more focused responses
                "repetition_penalty": 1.2,  # Higher to avoid repetition
            }
        }
        
        logger.info(f"Calling SageMaker with follow_up={is_follow_up}")
        logger.info(f"Prompt preview: {prompt[:200]}...")
        
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
        
        # Enhanced fallback with more specific responses
        if not generated_text or len(generated_text) < 20:
            logger.warning("SageMaker response too short, using enhanced fallback")
            return create_enhanced_fallback_response(query, concept_and_audience, relevant_chunks, is_follow_up)
        
        return generated_text
        
    except Exception as e:
        logger.error(f"SageMaker generation error: {str(e)}")
        return create_enhanced_fallback_response(query, concept_and_audience, relevant_chunks, is_follow_up)

def create_enhanced_fallback_response(query, concept_and_audience, relevant_chunks, is_follow_up=False):
    """Create more specific fallback responses"""
    concept = concept_and_audience['concept'].replace('-', ' ').title()
    audience = concept_and_audience['audience']
    
    if not relevant_chunks:
        return f"I'd be happy to explain {concept} for insurance {audience}s, but I need more specific information. Could you ask about a particular aspect of {concept}?"
    
    # Find the best matching chunk
    audience_chunks = [chunk for chunk in relevant_chunks if chunk['item'].get('audience') == audience]
    best_chunk = audience_chunks[0] if audience_chunks else relevant_chunks[0]
    
    query_lower = query.lower()
    
    # Provide specific responses based on query type
    if 'example' in query_lower:
        if concept.lower() == 'r-squared':
            return f"Here's an example for {audience}s: If your pricing model has an R-squared of 0.75, it means 75% of premium variation is explained by your risk factors like age, location, and claims history. The remaining 25% represents unexplained variation that could indicate missing risk factors."
        elif 'loss ratio' in concept.lower():
            return f"Example for {audience}s: If your book has a 65% loss ratio, you're paying $65 in claims for every $100 in premiums collected. With a 30% expense ratio, your combined ratio would be 95%, indicating a 5% underwriting profit."
        else:
            return best_chunk['item']['text'][:300] + "..."
    
    elif any(word in query_lower for word in ['what does it mean', 'means']):
        return f"For insurance {audience}s: " + best_chunk['item']['text'][:250] + "..."
    
    else:
        # General response
        response = f"**{concept} for Insurance {audience.title()}s**\n\n"
        response += best_chunk['item']['text'][:400]
        return response

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