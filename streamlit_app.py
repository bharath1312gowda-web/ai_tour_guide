import streamlit as st
from openai import OpenAI
import json
import os
import random
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="AI Tour Guide",
    page_icon="🌍",
    layout="wide"
)

# Load offline data
@st.cache_data
def load_offline_data():
    try:
        with open('data/offline_data.json', 'r') as f:
            return json.load(f)
    except:
        return {"destinations": {}, "phrases": {}}

offline_data = load_offline_data()

# Tour Guide Personalities
TOUR_GUIDES = {
    "adventure": {
        "name": "Adventure Guide Alex",
        "style": "enthusiastic and adventurous",
        "icon": "🏔️",
        "description": "Loves outdoor activities, hiking, and thrilling experiences"
    },
    "cultural": {
        "name": "Cultural Guide Clara", 
        "style": "knowledgeable and sophisticated",
        "icon": "🎭",
        "description": "Expert in history, art, and local traditions"
    },
    "foodie": {
        "name": "Foodie Guide Frank",
        "style": "passionate and detailed", 
        "icon": "🍜",
        "description": "Food expert who knows all the best local eateries"
    },
    "family": {
        "name": "Family Guide Fiona",
        "style": "friendly and practical",
        "icon": "👨‍👩‍👧‍👦", 
        "description": "Great with kids and family-friendly activities"
    },
    "luxury": {
        "name": "Luxury Guide Leo",
        "style": "elegant and exclusive",
        "icon": "⭐",
        "description": "Focuses on premium experiences and luxury travel"
    }
}

