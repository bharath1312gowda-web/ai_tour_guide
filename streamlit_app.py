import streamlit as st
import openai
import json
import requests
from geopy.distance import geodesic
import os

# Page configuration
st.set_page_config(
    page_title="AI Tour Guide",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'destination' not in st.session_state:
    st.session_state.destination = ''
if 'language' not in st.session_state:
    st.session_state.language = 'en'

# Load offline data
@st.cache_data
def load_offline_data():
    with open('data/offline_data.json', 'r') as f:
        return json.load(f)

offline_data = load_offline_data()

# Sidebar
with st.sidebar:
    st.title("🌍 AI Tour Guide")
    
    # API Configuration
    st.subheader("API Configuration")
    openai_api_key = st.text_input("OpenAI API Key", type="password")
    
    # Destination Selection
    st.subheader("Destination")
    destinations = {
        "": "Select Destination",
        "paris": "Paris, France",
        "tokyo": "Tokyo, Japan", 
        "newyork": "New York, USA",
        "london": "London, UK"
    }
    destination = st.selectbox("Choose Destination", options=list(destinations.keys()), 
                              format_func=lambda x: destinations[x])
    st.session_state.destination = destination
    
    # Language Selection
    st.subheader("Language")
    language = st.selectbox("Select Language", 
                           ["en", "es", "fr", "ja", "zh"],
                           format_func=lambda x: {
                               "en": "English",
                               "es": "Spanish", 
                               "fr": "French",
                               "ja": "Japanese",
                               "zh": "Chinese"
                           }[x])
    st.session_state.language = language
    
    # Quick Actions
    st.subheader("Quick Actions")
    if st.button("🗺️ Top Attractions"):
        st.session_state.messages.append({"role": "user", "content": "What are the top attractions?"})
    if st.button("🍽️ Local Food"):
        st.session_state.messages.append({"role": "user", "content": "Recommend local food"})
    if st.button("🚇 Transportation"):
        st.session_state.messages.append({"role": "user", "content": "Transportation options"})
    if st.button("🚨 Emergency Info"):
        st.session_state.messages.append({"role": "user", "content": "Emergency information"})

# Main Chat Interface
st.title("🌍 AI Tour Guide")
st.markdown("Your intelligent travel companion with multi-language support")

# Chat messages display
chat_container = st.container()
with chat_container:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask about travel destinations, tips, or recommendations..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Get AI response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                if not openai_api_key:
                    st.error("Please add your OpenAI API key in the sidebar")
                    st.stop()
                
                openai.api_key = openai_api_key
                
                # Get destination context
                destination_info = ""
                if st.session_state.destination and st.session_state.destination in offline_data['destinations']:
                    dest = offline_data['destinations'][st.session_state.destination]
                    destination_info = f" about {dest['name']}"
                
                # Call OpenAI
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": f"You are a friendly tour guide. Respond in {st.session_state.language}."},
                        *st.session_state.messages
                    ],
                    max_tokens=1000,
                    temperature=0.7
                )
                
                ai_response = response.choices[0].message.content
                st.markdown(ai_response)
                st.session_state.messages.append({"role": "assistant", "content": ai_response})
                
            except Exception as e:
                st.error(f"Error: {str(e)}")
                # Fallback to offline response
                offline_responses = {
                    "en": "I'm currently having trouble connecting. Basic information is available in the sidebar.",
                    "es": "Estoy teniendo problemas de conexión. La información básica está disponible en la barra lateral.",
                    "fr": "Je rencontre des problèmes de connexion. Les informations de base sont disponibles dans la barre latérale.",
                    "ja": "接続に問題が発生しています。基本情報はサイドバーで利用できます。",
                    "zh": "我目前连接有问题。基本信息在侧边栏中可用。"
                }
                fallback = offline_responses.get(st.session_state.language, offline_responses["en"])
                st.markdown(fallback)
                st.session_state.messages.append({"role": "assistant", "content": fallback})

# Requirements for Streamlit
st.sidebar.markdown("---")
st.sidebar.markdown("### Requirements")
st.sidebar.code("streamlit\nopenai\npython-dotenv")
