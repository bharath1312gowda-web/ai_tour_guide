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

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! I'm your AI tour guide. How can I help you today?"}
    ]
if 'destination' not in st.session_state:
    st.session_state.destination = ''
if 'language' not in st.session_state:
    st.session_state.language = 'en'

# Load offline data
@st.cache_data
def load_offline_data():
    try:
        with open('data/offline_data.json', 'r') as f:
            return json.load(f)
    except:
        return {"destinations": {}, "phrases": {}}

offline_data = load_offline_data()

# Sidebar
with st.sidebar:
    st.title("🌍 AI Tour Guide")
    
    # API Configuration
    st.subheader("🔑 API Configuration")
    openai_api_key = st.text_input("OpenAI API Key", type="password", 
                                  help="Get your API key from https://platform.openai.com")
    
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
        
        try:
            if not openai_api_key:
                st.error("❌ Please add your OpenAI API key in the sidebar")
                st.stop()
            
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
            offline_responses = {
                "en": "I'm currently having trouble connecting to AI services. Here's what I know:\n\n" + get_offline_info(st.session_state.destination, "en"),
                "es": "Estoy teniendo problemas para conectarme a los servicios de IA. Esto es lo que sé:\n\n" + get_offline_info(st.session_state.destination, "es"),
                "fr": "Je rencontre des problèmes de connexion aux services d'IA. Voici ce que je sais:\n\n" + get_offline_info(st.session_state.destination, "fr"),
                "ja": "AIサービスへの接続に問題が発生しています。私が知っていることは次のとおりです:\n\n" + get_offline_info(st.session_state.destination, "ja"),
                "zh": "我目前连接到AI服务有问题。这是我知道的:\n\n" + get_offline_info(st.session_state.destination, "zh")
            }
            fallback = offline_responses.get(st.session_state.language, offline_responses["en"])
            message_placeholder.markdown(fallback)
            full_response = fallback
        
        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": full_response})

def get_offline_info(destination, language):
    """Get offline information about a destination"""
    if not destination or destination not in offline_data['destinations']:
        return "Please select a destination from the sidebar to get specific information."
    
    dest_info = offline_data['destinations'][destination]
    attractions = "\n".join([f"• {attr}" for attr in dest_info.get('attractions', [])[:3]])
    tips = "\n".join([f"💡 {tip}" for tip in dest_info.get('tips', [])[:2]])
    
    responses = {
        "en": f"**{dest_info['name']}**\n\n**Top Attractions:**\n{attractions}\n\n**Travel Tips:**\n{tips}",
        "es": f"**{dest_info['name']}**\n\n**Principales Atracciones:**\n{attractions}\n\n**Consejos de Viaje:**\n{tips}",
        "fr": f"**{dest_info['name']}**\n\n**Principales Attractions:**\n{attractions}\n\n**Conseils de Voyage:**\n{tips}",
        "ja": f"**{dest_info['name']}**\n\n**主なアトラクション:**\n{attractions}\n\n**旅行のヒント:**\n{tips}",
        "zh": f"**{dest_info['name']}**\n\n**主要景点:**\n{attractions}\n\n**旅行提示:**\n{tips}"
    }
    
    return responses.get(language, responses["en"])

# Footer
st.markdown("---")
st.markdown("### 💡 Tips")
st.markdown("""
- Add your OpenAI API key in the sidebar to enable AI features
- Select a destination for personalized information  
- Use quick actions for common questions
- Works offline with basic destination info
""")
