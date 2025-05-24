/**
 * Main application logic for TechTranslator
 */
document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const authSection = document.getElementById('authSection');
    const chatSection = document.getElementById('chatSection');
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');
    const showRegisterButton = document.getElementById('showRegisterButton');
    const showLoginButton = document.getElementById('showLoginButton');
    const loginButton = document.getElementById('loginButton');
    const registerButton = document.getElementById('registerButton');
    const logoutButton = document.getElementById('logoutButton');
    const chatContainer = document.getElementById('chatContainer');
    const messageContainer = document.getElementById('messageContainer');
    const userInput = document.getElementById('userInput');
    const sendButton = document.getElementById('sendButton');
    const conversationHistory = document.getElementById('conversationHistory');
    
    // Current conversation ID
    let currentConversationId = null;
    
    // Initialize UI - Skip auth for now
    initializeUI();
    
    // Event listeners for authentication (keeping mock auth)
    showRegisterButton.addEventListener('click', () => {
        loginForm.style.display = 'none';
        registerForm.style.display = 'block';
    });
    
    showLoginButton.addEventListener('click', () => {
        registerForm.style.display = 'none';
        loginForm.style.display = 'block';
    });
    
    loginButton.addEventListener('click', async () => {
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        
        if (!email || !password) {
            alert('Please enter email and password');
            return;
        }
        
        try {
            loginButton.disabled = true;
            loginButton.innerHTML = '<span class="loading"></span> Logging in...';
            
            await authService.login(email, password);
            
            // Update UI to show chat
            updateUIAfterAuth();
            
            // Load conversation history (will be empty for now)
            loadConversationHistory();
        } catch (error) {
            alert('Login failed: ' + error.message);
        } finally {
            loginButton.disabled = false;
            loginButton.innerHTML = 'Login';
        }
    });
    
    registerButton.addEventListener('click', async () => {
        const email = document.getElementById('registerEmail').value;
        const password = document.getElementById('registerPassword').value;
        const confirmPassword = document.getElementById('confirmPassword').value;
        
        if (!email || !password || !confirmPassword) {
            alert('Please fill all fields');
            return;
        }
        
        if (password !== confirmPassword) {
            alert('Passwords do not match');
            return;
        }
        
        try {
            registerButton.disabled = true;
            registerButton.innerHTML = '<span class="loading"></span> Registering...';
            
            await authService.register(email, password);
            
            // Show login form after successful registration
            registerForm.style.display = 'none';
            loginForm.style.display = 'block';
            
            // Pre-fill email
            document.getElementById('email').value = email;
            
            alert('Registration successful! You can now log in.');
        } catch (error) {
            alert('Registration failed: ' + error.message);
        } finally {
            registerButton.disabled = false;
            registerButton.innerHTML = 'Register';
        }
    });
    
    logoutButton.addEventListener('click', () => {
        authService.logout();
        updateUIAfterLogout();
    });
    
    // Event listeners for chat
    sendButton.addEventListener('click', sendMessage);
    
    userInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
    
    /**
     * Initialize UI based on authentication status
     */
    function initializeUI() {
        // For now, just show the chat interface directly
        // You can re-enable auth later by uncommenting the original logic
        updateUIAfterAuth();
        
        /* Original auth-based initialization:
        if (authService.isUserAuthenticated()) {
            updateUIAfterAuth();
            loadConversationHistory();
        } else {
            updateUIAfterLogout();
        }
        */
    }
    
    /**
     * Update UI after successful authentication
     */
    function updateUIAfterAuth() {
        authSection.style.display = 'none';
        chatSection.style.display = 'block';
    }
    
    /**
     * Update UI after logout
     */
    function updateUIAfterLogout() {
        authSection.style.display = 'block';
        chatSection.style.display = 'none';
        loginForm.style.display = 'block';
        registerForm.style.display = 'none';
        
        // Clear forms
        document.getElementById('email').value = '';
        document.getElementById('password').value = '';
        document.getElementById('registerEmail').value = '';
        document.getElementById('registerPassword').value = '';
        document.getElementById('confirmPassword').value = '';
    }
    
    /**
     * Add a message to the chat
     */
    function addMessage(message, isUser, extraInfo = null) {
        const messageDiv = document.createElement('div');
        messageDiv.className = isUser ? 'user-message' : 'bot-message';
        
        // For bot messages, we might want to show extra info like concept/audience
        if (!isUser && extraInfo) {
            const infoDiv = document.createElement('div');
            infoDiv.style.fontSize = '0.8em';
            infoDiv.style.opacity = '0.7';
            infoDiv.style.marginBottom = '5px';
            infoDiv.textContent = `Concept: ${extraInfo.concept} | Audience: ${extraInfo.audience}`;
            messageDiv.appendChild(infoDiv);
        }
        
        const textDiv = document.createElement('div');
        textDiv.textContent = message;
        messageDiv.appendChild(textDiv);
        
        messageContainer.appendChild(messageDiv);
        
        // Auto-scroll to the bottom
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
    
    /**
     * Add a loading indicator to the chat
     */
    function addLoadingIndicator() {
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'bot-message loading-message';
        loadingDiv.innerHTML = '<span class="loading"></span> Thinking...';
        messageContainer.appendChild(loadingDiv);
        
        // Auto-scroll to the bottom
        chatContainer.scrollTop = chatContainer.scrollHeight;
        
        return loadingDiv;
    }
    
    /**
     * Send a message to the API
     */
    async function sendMessage() {
        const message = userInput.value.trim();
        if (!message) return;
        
        // Add user message to chat
        addMessage(message, true);
        userInput.value = '';
        
        // Add loading indicator
        const loadingIndicator = addLoadingIndicator();
        
        try {
            sendButton.disabled = true;
            userInput.disabled = true;
            
            // Call API
            const data = await apiService.sendQuery(message, currentConversationId);
            
            // Remove loading indicator
            loadingIndicator.remove();
            
            // Add bot response to chat with extra info
            addMessage(data.response, false, {
                concept: data.concept,
                audience: data.audience
            });
            
            // Update current conversation ID
            currentConversationId = data.conversation_id;
            
            // Don't refresh conversation history since we're not using auth yet
            // loadConversationHistory();
        } catch (error) {
            console.error('Error sending message:', error);
            
            // Remove loading indicator
            loadingIndicator.remove();
            
            // Show user-friendly error message
            let errorMessage = 'Sorry, there was an error processing your request.';
            
            if (error.message.includes('AI model is not available')) {
                errorMessage = 'The AI service is not available. Please ensure the SageMaker endpoint is deployed and configured.';
            } else if (error.message.includes('Failed to fetch')) {
                errorMessage = 'Unable to connect to the server. Please check your connection and try again.';
            }
            
            addMessage(errorMessage, false);
        } finally {
            sendButton.disabled = false;
            userInput.disabled = false;
            userInput.focus();
        }
    }
    
    /**
     * Load conversation history
     */
    async function loadConversationHistory() {
        // Skip this for now since we're not using auth
        // The conversation history section will remain empty
        
        // Hide the conversation history section since it's not functional yet
        const historySection = document.querySelector('.conversation-history');
        if (historySection) {
            historySection.style.display = 'none';
        }
    }
    
    /**
     * Load a specific conversation
     */
    async function loadConversation(conversationId) {
        // Skip this for now since we're not using auth
        console.log('Conversation loading not implemented without authentication');
    }
});