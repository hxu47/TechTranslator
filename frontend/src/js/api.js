/**
 * API service for TechTranslator - DEBUG VERSION
 * Enhanced with detailed authentication debugging
 */
class ApiService {
    constructor() {
        // API Gateway URL - to be replaced during deployment
        this.apiUrl = 'YOUR_API_GATEWAY_URL';
        this.token = null;
    }

    /**
     * Set the authentication token
     * @param {string} token - JWT token
     */
    setToken(token) {
        console.log('🔐 DEBUG: Setting token:', token ? `${token.substring(0, 20)}...` : 'null');
        this.token = token;
        
        // Debug: Parse and log JWT payload (without exposing sensitive info)
        if (token) {
            try {
                const parts = token.split('.');
                if (parts.length === 3) {
                    const payload = JSON.parse(atob(parts[1]));
                    console.log('🔍 DEBUG: JWT payload preview:', {
                        email: payload.email,
                        'cognito:username': payload['cognito:username'],
                        sub: payload.sub,
                        exp: payload.exp,
                        iss: payload.iss
                    });
                    
                    // Check if token is expired
                    const now = Math.floor(Date.now() / 1000);
                    if (payload.exp < now) {
                        console.warn('⚠️ DEBUG: Token appears to be expired!');
                    }
                }
            } catch (e) {
                console.error('❌ DEBUG: Error parsing JWT token:', e);
            }
        }
    }

    /**
     * Clear the authentication token
     */
    clearToken() {
        console.log('🔐 DEBUG: Clearing token');
        this.token = null;
    }

    /**
     * Get request headers with auth token if available
     * @returns {Object} Headers object
     */
    getHeaders() {
        const headers = {
            'Content-Type': 'application/json'
        };
        
        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
            console.log('🔐 DEBUG: Adding Authorization header:', `Bearer ${this.token.substring(0, 20)}...`);
        } else {
            console.warn('⚠️ DEBUG: No token available - request will be unauthenticated');
        }
        
        console.log('📤 DEBUG: Request headers:', Object.keys(headers));
        