def get_tour_guide_suggestions(city, guide_type, language, user_interests=[]):
    """Get proactive tour guide suggestions based on city and guide personality"""
    
    suggestions = {
        "adventure": {
            "en": [
                f"🌄 **Adventure Alert!** For thrill-seekers in {city}, I recommend starting with the mountain trails at sunrise - the views are absolutely breathtaking!",
                f"🚵 **Ready for action?** Let's explore {city}'s outdoor adventures! How about we start with the famous hiking routes?",
                f"🏞️ **Nature calls!** I know the perfect hidden waterfalls and scenic spots around {city} that most tourists miss!",
                f"⛰️ **Adventure time!** The best way to experience {city} is through its outdoor activities. Let me plan an exciting day for you!"
            ],
            "es": [
                f"🌄 **¡Alerta de aventura!** Para los buscadores de emociones en {city}, recomiendo comenzar con los senderos de montaña al amanecer - ¡las vistas son absolutamente impresionantes!",
                f"🚵 **¿Listo para la acción?** ¡Exploremos las aventuras al aire libre de {city}! ¿Qué tal si comenzamos con las rutas de senderismo famosas?",
            ],
            "fr": [
                f"🌄 **Alerte aventure !** Pour les amateurs de sensations fortes à {city}, je recommande de commencer par les sentiers de montagne au lever du soleil - les vues sont absolument à couper le souffle !",
                f"🚵 **Prêt pour l'action ?** Explorons les aventures en plein air de {city} ! Et si nous commencions par les célèbres routes de randonnée ?",
            ]
        },
        "cultural": {
            "en": [
                f"🏛️ **Cultural immersion!** {city} is rich with history! Let me take you through the ancient ruins and museums that tell incredible stories.",
                f"🎨 **Art lover's paradise!** The galleries and historical sites in {city} are magnificent. Shall we start with the most iconic museum?",
                f"📜 **Step back in time!** The historical district of {city} holds secrets from centuries past. I'd love to be your guide through these ancient streets!",
                f"🕌 **Cultural treasure!** Let me show you the architectural marvels and cultural landmarks that make {city} so special!"
            ],
            "es": [
                f"🏛️ **¡Inmersión cultural!** {city} es rica en historia! Permíteme llevarte a través de las ruinas antiguas y museos que cuentan historias increíbles.",
                f"🎨 **¡Paraíso para amantes del arte!** Las galerías y sitios históricos en {city} son magníficos. ¿Empezamos con el museo más icónico?",
            ]
        },
        "foodie": {
            "en": [
                f"🍜 **Food adventure!** The culinary scene in {city} is incredible! Let me take you to hidden local eateries that serve authentic flavors.",
                f"🍽️ **Taste exploration!** I know all the best food streets and markets in {city}. Ready for a delicious journey through local cuisine?",
                f"👨‍🍳 **Culinary secrets!** The real taste of {city} isn't in fancy restaurants - it's in the family-run spots I'll show you!",
                f"🍛 **Flavor discovery!** Let me guide you through {city}'s food culture, from street food stalls to traditional restaurants!"
            ],
            "es": [
                f"🍜 **¡Aventura culinaria!** La escena culinaria en {city} es increíble! Permíteme llevarte a comedores locales escondidos que sirven sabores auténticos.",
                f"🍽️ **¡Exploración de sabores!** Conozco todas las mejores calles y mercados de comida en {city}. ¿Listo para un delicioso viaje por la cocina local?",
            ]
        },
        "family": {
            "en": [
                f"👨‍👩‍👧‍👦 **Family fun!** {city} has amazing activities for all ages! Let me plan a day that both kids and adults will love.",
                f"🎡 **Kid-friendly adventure!** I know all the best parks, interactive museums, and family attractions in {city}. Ready for some fun?",
                f"🚂 **Family memories!** Let me show you the most enjoyable and educational spots in {city} that the whole family can enjoy together!",
                f"🎪 **Fun for everyone!** From zoos to science centers, {city} has so much to offer families. Let's create unforgettable memories!"
            ],
            "es": [
                f"👨‍👩‍👧‍👦 **¡Diversión familiar!** {city} tiene actividades increíbles para todas las edades! Permíteme planificar un día que tanto niños como adultos amarán.",
                f"🎡 **¡Aventura para niños!** Conozco todos los mejores parques, museos interactivos y atracciones familiares en {city}. ¿Listo para divertirse?",
            ]
        },
        "luxury": {
            "en": [
                f"⭐ **Luxury experience!** {city} offers world-class premium experiences. Let me arrange exclusive access and VIP treatment for you.",
                f"🏨 **Elegant exploration!** From five-star dining to private tours, I'll show you the most sophisticated side of {city}.",
                f"💎 **Premium journey!** Experience {city} in style with luxury accommodations, fine dining, and exclusive cultural experiences.",
                f"🛎️ **VIP treatment!** Let me curate a luxurious itinerary through {city}'s most exclusive venues and experiences."
            ],
            "es": [
                f"⭐ **¡Experiencia de lujo!** {city} ofrece experiencias premium de clase mundial. Permíteme organizar acceso exclusivo y tratamiento VIP para ti.",
                f"🏨 **¡Exploración elegante!** Desde cenas de cinco estrellas hasta tours privados, te mostraré el lado más sofisticado de {city}.",
            ]
        }
    }
    
    # Get suggestions for the selected language, fallback to English
    lang_suggestions = suggestions.get(guide_type, {}).get(language, suggestions.get(guide_type, {}).get("en", []))
    
    if lang_suggestions:
        return random.choice(lang_suggestions)
    else:
        return f"🌍 Welcome to {city}! I'm excited to be your tour guide and show you the best this amazing city has to offer!"

