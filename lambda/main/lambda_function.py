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

# Get environment variables
VECTOR_TABLE = os.environ.get('VECTOR_TABLE')
KNOWLEDGE_BUCKET = os.environ.get('KNOWLEDGE_BUCKET')
CONVERSATION_FUNCTION = os.environ.get('CONVERSATION_FUNCTION')

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
        
        # Step 1: Extract concept and audience from query using prompt engineering
        # (In a real implementation, this would call an LLM API)
        concept_and_audience = extract_concept_and_audience(query)
        concept = concept_and_audience['concept']
        audience = concept_and_audience['audience']
        
        logger.info(f"Extracted concept: {concept}, audience: {audience}")
        
        # Step 2: Retrieve relevant information from knowledge base
        relevant_info = retrieve_information(concept)
        
        logger.info(f"Retrieved information for {concept}")
        
        # Step 3: Generate the response
        # (In a real implementation, this would call an LLM API with retrieved context)
        response = generate_response(query, concept_and_audience, relevant_info)
        
        logger.info("Generated response")
        
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
            'body': json.dumps({'error': str(e)})
        }

# CORS headers for API Gateway integration
CORS_HEADERS = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET',
    'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'
}

def extract_concept_and_audience(query):
    """
    Mock function to extract concept and audience from query
    In a real implementation, this would use prompt engineering with an LLM
    """
    # Simple extraction based on query text
    # In a real implementation, this would use an LLM for more sophisticated extraction
    lower_query = query.lower()
    
    concept = 'data science'
    if 'r-squared' in lower_query:
        concept = 'r-squared'
    elif 'loss ratio' in lower_query:
        concept = 'loss ratio'
    elif 'model' in lower_query:
        concept = 'predictive model'
    
    audience = 'general'
    if 'underwriter' in lower_query:
        audience = 'underwriter'
    elif 'actuary' in lower_query:
        audience = 'actuary'
    elif 'ceo' in lower_query or 'executive' in lower_query:
        audience = 'executive'
    
    return {'concept': concept, 'audience': audience}

def retrieve_information(concept):
    """
    Function to retrieve relevant information from knowledge base
    In a real implementation, this would use vector search and RAG techniques
    """
    # Mock implementation - in a real system, this would retrieve from S3 and vector DB
    knowledge_base = {
        'r-squared': {
            'definition': 'R-squared is a statistical measure that represents the proportion of the variance for a dependent variable that\'s explained by an independent variable.',
            'insurance_context': 'In insurance pricing, R-squared helps actuaries understand how well factors like age, location, or claim history explain premium variations.',
            'examples': {
                'underwriter': 'If your pricing model has an R-squared of 0.75, it means that 75% of the premium variation is explained by the factors in your model.',
                'executive': 'An R-squared of 0.8 means our pricing model captures 80% of what drives premium differences, indicating a strong predictive model.',
                'actuary': 'When comparing GLMs for pricing, the model with higher R-squared (all else being equal) is explaining more of the variance in loss ratios across segments.'
            }
        },
        'loss ratio': {
            'definition': 'Loss ratio is the ratio of total losses paid out in claims plus adjustment expenses divided by the total earned premiums.',
            'insurance_context': 'It\'s a key metric to evaluate the profitability of an insurance product or line of business.',
            'examples': {
                'underwriter': 'If you're seeing a loss ratio of 85% in a particular segment, you may need to consider rate adjustments or tighter underwriting guidelines.',
                'executive': 'A loss ratio trend that increases from 60% to 70% over three quarters may signal emerging profitability challenges that require attention.',
                'actuary': 'When modeling loss ratios, we need to consider both frequency and severity trends, as well as large claim volatility and development patterns.'
            }
        },
        'predictive model': {
            'definition': 'A predictive model is a statistical algorithm that uses historical data to predict future outcomes.',
            'insurance_context': 'In insurance, predictive models help estimate the likelihood of claims, premium adequacy, and customer behavior.',
            'examples': {
                'underwriter': 'The predictive model flagged this application with a high-risk score based on its similarity to previous policies that had high claim frequencies.',
                'executive': 'Our new customer retention predictive model has improved retention by 5% by identifying at-risk policies before renewal.',
                'actuary': 'This predictive model uses generalized linear modeling techniques with a logarithmic link function to handle the skewed distribution of claim amounts.'
            }
        },
        'data science': {
            'definition': 'Data science is an interdisciplinary field that uses scientific methods, processes, algorithms and systems to extract knowledge from data.',
            'insurance_context': 'In insurance, data science combines statistical modeling, machine learning, and domain expertise to improve pricing, underwriting, and claims handling.',
            'examples': {
                'underwriter': 'Data science tools help you identify patterns in applications that might indicate higher risk but wouldn't be obvious from traditional underwriting guidelines.',
                'executive': 'Our data science initiatives reduced claims leakage by 12% last year by identifying patterns of potentially fraudulent claims.',
                'actuary': 'We're using data science techniques like natural language processing to extract insights from adjuster notes and improve our reserving models.'
            }
        }
    }
    
    return knowledge_base.get(concept, {
        'definition': 'General data science concept',
        'insurance_context': 'Data science is widely used in insurance',
        'examples': {
            'underwriter': 'Data science helps underwriters assess risk',
            'executive': 'Data science improves business outcomes',
            'actuary': 'Data science enhances actuarial modeling',
            'general': 'Data science is used to analyze patterns in data'
        }
    })

def generate_response(query, concept_and_audience, relevant_info):
    """
    Function to generate a response based on the query, concept, audience, and retrieved information
    In a real implementation, this would use prompt engineering with an LLM
    """
    concept = concept_and_audience['concept']
    audience = concept_and_audience['audience']
    
    # In a real implementation, this would use an LLM API call with a carefully crafted prompt
    # For this implementation, we'll create a template-based response
    
    audience_specific = relevant_info.get('examples', {}).get(audience, 
                                           relevant_info.get('examples', {}).get('general', ''))
    
    response = f"""
{relevant_info.get('definition', '')}

In the insurance industry: {relevant_info.get('insurance_context', '')}

Specifically for {audience}s: {audience_specific}
    """
    
    return response.strip()

def store_conversation(user_id, conversation_id, query, response, concept, audience):
    """
    Function to store conversation in DynamoDB via the Conversation Lambda
    """
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
        logger.error(f"Error storing conversation: {str(e)}", exc_info=True)
        raise e