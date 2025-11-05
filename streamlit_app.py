import streamlit as st
from openai import OpenAI
import json
import os

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

def get_offline_response(prompt, destination, language):
    """Get offline response based on user query"""
    prompt_lower = prompt.lower()
    
    if not destination or destination not in offline_data['destinations']:
        return get_generic_offline_response(language)
    
    dest_info = offline_data['destinations'][destination]
    
    # Match query type and provide relevant offline info
    if any(word in prompt_lower for word in ['attraction', 'place', 'see', 'visit', 'tour']):
        return get_attractions_response(dest_info, language)
    elif any(word in prompt_lower for word in ['food', 'restaurant', 'eat', 'cuisine', 'meal']):
        return get_food_response(dest_info, language)
    elif any(word in prompt_lower for word in ['transport', 'get around', 'travel', 'bus', 'train', 'metro']):
        return get_transport_response(dest_info, language)
    elif any(word in prompt_lower for word in ['emergency', 'help', 'police', 'hospital', 'doctor']):
        return get_emergency_response(dest_info, language)
    elif any(word in prompt_lower for word in ['hotel', 'stay', 'accommodation', 'sleep']):
        return get_accommodation_response(dest_info, language)
    else:
        return get_general_info_response(dest_info, language)

def get_generic_offline_response(language):
    """Generic response when no destination is selected"""
    responses = {
        "en": "🌍 **Welcome to AI Tour Guide!**\n\nPlease select a destination from the sidebar to get specific information about:\n• Top attractions\n• Local food\n• Transportation\n• Emergency contacts\n• Travel tips\n\nYou can also ask me specific questions about your travel plans!",
        "es": "🌍 **¡Bienvenido a AI Tour Guide!**\n\nSelecciona un destino en la barra lateral para obtener información específica sobre:\n• Principales atracciones\n• Comida local\n• Transporte\n• Contactos de emergencia\n• Consejos de viaje\n\n¡También puedes hacerme preguntas específicas sobre tus planes de viaje!",
        "fr": "🌍 **Bienvenue dans AI Tour Guide !**\n\nVeuillez sélectionner une destination dans la barre latérale pour obtenir des informations spécifiques sur :\n• Principales attractions\n• Nourriture locale\n• Transport\n• Contacts d'urgence\n• Conseils de voyage\n\nVous pouvez également me poser des questions spécifiques sur vos projets de voyage !",
        "ja": "🌍 **AI Tour Guideへようこそ！**\n\nサイドバーから目的地を選択して、以下の具体的な情報を入手してください：\n• 主なアトラクション\n• 地元の食べ物\n• 交通手段\n• 緊急連絡先\n• 旅行のヒント\n\n旅行計画について具体的な質問もできます！",
        "zh": "🌍 **欢迎使用 AI Tour Guide！**\n\n请从侧边栏选择一个目的地以获取有关以下方面的具体信息：\n• 主要景点\n• 当地美食\n• 交通方式\n• 紧急联系人\n• 旅行提示\n\n您也可以向我询问有关您旅行计划的具体问题！"
    }
    return responses.get(language, responses["en"])

def get_attractions_response(dest_info, language):
    """Get attractions information"""
    attractions = "\n".join([f"🏛️ {attr}" for attr in dest_info.get('attractions', [])])
    tips = "\n".join([f"💡 {tip}" for tip in dest_info.get('tips', [])[:3]])
    
    responses = {
        "en": f"**{dest_info['name']} - Top Attractions**\n\n{attractions}\n\n**Travel Tips:**\n{tips}",
        "es": f"**{dest_info['name']} - Principales Atracciones**\n\n{attractions}\n\n**Consejos de Viaje:**\n{tips}",
        "fr": f"**{dest_info['name']} - Principales Attractions**\n\n{attractions}\n\n**Conseils de Voyage:**\n{tips}",
        "ja": f"**{dest_info['name']} - 主なアトラクション**\n\n{attractions}\n\n**旅行のヒント:**\n{tips}",
        "zh": f"**{dest_info['name']} - 主要景点**\n\n{attractions}\n\n**旅行提示:**\n{tips}"
    }
    return responses.get(language, responses["en"])

