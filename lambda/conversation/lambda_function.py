# conversation lambda - IMPROVED VERSION
import json
import boto3
import os
import uuid
from datetime import datetime, timedelta
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')

# Get environment variables
CONVERSATION_TABLE = os.environ.get('CONVERSATION_TABLE')

def lambda_handler(event, context):
    """
    Lambda function for managing conversation history - ENHANCED for API Gateway
    Handles both direct invocations and API Gateway requests
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Check if this is an API Gateway request
        if 'httpMethod' in event:
            return handle_api_gateway_request(event, context)
        else:
            return handle_direct_invocation(event, context)
            
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'OPTIONS,GET,POST',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'
            },
            'body': json.dumps({'error': str(e)})
        }

def handle_api_gateway_request(event, context):
    """Handle API Gateway requests (GET /conversation)"""
    try:
        # Extract user ID from Cognito authorizer context
        user_id = extract_user_from_api_gateway_event(event)
        logger.info(f"API Gateway request from user: {user_id}")
        
        # Get query parameters
        query_params = event.get('queryStringParameters') or {}
        conversation_id = query_params.get('conversation_id')
        
        # Get conversation history
        result = get_conversation(user_id, conversation_id)
        
        return {
            'statusCode': result.get('statusCode', 200),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'OPTIONS,GET,POST',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'
            },
            'body': json.dumps({
                'conversations': result.get('conversations', []),
                'user_id': user_id
            })
        }
        
    except Exception as e:
        logger.error(f"API Gateway request error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': str(e)})
        }

def handle_direct_invocation(event, context):
    """Handle direct Lambda invocations (from main Lambda)"""
    # Get action and parameters from the event
    action = event.get('action', 'get')
    user_id = event.get('user_id', 'anonymous')
    conversation_id = event.get('conversation_id')
    query = event.get('query')
    response = event.get('response')
    concept = event.get('concept')
    audience = event.get('audience')
    
    logger.info(f"Direct invocation: {action} request for user: {user_id}, conversation: {conversation_id}")
    
    # Handle the requested action
    if action == 'store':
        return store_conversation(user_id, conversation_id, query, response, concept, audience)
    elif action == 'get':
        return get_conversation(user_id, conversation_id)
    elif action == 'get_context':
        return get_conversation_context(user_id, conversation_id)
    else:
        error_msg = f"Unknown action: {action}"
        logger.error(error_msg)
        return {
            'statusCode': 400,
            'body': json.dumps({'error': error_msg})
        }

def extract_user_from_api_gateway_event(event):
    """Extract user ID from API Gateway Cognito authorizer context"""
    try:
        # Method 1: Try authorizer context
        request_context = event.get('requestContext', {})
        authorizer = request_context.get('authorizer', {})
        
        if authorizer:
            # Check for claims
            claims = authorizer.get('claims', {})
            if claims:
                # Try email first
                email = claims.get('email')
                if email:
                    return email.lower().strip()
                
                # Try cognito:username
                username = claims.get('cognito:username')
                if username:
                    if '@' in username:
                        return username.lower().strip()
                    else:
                        return f"{username}@cognito.local"
                
                # Try sub as last resort
                sub = claims.get('sub')
                if sub:
                    return f"{sub}@cognito.local"
            
            # Check direct fields
            email = authorizer.get('email')
            if email:
                return email.lower().strip()
            
            principal_id = authorizer.get('principalId')
            if principal_id:
                if '@' in principal_id:
                    return principal_id.lower().strip()
                else:
                    return f"{principal_id}@principal.local"
        
        # Fallback: create user ID from source IP
        identity = request_context.get('identity', {})
        source_ip = identity.get('sourceIp', 'unknown')
        if source_ip != 'unknown':
            import hashlib
            session_hash = hashlib.md5(source_ip.encode()).hexdigest()[:12]
            return f"guest_{session_hash}@anonymous.local"
        
        return 'api_gateway_user@anonymous.local'
        
    except Exception as e:
        logger.error(f"Error extracting user from API Gateway event: {str(e)}")
        return 'extraction_failed@anonymous.local'

def store_conversation(user_id, conversation_id, query, response, concept, audience):
    """
    Function to store a conversation in DynamoDB - ENHANCED
    """
    conv_id = conversation_id or str(uuid.uuid4())
    
    # Calculate TTL (30 days from now)
    ttl = int((datetime.now() + timedelta(days=30)).timestamp())
    
    table = dynamodb.Table(CONVERSATION_TABLE)
    
    try:
        # Create a unique sort key for each interaction within a conversation
        interaction_timestamp = datetime.now().isoformat()
        sort_key = f"{conv_id}#{interaction_timestamp}"
        
        item = {
            'user_id': user_id,
            'conversation_id': sort_key,  # Using composite key for better querying
            'base_conversation_id': conv_id,  # Keep the original conversation ID
            'query': query,
            'response': response,
            'concept': concept or 'unknown',
            'audience': audience or 'general',
            'timestamp': interaction_timestamp,
            'ttl': ttl
        }
        
        table.put_item(Item=item)
        logger.info(f"Stored conversation: {conv_id}")
        
        return {
            'statusCode': 200,
            'conversation_id': conv_id,
            'stored_item': item
        }
    except Exception as e:
        logger.error(f"Error storing conversation: {str(e)}", exc_info=True)
        raise e

def get_conversation(user_id, conversation_id):
    """
    Function to retrieve conversation(s) from DynamoDB - ENHANCED
    """
    table = dynamodb.Table(CONVERSATION_TABLE)
    
    try:
        if conversation_id:
            # Get all interactions for a specific conversation
            logger.info(f"Retrieving conversation: {conversation_id}")
            
            # Query using GSI or scan with filter for base_conversation_id
            response = table.scan(
                FilterExpression='user_id = :user_id AND base_conversation_id = :conv_id',
                ExpressionAttributeValues={
                    ':user_id': user_id,
                    ':conv_id': conversation_id
                }
            )
            
            # Sort by timestamp
            items = sorted(response.get('Items', []), key=lambda x: x.get('timestamp', ''))
            
        else:
            # Get all conversations for a user (limit to recent ones)
            logger.info(f"Retrieving all conversations for user: {user_id}")
            response = table.scan(
                FilterExpression='user_id = :user_id',
                ExpressionAttributeValues={
                    ':user_id': user_id
                },
                Limit=50  # Limit to avoid large responses
            )
            
            # Sort by timestamp (most recent first)
            items = sorted(response.get('Items', []), key=lambda x: x.get('timestamp', ''), reverse=True)
        
        logger.info(f"Retrieved {len(items)} conversation items")
        
        return {
            'statusCode': 200,
            'conversations': items
        }
    except Exception as e:
        logger.error(f"Error retrieving conversation: {str(e)}", exc_info=True)
        raise e

def get_conversation_context(user_id, conversation_id):
    """
    NEW: Get just the latest context (concept/audience) for a conversation
    This is used by the main lambda for follow-up question handling
    """
    if not conversation_id:
        return {
            'statusCode': 200,
            'context': None
        }
    
    table = dynamodb.Table(CONVERSATION_TABLE)
    
    try:
        logger.info(f"Getting context for conversation: {conversation_id}")
        
        # Get recent interactions for this conversation
        response = table.scan(
            FilterExpression='user_id = :user_id AND base_conversation_id = :conv_id',
            ExpressionAttributeValues={
                ':user_id': user_id,
                ':conv_id': conversation_id
            },
            Limit=10  # Only need recent interactions
        )
        
        items = response.get('Items', [])
        
        if not items:
            return {
                'statusCode': 200,
                'context': None
            }
        
        # Sort by timestamp (most recent first)
        sorted_items = sorted(items, key=lambda x: x.get('timestamp', ''), reverse=True)
        
        # Find the most recent item with a valid concept
        for item in sorted_items:
            concept = item.get('concept')
            audience = item.get('audience', 'general')
            
            if concept and concept != 'unknown':
                context = {
                    'concept': concept,
                    'audience': audience,
                    'timestamp': item.get('timestamp')
                }
                
                logger.info(f"Found context: {context}")
                
                return {
                    'statusCode': 200,
                    'context': context
                }
        
        # No valid context found
        return {
            'statusCode': 200,
            'context': None
        }
        
    except Exception as e:
        logger.error(f"Error getting conversation context: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'error': str(e)
        }