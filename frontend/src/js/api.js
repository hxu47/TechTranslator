/**
 * API service for TechTranslator
 * Handles all the API calls to the backend
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
        this.token = token;
    }

    /**
     * Clear the authentication token
     */
    clearToken() {
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
        }
        
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
            console.log('Sending query:', { query, conversationId, apiUrl: this.apiUrl });
            
            const response = await fetch(`${this.apiUrl}/query`, {
                method: 'POST',
                headers: this.getHeaders(),
                body: JSON.stringify({ 
                    query,
                    conversation_id: conversationId 
                })
            });
            
            console.log('Response status:', response.status);
            
            if (!response.ok) {
                let errorData;
                try {
                    errorData = await response.json();
                } catch (e) {
                    // If we can't parse JSON, create a generic error
                    errorData = { error: `Request failed with status ${response.status}` };
                }
                
                console.error('API Error:', errorData);
                
                // Handle specific error cases
                if (response.status === 503) {
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
            console.log('API Response:', data);
            
            // Validate response structure
            if (!data.response) {
                throw new Error('Invalid response format from server');
            }
            
            return data;
            
        } catch (error) {
            console.error('Error sending query:', error);
            
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
            // Since we're not using authentication for now, return empty conversations
            // This can be implemented later when Cognito authentication is fully enabled
            
            console.log('Getting conversations (not implemented without auth)');
            return { conversations: [] };
            
            /* 
            // This is what it would look like with auth enabled:
            const queryParams = conversationId ? `?conversation_id=${conversationId}` : '';
            const response = await fetch(`${this.apiUrl}/conversation${queryParams}`, {
                method: 'GET',
                headers: this.getHeaders()
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `API request failed: ${response.statusText}`);
            }
            
            return await response.json();
            */
        } catch (error) {
            console.error('Error getting conversations:', error);
            throw error;
        }
    }

    /**
     * Test API connectivity
     * @returns {Promise<boolean>} True if API is reachable
     */
    async testConnection() {
        try {
            // Simple test query to check if API is working
            const testResponse = await this.sendQuery('test connection');
            return true;
        } catch (error) {
            console.error('API connection test failed:', error);
            return false;
        }
    }
}

// Create a singleton instance
const apiService = new ApiService();