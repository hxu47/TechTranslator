import json
import boto3
import os
import uuid
from datetime import datetime
import logging
from sentence_transformers import SentenceTransformer
from scipy.spatial.distance import cosine
import numpy as np

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

# Initialize sentence transformer model (lazy loading for cold start optimization)
model = None

def get_model():
    """Lazy load the sentence transformer model"""
    global model
    if model is None:
        logger.info("Loading sentence transformer model...")
        model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("Model loaded successfully")
    return model

def lambda_handler(event, context):
    """
    Main Lambda function for the TechTranslator application
    Handles prompt engineering, context retrieval, and response generation
    """
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
        if not SAGEMAKER_ENDPOINT:
            logger.error("SAGEMAKER_ENDPOINT environment variable not set")
            return {
                'statusCode': 500,
                'headers': CORS_HEADERS,
                'body': json.dumps({'error': 'SageMaker endpoint not configured'})
            }
        
        # Step 1: Extract concept and audience from query using prompt engineering
        concept_and_audience = extract_concept_and_audience(query)
        concept = concept_and_audience['concept']
        audience = concept_and_audience['audience']
        
        logger.info(f"Extracted concept: {concept}, audience: {audience}")
        
        # Step 2: Retrieve relevant information using RAG
        relevant_chunks = vector_search(query, concept)
        
        logger.info(f"Retrieved {len(relevant_chunks)} relevant chunks")
        
        # Step 3: Generate the response using SageMaker
        response = generate_response_with_sagemaker(query, concept_and_audience, relevant_chunks)
        
        logger.info("Generated response using SageMaker")
        
        # Step 4: Store conversation
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
        
        store_conversation(user_id, conversation_id, query, response, concept, audience)
        
        logger.info(f"Stored conversation: {conversation_id}")
        
        # Return the response
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

# CORS headers for API Gateway integration
CORS_HEADERS = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET',
    'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'
}

def extract_concept_and_audience(query):
    """Extract concept and audience from user query"""
    query_lower = query.lower()
    
    # Concept mapping
    concept_keywords = {
        'r-squared': ['r squared', 'r-squared', 'r2', 'coefficient of determination'],
        'loss-ratio': ['loss ratio', 'claims ratio', 'incurred losses'],
        'predictive-model': ['predictive model', 'prediction model', 'machine learning', 'ml model']
    }
    
    detected_concept = None
    for concept_id, keywords in concept_keywords.items():
        if any(keyword in query_lower for keyword in keywords):
            detected_concept = concept_id
            break
    
    if not detected_concept:
        detected_concept = 'predictive-model'  # Default
    
    # Audience mapping
    audience_keywords = {
        'underwriter': ['underwriter', 'underwriting'],
        'actuary': ['actuary', 'actuarial', 'actuaries'],
        'executive': ['executive', 'ceo', 'manager', 'leadership']
    }
    
    detected_audience = None
    for audience_id, keywords in audience_keywords.items():
        if any(keyword in query_lower for keyword in keywords):
            detected_audience = audience_id
            break
    
    if not detected_audience:
        detected_audience = 'general'
    
    return {'concept': detected_concept, 'audience': detected_audience}

def vector_search(query, concept_id=None, top_k=5):
    """Perform vector search on stored embeddings"""
    try:
        # Get the model
        embedding_model = get_model()
        
        # Generate query embedding
        query_embedding = embedding_model.encode(query)
        
        # Query DynamoDB
        table = dynamodb.Table(VECTOR_TABLE)
        
        if concept_id:
            logger.info(f"Searching in concept: {concept_id}")
            response = table.query(
                KeyConditionExpression="concept_id = :concept_id",
                ExpressionAttributeValues={":concept_id": concept_id}
            )
        else:
            logger.info("Searching across all concepts")
            response = table.scan()
        
        items = response.get('Items', [])
        logger.info(f"Found {len(items)} items to search")
        
        if not items:
            return []
        
        # Calculate similarities
        results = []
        for item in items:
            try:
                # Parse stored embedding
                stored_embedding = json.loads(item['embedding'])
                
                # Calculate cosine similarity
                similarity = 1 - cosine(query_embedding, stored_embedding)
                
                results.append({
                    'item': item,
                    'similarity': similarity
                })
            except Exception as e:
                logger.warning(f"Error processing item {item.get('vector_id', 'unknown')}: {str(e)}")
                continue
        
        # Sort by similarity (highest first)
        results.sort(key=lambda x: x['similarity'], reverse=True)
        
        return results[:top_k]
        
    except Exception as e:
        logger.error(f"Vector search error: {str(e)}")
        return []

def generate_response_with_sagemaker(query, concept_and_audience, relevant_chunks):
    """Generate response using SageMaker FLAN-T5 endpoint"""
    try:
        concept = concept_and_audience['concept']
        audience = concept_and_audience['audience']
        
        # Create context from relevant chunks
        context_text = ""
        for chunk in relevant_chunks[:3]:  # Use top 3 chunks
            context_text += f"- {chunk['item']['text'][:200]}...\n"
        
        # Create instruction-style prompt for FLAN-T5
        if context_text.strip():
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
                "max_new_tokens": 150,
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
        
        # Fallback if response is too short or empty
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
        return f"I'd be happy to explain {concept} for insurance {audience}s, but I couldn't find specific information in my knowledge base. Please try rephrasing your question or contact your data science team for more details."
    
    # Use the best matching chunk
    best_chunk = relevant_chunks[0]['item']
    
    response = f"**{concept} for Insurance {audience.title()}s**\n\n"
    
    # Add the most relevant information
    if best_chunk.get('audience') == audience:
        # Perfect match for audience
        response += best_chunk['text']
    else:
        # Find definition and context
        definition = None
        context = None
        audience_explanation = None
        
        for chunk in relevant_chunks:
            item = chunk['item']
            if item['type'] == 'definition' and not definition:
                definition = item['text']
            elif item['type'] == 'context' and not context:
                context = item['text']
            elif item.get('audience') == audience and not audience_explanation:
                audience_explanation = item['text']
        
        if definition:
            response += f"{definition}\n\n"
        if context:
            response += f"In insurance: {context}\n\n"
        if audience_explanation:
            response += f"For {audience}s specifically: {audience_explanation}"
    
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