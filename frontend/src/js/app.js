/**
 * Main application logic for TechTranslator - Email-based User ID Version
 */
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded - starting app with email-based user ID');
    
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
    let userEmail = null;
    
    // Mark page as loaded after a short delay
    setTimeout(() => {
        pageLoaded = true;
        console.log('Page ready for interactions');
    }, 500);
    
    // Initialize UI with email check
    initializeWithEmail();
    
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
    
    // ==========================================
    // EMAIL-BASED USER ID FUNCTIONS
    // ==========================================
    
    function getUserEmail() {
        let email = localStorage.getItem('user_email');
        
        if (!email || !isValidEmail(email)) {
            return null; // Will trigger email modal
        }
        
        return email.toLowerCase().trim();
    }
    
    function isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }
    
    function initializeWithEmail() {
        console.log('Initializing with email check...');
        
        userEmail = getUserEmail();
        
        if (!userEmail) {
            showEmailModal();
        } else {
            continueInitialization();
        }
    }
    
    function showEmailModal() {
        // Create modal HTML
        const modalHTML = `
            <div id="emailModal" class="modal" style="display: block; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.8);">
                <div class="modal-content" style="background-color: #ffffff; margin: 10% auto; padding: 30px; border-radius: 15px; width: 450px; max-width: 90%; box-shadow: 0 10px 30px rgba(0,0,0,0.3);">
                    <div style="text-align: center; margin-bottom: 25px;">
                        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); width: 60px; height: 60px; border-radius: 50%; margin: 0 auto 15px; display: flex; align-items: center; justify-content: center;">
                            <i class="bi bi-envelope" style="color: white; font-size: 24px;"></i>
                        </div>
                        <h3 style="color: #2c3e50; margin: 0; font-size: 24px;">Welcome to TechTranslator</h3>
                        <p style="color: #5a6c7d; margin: 10px 0 0 0; font-size: 16px;">AI-powered insurance concept explanations</p>
                    </div>
                    
                    <p style="color: #5a6c7d; margin-bottom: 25px; text-align: center; line-height: 1.5;">
                        Enter your email to personalize your experience and save your conversation history across sessions.
                    </p>
                    
                    <div class="form-group" style="margin-bottom: 20px;">
                        <input type="email" id="modalEmail" placeholder="your.email@company.com" 
                               style="width: 100%; padding: 15px; border: 2px solid #e9ecef; border-radius: 10px; font-size: 16px; box-sizing: border-box;"
                               required>
                        <div id="emailError" style="color: #dc3545; font-size: 14px; margin-top: 5px; display: none;">
                            Please enter a valid email address
                        </div>
                    </div>
                    
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <button id="skipEmail" style="background: none; border: none; color: #6c757d; cursor: pointer; font-size: 14px; text-decoration: underline;">
                            Skip for now
                        </button>
                        <button id="saveEmail" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; padding: 12px 25px; border-radius: 8px; cursor: pointer; font-size: 16px; font-weight: 500;">
                            Get Started
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        // Add modal to page
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        
        // Add event listeners
        document.getElementById('saveEmail').addEventListener('click', handleEmailSave);
        document.getElementById('skipEmail').addEventListener('click', handleEmailSkip);
        document.getElementById('modalEmail').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') handleEmailSave();
        });
        
        // Focus on input
        setTimeout(() => {
            document.getElementById('modalEmail').focus();
        }, 100);
    }
    
    function handleEmailSave() {
        const emailInput = document.getElementById('modalEmail');
        const errorDiv = document.getElementById('emailError');
        const email = emailInput.value.trim().toLowerCase();
        
        if (isValidEmail(email)) {
            localStorage.setItem('user_email', email);
            userEmail = email;
            closeEmailModal();
            continueInitialization();
            console.log('User email saved:', email);
        } else {
            errorDiv.style.display = 'block';
            emailInput.style.borderColor = '#dc3545';
            emailInput.focus();
        }
    }
    
    function handleEmailSkip() {
        const anonymousEmail = 'user_' + Date.now() + '@anonymous.local';
        localStorage.setItem('user_email', anonymousEmail);
        userEmail = anonymousEmail;
        closeEmailModal();
        continueInitialization();
        console.log('Using anonymous email:', anonymousEmail);
    }
    
    function closeEmailModal() {
        const modal = document.getElementById('emailModal');
        if (modal) {
            modal.remove();
        }
    }
    
    function continueInitialization() {
        console.log('Continuing initialization with email:', userEmail);
        
        // Update UI to show authenticated state
        updateUIAfterAuth();
        
        // Update user display
        updateUserEmailDisplay();
        
        // Load chat sessions
        loadChatSessions();
        
        // Create first chat if needed
        if (Object.keys(chatSessions).length === 0) {
            createNewChat();
        } else {
            // Switch to most recent chat
            const sortedChats = Object.values(chatSessions).sort((a, b) => 
                new Date(b.createdAt) - new Date(a.createdAt)
            );
            if (sortedChats.length > 0) {
                switchToChat(sortedChats[0].id);
            }
        }
    }
    
    function updateUserEmailDisplay() {
        const sidebar = document.querySelector('.sidebar');
        if (!sidebar || !userEmail) return;
        
        // Remove existing display
        const existingDisplay = sidebar.querySelector('.user-email-display');
        if (existingDisplay) existingDisplay.remove();
        
        // Create user email display
        const userDisplay = document.createElement('div');
        userDisplay.className = 'user-email-display';
        userDisplay.style.cssText = `
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px;
            border-radius: 10px;
            font-size: 0.9rem;
            margin-bottom: 15px;
            word-break: break-word;
            cursor: pointer;
            transition: transform 0.2s;
        `;
        
        const isAnonymous = userEmail.includes('@anonymous.local');
        const displayName = getDisplayName(userEmail);
        const displayEmail = isAnonymous ? 'Anonymous User' : userEmail;
        
        userDisplay.innerHTML = `
            <div style="display: flex; align-items: center; margin-bottom: 4px;">
                <i class="bi bi-person-circle" style="margin-right: 8px; font-size: 16px;"></i>
                <span style="font-weight: 500;">${displayName}</span>
            </div>
            <div style="font-size: 0.8em; opacity: 0.9;">${displayEmail}</div>
            ${isAnonymous ? '<div style="font-size: 0.75em; opacity: 0.8; margin-top: 4px;">Click to set your email</div>' : ''}
        `;
        
        // Add hover effect
        userDisplay.addEventListener('mouseenter', () => {
            userDisplay.style.transform = 'translateY(-2px)';
        });
        
        userDisplay.addEventListener('mouseleave', () => {
            userDisplay.style.transform = 'translateY(0)';
        });
        
        // Add click to change email
        userDisplay.addEventListener('click', () => {
            const newEmail = prompt('Enter your email address:', isAnonymous ? '' : userEmail);
            if (newEmail && isValidEmail(newEmail)) {
                localStorage.setItem('user_email', newEmail.toLowerCase().trim());
                location.reload();
            }
        });
        
        // Insert after the TechTranslator title
        const title = sidebar.querySelector('h5');
        if (title) {
            title.parentNode.insertBefore(userDisplay, title.nextSibling);
        }
    }
    
    function getDisplayName(email) {
        if (email.includes('@anonymous.local')) {
            return 'Anonymous User';
        }
        
        const localPart = email.split('@')[0];
        return localPart.replace(/[._]/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    }
    
    // ==========================================
    // EXISTING FUNCTIONS (Updated for Email)
    // ==========================================
    
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
        localStorage.removeItem('user_email');
        location.reload(); // Restart with email modal
    }
    
    /**
     * Update UI after successful authentication
     */
    function updateUIAfterAuth() {
        console.log('Updating UI after auth');
        
        if (authSection) {
            authSection.style.display = 'none';
        }
        
        if (chatSection) {
            chatSection.style.display = 'block';
        }
    }
    
    /**
     * Send a message to the API (Updated with email user context)
     */
    async function sendMessage() {
        if (!userInput || !userEmail) return;
        
        const message = userInput.value.trim();
        if (!message) return;

        console.log('Sending message:', message, 'for user:', userEmail);

        // Add user message to chat
        addMessage(message, true);
        userInput.value = '';

        // Add loading indicator
        const loadingIndicator = addLoadingIndicator();

        try {
            if (sendButton) sendButton.disabled = true;
            userInput.disabled = true;
            
            // Enhanced query with user context for follow-up questions
            const followUpKeywords = ['example', 'more', 'explain', 'tell me', 'what about', 'can you', 'how about'];
            const isFollowUp = followUpKeywords.some(keyword => message.toLowerCase().includes(keyword)) && message.length < 50;

            let queryToSend = message;
            let contextualInfo = null;

            if (isFollowUp) {
                contextualInfo = getConversationContext();
                if (contextualInfo) {
                    queryToSend = `${message} (continuing discussion about ${contextualInfo.concept} for ${contextualInfo.audience})`;
                    console.log('Follow-up detected, enhanced query:', queryToSend);
                }
            }

            // Update API service to include user email
            const originalSendQuery = apiService.sendQuery;
            apiService.sendQuery = async function(query, conversationId) {
                // Override to include user email in request
                const response = await fetch(`${this.apiUrl}/query`, {
                    method: 'POST',
                    headers: {
                        ...this.getHeaders(),
                        'X-User-Context': userEmail  // Add email in header
                    },
                    body: JSON.stringify({ 
                        query,
                        conversation_id: conversationId,
                        user_context: userEmail  // Also in body
                    })
                });
                
                if (!response.ok) {
                    let errorData;
                    try {
                        errorData = await response.json();
                    } catch (e) {
                        errorData = { error: `Request failed with status ${response.status}` };
                    }
                    throw new Error(errorData.error || `API request failed: ${response.statusText}`);
                }
                
                return await response.json();
            };

            const data = await apiService.sendQuery(queryToSend, currentConversationId);

            // Remove loading indicator
            if (loadingIndicator) loadingIndicator.remove();

            // For follow-up questions, preserve the context if API doesn't provide it
            if (isFollowUp && contextualInfo && (!data.concept || data.concept === 'predictive-model')) {
                console.log('Preserving context for follow-up question');
                data.concept = contextualInfo.concept;
                data.audience = contextualInfo.audience;
            }

            // Add bot response to chat with extra info
            addMessage(data.response, false, {
                concept: data.concept,
                audience: data.audience
            });

            // Update current conversation ID
            if (data.conversation_id && data.conversation_id !== currentConversationId) {
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
    
    // ==========================================
    // REST OF EXISTING FUNCTIONS (Unchanged)
    // ==========================================
    
    /**
     * Create a new chat session
     */
    function createNewChat() {
        console.log('Creating new chat');
        
        const newConversationId = generateConversationId();
        currentConversationId = newConversationId;
        
        const chatSession = {
            id: newConversationId,
            title: `Chat ${chatCounter}`,
            messages: [],
            concept: null,
            audience: null,
            createdAt: new Date().toISOString()
        };
        
        chatSessions[newConversationId] = chatSession;
        chatCounter++;
        
        if (messageContainer) {
            messageContainer.innerHTML = '';
        }
        
        addWelcomeMessage();
        updateChatTitle(chatSession.title);
        updateChatList();
        saveChatSessions();
        
        if (userInput) userInput.focus();
    }
    
    function addWelcomeMessage() {
        if (!messageContainer) return;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = 'bot-message';
        messageDiv.setAttribute('data-welcome', 'true');
        
        const textDiv = document.createElement('div');
        textDiv.textContent = "Hello! I'm TechTranslator. I can explain data science and machine learning concepts for insurance professionals. Try asking me about concepts like \"R-squared\", \"loss ratio\", or \"predictive models\". You can also specify your role (e.g., \"Explain R-squared to an underwriter\").";
        messageDiv.appendChild(textDiv);
        
        messageContainer.appendChild(messageDiv);
        
        if (pageLoaded && chatContainer) {
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
    }
    
    function switchToChat(conversationId) {
        console.log('Switching to chat:', conversationId);
        
        if (!chatSessions[conversationId]) return;
        
        currentConversationId = conversationId;
        const chatSession = chatSessions[conversationId];
        
        if (messageContainer) {
            messageContainer.innerHTML = '';
        }
        
        addWelcomeMessage();
        
        chatSession.messages.forEach(msg => {
            addMessageToDisplay(msg.content, msg.isUser, msg.extraInfo, false);
        });
        
        updateChatTitle(chatSession.title);
        updateChatList();
        
        if (userInput) userInput.focus();
    }
    
    function updateChatTitle(title) {
        if (currentChatTitle) {
            currentChatTitle.textContent = title;
        }
    }
    
    function updateChatList() {
        if (!conversationHistory) return;
        
        conversationHistory.innerHTML = '';
        
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
            
            chatItem.addEventListener('click', () => switchToChat(chat.id));
            
            conversationHistory.appendChild(chatItem);
        });
    }
    
    function generateConversationId() {
        return 'chat_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
    
    function addMessage(message, isUser, extraInfo = null) {
        addMessageToDisplay(message, isUser, extraInfo, true);
    }
    
    function addMessageToDisplay(message, isUser, extraInfo = null, shouldStore = true) {
        if (!messageContainer) return;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = isUser ? 'user-message' : 'bot-message';
        
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
        
        if (shouldStore && chatSessions[currentConversationId]) {
            chatSessions[currentConversationId].messages.push({
                content: message,
                isUser: isUser,
                extraInfo: extraInfo,
                timestamp: new Date().toISOString()
            });
            
            if (isUser && chatSessions[currentConversationId].messages.filter(m => m.isUser).length === 1) {
                const title = message.length > 30 ? message.substring(0, 30) + '...' : message;
                chatSessions[currentConversationId].title = title;
                updateChatTitle(title);
            } else if (!isUser && extraInfo?.concept) {
                chatSessions[currentConversationId].concept = extraInfo.concept;
                chatSessions[currentConversationId].audience = extraInfo.audience;
            }
            
            saveChatSessions();
            updateChatList();
        }
        
        if (pageLoaded && chatContainer) {
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
    }
    
    function addLoadingIndicator() {
        if (!messageContainer) return null;
        
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'bot-message loading-message';
        loadingDiv.innerHTML = '<span class="loading"></span> Thinking...';
        messageContainer.appendChild(loadingDiv);
        
        if (chatContainer) {
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
        
        return loadingDiv;
    }
    
    function getConversationContext() {
        if (!chatSessions[currentConversationId]) return null;
        
        const session = chatSessions[currentConversationId];
        
        if (session.messages.length > 0) {
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
        
        if (session.concept) {
            return {
                concept: session.concept,
                audience: session.audience
            };
        }
        
        return null;
    }
    
    function saveChatSessions() {
        try {
            localStorage.setItem('techTranslatorChats', JSON.stringify(chatSessions));
        } catch (error) {
            console.warn('Could not save chat sessions to localStorage:', error);
        }
    }
    
    function loadChatSessions() {
        try {
            const saved = localStorage.getItem('techTranslatorChats');
            if (saved) {
                const parsedSessions = JSON.parse(saved);
                Object.assign(chatSessions, parsedSessions);
                
                const maxChatNumber = Object.values(chatSessions)
                    .map(chat => {
                        const match = chat.title.match(/Chat (\d+)/);
                        return match ? parseInt(match[1]) : 0;
                    })
                    .reduce((max, num) => Math.max(max, num), 0);
                
                chatCounter = maxChatNumber + 1;
                updateChatList();
            }
        } catch (error) {
            console.warn('Could not load chat sessions from localStorage:', error);
        }
    }
});