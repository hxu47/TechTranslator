/**
 * Main application logic for TechTranslator - Fixed Version v2
 */
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded - starting app');
    
    // DOM Elements - with null checks
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
    const newChatButton = document.getElementById('newChatButton');
    const currentChatTitle = document.getElementById('currentChatTitle');
    
    // Chat management
    let currentConversationId = null;
    let chatSessions = {};
    let chatCounter = 1;
    let pageLoaded = false;
    
    // Mark page as loaded after a short delay
    setTimeout(() => {
        pageLoaded = true;
        console.log('Page ready for interactions');
    }, 500);
    
    // Initialize UI - Show chat interface directly
    initializeUI();
    
    // Event listeners for authentication (keeping mock auth structure but with null checks)
    if (showRegisterButton) {
        showRegisterButton.addEventListener('click', () => {
            if (loginForm && registerForm) {
                loginForm.style.display = 'none';
                registerForm.style.display = 'block';
            }
        });
    }
    
    if (showLoginButton) {
        showLoginButton.addEventListener('click', () => {
            if (registerForm && loginForm) {
                registerForm.style.display = 'none';
                loginForm.style.display = 'block';
            }
        });
    }
    
    if (loginButton) loginButton.addEventListener('click', handleLogin);
    if (registerButton) registerButton.addEventListener('click', handleRegister);
    if (logoutButton) logoutButton.addEventListener('click', handleLogout);
    
    // Event listeners for chat
    if (sendButton) sendButton.addEventListener('click', sendMessage);
    if (newChatButton) newChatButton.addEventListener('click', createNewChat);
    
    if (userInput) {
        userInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
    }
    
    // Example questions event listeners
    document.querySelectorAll('.example-question').forEach(question => {
        question.addEventListener('click', function() {
            const questionText = this.getAttribute('data-question');
            if (userInput) {
                userInput.value = questionText;
                userInput.focus();
            }
        });
    });
    
    /**
     * Initialize UI - Show chat interface directly
     */
    function initializeUI() {
        console.log('Initializing UI');
        
        // Show chat interface directly without authentication
        updateUIAfterAuth();
        
        // Load any existing chat sessions from localStorage first
        loadChatSessions();
        
        // Create the first chat session only if no existing sessions
        if (Object.keys(chatSessions).length === 0) {
            createNewChat();
        } else {
            // Switch to the most recent chat
            const sortedChats = Object.values(chatSessions).sort((a, b) => 
                new Date(b.createdAt) - new Date(a.createdAt)
            );
            if (sortedChats.length > 0) {
                switchToChat(sortedChats[0].id);
            }
        }
    }
    
    /**
     * Handle login (mock implementation)
     */
    async function handleLogin() {
        console.log('Login clicked');
        const email = document.getElementById('email')?.value;
        const password = document.getElementById('password')?.value;
        
        if (!email || !password) {
            alert('Please enter email and password');
            return;
        }
        
        try {
            if (loginButton) {
                loginButton.disabled = true;
                loginButton.innerHTML = '<span class="loading"></span> Logging in...';
            }
            
            // Mock login - just update UI
            await new Promise(resolve => setTimeout(resolve, 1000));
            updateUIAfterAuth();
            
        } catch (error) {
            alert('Login failed: ' + error.message);
        } finally {
            if (loginButton) {
                loginButton.disabled = false;
                loginButton.innerHTML = 'Login';
            }
        }
    }
    
    /**
     * Handle registration (mock implementation)
     */
    async function handleRegister() {
        console.log('Register clicked');
        const email = document.getElementById('registerEmail')?.value;
        const password = document.getElementById('registerPassword')?.value;
        const confirmPassword = document.getElementById('confirmPassword')?.value;
        
        if (!email || !password || !confirmPassword) {
            alert('Please fill all fields');
            return;
        }
        
        if (password !== confirmPassword) {
            alert('Passwords do not match');
            return;
        }
        
        try {
            if (registerButton) {
                registerButton.disabled = true;
                registerButton.innerHTML = '<span class="loading"></span> Registering...';
            }
            
            // Mock registration
            await new Promise(resolve => setTimeout(resolve, 1000));
            
            // Show login form after successful registration
            if (registerForm && loginForm) {
                registerForm.style.display = 'none';
                loginForm.style.display = 'block';
            }
            
            // Pre-fill email
            const emailInput = document.getElementById('email');
            if (emailInput) emailInput.value = email;
            
            alert('Registration successful! You can now log in.');
        } catch (error) {
            alert('Registration failed: ' + error.message);
        } finally {
            if (registerButton) {
                registerButton.disabled = false;
                registerButton.innerHTML = 'Register';
            }
        }
    }
    
    /**
     * Handle logout
     */
    function handleLogout() {
        console.log('Logout clicked');
        // Clear chat sessions and reset UI
        chatSessions = {};
        currentConversationId = null;
        localStorage.removeItem('techTranslatorChats');
        updateUIAfterLogout();
    }
    
    /**
     * Update UI after successful authentication
     */
    function updateUIAfterAuth() {
        console.log('Updating UI after auth');
        
        // Only hide auth section if it exists
        if (authSection) {
            authSection.style.display = 'none';
        }
        
        // Show chat section if it exists
        if (chatSection) {
            chatSection.style.display = 'block';
        }
    }
    
    /**
     * Update UI after logout
     */
    function updateUIAfterLogout() {
        console.log('Updating UI after logout');
        
        if (authSection) {
            authSection.style.display = 'block';
        }
        
        if (chatSection) {
            chatSection.style.display = 'none';
        }
        
        if (loginForm) loginForm.style.display = 'block';
        if (registerForm) registerForm.style.display = 'none';
        
        // Clear forms
        const forms = ['email', 'password', 'registerEmail', 'registerPassword', 'confirmPassword'];
        forms.forEach(id => {
            const element = document.getElementById(id);
            if (element) element.value = '';
        });
    }
    
    /**
     * Create a new chat session
     */
    function createNewChat() {
        console.log('Creating new chat');
        
        // Generate new conversation ID
        const newConversationId = generateConversationId();
        currentConversationId = newConversationId;
        
        // Create new chat session - IMPORTANT: Start with empty messages
        const chatSession = {
            id: newConversationId,
            title: `Chat ${chatCounter}`,
            messages: [], // Start empty - no welcome message stored
            concept: null,
            audience: null,
            createdAt: new Date().toISOString()
        };
        
        chatSessions[newConversationId] = chatSession;
        chatCounter++;
        
        // Clear current chat display
        if (messageContainer) {
            messageContainer.innerHTML = '';
        }
        
        // Add welcome message to display ONLY (don't store it)
        addWelcomeMessage();
        
        // Update chat title
        updateChatTitle(chatSession.title);
        
        // Update chat list
        updateChatList();
        
        // Save to localStorage
        saveChatSessions();
        
        // Focus on input
        if (userInput) userInput.focus();
    }
    
    /**
     * Add welcome message to display without storing it
     */
    function addWelcomeMessage() {
        if (!messageContainer) return;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = 'bot-message';
        messageDiv.setAttribute('data-welcome', 'true'); // Mark as welcome message
        
        const textDiv = document.createElement('div');
        textDiv.textContent = "Hello! I'm TechTranslator. I can explain data science and machine learning concepts for insurance professionals. Try asking me about concepts like \"R-squared\", \"loss ratio\", or \"predictive models\". You can also specify your role (e.g., \"Explain R-squared to an underwriter\").";
        messageDiv.appendChild(textDiv);
        
        messageContainer.appendChild(messageDiv);
        
        // Auto-scroll to the bottom only if page is ready
        if (pageLoaded && chatContainer) {
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
    }
    
    /**
     * Switch to an existing chat
     */
    function switchToChat(conversationId) {
        console.log('Switching to chat:', conversationId);
        
        if (!chatSessions[conversationId]) return;
        
        currentConversationId = conversationId;
        const chatSession = chatSessions[conversationId];
        
        // Clear current chat display
        if (messageContainer) {
            messageContainer.innerHTML = '';
        }
        
        // Always show welcome message first (but don't store it)
        addWelcomeMessage();
        
        // Load messages from this chat session (stored messages only)
        chatSession.messages.forEach(msg => {
            addMessageToDisplay(msg.content, msg.isUser, msg.extraInfo, false); // false = don't store
        });
        
        // Update chat title
        updateChatTitle(chatSession.title);
        
        // Update chat list to show active chat
        updateChatList();
        
        // Focus on input
        if (userInput) userInput.focus();
    }
    
    /**
     * Update chat title
     */
    function updateChatTitle(title) {
        if (currentChatTitle) {
            currentChatTitle.textContent = title;
        }
    }
    
    /**
     * Update the chat list in the sidebar
     */
    function updateChatList() {
        if (!conversationHistory) return;
        
        conversationHistory.innerHTML = '';
        
        // Sort chats by creation date (newest first)
        const sortedChats = Object.values(chatSessions).sort((a, b) => 
            new Date(b.createdAt) - new Date(a.createdAt)
        );
        
        sortedChats.forEach(chat => {
            const chatItem = document.createElement('div');
            chatItem.className = `list-group-item list-group-item-action conversation-item ${
                chat.id === currentConversationId ? 'active' : ''
            }`;
            
            const chatTitle = document.createElement('div');
            chatTitle.className = 'fw-bold';
            chatTitle.textContent = chat.title;
            
            const chatPreview = document.createElement('div');
            chatPreview.className = 'text-muted small';
            
            // Show preview of last user message or concept info
            if (chat.messages.length > 0) {
                const lastUserMessage = chat.messages.filter(m => m.isUser).pop();
                if (lastUserMessage) {
                    chatPreview.textContent = lastUserMessage.content.substring(0, 50) + 
                        (lastUserMessage.content.length > 50 ? '...' : '');
                } else if (chat.concept) {
                    chatPreview.textContent = `About: ${chat.concept}`;
                } else {
                    chatPreview.textContent = 'New conversation';
                }
            } else {
                chatPreview.textContent = 'New conversation';
            }
            
            chatItem.appendChild(chatTitle);
            chatItem.appendChild(chatPreview);
            
            // Add click handler
            chatItem.addEventListener('click', () => switchToChat(chat.id));
            
            conversationHistory.appendChild(chatItem);
        });
    }
    
    /**
     * Generate a unique conversation ID
     */
    function generateConversationId() {
        return 'chat_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
    
    /**
     * Add a message to the current chat (stores the message)
     */
    function addMessage(message, isUser, extraInfo = null) {
        // Add to display
        addMessageToDisplay(message, isUser, extraInfo, true); // true = store the message
    }
    
    /**
     * Add message to display with option to store or not
     */
    function addMessageToDisplay(message, isUser, extraInfo = null, shouldStore = true) {
        if (!messageContainer) return;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = isUser ? 'user-message' : 'bot-message';
        
        // For bot messages, show extra info like concept/audience
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
        
        // Only store the message if requested
        if (shouldStore && chatSessions[currentConversationId]) {
            chatSessions[currentConversationId].messages.push({
                content: message,
                isUser: isUser,
                extraInfo: extraInfo,
                timestamp: new Date().toISOString()
            });
            
            // Update chat title based on first user message or detected concept
            if (isUser && chatSessions[currentConversationId].messages.filter(m => m.isUser).length === 1) {
                // This is the first user message, use it to create a meaningful title
                const title = message.length > 30 ? message.substring(0, 30) + '...' : message;
                chatSessions[currentConversationId].title = title;
                updateChatTitle(title);
            } else if (!isUser && extraInfo?.concept) {
                // Update concept info
                chatSessions[currentConversationId].concept = extraInfo.concept;
                chatSessions[currentConversationId].audience = extraInfo.audience;
            }
            
            saveChatSessions();
            updateChatList();
        }
        
        // Auto-scroll to the bottom only if page is ready
        if (pageLoaded && chatContainer) {
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
    }
    
    /**
     * Add a loading indicator to the chat
     */
    function addLoadingIndicator() {
        if (!messageContainer) return null;
        
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'bot-message loading-message';
        loadingDiv.innerHTML = '<span class="loading"></span> Thinking...';
        messageContainer.appendChild(loadingDiv);
        
        // Auto-scroll to the bottom
        if (chatContainer) {
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
        
        return loadingDiv;
    }
    
    /**
     * Get conversation context for follow-up questions
     */
    function getConversationContext() {
        if (!chatSessions[currentConversationId]) return null;
        
        const session = chatSessions[currentConversationId];
        
        // If we have previous messages, try to get the last concept/audience
        if (session.messages.length > 0) {
            // Look for the most recent bot message with concept info
            for (let i = session.messages.length - 1; i >= 0; i--) {
                const msg = session.messages[i];
                if (!msg.isUser && msg.extraInfo && msg.extraInfo.concept) {
                    return {
                        concept: msg.extraInfo.concept,
                        audience: msg.extraInfo.audience
                    };
                }
            }
        }
        
        // Fall back to session-level concept/audience
        if (session.concept) {
            return {
                concept: session.concept,
                audience: session.audience
            };
        }
        
        return null;
    }
    
    /**
     * Send a message to the API
     */
    async function sendMessage() {
        if (!userInput) return;
        
        const message = userInput.value.trim();
        if (!message) return;
        
        console.log('Sending message:', message);
        
        // Add user message to chat
        addMessage(message, true);
        userInput.value = '';
        
        // Add loading indicator
        const loadingIndicator = addLoadingIndicator();
        
        try {
            if (sendButton) sendButton.disabled = true;
            userInput.disabled = true;
            
            // For follow-up questions, we need to provide context
            // Check if this looks like a follow-up question
            const followUpKeywords = ['example', 'more', 'explain', 'tell me', 'what about', 'can you', 'how about'];
            const isFollowUp = followUpKeywords.some(keyword => message.toLowerCase().includes(keyword)) && message.length < 50;
            
            let queryToSend = message;
            let contextualInfo = null;
            
            if (isFollowUp) {
                // Get the previous conversation context
                contextualInfo = getConversationContext();
                if (contextualInfo) {
                    // Enhance the query with context for better API response
                    queryToSend = `${message} (continuing discussion about ${contextualInfo.concept} for ${contextualInfo.audience})`;
                    console.log('Follow-up detected, enhanced query:', queryToSend);
                }
            }
            
            // Call API - use the current conversation ID for follow-up context
            const data = await apiService.sendQuery(queryToSend, currentConversationId);
            
            // For follow-up questions, preserve the context if API doesn't provide it
            if (isFollowUp && contextualInfo && (!data.concept || data.concept === 'predictive-model')) {
                console.log('Preserving context for follow-up question');
                data.concept = contextualInfo.concept;
                data.audience = contextualInfo.audience;
            }
            
            // Remove loading indicator
            if (loadingIndicator) loadingIndicator.remove();
            
            // Add bot response to chat with extra info
            addMessage(data.response, false, {
                concept: data.concept,
                audience: data.audience
            });
            
            // Update current conversation ID (API might return a new one for first message)
            if (data.conversation_id && data.conversation_id !== currentConversationId) {
                // Update the chat session ID if API returned a different one
                const oldId = currentConversationId;
                const newId = data.conversation_id;
                
                if (chatSessions[oldId]) {
                    chatSessions[newId] = chatSessions[oldId];
                    chatSessions[newId].id = newId;
                    delete chatSessions[oldId];
                    currentConversationId = newId;
                    saveChatSessions();
                    updateChatList();
                }
            }
            
        } catch (error) {
            console.error('Error sending message:', error);
            
            // Remove loading indicator
            if (loadingIndicator) loadingIndicator.remove();
            
            // Show user-friendly error message
            let errorMessage = 'Sorry, there was an error processing your request.';
            
            if (error.message.includes('AI model is not available') || 
                error.message.includes('AI service temporarily unavailable')) {
                errorMessage = 'The AI service is not available. Please ensure the SageMaker endpoint is deployed and configured.';
            } else if (error.message.includes('Failed to fetch')) {
                errorMessage = 'Unable to connect to the server. Please check your connection and try again.';
            }
            
            addMessage(errorMessage, false);
        } finally {
            if (sendButton) sendButton.disabled = false;
            userInput.disabled = false;
            if (userInput) userInput.focus();
        }
    }
    
    /**
     * Save chat sessions to localStorage
     */
    function saveChatSessions() {
        try {
            localStorage.setItem('techTranslatorChats', JSON.stringify(chatSessions));
        } catch (error) {
            console.warn('Could not save chat sessions to localStorage:', error);
        }
    }
    
    /**
     * Load chat sessions from localStorage
     */
    function loadChatSessions() {
        try {
            const saved = localStorage.getItem('techTranslatorChats');
            if (saved) {
                const parsedSessions = JSON.parse(saved);
                
                // Merge with existing sessions
                Object.assign(chatSessions, parsedSessions);
                
                // Update chat counter
                const maxChatNumber = Object.values(chatSessions)
                    .map(chat => {
                        const match = chat.title.match(/Chat (\d+)/);
                        return match ? parseInt(match[1]) : 0;
                    })
                    .reduce((max, num) => Math.max(max, num), 0);
                
                chatCounter = maxChatNumber + 1;
                
                // Update chat list
                updateChatList();
            }
        } catch (error) {
            console.warn('Could not load chat sessions from localStorage:', error);
        }
    }
});