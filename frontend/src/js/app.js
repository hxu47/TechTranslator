/**
 * Main application logic for TechTranslator - With Real Authentication
 */
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded - starting app with authentication');
    
    // DOM Elements - with null checks
    const authSection = document.getElementById('authSection');
    const chatSection = document.getElementById('chatSection');
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');
    const confirmForm = document.getElementById('confirmForm');
    const showRegisterButton = document.getElementById('showRegisterButton');
    const showLoginButton = document.getElementById('showLoginButton');
    const loginButton = document.getElementById('loginButton');
    const registerButton = document.getElementById('registerButton');
    const confirmButton = document.getElementById('confirmButton');
    const resendCodeButton = document.getElementById('resendCodeButton');
    const logoutButton = document.getElementById('logoutButton');
    const chatContainer = document.getElementById('chatContainer');
    const messageContainer = document.getElementById('messageContainer');
    const userInput = document.getElementById('userInput');
    const sendButton = document.getElementById('sendButton');
    const conversationHistory = document.getElementById('conversationHistory');
    const newChatButton = document.getElementById('newChatButton');
    const currentChatTitle = document.getElementById('currentChatTitle');
    const userEmailDisplay = document.getElementById('userEmailDisplay');
    
    // Chat management
    let currentConversationId = null;
    let chatSessions = {};
    let chatCounter = 1;
    let pageLoaded = false;
    let pendingRegistrationEmail = null;
    
    // Mark page as loaded after a short delay
    setTimeout(() => {
        pageLoaded = true;
        console.log('Page ready for interactions');
    }, 500);
    
    // Initialize UI based on authentication status
    initializeUI();
    
    // Event listeners for authentication
    if (showRegisterButton) {
        showRegisterButton.addEventListener('click', () => {
            showRegisterForm();
        });
    }
    
    if (showLoginButton) {
        showLoginButton.addEventListener('click', () => {
            showLoginForm();
        });
    }
    
    if (loginButton) loginButton.addEventListener('click', handleLogin);
    if (registerButton) registerButton.addEventListener('click', handleRegister);
    if (confirmButton) confirmButton.addEventListener('click', handleConfirmRegistration);
    if (resendCodeButton) resendCodeButton.addEventListener('click', handleResendCode);
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
     * Initialize UI based on authentication status
     */
    async function initializeUI() {
        console.log('Initializing UI with authentication check');
        
        // Check if user is already authenticated
        const isAuthenticated = await authService.checkExistingSession();
        
        if (isAuthenticated) {
            console.log('User is authenticated, showing chat interface');
            updateUIAfterAuth();
            loadUserData();
        } else {
            console.log('User not authenticated, showing login form');
            updateUIAfterLogout();
        }
    }
    
    /**
     * Show login form
     */
    function showLoginForm() {
        if (loginForm && registerForm && confirmForm) {
            loginForm.style.display = 'block';
            registerForm.style.display = 'none';
            confirmForm.style.display = 'none';
        }
        clearForms();
    }
    
    /**
     * Show register form
     */
    function showRegisterForm() {
        if (registerForm && loginForm && confirmForm) {
            registerForm.style.display = 'block';
            loginForm.style.display = 'none';
            confirmForm.style.display = 'none';
        }
        clearForms();
    }
    
    /**
     * Show confirmation form
     */
    function showConfirmForm() {
        if (confirmForm && loginForm && registerForm) {
            confirmForm.style.display = 'block';
            loginForm.style.display = 'none';
            registerForm.style.display = 'none';
        }
    }
    
    /**
     * Handle login
     */
    async function handleLogin() {
        console.log('Login clicked');
        const email = document.getElementById('email')?.value;
        const password = document.getElementById('password')?.value;
        
        if (!email || !password) {
            showError('Please enter email and password');
            return;
        }
        
        try {
            if (loginButton) {
                loginButton.disabled = true;
                loginButton.innerHTML = '<span class="loading"></span> Logging in...';
            }
            
            const result = await authService.login(email, password);
            
            if (result.success) {
                console.log('Login successful');
                updateUIAfterAuth();
                loadUserData();
                //showSuccess('Login successful!');
            } else if (result.challenge) {
                showError(result.message || 'Additional authentication required');
                // Handle challenges if needed
            }
            
        } catch (error) {
            console.error('Login failed:', error);
            showError('Login failed: ' + error.message);
        } finally {
            if (loginButton) {
                loginButton.disabled = false;
                loginButton.innerHTML = 'Login';
            }
        }
    }
    
    /**
     * Handle registration
     */
    async function handleRegister() {
        console.log('Register clicked');
        const email = document.getElementById('registerEmail')?.value;
        const password = document.getElementById('registerPassword')?.value;
        const confirmPassword = document.getElementById('confirmPassword')?.value;
        const name = document.getElementById('registerName')?.value || '';
        
        if (!email || !password || !confirmPassword) {
            showError('Please fill all required fields');
            return;
        }
        
        if (password !== confirmPassword) {
            showError('Passwords do not match');
            return;
        }
        
        if (password.length < 8) {
            showError('Password must be at least 8 characters long');
            return;
        }
        
        try {
            if (registerButton) {
                registerButton.disabled = true;
                registerButton.innerHTML = '<span class="loading"></span> Registering...';
            }
            
            const result = await authService.register(email, password, name);
            
            if (result.success) {
                pendingRegistrationEmail = email;
                
                if (result.needsConfirmation) {
                    showConfirmForm();
                    showSuccess('Registration successful! Please check your email for a verification code.');
                    
                    // Pre-fill email in confirmation form
                    const confirmEmailInput = document.getElementById('confirmEmail');
                    if (confirmEmailInput) confirmEmailInput.value = email;
                } else {
                    // Auto-confirmed, go to login
                    showLoginForm();
                    const emailInput = document.getElementById('email');
                    if (emailInput) emailInput.value = email;
                    showSuccess('Registration successful! You can now log in.');
                }
            }
        } catch (error) {
            console.error('Registration failed:', error);
            showError('Registration failed: ' + error.message);
        } finally {
            if (registerButton) {
                registerButton.disabled = false;
                registerButton.innerHTML = 'Register';
            }
        }
    }
    
    /**
     * Handle email confirmation
     */
    async function handleConfirmRegistration() {
        console.log('Confirm registration clicked');
        const email = document.getElementById('confirmEmail')?.value || pendingRegistrationEmail;
        const code = document.getElementById('confirmationCode')?.value;
        
        if (!email || !code) {
            showError('Please enter email and confirmation code');
            return;
        }
        
        try {
            if (confirmButton) {
                confirmButton.disabled = true;
                confirmButton.innerHTML = '<span class="loading"></span> Confirming...';
            }
            
            const result = await authService.confirmRegistration(email, code);
            
            if (result.success) {
                showLoginForm();
                
                // Pre-fill email
                const emailInput = document.getElementById('email');
                if (emailInput) emailInput.value = email;
                
                showSuccess('Email confirmed successfully! You can now log in.');
                pendingRegistrationEmail = null;
            }
        } catch (error) {
            console.error('Confirmation failed:', error);
            showError('Confirmation failed: ' + error.message);
        } finally {
            if (confirmButton) {
                confirmButton.disabled = false;
                confirmButton.innerHTML = 'Confirm Email';
            }
        }
    }
    
    /**
     * Handle resend confirmation code
     */
    async function handleResendCode() {
        console.log('Resend code clicked');
        const email = document.getElementById('confirmEmail')?.value || pendingRegistrationEmail;
        
        if (!email) {
            showError('Please enter your email address');
            return;
        }
        
        try {
            if (resendCodeButton) {
                resendCodeButton.disabled = true;
                resendCodeButton.innerHTML = '<span class="loading"></span> Sending...';
            }
            
            const result = await authService.resendConfirmationCode(email);
            
            if (result.success) {
                showSuccess('Confirmation code sent! Please check your email.');
            }
        } catch (error) {
            console.error('Resend failed:', error);
            showError('Failed to resend code: ' + error.message);
        } finally {
            if (resendCodeButton) {
                resendCodeButton.disabled = false;
                resendCodeButton.innerHTML = 'Resend Code';
            }
        }
    }
    
    /**
     * Handle logout
     */
    async function handleLogout() {
        console.log('Logout clicked - starting logout process');
        
        try {
            // Step 1: Call auth service logout
            console.log('Step 1: Calling authService.logout()');
            await authService.logout();
            console.log('Step 1: authService.logout() completed');
            
            // Step 2: Clear chat sessions and reset UI
            console.log('Step 2: Clearing chat sessions');
            chatSessions = {};
            currentConversationId = null;
            localStorage.removeItem('techTranslatorChats');
            console.log('Step 2: Chat sessions cleared');
            
            // Step 3: Force UI update
            console.log('Step 3: Forcing UI update');
            updateUIAfterLogout();
            console.log('Step 3: UI update completed');
            
            console.log('Logout process completed successfully');
            
        } catch (error) {
            console.error('Logout error:', error);
            // Still update UI even if logout fails
            console.log('Error occurred, but still updating UI');
            updateUIAfterLogout();
        }
    }
    
    /**
     * Load user data after authentication
     */
    function loadUserData() {
        // Load chat sessions from localStorage
        loadChatSessions();
        
        // Display user email
        const userEmail = authService.getUserEmail();
        if (userEmailDisplay && userEmail) {
            userEmailDisplay.textContent = userEmail;
        }
        
        // Create the first chat session if no existing sessions
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
     * Update UI after successful authentication
     */
    function updateUIAfterAuth() {
        console.log('Updating UI after auth - WITH CLASSES');
        
        // Remove classes and add new ones
        if (authSection) {
            authSection.classList.add('force-hide');
            authSection.classList.remove('force-show');
            authSection.style.display = 'none';
        }
        
        if (chatSection) {
            chatSection.classList.add('force-show');
            chatSection.classList.remove('force-hide');
            chatSection.style.display = 'flex';
            chatSection.style.flexDirection = 'row';
        }
        
        // Ensure sidebar is visible
        const sidebar = document.querySelector('.sidebar');
        if (sidebar) {
            sidebar.style.display = 'block';
            console.log('Sidebar made visible');
        }
        
        console.log('UI update after auth completed');
    }


    /**
     * Update UI after logout
     */
    function updateUIAfterLogout() {
        console.log('Updating UI after logout - WITH CLASSES');
        
        // Remove classes and add new ones
        if (chatSection) {
            chatSection.classList.add('force-hide');
            chatSection.classList.remove('force-show');
        }
        
        if (authSection) {
            authSection.classList.add('force-show');
            authSection.classList.remove('force-hide');
        }
        
        showLoginForm();
        clearForms();
        
        console.log('UI update with classes completed');
    }
    
    /**
     * Clear all form fields
     */
    function clearForms() {
        const forms = ['email', 'password', 'registerEmail', 'registerPassword', 'confirmPassword', 'registerName', 'confirmEmail', 'confirmationCode'];
        forms.forEach(id => {
            const element = document.getElementById(id);
            if (element) element.value = '';
        });
    }
    
    /**
     * Show error message
     */
    function showError(message) {
        // You can implement a toast notification or alert
        alert('Error: ' + message);
    }
    
    /**
     * Show success message
     */
    function showSuccess(message) {
        // You can implement a toast notification or alert
        alert('Success: ' + message);
    }
    
    // === Chat Functions (same as before) ===
    
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
    
    async function sendMessage() {
        if (!userInput) return;
        
        const message = userInput.value.trim();
        if (!message) return;
        
        console.log('Sending message:', message);
        
        addMessage(message, true);
        userInput.value = '';
        
        const loadingIndicator = addLoadingIndicator();
        
        try {
            if (sendButton) sendButton.disabled = true;
            userInput.disabled = true;
            
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
            
            const data = await apiService.sendQuery(queryToSend, currentConversationId);
            
            if (isFollowUp && contextualInfo && (!data.concept || data.concept === 'predictive-model')) {
                console.log('Preserving context for follow-up question');
                data.concept = contextualInfo.concept;
                data.audience = contextualInfo.audience;
            }
            
            if (loadingIndicator) loadingIndicator.remove();
            
            addMessage(data.response, false, {
                concept: data.concept,
                audience: data.audience
            });
            
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
            
            if (loadingIndicator) loadingIndicator.remove();
            
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