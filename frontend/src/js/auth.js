/**
 * Authentication service for TechTranslator
 * Real Cognito implementation using AWS SDK
 */
class AuthService {
    constructor() {
        // Cognito parameters - to be replaced during deployment
        this.userPoolId = 'YOUR_USER_POOL_ID';
        this.clientId = 'YOUR_CLIENT_ID';
        this.region = 'us-east-1';
        this.isAuthenticated = false;
        this.token = null;
        this.user = null;
        
        // Initialize Cognito
        this.initializeCognito();
        
        // Check for existing session
        this.checkExistingSession();
    }
    
    /**
     * Initialize AWS Cognito SDK
     */
    initializeCognito() {
        // Configure AWS SDK
        AWS.config.region = this.region;
        
        // Create Cognito Identity Service Provider
        this.cognitoIdentityServiceProvider = new AWS.CognitoIdentityServiceProvider();
        
        // User pool configuration
        this.poolData = {
            UserPoolId: this.userPoolId,
            ClientId: this.clientId
        };
        
        console.log('Cognito initialized with pool:', this.userPoolId);
    }
    
    /**
     * Check for existing authenticated session
     */
    async checkExistingSession() {
        try {
            const accessToken = localStorage.getItem('accessToken');
            const idToken = localStorage.getItem('idToken');
            const refreshToken = localStorage.getItem('refreshToken');
            
            if (accessToken && idToken && refreshToken) {
                // Verify the access token is still valid
                const params = {
                    AccessToken: accessToken
                };
                
                const result = await this.cognitoIdentityServiceProvider.getUser(params).promise();
                
                // Token is valid
                this.token = idToken;
                this.isAuthenticated = true;
                this.user = result;
                apiService.setToken(idToken);
                
                console.log('Restored existing session for user:', result.Username);
                return true;
            }
        } catch (error) {
            console.log('No valid existing session found:', error.message);
            this.clearStoredTokens();
        }
        
        return false;
    }
    
    /**
     * Login user with Cognito
     * @param {string} email - User email
     * @param {string} password - User password
     * @returns {Promise} Promise with login result
     */
    async login(email, password) {
        try {
            const params = {
                AuthFlow: 'USER_PASSWORD_AUTH',
                ClientId: this.clientId,
                AuthParameters: {
                    USERNAME: email,
                    PASSWORD: password
                }
            };
            
            const result = await this.cognitoIdentityServiceProvider.initiateAuth(params).promise();
            
            if (result.AuthenticationResult) {
                // Successful authentication
                const { AccessToken, IdToken, RefreshToken } = result.AuthenticationResult;
                
                // Store tokens
                this.storeTokens(AccessToken, IdToken, RefreshToken);
                
                // Set authentication state
                this.token = IdToken;
                this.isAuthenticated = true;
                
                // Get user info
                await this.getUserInfo(AccessToken);
                
                // Set token in API service
                apiService.setToken(IdToken);
                
                console.log('Login successful for user:', this.user?.Username);
                return { success: true };
                
            } else if (result.ChallengeName) {
                // Handle authentication challenges (MFA, password reset, etc.)
                return { 
                    success: false, 
                    challenge: result.ChallengeName,
                    session: result.Session,
                    message: this.getChallengeMessage(result.ChallengeName)
                };
            }
            
        } catch (error) {
            console.error('Login error:', error);
            
            // Handle specific Cognito errors
            if (error.code === 'NotAuthorizedException') {
                throw new Error('Invalid email or password');
            } else if (error.code === 'UserNotConfirmedException') {
                throw new Error('Please confirm your email address before logging in');
            } else if (error.code === 'UserNotFoundException') {
                throw new Error('User not found. Please check your email address');
            } else if (error.code === 'TooManyRequestsException') {
                throw new Error('Too many login attempts. Please try again later');
            } else {
                throw new Error(error.message || 'Login failed');
            }
        }
    }
    
    /**
     * Register a new user with Cognito
     * @param {string} email - User email
     * @param {string} password - User password
     * @param {string} name - User name
     * @returns {Promise} Promise with registration result
     */
    async register(email, password, name = '') {
        try {
            const params = {
                ClientId: this.clientId,
                Username: email,
                Password: password,
                UserAttributes: [
                    {
                        Name: 'email',
                        Value: email
                    }
                ]
            };
            
            // Add name attribute if provided
            if (name.trim()) {
                params.UserAttributes.push({
                    Name: 'name',
                    Value: name.trim()
                });
            }
            
            const result = await this.cognitoIdentityServiceProvider.signUp(params).promise();
            
            console.log('Registration successful:', result);
            
            return { 
                success: true, 
                needsConfirmation: !result.UserConfirmed,
                userSub: result.UserSub
            };
            
        } catch (error) {
            console.error('Registration error:', error);
            
            // Handle specific Cognito errors
            if (error.code === 'UsernameExistsException') {
                throw new Error('An account with this email already exists');
            } else if (error.code === 'InvalidPasswordException') {
                throw new Error('Password must be at least 8 characters with uppercase, lowercase, and numbers');
            } else if (error.code === 'InvalidParameterException') {
                throw new Error('Invalid email format');
            } else {
                throw new Error(error.message || 'Registration failed');
            }
        }
    }
    