def get_food_response(dest_info, language):
    """Get food information"""
    food_items = "\n".join([f"🍽️ {dish}" for dish in dest_info.get('food', {}).get('popular_dishes', [])])
    tips = dest_info.get('food', {}).get('dining_tips', [])
    dining_tips = "\n".join([f"💡 {tip}" for tip in tips]) if tips else "• Try local restaurants for authentic experience"
    
    responses = {
        "en": f"**{dest_info['name']} - Local Food**\n\n**Popular Dishes:**\n{food_items}\n\n**Dining Tips:**\n{dining_tips}",
        "es": f"**{dest_info['name']} - Comida Local**\n\n**Platos Populares:**\n{food_items}\n\n**Consejos Gastronómicos:**\n{dining_tips}",
        "fr": f"**{dest_info['name']} - Nourriture Locale**\n\n**Plats Populaires:**\n{food_items}\n\n**Conseils de Restaurant:**\n{dining_tips}",
        "ja": f"**{dest_info['name']} - 地元の食べ物**\n\n**人気料理:**\n{food_items}\n\n**食事のヒント:**\n{dining_tips}",
        "zh": f"**{dest_info['name']} - 当地美食**\n\n**热门菜肴:**\n{food_items}\n\n**用餐提示:**\n{dining_tips}"
    }
    return responses.get(language, responses["en"])

def get_transport_response(dest_info, language):
    """Get transportation information"""
    transport = dest_info.get('transportation', {})
    transport_info = "\n".join([f"🚗 {key.replace('_', ' ').title()}: {value}" for key, value in transport.items()])
    
    responses = {
        "en": f"**{dest_info['name']} - Transportation**\n\n{transport_info}",
        "es": f"**{dest_info['name']} - Transporte**\n\n{transport_info}",
        "fr": f"**{dest_info['name']} - Transport**\n\n{transport_info}",
        "ja": f"**{dest_info['name']} - 交通手段**\n\n{transport_info}",
        "zh": f"**{dest_info['name']} - 交通方式**\n\n{transport_info}"
    }
    return responses.get(language, responses["en"])

def get_emergency_response(dest_info, language):
    """Get emergency information"""
    emergency = dest_info.get('emergency', {})
    emergency_info = "\n".join([f"📞 {key.replace('_', ' ').title()}: **{value}**" for key, value in emergency.items()])
    
    responses = {
        "en": f"**{dest_info['name']} - Emergency Contacts**\n\n{emergency_info}\n\n🚨 In case of emergency, stay calm and describe your location clearly.",
        "es": f"**{dest_info['name']} - Contactos de Emergencia**\n\n{emergency_info}\n\n🚨 En caso de emergencia, mantén la calma y describe tu ubicación claramente.",
        "fr": f"**{dest_info['name']} - Contacts d'Urgence**\n\n{emergency_info}\n\n🚨 En cas d'urgence, restez calme et décrivez clairement votre emplacement.",
        "ja": f"**{dest_info['name']} - 緊急連絡先**\n\n{emergency_info}\n\n🚨 緊急時は落ち着いて、自分の場所を明確に説明してください。",
        "zh": f"**{dest_info['name']} - 紧急联系人**\n\n{emergency_info}\n\n🚨 遇到紧急情况时，请保持冷静并清楚描述您的位置。"
    }
    return responses.get(language, responses["en"])

def get_accommodation_response(dest_info, language):
    """Get accommodation information"""
    tips = "\n".join([f"🏨 {tip}" for tip in dest_info.get('tips', []) if any(word in tip.lower() for word in ['hotel', 'stay', 'accommodation', 'sleep'])])
    if not tips:
        tips = "• Book in advance during peak season\n• Read recent reviews before booking\n• Consider location proximity to attractions"
    
    responses = {
        "en": f"**{dest_info['name']} - Accommodation Tips**\n\n{tips}",
        "es": f"**{dest_info['name']} - Consejos de Alojamiento**\n\n{tips}",
        "fr": f"**{dest_info['name']} - Conseils d'Hébergement**\n\n{tips}",
        "ja": f"**{dest_info['name']} - 宿泊のヒント**\n\n{tips}",
        "zh": f"**{dest_info['name']} - 住宿提示**\n\n{tips}"
    }
    return responses.get(language, responses["en"])

