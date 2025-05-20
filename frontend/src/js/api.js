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
            // In a real implementation, this would call the API
            // For now, we'll simulate a response
            
            /* 
            // Real API implementation would be:
            const response = await fetch(`${this.apiUrl}/query`, {
                method: 'POST',
                headers: this.getHeaders(),
                body: JSON.stringify({ 
                    query,
                    conversation_id: conversationId 
                })
            });
            
            if (!response.ok) {
                throw new Error('API request failed');
            }
            
            return await response.json();
            */
            
            // Simulated API call delay
            await new Promise(resolve => setTimeout(resolve, 1000));
            
            // Simulated response
            let response = "I'm a simulated response since the API is not connected yet. In the full implementation, I would explain insurance data science concepts based on your query.";
            
            if (query.toLowerCase().includes('r-squared')) {
                response = "R-squared is a statistical measure that represents the proportion of the variance for a dependent variable that's explained by an independent variable. In insurance pricing, R-squared helps actuaries understand how well factors like age, location, or claim history explain premium variations.";
            } else if (query.toLowerCase().includes('loss ratio')) {
                response = "Loss ratio is the ratio of total losses paid out in claims plus adjustment expenses divided by the total earned premiums. It's a key metric to evaluate the profitability of an insurance product or line of business.";
            } else if (query.toLowerCase().includes('model')) {
                response = "Predictive models in insurance use historical data to estimate future outcomes like claims frequency, severity, or policyholder behavior. They help in pricing, underwriting, and claims management processes.";
            }
            
            // Mock successful API response
            return {
                query,
                response,
                conversation_id: conversationId || 'sim-' + Date.now(),
                concept: query.toLowerCase().includes('r-squared') ? 'r-squared' : 
                         query.toLowerCase().includes('loss ratio') ? 'loss ratio' : 
                         query.toLowerCase().includes('model') ? 'predictive model' : 'data science',
                audience: query.toLowerCase().includes('underwriter') ? 'underwriter' : 
                          query.toLowerCase().includes('actuary') ? 'actuary' : 
                          query.toLowerCase().includes('executive') ? 'executive' : 'general'
            };
        } catch (error) {
            console.error('Error sending query:', error);
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
            // In a real implementation, this would call the API
            // For now, we'll simulate a response
            
            /* 
            // Real API implementation would be:
            const queryParams = conversationId ? `?conversation_id=${conversationId}` : '';
            const response = await fetch(`${this.apiUrl}/conversation${queryParams}`, {
                method: 'GET',
                headers: this.getHeaders()
            });
            
            if (!response.ok) {
                throw new Error('API request failed');
            }
            
            return await response.json();
            */
            
            // Simulated API call delay
            await new Promise(resolve => setTimeout(resolve, 500));
            
            // Mock conversation history
            const conversations = [
                {
                    conversation_id: 'sim-1',
                    timestamp: new Date(Date.now() - 3600000).toISOString(),
                    query: 'What is R-squared?',
                    concept: 'r-squared'
                },
                {
                    conversation_id: 'sim-2',
                    timestamp: new Date(Date.now() - 7200000).toISOString(),
                    query: 'Explain loss ratio to an underwriter',
                    concept: 'loss ratio'
                }
            ];
            
            return { conversations: conversationId ? 
                    conversations.filter(c => c.conversation_id === conversationId) : 
                    conversations };
        } catch (error) {
            console.error('Error getting conversations:', error);
            throw error;
        }
    }
}

// Create a singleton instance
const apiService = new ApiService();