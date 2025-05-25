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





def generate_response_with_sagemaker(query, concept_and_audience, relevant_chunks, is_follow_up=False):
    """FLAN-T5 optimized response generation with simple prompts"""
    try:
        concept = concept_and_audience['concept']
        audience = concept_and_audience['audience']
        
        # Get the best context chunk for this audience
        audience_chunks = [chunk for chunk in relevant_chunks if chunk['item'].get('audience') == audience]
        best_chunk = audience_chunks[0] if audience_chunks else (relevant_chunks[0] if relevant_chunks else None)
        
        # Create VERY simple prompts that FLAN-T5 can handle
        if is_follow_up and best_chunk:
            context = best_chunk['item']['text'][:400]  # Keep context shorter
            
            # Simple follow-up prompts based on question type
            if any(word in query.lower() for word in ['example', 'give me']):
                prompt = f"Context: {context}\n\nQuestion: Give a specific example of {concept.replace('-', ' ')} for insurance {audience}s.\n\nAnswer:"
                
            elif 'what does it mean' in query.lower() or 'means' in query.lower():
                prompt = f"Context: {context}\n\nQuestion: {query}\n\nAnswer:"
                
            elif any(word in query.lower() for word in ['if ', 'when ', 'suppose']):
                # For scenario questions like "If R-squared is 0"
                prompt = f"Question: In insurance, {query.lower()}\n\nContext: {context}\n\nAnswer:"
                
            else:
                # General follow-up - keep it very simple
                prompt = f"Context: {context}\n\nQuestion: {query}\n\nAnswer:"
        
        elif best_chunk:
            # New question with context - use simple format
            context = best_chunk['item']['text'][:400]
            prompt = f"Context: {context}\n\nQuestion: {query}\n\nAnswer:"
            
        else:
            # No context - very simple prompt
            prompt = f"Question: Explain {concept.replace('-', ' ')} for insurance {audience}s.\n\nAnswer:"
        
        # Simpler parameters for FLAN-T5
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 150,  # Shorter responses work better
                "temperature": 0.3,     # Lower temperature for more focused responses
                "do_sample": True,
                "top_p": 0.8,
                "repetition_penalty": 1.3,  # Higher to avoid repetition
            }
        }
        
        logger.info(f"FLAN-T5 Simple Prompt: {prompt[:150]}...")
        
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
        
        # If response is too short or generic, use fallback
        if not generated_text or len(generated_text) < 15 or generated_text.lower().startswith('the model'):
            logger.warning("Using enhanced fallback for better response")
            return create_smart_fallback_response(query, concept_and_audience, best_chunk, is_follow_up)
        
        return generated_text
        
    except Exception as e:
        logger.error(f"SageMaker generation error: {str(e)}")
        return create_smart_fallback_response(query, concept_and_audience, relevant_chunks[0] if relevant_chunks else None, is_follow_up)

