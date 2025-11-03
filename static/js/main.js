class TourGuideApp {
    constructor() {
        this.socket = io();
        this.userId = this.generateUserId();
        this.currentDestination = '';
        this.currentLanguage = 'en';
        this.isOnline = true;
        this.userPreferences = {
            interests: ['sightseeing'],
            budget: 'medium',
            travel_style: 'sightseeing',
            language: 'en'
        };
        
        this.initializeApp();
    }

    generateUserId() {
        return 'user_' + Math.random().toString(36).substr(2, 9);
    }

    initializeApp() {
        this.initializeEventListeners();
        this.initializeSocketListeners();
        this.loadUserPreferences();
        this.checkConnection();
    }

    initializeEventListeners() {
        // Message sending
        document.getElementById('send-btn').addEventListener('click', () => this.sendMessage());
        document.getElementById('message-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.sendMessage();
        });

        // Voice control
        document.getElementById('voice-toggle').addEventListener('click', () => this.toggleVoiceMode());
        document.getElementById('voice-input-btn').addEventListener('click', () => this.startVoiceInput());

        // Preferences
        document.getElementById('edit-preferences').addEventListener('click', () => this.openPreferencesModal());
        document.getElementById('close-modal').addEventListener('click', () => this.closePreferencesModal());
        document.getElementById('save-preferences').addEventListener('click', () => this.savePreferences());

        // Destination and language
        document.getElementById('destination-select').addEventListener('change', (e) => {
            this.currentDestination = e.target.value;
            this.updateNavigationInfo();
        });
        document.getElementById('language-select').addEventListener('change', (e) => {
            this.currentLanguage = e.target.value;
            this.updateLanguage();
        });

        // Quick actions
        document.querySelectorAll('.quick-action').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const action = e.currentTarget.getAttribute('data-action');
                this.handleQuickAction(action);
            });
        });

        // Navigation
        document.getElementById('start-navigation').addEventListener('click', () => this.startNavigation());

        // Interest tags
        document.querySelectorAll('.interest-tag').forEach(tag => {
            tag.addEventListener('click', (e) => {
                e.currentTarget.classList.toggle('active');
            });
        });
    }

    initializeSocketListeners() {
        this.socket.on('connect', () => {
            this.updateConnectionStatus(true);
        });

        this.socket.on('disconnect', () => {
            this.updateConnectionStatus(false);
        });

        this.socket.on('voice_response', (data) => {
            this.handleVoiceResponse(data);
        });
    }

    async sendMessage() {
        const input = document.getElementById('message-input');
        const message = input.value.trim();

        if (!message) return;

        // Add user message to chat
        this.addMessage(message, 'user');
        input.value = '';

        // Show typing indicator
        this.showTypingIndicator();

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    user_id: this.userId,
                    destination: this.currentDestination,
                    language: this.currentLanguage,
                    coordinates: window.currentCoordinates
                })
            });

            const data = await response.json();

            this.removeTypingIndicator();

            if (data.error) {
                this.addMessage('Sorry, I encountered an error. Please try again.', 'bot');
            } else {
                this.addMessage(data.response, 'bot');
                
                // Speak response if voice mode is active
                if (window.voiceEnabled) {
                    this.speakText(data.response);
                }
            }
        } catch (error) {
            this.removeTypingIndicator();
            this.addMessage('I\'m in offline mode. Some features may be limited.', 'bot');
        }
    }

    addMessage(text, sender) {
        const chatMessages = document.getElementById('chat-messages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        
        const avatar = sender === 'bot' ? 
            '<i class="fas fa-robot"></i>' : 
            '<i class="fas fa-user"></i>';
        
        messageDiv.innerHTML = `
            <div class="message-avatar">
                ${avatar}
            </div>
            <div class="message-content">
                <strong>${sender === 'bot' ? 'AI Guide' : 'You'}:</strong> ${this.formatMessage(text)}
            </div>
        `;
        
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    formatMessage(text) {
        return text.replace(/\n/g, '<br>')
                   .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                   .replace(/\*(.*?)\*/g, '<em>$1</em>');
    }

    showTypingIndicator() {
        const chatMessages = document.getElementById('chat-messages