    /**
     * Confirm user registration with verification code
     * @param {string} email - User email
     * @param {string} code - Verification code
     * @returns {Promise} Promise with confirmation result
     */
    async confirmRegistration(email, code) {
        try {
            const params = {
                ClientId: this.clientId,
                Username: email,
                ConfirmationCode: code
            };
            
            await this.cognitoIdentityServiceProvider.confirmSignUp(params).promise();
            
            console.log('Email confirmation successful');
            return { success: true };
            
        } catch (error) {
            console.error('Confirmation error:', error);
            
            if (error.code === 'CodeMismatchException') {
                throw new Error('Invalid verification code');
            } else if (error.code === 'ExpiredCodeException') {
                throw new Error('Verification code has expired');
            } else {
                throw new Error(error.message || 'Email confirmation failed');
            }
        }
    }
    
    /**
     * Resend confirmation code
     * @param {string} email - User email
     * @returns {Promise} Promise with resend result
     */
    async resendConfirmationCode(email) {
        try {
            const params = {
                ClientId: this.clientId,
                Username: email
            };
            
            await this.cognitoIdentityServiceProvider.resendConfirmationCode(params).promise();
            return { success: true };
            
        } catch (error) {
            console.error('Resend confirmation error:', error);
            throw new Error(error.message || 'Failed to resend confirmation code');
        }
    }
    
    /**
     * Get user information
     * @param {string} accessToken - Access token
     */
    async getUserInfo(accessToken) {
        try {
            const params = {
                AccessToken: accessToken
            };
            
            this.user = await this.cognitoIdentityServiceProvider.getUser(params).promise();
            
        } catch (error) {
            console.error('Error getting user info:', error);
        }
    }
    
    /**
     * Store tokens in localStorage
     * @param {string} accessToken - Access token
     * @param {string} idToken - ID token
     * @param {string} refreshToken - Refresh token
     */
    storeTokens(accessToken, idToken, refreshToken) {
        localStorage.setItem('accessToken', accessToken);
        localStorage.setItem('idToken', idToken);
        localStorage.setItem('refreshToken', refreshToken);
    }
    
    /**
     * Clear stored tokens
     */
    clearStoredTokens() {
        localStorage.removeItem('accessToken');
        localStorage.removeItem('idToken');
        localStorage.removeItem('refreshToken');
    }
    
    /**
     * Get challenge message for user
     * @param {string} challengeName - Challenge name
     * @returns {string} User-friendly message
     */
    getChallengeMessage(challengeName) {
        switch (challengeName) {
            case 'NEW_PASSWORD_REQUIRED':
                return 'Please set a new password';
            case 'SMS_MFA':
                return 'Please enter the SMS verification code';
            case 'SOFTWARE_TOKEN_MFA':
                return 'Please enter the code from your authenticator app';
            default:
                return 'Additional authentication required';
        }
    }
    
    /**
     * Logout the current user
     */
    async logout() {
        try {
            const accessToken = localStorage.getItem('accessToken');
            
            if (accessToken) {
                // Revoke the tokens on Cognito side
                const params = {
                    AccessToken: accessToken
                };
                
                await this.cognitoIdentityServiceProvider.globalSignOut(params).promise();
            }
        } catch (error) {
            console.error('Error during logout:', error);
            // Continue with local logout even if remote logout fails
        }
        
        // Clear local state
        this.token = null;
        this.isAuthenticated = false;
        this.user = null;
        this.clearStoredTokens();
        apiService.clearToken();
        
        console.log('Logout completed');
    }
    
    /**
     * Check if user is authenticated
     * @returns {boolean} True if authenticated
     */
    isUserAuthenticated() {
        return this.isAuthenticated;
    }
    
    /**
     * Get current user information
     * @returns {Object|null} User object or null
     */
    getCurrentUser() {
        return this.user;
    }
    
    /**
     * Get user's email
     * @returns {string|null} User email or null
     */
    getUserEmail() {
        if (this.user && this.user.UserAttributes) {
            const emailAttr = this.user.UserAttributes.find(attr => attr.Name === 'email');
            return emailAttr ? emailAttr.Value : null;
        }
        return null;
    }
    
    /**
     * Refresh authentication tokens
     * @returns {Promise} Promise with refresh result
     */
    async refreshTokens() {
        try {
            const refreshToken = localStorage.getItem('refreshToken');
            
            if (!refreshToken) {
                throw new Error('No refresh token available');
            }
            
            const params = {
                AuthFlow: 'REFRESH_TOKEN_AUTH',
                ClientId: this.clientId,
                AuthParameters: {
                    REFRESH_TOKEN: refreshToken
                }
            };
            
            const result = await this.cognitoIdentityServiceProvider.initiateAuth(params).promise();
            
            if (result.AuthenticationResult) {
                const { AccessToken, IdToken } = result.AuthenticationResult;
                const newRefreshToken = result.AuthenticationResult.RefreshToken || refreshToken;
                
                // Update stored tokens
                this.storeTokens(AccessToken, IdToken, newRefreshToken);
                
                // Update authentication state
                this.token = IdToken;
                apiService.setToken(IdToken);
                
                console.log('Tokens refreshed successfully');
                return { success: true };
            }
            
        } catch (error) {
            console.error('Token refresh error:', error);
            // If refresh fails, logout the user
            await this.logout();
            throw new Error('Session expired. Please log in again.');
        }
    }
}

// Create a singleton instance
const authService = new AuthService();