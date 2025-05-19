const AWS = require('aws-sdk');
const { v4: uuidv4 } = require('uuid');

// Initialize AWS clients
const s3 = new AWS.S3();
const dynamodb = new AWS.DynamoDB.DocumentClient();
const lambda = new AWS.Lambda();

// Constants from environment variables
const VECTOR_TABLE = process.env.VECTOR_TABLE;
const KNOWLEDGE_BUCKET = process.env.KNOWLEDGE_BUCKET;
const CONVERSATION_FUNCTION = process.env.CONVERSATION_FUNCTION;

/**
 * Main Lambda function for the TechTranslator application
 * Handles prompt engineering, context retrieval, and response generation
 */
exports.handler = async (event) => {
  try {
    // Parse request body
    const body = event.body ? JSON.parse(event.body) : {};
    const { query, conversation_id } = body;
    const user_id = event.requestContext?.authorizer?.claims?.sub || 'anonymous';
    
    if (!query) {
      return {
        statusCode: 400,
        headers: corsHeaders,
        body: JSON.stringify({ error: 'Query is required' })
      };
    }
    
    console.log(`Processing query: ${query} for user: ${user_id}`);
    
    // Step 1: Extract concept and audience from query using prompt engineering
    // (In a real implementation, this would call an LLM API)
    const conceptAndAudience = extractConceptAndAudience(query);
    const { concept, audience } = conceptAndAudience;
    
    console.log(`Extracted concept: ${concept}, audience: ${audience}`);
    
    // Step 2: Retrieve relevant information from knowledge base
    const relevantInfo = await retrieveInformation(concept);
    
    console.log(`Retrieved information for ${concept}`);
    
    // Step 3: Generate the response
    // (In a real implementation, this would call an LLM API with retrieved context)
    const response = generateResponse(query, conceptAndAudience, relevantInfo);
    
    console.log('Generated response');
    
    // Step 4: Store conversation
    const conversationId = conversation_id || uuidv4();
    await storeConversation(user_id, conversationId, query, response, concept, audience);
    
    console.log(`Stored conversation: ${conversationId}`);
    
    // Return the response
    return {
      statusCode: 200,
      headers: corsHeaders,
      body: JSON.stringify({
        query,
        response,
        concept,
        audience,
        conversation_id: conversationId
      })
    };
  } catch (error) {
    console.error('Error:', error);
    return {
      statusCode: 500,
      headers: corsHeaders,
      body: JSON.stringify({ error: error.message })
    };
  }
};

// CORS headers for API Gateway integration
const corsHeaders = {
  'Content-Type': 'application/json',
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'OPTIONS,POST,GET',
  'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'
};

/**
 * Mock function to extract concept and audience from query
 * In a real implementation, this would use prompt engineering with an LLM
 */
function extractConceptAndAudience(query) {
  // Simple extraction based on query text
  // In a real implementation, this would use an LLM for more sophisticated extraction
  const lowerQuery = query.toLowerCase();
  
  let concept = 'data science';
  if (lowerQuery.includes('r-squared')) concept = 'r-squared';
  else if (lowerQuery.includes('loss ratio')) concept = 'loss ratio';
  else if (lowerQuery.includes('model')) concept = 'predictive model';
  
  let audience = 'general';
  if (lowerQuery.includes('underwriter')) audience = 'underwriter';
  else if (lowerQuery.includes('actuary')) audience = 'actuary';
  else if (lowerQuery.includes('ceo') || lowerQuery.includes('executive')) audience = 'executive';
  
  return { concept, audience };
}

/**
 * Function to retrieve relevant information from knowledge base
 * In a real implementation, this would use vector search and RAG techniques
 */
