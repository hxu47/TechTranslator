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
    Lambda function for managing conversation history - ENHANCED
    Handles storing and retrieving conversation data with better context support
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Get action and parameters from the event
        action = event.get('action', 'get')
        user_id = event.get('user_id', 'anonymous')
        conversation_id = event.get('conversation_id')
        query = event.get('query')
        response = event.get('response')
        concept = event.get('concept')
        audience = event.get('audience')
        
        logger.info(f"Processing {action} request for user: {user_id}, conversation: {conversation_id}")
        
        # Handle the requested action
        if action == 'store':
            return store_conversation(user_id, conversation_id, query, response, concept, audience)
        elif action == 'get':
            return get_conversation(user_id, conversation_id)
        elif action == 'get_context':
            # NEW: Get just the context info for follow-up questions
            return get_conversation_context(user_id, conversation_id)
        else:
            error_msg = f"Unknown action: {action}"
            logger.error(error_msg)
            return {
                'statusCode': 400,
                'body': json.dumps({'error': error_msg})
            }
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

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