        return headers;
    }

    /**
     * Send a query to the API
     * @param {string} query - User query
     * @param {string} conversationId - Optional conversation ID for follow-up queries
     * @returns {Promise} Promise with API response
     */
    async sendQuery(query, conversationId = null) {
        try {
            console.log('📤 DEBUG: Sending query:', { 
                query, 
                conversationId, 
                apiUrl: this.apiUrl,
                hasToken: !!this.token 
            });
            
            const headers = this.getHeaders();
            const body = JSON.stringify({ 
                query,
                conversation_id: conversationId 
            });
            
            console.log('📤 DEBUG: Full request details:', {
                url: `${this.apiUrl}/query`,
                method: 'POST',
                headers: headers,
                bodyLength: body.length
            });
            
            const response = await fetch(`${this.apiUrl}/query`, {
                method: 'POST',
                headers: headers,
                body: body
            });
            
            console.log('📥 DEBUG: Response received:', {
                status: response.status,
                statusText: response.statusText,
                headers: Object.fromEntries(response.headers.entries())
            });
            
            if (!response.ok) {
                let errorData;
                try {
                    errorData = await response.json();
                } catch (e) {
                    // If we can't parse JSON, create a generic error
                    errorData = { error: `Request failed with status ${response.status}` };
                }
                
                console.error('❌ DEBUG: API Error:', errorData);
                
                // Handle specific error cases
                if (response.status === 401) {
                    console.error('🔐 DEBUG: Authentication failed - token might be invalid or expired');
                    throw new Error('Authentication failed. Please log in again.');
                } else if (response.status === 503) {
                    throw new Error('AI service temporarily unavailable. Please ensure the SageMaker endpoint is deployed and configured.');
                } else if (response.status === 500) {
                    throw new Error(errorData.error || 'Internal server error occurred. Please try again.');
                } else if (response.status === 400) {
                    throw new Error(errorData.error || 'Invalid request. Please check your input.');
                } else {
                    throw new Error(errorData.error || `API request failed: ${response.statusText}`);
                }
            }
            
            const data = await response.json();
            console.log('📥 DEBUG: API Response preview:', {
                hasResponse: !!data.response,
                concept: data.concept,
                audience: data.audience,
                conversationId: data.conversation_id
            });
            
            // Validate response structure
            if (!data.response) {
                throw new Error('Invalid response format from server');
            }
            
            return data;
            
        } catch (error) {
            console.error('❌ DEBUG: Error in sendQuery:', error);
            
            // Handle network errors
            if (error.name === 'TypeError' && error.message.includes('fetch')) {
                throw new Error('Unable to connect to the server. Please check your internet connection and try again.');
            }
            
            // Re-throw other errors as-is
            throw error;
        }
    }

    /**
     * Get conversation history
     * @param {string} conversationId - Optional conversation ID to retrieve a specific conversation
     * @returns {Promise} Promise with conversation history
     */
    async getConversations(conversationId = null) {
        try {
            console.log('📤 DEBUG: Getting conversations (not fully implemented without auth endpoint)');
            return { conversations: [] };
            
        } catch (error) {
            console.error('❌ DEBUG: Error getting conversations:', error);
            throw error;
        }
    }

    /**
     * Test API connectivity
     * @returns {Promise<boolean>} True if API is reachable
     */
    async testConnection() {
        try {
            console.log('🧪 DEBUG: Testing API connection...');
            // Simple test query to check if API is working
            const testResponse = await this.sendQuery('test connection');
            console.log('✅ DEBUG: API connection test passed');
            return true;
        } catch (error) {
            console.error('❌ DEBUG: API connection test failed:', error);
            return false;
        }
    }

        /**
     * Get conversation history from DynamoDB
     * @param {string} conversationId - Optional specific conversation ID
     * @returns {Promise} Promise with conversation history
     */
    async getConversationHistory(conversationId = null) {
        try {
            console.log('📤 DEBUG: Getting conversation history from DynamoDB:', { 
                conversationId,
                hasToken: !!this.token 
            });
            
            const headers = this.getHeaders();
            const params = conversationId ? `?conversation_id=${conversationId}` : '';
            
            console.log('📤 DEBUG: Request details:', {
                url: `${this.apiUrl}/conversation${params}`,
                method: 'GET',
                headers: headers
            });
            
            const response = await fetch(`${this.apiUrl}/conversation${params}`, {
                method: 'GET',
                headers: headers
            });
            
            console.log('📥 DEBUG: Conversation history response:', {
                status: response.status,
                statusText: response.statusText
            });
            
            if (!response.ok) {
                let errorData;
                try {
                    errorData = await response.json();
                } catch (e) {
                    errorData = { error: `Request failed with status ${response.status}` };
                }
                
                console.error('❌ DEBUG: Conversation API Error:', errorData);
                
                if (response.status === 401) {
                    throw new Error('Authentication failed. Please log in again.');
                } else {
                    throw new Error(errorData.error || `Failed to load conversation history: ${response.statusText}`);
                }
            }
            
            const data = await response.json();
            console.log('📥 DEBUG: Conversation data preview:', {
                hasConversations: !!data.conversations,
                conversationCount: data.conversations ? data.conversations.length : 0
            });
            
            return data;
            
        } catch (error) {
            console.error('❌ DEBUG: Error getting conversation history:', error);
            
            // Handle network errors
            if (error.name === 'TypeError' && error.message.includes('fetch')) {
                throw new Error('Unable to connect to the server. Please check your internet connection.');
            }
            
            throw error;
        }
    }

    /**
     * Get conversation history from DynamoDB
     * @param {string} conversationId - Optional specific conversation ID
     * @returns {Promise} Promise with conversation history
     */
    async getConversationHistory(conversationId = null) {
        try {
            console.log('📤 DEBUG: Getting conversation history from DynamoDB:', { 
                conversationId,
                hasToken: !!this.token 
            });
            
            const headers = this.getHeaders();
            const params = conversationId ? `?conversation_id=${conversationId}` : '';
            
            console.log('📤 DEBUG: Request details:', {
                url: `${this.apiUrl}/conversation${params}`,
                method: 'GET',
                headers: headers
            });
            
            const response = await fetch(`${this.apiUrl}/conversation${params}`, {
                method: 'GET',
                headers: headers
            });
            
            console.log('📥 DEBUG: Conversation history response:', {
                status: response.status,
                statusText: response.statusText
            });
            
            if (!response.ok) {
                let errorData;
                try {
                    errorData = await response.json();
                } catch (e) {
                    errorData = { error: `Request failed with status ${response.status}` };
                }
                
                console.error('❌ DEBUG: Conversation API Error:', errorData);
                
                if (response.status === 401) {
                    throw new Error('Authentication failed. Please log in again.');
                } else {
                    throw new Error(errorData.error || `Failed to load conversation history: ${response.statusText}`);
                }
            }
            
            const data = await response.json();
            console.log('📥 DEBUG: Conversation data preview:', {
                hasConversations: !!data.conversations,
                conversationCount: data.conversations ? data.conversations.length : 0
            });
            
            return data;
            
        } catch (error) {
            console.error('❌ DEBUG: Error getting conversation history:', error);
            
            // Handle network errors
            if (error.name === 'TypeError' && error.message.includes('fetch')) {
                throw new Error('Unable to connect to the server. Please check your internet connection.');
            }
            
            throw error;
        }
    }


    /**
     * Convert DynamoDB conversation items to frontend chat sessions
     * @param {Array} conversationItems - Array of conversation items from DynamoDB
     * @returns {Object} Chat sessions object
     */
    convertDynamoDBToChats(conversationItems) {
        console.log('🔄 DEBUG: Converting DynamoDB items to chat sessions:', conversationItems.length);
        
        const chatSessions = {};
        const conversationGroups = {};
        
        // Group items by base_conversation_id
        conversationItems.forEach(item => {
            const baseId = item.base_conversation_id || item.conversation_id.split('#')[0];
            if (!conversationGroups[baseId]) {
                conversationGroups[baseId] = [];
            }
            conversationGroups[baseId].push(item);
        });
        
        // Convert each conversation group to a chat session
        Object.keys(conversationGroups).forEach(baseId => {
            const items = conversationGroups[baseId].sort((a, b) => 
                new Date(a.timestamp) - new Date(b.timestamp)
            );
            
            if (items.length > 0) {
                const firstItem = items[0];
                const lastItem = items[items.length - 1];
                
                // Create chat session
                const chatSession = {
                    id: baseId,
                    title: this.generateChatTitle(firstItem.query),
                    messages: [],
                    concept: lastItem.concept || null,
                    audience: lastItem.audience || null,
                    createdAt: firstItem.timestamp
                };
                
                // Add messages for each item
                items.forEach(item => {
                    // Add user message
                    chatSession.messages.push({
                        content: item.query,
                        isUser: true,
                        extraInfo: null,
                        timestamp: item.timestamp
                    });
                    
                    // Add bot response
                    chatSession.messages.push({
                        content: item.response,
                        isUser: false,
                        extraInfo: {
                            concept: item.concept,
                            audience: item.audience
                        },
                        timestamp: item.timestamp
                    });
                });
                
                chatSessions[baseId] = chatSession;
            }
        });
        
        console.log('✅ DEBUG: Converted to chat sessions:', Object.keys(chatSessions).length);
        return chatSessions;
    }


    /**
     * Generate a chat title from the first query
     * @param {string} query - First query in the conversation
     * @returns {string} Chat title
     */
    generateChatTitle(query) {
        if (!query) return 'New Chat';
        return query.length > 30 ? query.substring(0, 30) + '...' : query;
    }


}

// Create a singleton instance
const apiService = new ApiService();