def get_daily_itinerary(city, guide_type, days=1, language="en"):
    """Generate a sample daily itinerary"""
    
    itineraries = {
        "adventure": {
            "en": f"""
**🌅 Adventure Itinerary for {city}**

**Morning (8 AM - 12 PM):**
• Sunrise hike to scenic viewpoints
• Explore nature trails and parks
• Adventure photography session

**Afternoon (1 PM - 5 PM):**
• Outdoor activity (kayaking/biking/hiking)
• Local adventure sports experience
• Picnic with local snacks

**Evening (6 PM - 9 PM):**
• Sunset at best viewing spot
• Casual dinner at adventure-themed restaurant
• Stargazing if weather permits
""",
            "es": f"""
**🌅 Itinerario de Aventura para {city}**

**Mañana (8 AM - 12 PM):**
• Caminata al amanecer a miradores escénicos
• Explorar senderos naturales y parques
• Sesión de fotografía de aventura

**Tarde (1 PM - 5 PM):**
• Actividad al aire libre (kayak/ciclismo/senderismo)
• Experiencia de deportes de aventura locales
• Picnic con bocadillos locales

**Noche (6 PM - 9 PM):**
• Atardecer en el mejor lugar de observación
• Cena casual en restaurante con tema de aventura
• Observación de estrellas si el clima lo permite
"""
        },
        "cultural": {
            "en": f"""
**🏛️ Cultural Itinerary for {city}**

**Morning (9 AM - 12 PM):**
• Guided tour of historical landmarks
• Visit to main museums and galleries
• Cultural heritage sites exploration

**Afternoon (1 PM - 5 PM):**
• Traditional architecture tour
• Local artisan workshops visit
• Cultural performance/show

**Evening (6 PM - 9 PM):**
• Fine dining with local cuisine
• Night tour of illuminated monuments
• Cultural district exploration
"""
        }
    }
    
    return itineraries.get(guide_type, {}).get(language, "I'll create a personalized itinerary based on your interests!")

def get_proactive_recommendations(city, context, language):
    """Get proactive recommendations based on conversation context"""
    
    recommendations = {
        "en": [
            f"💡 **Pro Tip**: The best time to visit {city}'s main attractions is early morning to avoid crowds!",
            f"🌟 **Hidden Gem**: Most tourists miss the local market in {city}'s old town - it's absolutely worth visiting!",
            f"🚶 **Walking Route**: I recommend starting at the city center and exploring {city} on foot to discover hidden treasures!",
            f"🍽️ **Local Secret**: Ask me about the family-run restaurant that serves the most authentic food in {city}!",
            f"📸 **Photo Spot**: The best views of {city} are from the hilltop park - perfect for sunset photos!",
            f"🎭 **Cultural Tip**: Check if there are any local festivals happening during your visit to {city}!",
            f"🚇 **Transport Advice**: The local transit system in {city} is very efficient for getting around!",
            f"🛍️ **Shopping Tip**: The artisan quarter in {city} has unique souvenirs you won't find elsewhere!"
        ],
        "es": [
            f"💡 **Consejo Pro**: ¡La mejor hora para visitar las principales atracciones de {city} es temprano en la mañana para evitar multitudes!",
            f"🌟 **Gema Oculta**: La mayoría de los turistas se pierden el mercado local en el casco antiguo de {city} - ¡vale absolutamente la pena visitarlo!",
        ],
        "fr": [
            f"💡 **Conseil Pro**: Le meilleur moment pour visiter les principales attractions de {city} est tôt le matin pour éviter les foules!",
            f"🌟 **Joyau Caché**: La plupart des touristes manquent le marché local dans la vieille ville de {city} - ça vaut vraiment le détour!",
        ]
    }
    
    lang_recs = recommendations.get(language, recommendations["en"])
    return random.choice(lang_recs)

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "🌍 Hello! I'm your personal AI tour guide! Tell me which city you'd like to explore, and I'll create amazing experiences for you!"}
    ]
if 'destination' not in st.session_state:
    st.session_state.destination = ''
if 'language' not in st.session_state:
    st.session_state.language = 'en'
if 'guide_type' not in st.session_state:
    st.session_state.guide_type = 'cultural'
if 'user_interests' not in st.session_state:
    st.session_state.user_interests = []
if 'last_suggestion_time' not in st.session_state:
    st.session_state.last_suggestion_time = None

