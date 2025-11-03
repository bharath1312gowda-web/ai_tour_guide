from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit
import openai
import json
import os
from geopy.distance import geodesic
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = Config.SECRET_KEY
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize OpenAI
openai.api_key = Config.OPENAI_API_KEY

# Sample destination database
DESTINATIONS = {
    "paris": {
        "name": "Paris, France",
        "coordinates": (48.8566, 2.3522),
        "language": "fr",
        "attractions": ["Eiffel Tower", "Louvre Museum", "Notre-Dame"],
        "offline_data": "paris_guide.json"
    },
    "tokyo": {
        "name": "Tokyo, Japan",
        "coordinates": (35.6762, 139.6503),
        "language": "ja",
        "attractions": ["Tokyo Tower", "Sensoji Temple", "Shibuya Crossing"],
        "offline_data": "tokyo_guide.json"
    },
    "newyork": {
        "name": "New York City, USA",
        "coordinates": (40.7128, -74.0060),
        "language": "en",
        "attractions": ["Statue of Liberty", "Central Park", "Times Square"],
        "offline_data": "nyc_guide.json"
    }
}

# User preferences storage
user_preferences = {}

def get_ai_response(prompt, user_context="", language="en"):
    """Get AI response with context and language support"""
    try:
        system_message = f"""You are a friendly, knowledgeable tour guide. 
        Provide helpful, engaging information about travel destinations.
        User context: {user_context}
        Respond in {language} language.
        Include local tips, cultural insights, and practical advice."""
        
        response = openai.ChatCompletion.create(
            model=Config.AI_MODEL,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            max_tokens=Config.MAX_TOKENS,
            temperature=Config.TEMPERATURE
        )
        
        return response.choices[0].message.content
    except Exception as e:
        return get_offline_response(prompt, language)

def get_offline_response(prompt, language="en"):
    """Provide offline responses when AI is unavailable"""
    offline_responses = {
        "en": "I'm currently in offline mode. Basic information is available.",
        "es": "Estoy en modo offline. Información básica disponible.",
        "fr": "Je suis en mode hors ligne. Informations de base disponibles.",
        "ja": "オフラインモードです。基本情報が利用可能です。"
    }
    return offline_responses.get(language, offline_responses["en"])

def get_personalized_recommendations(user_id, destination):
    """Generate personalized recommendations based on user preferences"""
    preferences = user_preferences.get(user_id, {})
    
    interests = preferences.get('interests', [])
    budget = preferences.get('budget', 'medium')
    travel_style = preferences.get('travel_style', 'sightseeing')
    
    # Generate recommendations based on preferences
    rec_prompt = f"""
    User interests: {interests}
    Budget: {budget}
    Travel style: {travel_style}
    Destination: {destination}
    
    Provide 3 personalized recommendations for this user.
    """
    
    return get_ai_response(rec_prompt, "Personalized recommendations")

@app.route('/')
def index():
    return render_template('index.html', destinations=DESTINATIONS)

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_message = data.get('message', '')
        user_id = data.get('user_id', 'default')
        destination = data.get('destination', '')
        language = data.get('language', 'en')
        coordinates = data.get('coordinates')
        
        # Update user preferences based on conversation
        update_user_preferences(user_id, user_message)
        
        # Get user context for personalization
        user_context = f"Preferences: {user_preferences.get(user_id, {})}"
        
        # Add location context if available
        if coordinates and destination in DESTINATIONS:
            dest_coords = DESTINATIONS[destination]['coordinates']
            distance = geodesic(coordinates, dest_coords).km
            user_context += f" Current distance from {destination}: {distance:.1f}km"
        
        # Get AI response
        response = get_ai_response(user_message, user_context, language)
        
        return jsonify({
            'response': response,
            'destination': destination,
            'language': language
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/set_preferences', methods=['POST'])
def set_preferences():
    """Set user preferences"""
    data = request.json
    user_id = data.get('user_id', 'default')
    
    user_preferences[user_id] = {
        'interests': data.get('interests', []),
        'budget': data.get('budget', 'medium'),
        'travel_style': data.get('travel_style', 'sightseeing'),
        'language': data.get('language', 'en')
    }
    
    return jsonify({'status': 'success', 'preferences': user_preferences[user_id]})

@app.route('/get_navigation', methods=['POST'])
def get_navigation():
    """Get navigation instructions between two points"""
    data = request.json
    start_coords = data.get('start_coords')
    end_coords = data.get('end_coords')
    destination = data.get('destination')
    
    if start_coords and end_coords:
        distance = geodesic(start_coords, end_coords).km
        bearing = calculate_bearing(start_coords, end_coords)
        
        return jsonify({
            'distance_km': round(distance, 2),
            'bearing': bearing,
            'instructions': get_navigation_instructions(bearing, distance, destination)
        })
    
    return jsonify({'error': 'Invalid coordinates'})

def calculate_bearing(start, end):
    """Calculate bearing between two coordinates"""
    # Simplified bearing calculation
    return "north"  # In real implementation, calculate actual bearing

def get_navigation_instructions(bearing, distance, destination):
    """Generate navigation instructions"""
    instructions = {
        'en': f"Head {bearing} for {distance}km towards {destination}",
        'es': f"Diríjase {bearing} por {distance}km hacia {destination}",
        'fr': f"Allez {bearing} pendant {distance}km vers {destination}",
        'ja': f"{destination}まで{bearing}方向に{distance}km進んでください"
    }
    return instructions

def update_user_preferences(user_id, message):
    """Update user preferences based on conversation analysis"""
    if user_id not in user_preferences:
        user_preferences[user_id] = {}
    
    # Simple keyword-based preference detection
    message_lower = message.lower()
    
    if 'budget' in message_lower or 'cheap' in message_lower:
        user_preferences[user_id]['budget'] = 'low'
    elif 'luxury' in message_lower:
        user_preferences[user_id]['budget'] = 'high'
    
    if 'adventure' in message_lower:
        user_preferences[user_id]['travel_style'] = 'adventure'
    elif 'relax' in message_lower:
        user_preferences[user_id]['travel_style'] = 'relaxation'

@socketio.on('voice_message')
def handle_voice_message(data):
    """Handle real-time voice messages"""
    audio_data = data.get('audio_data')
    user_id = data.get('user_id')
    
    # Process voice data (simplified)
    text_message = "Voice message received"  # In real implementation, use speech-to-text
    
    emit('voice_response', {
        'text': text_message,
        'user_id': user_id
    })

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
