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
    Lambda function for managing conversation history
    Handles storing and retrieving conversation data
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
        
        logger.info(f"Processing {action} request for user: {user_id}")
        
        # Handle the requested action
        if action == 'store':
            return store_conversation(user_id, conversation_id, query, response, concept, audience)
        elif action == 'get':
            return get_conversation(user_id, conversation_id)
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
    Function to store a conversation in DynamoDB
    """
    conv_id = conversation_id or str(uuid.uuid4())
    
    # Calculate TTL (30 days from now)
    ttl = int((datetime.now() + timedelta(days=30)).timestamp())
    
    table = dynamodb.Table(CONVERSATION_TABLE)
    
    try:
        item = {
            'user_id': user_id,
            'conversation_id': conv_id,
            'query': query,
            'response': response,
            'concept': concept,
            'audience': audience,
            'timestamp': datetime.now().isoformat(),
            'ttl': ttl
        }
        
        table.put_item(Item=item)
        logger.info(f"Stored conversation: {conv_id}")
        
        return {
            'statusCode': 200,
            'conversation_id': conv_id
        }
    except Exception as e:
        logger.error(f"Error storing conversation: {str(e)}", exc_info=True)
        raise e

def get_conversation(user_id, conversation_id):
    """
    Function to retrieve conversation(s) from DynamoDB
    """
    table = dynamodb.Table(CONVERSATION_TABLE)
    
    try:
        if conversation_id:
            # Get a specific conversation
            logger.info(f"Retrieving conversation: {conversation_id}")
            response = table.query(
                KeyConditionExpression='user_id = :user_id AND conversation_id = :conversation_id',
                ExpressionAttributeValues={
                    ':user_id': user_id,
                    ':conversation_id': conversation_id
                }
            )
        else:
            # Get all conversations for a user
            logger.info(f"Retrieving all conversations for user: {user_id}")
            response = table.query(
                KeyConditionExpression='user_id = :user_id',
                ExpressionAttributeValues={
                    ':user_id': user_id
                },
                ScanIndexForward=False  # Sort by most recent
            )
        
        logger.info(f"Retrieved {len(response['Items'])} conversations")
        
        return {
            'statusCode': 200,
            'conversations': response['Items']
        }
    except Exception as e:
        logger.error(f"Error retrieving conversation: {str(e)}", exc_info=True)
        raise e