const AWS = require('aws-sdk');
const { v4: uuidv4 } = require('uuid');

// Initialize AWS clients
const dynamodb = new AWS.DynamoDB.DocumentClient();

// Constants from environment variables
const CONVERSATION_TABLE = process.env.CONVERSATION_TABLE;

/**
 * Lambda function for managing conversation history
 * Handles storing and retrieving conversation data
 */
exports.handler = async (event) => {
  try {
    console.log('Event:', JSON.stringify(event));
    
    // Get action and parameters from the event
    const {
      action = 'get',
      user_id = 'anonymous',
      conversation_id,
      query,
      response,
      concept,
      audience
    } = event;
    
    console.log(`Processing ${action} request for user: ${user_id}`);
    
    // Handle the requested action
    if (action === 'store') {
      return await storeConversation(user_id, conversation_id, query, response, concept, audience);
    } else if (action === 'get') {
      return await getConversation(user_id, conversation_id);
    } else {
      return {
        statusCode: 400,
        body: JSON.stringify({ error: `Unknown action: ${action}` })
      };
    }
  } catch (error) {
    console.error('Error:', error);
    return {
      statusCode: 500,
      body: JSON.stringify({ error: error.message })
    };
  }
};

/**
 * Function to store a conversation in DynamoDB
 */
async function storeConversation(user_id, conversation_id, query, response, concept, audience) {
  const convId = conversation_id || uuidv4();
  
  // Calculate TTL (30 days from now)
  const ttl = Math.floor(Date.now() / 1000) + (30 * 24 * 60 * 60);
  
  const params = {
    TableName: CONVERSATION_TABLE,
    Item: {
      user_id,
      conversation_id: convId,
      query,
      response,
      concept,
      audience,
      timestamp: new Date().toISOString(),
      ttl
    }
  };
  
  try {
    await dynamodb.put(params).promise();
    console.log(`Stored conversation: ${convId}`);
    
    return {
      statusCode: 200,
      conversation_id: convId
    };
  } catch (error) {
    console.error('Error storing conversation:', error);
    throw error;
  }
}

/**
 * Function to retrieve conversation(s) from DynamoDB
 */
async function getConversation(user_id, conversation_id) {
  try {
    let params;
    
    if (conversation_id) {
      // Get a specific conversation
      params = {
        TableName: CONVERSATION_TABLE,
        KeyConditionExpression: 'user_id = :user_id AND conversation_id = :conversation_id',
        ExpressionAttributeValues: {
          ':user_id': user_id,
          ':conversation_id': conversation_id
        }
      };
      console.log(`Retrieving conversation: ${conversation_id}`);
    } else {
      // Get all conversations for a user
      params = {
        TableName: CONVERSATION_TABLE,
        KeyConditionExpression: 'user_id = :user_id',
        ExpressionAttributeValues: {
          ':user_id': user_id
        },
        ScanIndexForward: false  // Sort by most recent (assuming timestamp is the sort key)
      };
      console.log(`Retrieving all conversations for user: ${user_id}`);
    }
    
    const result = await dynamodb.query(params).promise();
    console.log(`Retrieved ${result.Items.length} conversations`);
    
    return {
      statusCode: 200,
      conversations: result.Items
    };
  } catch (error) {
    console.error('Error retrieving conversation:', error);
    throw error;
  }
}