def get_general_info_response(dest_info, language):
    """Get general destination information"""
    basic_info = dest_info.get('basic_info', 'No additional information available.')
    tips = "\n".join([f"💡 {tip}" for tip in dest_info.get('tips', [])[:3]])
    
    responses = {
        "en": f"**{dest_info['name']}**\n\n{basic_info}\n\n**Quick Tips:**\n{tips}",
        "es": f"**{dest_info['name']}**\n\n{basic_info}\n\n**Consejos Rápidos:**\n{tips}",
        "fr": f"**{dest_info['name']}**\n\n{basic_info}\n\n**Conseils Rapides:**\n{tips}",
        "ja": f"**{dest_info['name']}**\n\n{basic_info}\n\n**簡単なヒント:**\n{tips}",
        "zh": f"**{dest_info['name']}**\n\n{basic_info}\n\n**快速提示:**\n{tips}"
    }
    return responses.get(language, responses["en"])

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! I'm your AI tour guide. How can I help you today?"}
    ]
if 'destination' not in st.session_state:
    st.session_state.destination = ''
if 'language' not in st.session_state:
    st.session_state.language = 'en'
if 'api_key_configured' not in st.session_state:
    st.session_state.api_key_configured = False

# Sidebar
with st.sidebar:
    st.title("🌍 AI Tour Guide")
    
    # Destination Selection
    st.subheader("🗺️ Destination")
    destinations = {
        "": "Select Destination",
        "paris": "🇫🇷 Paris, France",
        "tokyo": "🇯🇵 Tokyo, Japan", 
        "newyork": "🇺🇸 New York, USA",
        "london": "🇬🇧 London, UK"
    }
    destination = st.selectbox("Choose Destination", 
                              options=list(destinations.keys()), 
                              format_func=lambda x: destinations[x])
    st.session_state.destination = destination
    
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
    
    # Quick Actions
    st.subheader("⚡ Quick Actions")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🗺️ Attractions", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": "What are the top attractions here?"})
        if st.button("🍽️ Food", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": "Recommend local food and restaurants"})
    
    with col2:
        if st.button("🚇 Transport", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": "How to get around?"})
        if st.button("🚨 Emergency", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": "Emergency contacts and information"})

    # API Key Configuration (Hidden in expander)
    with st.expander("🔧 Developer Settings"):
        st.info("Configure API key for AI features")
        openai_api_key = st.text_input("OpenAI API Key", type="password", 
                                      help="Get your API key from https://platform.openai.com")
        if openai_api_key:
            st.session_state.api_key_configured = True
            st.session_state.openai_api_key = openai_api_key
            st.success("✅ API key configured!")
        else:
            st.session_state.api_key_configured = False
            if hasattr(st.session_state, 'openai_api_key'):
                del st.session_state.openai_api_key
            st.warning("⚠️ AI features disabled without API key")

# Main Chat Interface
st.title("🌍 AI Tour Guide")
st.markdown("Your intelligent travel companion with multi-language support")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask about travel destinations, tips, or recommendations..."):
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
            # Use offline mode
            full_response = get_offline_response(prompt, st.session_state.destination, st.session_state.language)
            message_placeholder.markdown(full_response)
        else:
            try:
                # Initialize OpenAI client
                client = OpenAI(api_key=openai_api_key)
                
                # Prepare messages for OpenAI
                messages_for_api = [
                    {"role": "system", "content": f"You are a friendly, knowledgeable tour guide. Respond in {st.session_state.language} language. Be helpful and provide practical travel advice."}
                ] + st.session_state.messages
                
                # Get AI response
                stream = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages_for_api,
                    stream=True,
                    max_tokens=1000,
                    temperature=0.7
                )
                
                # Stream the response
                for chunk in stream:
                    if chunk.choices[0].delta.content is not None:
                        full_response += chunk.choices[0].delta.content
                        message_placeholder.markdown(full_response + "▌")
                
                message_placeholder.markdown(full_response)
                
            except Exception as e:
                # Fallback to offline response
                full_response = get_offline_response(prompt, st.session_state.destination, st.session_state.language)
                message_placeholder.markdown(full_response)
        
        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": full_response})

# Footer
st.markdown("---")
st.markdown("### 💡 How to Use")
st.markdown("""
1. **Select a destination** from the sidebar
2. **Choose your preferred language**
3. **Ask questions** about attractions, food, transport, etc.
4. **Use quick actions** for common queries
5. **Configure API key** in Developer Settings for AI features
""")

st.markdown("### 🌟 Features")
st.markdown("""
- **Multi-language support** - English, Spanish, French, Japanese, Chinese
- **Destination guides** - Paris, Tokyo, New York, London
- **Quick actions** - One-click common questions
- **Offline mode** - Works without API key
- **AI-powered** - Enhanced responses with API key
""")
