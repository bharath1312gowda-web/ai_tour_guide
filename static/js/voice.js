class VoiceController {
    constructor() {
        this.recognition = null;
        this.isListening = false;
        this.isVoiceEnabled = false;
        this.synthesis = window.speechSynthesis;
        this.initializeVoiceRecognition();
    }

    initializeVoiceRecognition() {
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            this.recognition = new SpeechRecognition();
            
            this.recognition.continuous = false;
            this.recognition.interimResults = false;
            this.recognition.lang = 'en-US';
            
            this.recognition.onstart = () => {
                this.isListening = true;
                this.updateVoiceUI(true);
            };
            
            this.recognition.onresult = (event) => {
                const transcript = event.results[0][0].transcript;
                this.handleVoiceCommand(transcript);
            };
            
            this.recognition.onerror = (event) => {
                console.error('Speech recognition error:', event.error);
                this.isListening = false;
                this.updateVoiceUI(false);
            };
            
            this.recognition.onend = () => {
                this.isListening = false;
                this.updateVoiceUI(false);
            };
        } else {
            console.warn('Speech recognition not supported in this browser');
        }
    }

    toggleVoiceMode() {
        this.isVoiceEnabled = !this.isVoiceEnabled;
        const voiceBtn = document.getElementById('voice-toggle');
        
        if (this.isVoiceEnabled) {
            voiceBtn.classList.add('active');
            voiceBtn.innerHTML = '<i class="fas fa-microphone-slash"></i><span>Voice Mode ON</span>';
            this.speakText('Voice mode activated. How can I help you?');
        } else {
            voiceBtn.classList.remove('active');
            voiceBtn.innerHTML = '<i class="fas fa-microphone"></i><span>Voice Mode</span>';
            this.speakText('Voice mode deactivated.');
        }
    }

    startVoiceInput() {
        if (!this.recognition) {
            alert('Speech recognition is not supported in your browser.');
            return;
        }

        if (this.isListening) {
            this.stopVoiceInput();
            return;
        }

        try {
            this.recognition.start();
        } catch (error) {
            console.error('Error starting voice recognition:', error);
        }
    }

    stopVoiceInput() {
        if (this.recognition && this.isListening) {
            this.recognition.stop();
        }
    }

    handleVoiceCommand(transcript) {
        console.log('Voice command:', transcript);
        
        // Add voice message to chat
        if (window.tourGuideApp) {
            window.tourGuideApp.addMessage(transcript, 'user');
        }
        
        // Set input value and send
        const input = document.getElementById('message-input');
        input.value = transcript;
        
        // Auto-send after short delay
        setTimeout(() => {
            if (window.tourGuideApp) {
                window.tourGuideApp.sendMessage();
            }
        }, 500);
    }

    speakText(text) {
        if (!this.isVoiceEnabled || !this.synthesis) return;

        // Stop any ongoing speech
        this.synthesis.cancel();

        const utterance = new SpeechSynthesisUtterance(text);
        
        // Configure voice settings
        utterance.rate = 0.9;
        utterance.pitch = 1.0;
        utterance.volume = 0.8;
        utterance.lang = this.getLanguageCode(window.currentLanguage || 'en');
        
        utterance.onstart = () => {
            console.log('Speech started');
        };
        
        utterance.onend = () => {
            console.log('Speech ended');
        };
        
        utterance.onerror = (event) => {
            console.error('Speech synthesis error:', event);
        };

        this.synthesis.speak(utterance);
    }

    getLanguageCode(lang) {
        const languageMap = {
            'en': 'en-US',
            'es': 'es-ES',
            'fr': 'fr-FR',
            'ja': 'ja-JP',
            'zh': 'zh-CN'
        };
        return languageMap[lang] || 'en-US';
    }

    updateVoiceUI(listening) {
        const voiceInputBtn = document.getElementById('voice-input-btn');
        
        if (listening) {
            voiceInputBtn.classList.add('recording');
            voiceInputBtn.innerHTML = '<i class="fas fa-stop"></i>';
            voiceInputBtn.style.background = 'var(--error-color)';
        } else {
            voiceInputBtn.classList.remove('recording');
            voiceInputBtn.innerHTML = '<i class="fas fa-microphone"></i>';
            voiceInputBtn.style.background = 'var(--accent-color)';
        }
    }

    setLanguage(language) {
        if (this.recognition) {
            const langCode = this.getLanguageCode(language);
            this.recognition.lang = langCode;
        }
    }

    // Voice commands processing
    processVoiceCommand(command) {
        const lowerCommand = command.toLowerCase();
        
        // Navigation commands
        if (lowerCommand.includes('navigate to') || lowerCommand.includes('directions to')) {
            const destination = this.extractDestination(command);
            if (destination) {
                this.handleNavigationCommand(destination);
            }
        }
        
        // Information commands
        else if (lowerCommand.includes('tell me about') || lowerCommand.includes('information about')) {
            const topic = this.extractTopic(command);
            if (topic) {
                this.handleInformationCommand(topic);
            }
        }
        
        // Recommendation commands
        else if (lowerCommand.includes('recommend') || lowerCommand.includes('suggest')) {
            this.handleRecommendationCommand(command);
        }
        
        // Emergency commands
        else if (lowerCommand.includes('emergency') || lowerCommand.includes('help')) {
            this.handleEmergencyCommand();
        }
    }

    extractDestination(command) {
        // Simple destination extraction
        const destinations = ['paris', 'tokyo', 'new york', 'london', 'rome'];
        for (const dest of destinations) {
            if (command.toLowerCase().includes(dest)) {
                return dest;
            }
        }
        return null;
    }

    extractTopic(command) {
        // Extract topic from voice command
        const topics = ['restaurant', 'hotel', 'attraction', 'museum', 'park'];
        for (const topic of topics) {
            if (command.toLowerCase().includes(topic)) {
                return topic;
            }
        }
        return null;
    }

    handleNavigationCommand(destination) {
        const message = `Navigate to ${destination}`;
        document.getElementById('message-input').value = message;
        if (window.tourGuideApp) {
            window.tourGuideApp.sendMessage();
        }
    }

    handleInformationCommand(topic) {
        const message = `Tell me about ${topic} in this area`;
        document.getElementById('message-input').value = message;
        if (window.tourGuideApp) {
            window.tourGuideApp.sendMessage();
        }
    }

    handleRecommendationCommand(command) {
        document.getElementById('message-input').value = command;
        if (window.tourGuideApp) {
            window.tourGuideApp.sendMessage();
        }
    }

    handleEmergencyCommand() {
        const emergencyMessage = "Emergency! I need help!";
        document.getElementById('message-input').value = emergencyMessage;
        if (window.tourGuideApp) {
            window.tourGuideApp.sendMessage();
        }
        
        // Speak emergency response
        this.speakText("Emergency assistance requested. I'm here to help. Please provide your location and nature of emergency.");
    }
}

// Initialize voice controller when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.voiceController = new VoiceController();
    window.voiceEnabled = false;
});