async function retrieveInformation(concept) {
  // Mock implementation - in a real system, this would retrieve from S3 and vector DB
  return {
    'r-squared': {
      definition: 'R-squared is a statistical measure that represents the proportion of the variance for a dependent variable that\'s explained by an independent variable.',
      insurance_context: 'In insurance pricing, R-squared helps actuaries understand how well factors like age, location, or claim history explain premium variations.',
      examples: {
        underwriter: 'If your pricing model has an R-squared of 0.75, it means that 75% of the premium variation is explained by the factors in your model.',
        executive: 'An R-squared of 0.8 means our pricing model captures 80% of what drives premium differences, indicating a strong predictive model.',
        actuary: 'When comparing GLMs for pricing, the model with higher R-squared (all else being equal) is explaining more of the variance in loss ratios across segments.'
      }
    },
    'loss ratio': {
      definition: 'Loss ratio is the ratio of total losses paid out in claims plus adjustment expenses divided by the total earned premiums.',
      insurance_context: 'It\'s a key metric to evaluate the profitability of an insurance product or line of business.',
      examples: {
        underwriter: 'If you're seeing a loss ratio of 85% in a particular segment, you may need to consider rate adjustments or tighter underwriting guidelines.',
        executive: 'A loss ratio trend that increases from 60% to 70% over three quarters may signal emerging profitability challenges that require attention.',
        actuary: 'When modeling loss ratios, we need to consider both frequency and severity trends, as well as large claim volatility and development patterns.'
      }
    },
    'predictive model': {
      definition: 'A predictive model is a statistical algorithm that uses historical data to predict future outcomes.',
      insurance_context: 'In insurance, predictive models help estimate the likelihood of claims, premium adequacy, and customer behavior.',
      examples: {
        underwriter: 'The predictive model flagged this application with a high-risk score based on its similarity to previous policies that had high claim frequencies.',
        executive: 'Our new customer retention predictive model has improved retention by 5% by identifying at-risk policies before renewal.',
        actuary: 'This predictive model uses generalized linear modeling techniques with a logarithmic link function to handle the skewed distribution of claim amounts.'
      }
    },
    'data science': {
      definition: 'Data science is an interdisciplinary field that uses scientific methods, processes, algorithms and systems to extract knowledge from data.',
      insurance_context: 'In insurance, data science combines statistical modeling, machine learning, and domain expertise to improve pricing, underwriting, and claims handling.',
      examples: {
        underwriter: 'Data science tools help you identify patterns in applications that might indicate higher risk but wouldn't be obvious from traditional underwriting guidelines.',
        executive: 'Our data science initiatives reduced claims leakage by 12% last year by identifying patterns of potentially fraudulent claims.',
        actuary: 'We're using data science techniques like natural language processing to extract insights from adjuster notes and improve our reserving models.'
      }
    }
  }[concept] || {
    definition: 'General data science concept',
    insurance_context: 'Data science is widely used in insurance',
    examples: {
      underwriter: 'Data science helps underwriters assess risk',
      executive: 'Data science improves business outcomes',
      actuary: 'Data science enhances actuarial modeling'
    }
  };
}

/**
 * Function to generate a response based on the query, concept, audience, and retrieved information
 * In a real implementation, this would use prompt engineering with an LLM
 */
function generateResponse(query, conceptAndAudience, relevantInfo) {
  const { concept, audience } = conceptAndAudience;
  
  // In a real implementation, this would use an LLM API call with a carefully crafted prompt
  // For this implementation, we'll create a template-based response
  
  let audienceSpecific = relevantInfo.examples[audience] || relevantInfo.examples.general || '';
  
  const response = `
${relevantInfo.definition}

In the insurance industry: ${relevantInfo.insurance_context}

Specifically for ${audience}s: ${audienceSpecific}
`;
  
  return response.trim();
}

/**
 * Function to store conversation in DynamoDB via the Conversation Lambda
 */
async function storeConversation(user_id, conversation_id, query, response, concept, audience) {
  try {
    const params = {
      FunctionName: CONVERSATION_FUNCTION,
      InvocationType: 'RequestResponse',
      Payload: JSON.stringify({
        action: 'store',
        user_id,
        conversation_id,
        query,
        response,
        concept,
        audience
      })
    };
    
    const result = await lambda.invoke(params).promise();
    return JSON.parse(result.Payload);
  } catch (error) {
    console.error('Error storing conversation:', error);
    throw error;
  }
}