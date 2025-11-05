import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Page configuration
st.set_page_config(page_title="AI Tour Guide", layout="wide")

# Retrieve OpenAI API key (from Streamlit secrets or .env)
api_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))

if not api_key or not api_key.startswith("sk-"):
    st.error("⚠ Invalid or missing OpenAI API key. Please check your .env or .streamlit/secrets.toml file.")
    st.stop()

# Initialize OpenAI client
client = OpenAI(api_key=api_key)

# Sidebar navigation
st.sidebar.title("🧭 Navigation")
page = st.sidebar.radio("Go to:", ["🏙 Personal Tour Guide", "👥 Meet Your Guides"])

# --- PAGE 1: Personal Tour Guide ---
if page == "🏙 Personal Tour Guide":
    st.title("🗺 Your Personal AI Tour Guide")
    st.write("Discover destinations, get personalized suggestions, and plan your trips effortlessly.")

    location = st.text_input("📍 Enter a place you'd like to explore:")
    mood = st.selectbox("🎯 Choose your travel style:", ["Adventure", "Relaxation", "Culture", "Food", "Nature"])

    if st.button("✨ Get Recommendations"):
        if not location.strip():
            st.warning("Please enter a location to continue.")
        else:
            with st.spinner("Finding your perfect spots..."):
                try:
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "You are an AI travel guide who gives short, exciting travel suggestions."},
                            {"role": "user", "content": f"Suggest 3 must-visit places and activities in {location} for a {mood} trip."}
                        ],
                    )
                    tour_plan = response.choices[0].message.content
                    st.success("Here’s your personalized travel plan:")
                    st.write(tour_plan)
                except Exception as e:
                    st.error(f"An error occurred: {e}")

# --- PAGE 2: Meet Your Guides ---
elif page == "👥 Meet Your Guides":
    st.title("👥 Meet Your Local Guides")
    st.write("Here are your friendly tour companions who can help you explore!")

    guides = [
        {"name": "Ravi", "specialty": "Historical sites & temples", "location": "Mysuru"},
        {"name": "Ananya", "specialty": "Food tours & markets", "location": "Bengaluru"},
        {"name": "Kiran", "specialty": "Beaches & nature", "location": "Mangaluru"},
    ]

    for guide in guides:
        with st.expander(f"👤 {guide['name']} - {guide['location']}"):
            st.write(f"*Specialty:* {guide['specialty']}")
            st.write("📞 Contact: Available on request")

    st.info("You can expand each guide's profile to know more!")

st.sidebar.info("Developed by Bharath Gowda M — AI Tour Guide Project 🌍")