# Sidebar
with st.sidebar:
    st.title("🌍 AI Tour Guide")
    
    # Tour Guide Selection
    st.subheader("👨‍🏫 Choose Your Guide")
    guide_options = {
        "cultural": "🎭 Cultural Guide",
        "adventure": "🏔️ Adventure Guide", 
        "foodie": "🍜 Foodie Guide",
        "family": "👨‍👩‍👧‍👦 Family Guide",
        "luxury": "⭐ Luxury Guide"
    }
    
    selected_guide = st.selectbox("Guide Personality", 
                                 options=list(guide_options.keys()),
                                 format_func=lambda x: guide_options[x])
    st.session_state.guide_type = selected_guide
    
    # Show guide description
    guide_info = TOUR_GUIDES[selected_guide]
    st.caption(f"**{guide_info['name']}** - {guide_info['description']}")
    
    # City Input
    st.subheader("🏙️ Enter Your Destination")
    city_input = st.text_input("City Name", 
                              placeholder="e.g., Rome, Dubai, Bangkok, Sydney...",
                              help="Enter any city in the world!")
    
    if city_input:
        st.session_state.destination = city_input.lower().strip()
        st.success(f"✅ Exploring: {city_input.title()}")
    
    # Quick City Buttons
    st.subheader("💡 Popular Destinations")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Paris", use_container_width=True):
            st.session_state.destination = "paris"
        if st.button("Tokyo", use_container_width=True):
            st.session_state.destination = "tokyo"
        if st.button("Dubai", use_container_width=True):
            st.session_state.destination = "dubai"
    
    with col2:
        if st.button("New York", use_container_width=True):
            st.session_state.destination = "newyork"
        if st.button("London", use_container_width=True):
            st.session_state.destination = "london"
        if st.button("Bangkok", use_container_width=True):
            st.session_state.destination = "bangkok"
    
    # Language Selection
    st.subheader("🌐 Language")
    language = st.selectbox("Select Language", 
                           ["en", "es", "fr", "ja", "zh"],
                           format_func=lambda x: {
                               "en": "🇺🇸 English",
                               "es": "🇪🇸 Spanish", 
                               "fr": "🇫🇷 French",
                               "ja": "🇯🇵 Japanese",
                               "zh": "🇨🇳 Chinese"
                           }[x])
    st.session_state.language = language
    
    # Quick Actions - Tour Guide Style
    st.subheader("🎯 Quick Experiences")
    
    if st.button("🗺️ Get City Introduction", use_container_width=True):
        st.session_state.messages.append({"role": "user", "content": "Tell me about this city and suggest must-see places"})
    
    if st.button("🍽️ Food & Dining Guide", use_container_width=True):
        st.session_state.messages.append({"role": "user", "content": "Recommend local food and restaurants"})
    
    if st.button("🏨 Daily Itinerary", use_container_width=True):
        st.session_state.messages.append({"role": "user", "content": "Create a daily itinerary for me"})
    
    if st.button("💎 Hidden Gems", use_container_width=True):
        st.session_state.messages.append({"role": "user", "content": "Show me places most tourists miss"})

    # API Key Configuration
    with st.expander("🔧 AI Settings"):
        st.info("Enable enhanced AI features")
        openai_api_key = st.text_input("OpenAI API Key", type="password")
        if openai_api_key:
            st.session_state.openai_api_key = openai_api_key
            st.success("✅ AI Guide Enhanced!")
        else:
            if hasattr(st.session_state, 'openai_api_key'):
                del st.session_state.openai_api_key

# Main Chat Interface
st.title("🌍 AI Tour Guide")
st.markdown("Your **personal tour guide** that proactively suggests amazing experiences!")

# Display current guide and city
col1, col2 = st.columns(2)
with col1:
    if st.session_state.destination:
        current_city = st.session_state.destination.title()
        st.info(f"🗺️ **Exploring:** {current_city}")
with col2:
    current_guide = TOUR_GUIDES[st.session_state.guide_type]
    st.info(f"👨‍🏫 **Your Guide:** {current_guide['icon']} {current_guide['name']}")

