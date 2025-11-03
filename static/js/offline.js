class OfflineManager {
    constructor() {
        this.isOnline = navigator.onLine;
        this.offlineData = null;
        this.syncQueue = [];
        this.initializeOfflineSupport();
    }

    initializeOfflineSupport() {
        // Listen for online/offline events
        window.addEventListener('online', () => this.handleOnline());
        window.addEventListener('offline', () => this.handleOffline());
        
        // Load offline data
        this.loadOfflineData();
        
        // Initialize service worker for offline caching
        this.initializeServiceWorker();
    }

    async initializeServiceWorker() {
        if ('serviceWorker' in navigator) {
            try {
                await navigator.serviceWorker.register('/sw.js');
                console.log('Service Worker registered');
            } catch (error) {
                console.log('Service Worker registration failed:', error);
            }
        }
    }

    async loadOfflineData() {
        try {
            const response = await fetch('/data/offline_data.json');
            this.offlineData = await response.json();
            console.log('Offline data loaded');
        } catch (error) {
            console.error('Failed to load offline data:', error);
            this.offlineData = this.getDefaultOfflineData();
        }
    }

    getDefaultOfflineData() {
        return {
            destinations: {
                "paris": {
                    name: "Paris, France",
                    basic_info: "The City of Light, famous for its art, fashion, and culture.",
                    attractions: [
                        "Eiffel Tower - Iconic iron tower offering city views",
                        "Louvre Museum - World's largest art museum",
                        "Notre-Dame Cathedral - Medieval Catholic cathedral"
                    ],
                    emergency: {
                        police: "17",
                        ambulance: "15",
                        fire: "18"
                    },
                    tips: [
                        "Learn basic French phrases",
                        "Purchase museum passes in advance",
                        "Use the Metro for transportation"
                    ]
                },
                "tokyo": {
                    name: "Tokyo, Japan",
                    basic_info: "Bustling metropolis blending tradition and technology.",
                    attractions: [
                        "Tokyo Tower - Communications and observation tower",
                        "Sensoji Temple - Ancient Buddhist temple",
                        "Shibuya Crossing - World's busiest pedestrian crossing"
                    ],
                    emergency: {
                        police: "110",
                        ambulance: "119",
                        fire: "119"
                    },
                    tips: [
                        "Carry cash as some places don't accept cards",
                        "Learn to use the train system",
                        "Be punctual for appointments"
                    ]
                }
            },
            phrases: {
                en: {
                    greetings: ["Hello", "Good morning", "Good afternoon"],
                    directions: ["Where is...", "How do I get to...", "Is it far?"],
                    emergency: ["Help", "I need a doctor", "Call the police"],
                    food: ["I'm hungry", "Restaurant", "Menu please"]
                },
                es: {
                    greetings: ["Hola", "Buenos días", "Buenas tardes"],
                    directions: ["¿Dónde está...?", "¿Cómo llego a...?", "¿Está lejos?"],
                    emergency: ["Ayuda", "Necesito un médico", "Llame a la policía"],
                    food: ["Tengo hambre", "Restaurante", "La carta por favor"]
                },
                fr: {
                    greetings: ["Bonjour", "Bonne matin", "Bonne après-midi"],
                    directions: ["Où est...", "Comment aller à...", "C'est loin?"],
                    emergency: ["Au secours", "J'ai besoin d'un médecin", "Appelez la police"],
                    food: ["J'ai faim", "Restaurant", "La carte s'il vous plaît"]
                },
                ja: {
                    greetings: ["こんにちは", "おはようございます", "こんばんは"],
                    directions: ["...はどこですか", "...へはどう行きますか", "遠いですか"],
                    emergency: ["助けて", "医者が必要です", "警察を呼んでください"],
                    food: ["お腹が空きました", "レストラン", "メニューをください"]
                }
            }
        };
    }

    handleOnline() {
        this.isOnline = true;
        this.updateOnlineStatus(true);
        this.syncOfflineData();
        
        if (window.tourGuideApp) {
            window.tourGuideApp.addMessage('Connection restored. Back online!', 'bot');
        }
    }

    handleOffline() {
        this.isOnline = false;
        this.updateOnlineStatus(false);
        
        if (window.tourGuideApp) {
            window.tourGuideApp.addMessage('You are currently offline. Basic information is available.', 'bot');
        }
    }

    updateOnlineStatus(online) {
        const statusElement = document.getElementById('connection-status');
        if (statusElement) {
            if (online) {
                statusElement.innerHTML = '<i class="fas fa-wifi"></i> Online';
                statusElement.style.background = 'var(--success-color)';
            } else {
                statusElement.innerHTML = '<i class="fas fa-wifi-slash"></i> Offline';
                statusElement.style.background = 'var(--warning-color)';
            }
        }
    }

    async syncOfflineData() {
        if (this.syncQueue.length > 0) {
            console.log('Syncing offline data...');
            // Process sync queue
            for (const item of this.syncQueue) {
                try {
                    // Send data to server
                    await this.sendToServer(item);
                } catch (error) {
                    console.error('Failed to sync item:', item, error);
                }
            }
            this.syncQueue = [];
        }
    }

    async sendToServer(data) {
        // Implement server synchronization
        const response = await fetch('/api/sync', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });
        
        if (!response.ok) {
            throw new Error('Sync failed');
        }
        
        return response.json();
    }

    // Offline chat responses
    getOfflineResponse(message, destination = '', language = 'en') {
        const lowerMessage = message.toLowerCase();
        
        // Basic keyword matching for offline responses
        if (lowerMessage.includes('hello') || lowerMessage.includes('hi')) {
            return this.getPhrase('greetings', language);
        }
        
        if (lowerMessage.includes('where') || lowerMessage.includes('direction')) {
            return this.getDirectionResponse(destination, language);
        }
        
        if (lowerMessage.includes('emergency') || lowerMessage.includes('help')) {
            return this.getEmergencyInfo(destination, language);
        }
        
        if (lowerMessage.includes('attraction') || lowerMessage.includes('place to visit')) {
            return this.getAttractionsList(destination, language);
        }
        
        if (lowerMessage.includes('food') || lowerMessage.includes('restaurant')) {
            return this.getFoodRecommendations(language);
        }
        
        return this.getGenericResponse(language);
    }

    getPhrase(category, language) {
        const phrases = this.offlineData?.phrases?.[language] || this.offlineData?.phrases?.en;
        if (phrases && phrases[category]) {
            const randomIndex = Math.floor(Math.random() * phrases[category].length);
            return phrases[category][randomIndex];
        }
        return "I'm currently in offline mode. Basic information is available.";
    }

    getDirectionResponse(destination, language) {
        const destData = this.offlineData?.destinations?.[destination];
        if (destData) {
            const responses = {
                en: `For ${destData.name}, major attractions include ${destData.attractions.slice(0, 2).join(' and ')}. Use offline maps for navigation.`,
                es: `Para ${destData.name}, las atracciones principales incluyen ${destData.attractions.slice(0, 2).join(' y ')}. Use mapas sin conexión para navegación.`,
                fr: `Pour ${destData.name}, les attractions principales incluent ${destData.attractions.slice(0, 2).join(' et ')}. Utilisez des cartes hors ligne pour la navigation.`,
                ja: `${destData.name}の主なアトラクションには、${destData.attractions.slice(0, 2).join('と')}が含まれます。オフラインマップを使用してナビゲーションしてください。`
            };
            return responses[language] || responses.en;
        }
        return this.getPhrase('directions', language);
    }

    getEmergencyInfo(destination, language) {
        const destData = this.offlineData?.destinations?.[destination];
        if (destData && destData.emergency) {
            const emergency = destData.emergency;
            const responses = {
                en: `Emergency contacts - Police: ${emergency.police}, Ambulance: ${emergency.ambulance}, Fire: ${emergency.fire}. Stay calm and describe your location.`,
                es: `Contactos de emergencia - Policía: ${emergency.police}, Ambulancia: ${emergency.ambulance}, Bomberos: ${emergency.fire}. Mantenga la calma y describa su ubicación.`,
                fr: `Contacts d'urgence - Police: ${emergency.police}, Ambulance: ${emergency.ambulance}, Pompiers: ${emergency.fire}. Restez calme et décrivez votre emplacement.`,
                ja: `緊急連絡先 - 警察: ${emergency.police}, 救急車: ${emergency.ambulance}, 消防: ${emergency.fire}. 落ち着いてあなたの場所を説明してください。`
            };
            return responses[language] || responses.en;
        }
        
        const defaultEmergency = {
            en: "Emergency: Call 112 (EU) or 911 (US). Describe your location and emergency clearly.",
            es: "Emergencia: Llame al 112 (UE) o 911 (EEUU). Describa su ubicación y emergencia claramente.",
            fr: "Urgence: Appelez le 112 (UE) ou le 911 (États-Unis). Décrivez clairement votre emplacement et votre urgence.",
            ja: "緊急時：112（EU）または911（米国）に電話してください。場所と緊急事態を明確に説明してください。"
        };
        return defaultEmergency[language] || defaultEmergency.en;
    }

    getAttractionsList(destination, language) {
        const destData = this.offlineData?.destinations?.[destination];
        if (destData) {
            const attractions = destData.attractions.join(', ');
            const responses = {
                en: `Top attractions in ${destData.name}: ${attractions}. ${destData.tips?.join(' ')}`,
                es: `Principales atracciones en ${destData.name}: ${attractions}. ${destData.tips?.join(' ')}`,
                fr: `Principales attractions à ${destData.name}: ${attractions}. ${destData.tips?.join(' ')}`,
                ja: `${destData.name}の主なアトラクション: ${attractions}. ${destData.tips?.join(' ')}`
            };
            return responses[language] || responses.en;
        }
        return this.getGenericResponse(language);
    }

    getFoodRecommendations(language) {
        const responses = {
            en: "In offline mode, I recommend trying local cuisine. Look for busy restaurants with local customers for authentic food.",
            es: "En modo offline, recomiendo probar la cocina local. Busque restaurantes concurridos con clientes locales para comida auténtica.",
            fr: "En mode hors ligne, je recommande d'essayer la cuisine locale. Cherchez des restaurants animés avec des clients locaux pour une nourriture authentique.",
            ja: "オフラインモードでは、地元の料理を試すことをお勧めします。本格的な料理を求めて、地元の客でにぎわうレストランを探してください。"
        };
        return responses[language] || responses.en;
    }

    getGenericResponse(language) {
        const responses = {
            en: "I'm currently in offline mode. I can provide basic information about destinations, emergency contacts, and common phrases. For detailed information, please check when online.",
            es: "Actualmente estoy en modo offline. Puedo proporcionar información básica sobre destinos, contactos de emergencia y frases comunes. Para información detallada, consulte cuando esté en línea.",
            fr: "Je suis actuellement en mode hors ligne. Je peux fournir des informations de base sur les destinations, les contacts d'urgence et les phrases courantes. Pour des informations détaillées, veuillez vérifier lorsque vous êtes en ligne.",
            ja: "現在オフラインモードです。目的地、緊急連絡先、一般的なフレーズに関する基本情報を提供できます。詳細な情報については、オンライン時に確認してください。"
        };
        return responses[language] || responses.en;
    }

    // Cache data for offline use
    async cacheData(key, data) {
        if ('caches' in window) {
            try {
                const cache = await caches.open('tour-guide-v1');
                const response = new Response(JSON.stringify(data));
                await cache.put(`/api/cache/${key}`, response);
            } catch (error) {
                console.error('Failed to cache data:', error);
            }
        }
        
        // Also store in localStorage as backup
        try {
            localStorage.setItem(`tour_guide_${key}`, JSON.stringify(data));
        } catch (error) {
            console.error('Failed to store in localStorage:', error);
        }
    }

    // Retrieve cached data
    async getCachedData(key) {
        // Try cache first
        if ('caches' in window) {
            try {
                const cache = await caches.open('tour-guide-v1');
                const response = await cache.match(`/api/cache/${key}`);
                if (response) {
                    return await response.json();
                }
            } catch (error) {
                console.error('Failed to retrieve from cache:', error);
            }
        }
        
        // Fallback to localStorage
        try {
            const data = localStorage.getItem(`tour_guide_${key}`);
            return data ? JSON.parse(data) : null;
        } catch (error) {
            console.error('Failed to retrieve from localStorage:', error);
            return null;
        }
    }

    // Check if specific data is available offline
    isDataAvailableOffline(dataType, identifier) {
        if (!this.offlineData) return false;
        
        switch(dataType) {
            case 'destination':
                return !!this.offlineData.destinations?.[identifier];
            case 'phrase':
                return !!this.offlineData.phrases?.[identifier];
            default:
                return false;
        }
    }
}

// Initialize offline manager
document.addEventListener('DOMContentLoaded', function() {
    window.offlineManager = new OfflineManager();
});
