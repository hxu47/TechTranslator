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
            const response = await fetch(`${this.apiUrl}/query`, {
                method: 'POST',
                headers: this.getHeaders(),
                body: JSON.stringify({ 
                    query,
                    conversation_id: conversationId 
                })
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `API request failed: ${response.statusText}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('Error sending query:', error);
            
            // Check if it's a 503 error (SageMaker not configured)
            if (error.message.includes('503') || error.message.includes('AI service temporarily unavailable')) {
                throw new Error('The AI model is not available. Please ensure the SageMaker endpoint is deployed and configured.');
            }
            
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
            // Since we're not using authentication, we'll skip this for now
            // In a real implementation with Cognito, this would work
            
            // For now, return empty conversations
            return { conversations: [] };
            
            /* 
            // This is what it would look like with auth enabled:
            const queryParams = conversationId ? `?conversation_id=${conversationId}` : '';
            const response = await fetch(`${this.apiUrl}/conversation${queryParams}`, {
                method: 'GET',
                headers: this.getHeaders()
            });
            
            if (!response.ok) {
                throw new Error(`API request failed: ${response.statusText}`);
            }
            
            return await response.json();
            */
        } catch (error) {
            console.error('Error getting conversations:', error);
            throw error;
        }
    }
}

// Create a singleton instance
const apiService = new ApiService();