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
    
    // Initialize UI
    initializeUI();
    
    // Event listeners for authentication
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
            
            // Load conversation history
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
        if (authService.isUserAuthenticated()) {
            updateUIAfterAuth();
            loadConversationHistory();
        } else {
            updateUIAfterLogout();
        }
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
    function addMessage(message, isUser) {
        const messageDiv = document.createElement('div');
        messageDiv.className = isUser ? 'user-message' : 'bot-message';
        messageDiv.textContent = message;
        messageContainer.appendChild(messageDiv);
        
        // Auto-scroll to the bottom
        chatContainer.scrollTop = chatContainer.scrollHeight;
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
        
        try {
            sendButton.disabled = true;
            
            // Call API
            const data = await apiService.sendQuery(message, currentConversationId);
            
            // Add bot response to chat
            addMessage(data.response, false);
            
            // Update current conversation ID
            currentConversationId = data.conversation_id;
            
            // Refresh conversation history
            loadConversationHistory();
        } catch (error) {
            console.error('Error sending message:', error);
            addMessage('Sorry, there was an error processing your request.', false);
        } finally {
            sendButton.disabled = false;
        }
    }
    
    /**
     * Load conversation history
     */
    async function loadConversationHistory() {
        try {
            // Clear existing history
            conversationHistory.innerHTML = '';
            
            // Add loading indicator
            const loadingItem = document.createElement('div');
            loadingItem.className = 'list-group-item';
            loadingItem.innerHTML = '<span class="loading"></span> Loading...';
            conversationHistory.appendChild(loadingItem);
            
            // Get conversations
            const result = await apiService.getConversations();
            
            // Remove loading indicator
            conversationHistory.innerHTML = '';
            
            if (result.conversations && result.conversations.length > 0) {
                // Sort by most recent
                result.conversations.sort((a, b) => {
                    return new Date(b.timestamp) - new Date(a.timestamp);
                });
                
                // Add each conversation to the list
                result.conversations.forEach(conv => {
                    const item = document.createElement('a');
                    item.className = 'list-group-item list-group-item-action conversation-item';
                    if (conv.conversation_id === currentConversationId) {
                        item.classList.add('active');
                    }
                    
                    // Format timestamp
                    const timestamp = new Date(conv.timestamp).toLocaleString();
                    
                    item.innerHTML = `
                        <div class="d-flex w-100 justify-content-between">
                            <h5 class="mb-1">${conv.concept || 'Conversation'}</h5>
                            <small>${timestamp}</small>
                        </div>
                        <p class="mb-1">${conv.query}</p>
                    `;
                    
                    // Add click event to load conversation
                    item.addEventListener('click', () => loadConversation(conv.conversation_id));
                    
                    conversationHistory.appendChild(item);
                });
            } else {
                // No conversations found
                const noConvItem = document.createElement('div');
                noConvItem.className = 'list-group-item';
                noConvItem.textContent = 'No previous conversations';
                conversationHistory.appendChild(noConvItem);
            }
        } catch (error) {
            console.error('Error loading conversation history:', error);
            
            // Show error
            conversationHistory.innerHTML = '';
            const errorItem = document.createElement('div');
            errorItem.className = 'list-group-item text-danger';
            errorItem.textContent = 'Error loading conversations';
            conversationHistory.appendChild(errorItem);
        }
    }
    
    /**
     * Load a specific conversation
     */
    async function loadConversation(conversationId) {
        try {
            // Get conversation details
            const result = await apiService.getConversations(conversationId);
            
            if (result.conversations && result.conversations.length > 0) {
                const conversation = result.conversations[0];
                
                // Clear chat
                messageContainer.innerHTML = '';
                
                // Add welcome message
                const welcomeDiv = document.createElement('div');
                welcomeDiv.className = 'bot-message';
                welcomeDiv.textContent = "Hello! I'm TechTranslator. I can explain data science and machine learning concepts for insurance professionals. Try asking me about concepts like \"R-squared\", \"loss ratio\", or \"predictive models\".";
                messageContainer.appendChild(welcomeDiv);
                
                // Add user query
                addMessage(conversation.query, true);
                
                // Add bot response
                if (conversation.response) {
                    addMessage(conversation.response, false);
                }
                
                // Update current conversation ID
                currentConversationId = conversationId;
                
                // Update UI to show active conversation
                document.querySelectorAll('.conversation-item').forEach(item => {
                    item.classList.remove('active');
                });
                const activeItem = Array.from(document.querySelectorAll('.conversation-item')).find(
                    item => item.querySelector('p').textContent === conversation.query
                );
                if (activeItem) {
                    activeItem.classList.add('active');
                }
            }
        } catch (error) {
            console.error('Error loading conversation:', error);
            alert('Failed to load conversation. Please try again.');
        }
    }
});