# Proactive suggestion button
if st.session_state.destination and len(st.session_state.messages) < 3:
    if st.button("🎯 Get Proactive Suggestions", type="primary"):
        suggestion = get_tour_guide_suggestions(
            st.session_state.destination.title(),
            st.session_state.guide_type,
            st.session_state.language
        )
        st.session_state.messages.append({"role": "assistant", "content": suggestion})

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input(f"Ask about {st.session_state.destination.title() if st.session_state.destination else 'your destination'}..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Display assistant response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        # Check if API key is available
        openai_api_key = st.session_state.get('openai_api_key', '')
        
        if not openai_api_key:
            # Use offline mode with tour guide personality
            current_guide = TOUR_GUIDES[st.session_state.guide_type]
            guide_intro = f"{current_guide['icon']} **{current_guide['name']}**: "
            
            # Add proactive suggestions randomly
            if random.random() < 0.3:  # 30% chance to add proactive tip
                proactive_tip = get_proactive_recommendations(
                    st.session_state.destination.title(),
                    prompt,
                    st.session_state.language
                )
                full_response = guide_intro + " " + proactive_tip
            else:
                # Regular response with guide personality
                basic_response = f"I'd love to show you around {st.session_state.destination.title()}! "
                if "attraction" in prompt.lower() or "see" in prompt.lower() or "visit" in prompt.lower():
                    full_response = guide_intro + basic_response + "Let me suggest some amazing places you shouldn't miss!"
                elif "food" in prompt.lower() or "eat" in prompt.lower():
                    full_response = guide_intro + basic_response + "The local cuisine here is fantastic! I know all the best spots."
                elif "itinerary" in prompt.lower() or "plan" in prompt.lower():
                    itinerary = get_daily_itinerary(
                        st.session_state.destination.title(),
                        st.session_state.guide_type,
                        language=st.session_state.language
                    )
                    full_response = guide_intro + "\n\n" + itinerary
                else:
                    full_response = guide_intro + basic_response + "What would you like to know about this beautiful city?"
            
            message_placeholder.markdown(full_response)
        else:
            try:
                # Initialize OpenAI client
                client = OpenAI(api_key=openai_api_key)
                
                # Prepare messages with tour guide personality
                current_guide = TOUR_GUIDES[st.session_state.guide_type]
                system_message = f"""You are {current_guide['name']}, a {current_guide['style']} tour guide. 
                You are showing the user around {st.session_state.destination.title()}. 
                Respond in {st.session_state.language} language.
                
                BE PROACTIVE AND SUGGESTIVE like a real tour guide:
                - Suggest specific places, activities, and experiences
                - Share local tips and hidden gems
                - Create excitement and enthusiasm
                - Offer personalized recommendations
                - Use emojis and engaging language
                - Ask follow-up questions about their interests
                
                Make the user feel like they have a personal guide showing them around!"""
                
                messages_for_api = [
                    {"role": "system", "content": system_message}
                ] + st.session_state.messages
                
                # Get AI response
                stream = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages_for_api,
                    stream=True,
                    max_tokens=1000,
                    temperature=0.8
                )
                
                # Stream the response
                for chunk in stream:
                    if chunk.choices[0].delta.content is not None:
                        full_response += chunk.choices[0].delta.content
                        message_placeholder.markdown(full_response + "▌")
                
                message_placeholder.markdown(full_response)
                
            except Exception as e:
                # Fallback to offline response
                current_guide = TOUR_GUIDES[st.session_state.guide_type]
                fallback = f"{current_guide['icon']} **{current_guide['name']}**: I'd love to show you the best of {st.session_state.destination.title()}! Let me suggest some amazing experiences..."
                message_placeholder.markdown(fallback)
                full_response = fallback
        
        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": full_response})

# Footer with tour guide features
st.markdown("---")
st.markdown("### 🎯 Your Personal Tour Guide Can:")
st.markdown("""
- **🗺️ Proactively suggest** must-see attractions and hidden gems
- **🍽️ Recommend restaurants** and local food experiences  
- **🚶 Create personalized itineraries** based on your interests
- **💎 Share local secrets** and insider tips
- **📸 Suggest photo spots** and best times to visit
- **🎭 Adapt to different travel styles** (adventure, luxury, family, etc.)
- **🌍 Work with any city** worldwide
""")

st.markdown("### 👨‍🏫 Meet Your Guides:")
cols = st.columns(5)
for i, (guide_type, guide_info) in enumerate(TOUR_GUIDES.items()):
    with cols[i]:
        st.markdown(f"**{guide_info['icon']} {guide_info['name']}**")
        st.caption(guide_info['description'])