def create_smart_fallback_response(query, concept_and_audience, best_chunk, is_follow_up=False):
    """Create intelligent fallback responses using the knowledge base directly"""
    concept = concept_and_audience['concept']
    audience = concept_and_audience['audience']
    query_lower = query.lower()
    
    if not best_chunk:
        return f"I can explain {concept.replace('-', ' ')} concepts, but I need more specific information. Could you ask about a particular aspect?"
    
    chunk_text = best_chunk['item']['text']
    chunk_type = best_chunk['item'].get('type', 'general')
    
    # Handle specific question types with direct knowledge base responses
    if 'example' in query_lower:
        # Look for example chunks or create examples from context
        if chunk_type == 'example':
            return chunk_text
        else:
            # Create specific examples based on concept
            if concept == 'r-squared':
                if audience == 'underwriter':
                    return "Here's an example for underwriters: If your pricing model has an R-squared of 0.75, it means 75% of the premium variation is explained by factors like driver age, vehicle type, and claims history. The remaining 25% represents unexplained variation - possibly missing risk factors that competitors might be capturing."
                elif audience == 'actuary':
                    return "Example for actuaries: When comparing GLMs for homeowners insurance, Model A has R-squared of 0.68 while Model B has 0.72. Model B explains 4% more variance in loss costs, suggesting better factor selection. However, check if the improvement is statistically significant and not due to overfitting."
                else:
                    return "Example: An auto insurance pricing model with R-squared of 0.80 means that 80% of premium differences between policies are explained by rating factors like age, location, and driving record. Higher R-squared generally indicates a more predictive model."
                    
            elif concept == 'loss-ratio':
                if audience == 'underwriter':
                    return "Example for underwriters: Your book shows a 75% loss ratio. For every $100 in premiums, you're paying $75 in claims. With a 25% expense ratio, your combined ratio is 100% - you're breaking even on underwriting. Consider rate increases or tighter guidelines."
                elif audience == 'executive':
                    return "Example for executives: Q3 loss ratio increased from 62% to 68%. This 6-point increase on $50M premiums means an additional $3M in claims costs, directly impacting profitability. Root causes might include claims inflation, adverse selection, or competitive pricing pressure."
                else:
                    return "Example: A commercial auto line with 85% loss ratio and 20% expense ratio has a 105% combined ratio, indicating a 5% underwriting loss. This means the insurer pays out more in claims and expenses than it collects in premiums."
            
            elif concept == 'predictive-model':
                return "Example: A fraud detection model flags 5% of claims for investigation, catching 80% of fraudulent claims while minimizing false positives. This helps reduce loss ratios by 2-3 percentage points compared to random sampling."
    
    elif any(phrase in query_lower for phrase in ['what does it mean', 'means', 'if ', 'when ']):
        # For scenario/meaning questions, be very specific
        if 'if r-squared is 0' in query_lower:
            return f"If R-squared is 0, it means your pricing model explains none of the variation in {['claims costs', 'premiums', 'losses'][0]}. Essentially, your rating factors (age, location, etc.) have no predictive power - you might as well price everyone the same. This indicates you need better rating factors or a different modeling approach."
        
        elif 'if r-squared is 1' in query_lower:
            return f"If R-squared is 1, your model perfectly predicts {['claims', 'outcomes', 'results'][0]} - which is theoretically impossible in insurance due to random variation. In practice, R-squared above 0.9 might indicate overfitting, where your model memorized training data but won't perform well on new policies."
        
        elif 'loss ratio' in query_lower and any(word in query_lower for word in ['high', 'low', 'good', 'bad']):
            return f"For insurance {audience}s: Loss ratios below 60% are typically very good, 60-75% are acceptable, 75-85% need attention, and above 85% indicate problems. However, this varies by line of business - workers' comp might target 65% while personal auto might target 70%."
    
    # Default: use the best available chunk, formatted for the audience
    if chunk_type == 'audience' and best_chunk['item'].get('audience') == audience:
        # Perfect match - return the audience-specific content
        return chunk_text
    else:
        # General content - add audience context
        return f"For insurance {audience}s: {chunk_text[:300]}..."

# Also update the follow-up detection to be more precise
def is_follow_up_question(query, conversation_context):
    """Simplified follow-up detection optimized for FLAN-T5"""
    if not conversation_context:
        return False
    
    query_lower = query.lower().strip()
    
    # Very specific follow-up patterns that work well with simple prompts
    definite_follow_ups = [
        'example', 'give me an example', 'can you give me', 'show me',
        'what does it mean', 'what does that mean', 'what if', 'if ',
        'why', 'how', 'when', 'where', 'tell me more', 'more about'
    ]
    
    # Short questions are likely follow-ups
    is_short = len(query.split()) <= 8
    
    # Contains follow-up patterns
    has_follow_up_pattern = any(pattern in query_lower for pattern in definite_follow_ups)
    
    # Doesn't contain new concept introduction
    new_concept_patterns = ['what is', 'explain ', 'tell me about', 'describe']
    has_new_concept = any(pattern in query_lower for pattern in new_concept_patterns)
    
    # Decision: follow-up if it has follow-up patterns OR is short without new concept introduction
    return has_follow_up_pattern or (is_short and not has_new_concept)



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