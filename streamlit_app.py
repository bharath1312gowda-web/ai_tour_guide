import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import os
import os
import requests
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import folium
from streamlit_folium import st_folium

# -------------------------------------------------------------------
# Load environment variables
# -------------------------------------------------------------------
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")

if not OPENAI_API_KEY:
    st.error("❌ Missing OpenAI API key in .env")
    st.stop()

client = OpenAI(api_key=OPENAI_API_KEY)

# -------------------------------------------------------------------
# Streamlit page setup
# -------------------------------------------------------------------
st.set_page_config(page_title="AI Tour Guide 🌍", layout="wide")

st.sidebar.title("🎨 Theme")
theme = st.sidebar.radio("Select Theme", ["🌞 Light", "🌙 Dark"])
bg_color = "#f2f6ff" if theme == "🌞 Light" else "#0e1117"
text_color = "#000000" if theme == "🌞 Light" else "#ffffff"

st.markdown(
    f"""
    <style>
    .stApp {{
        background-color: {bg_color};
        color: {text_color};
    }}
    .chat-bubble-user {{
        background-color: #0078ff20;
        border-radius: 12px;
        padding: 10px;
        margin: 5px 0;
    }}
    .chat-bubble-bot {{
        background-color: #00b4d820;
        border-radius: 12px;
        padding: 10px;
        margin: 5px 0;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------------------------------------------------------
# Sidebar input
# -------------------------------------------------------------------
st.sidebar.header("🌍 Destination Info")
city = st.sidebar.text_input("Enter a destination (e.g., Paris, Bengaluru, Tokyo)")
category = st.sidebar.radio(
    "What would you like to explore?",
    ["🏞 Places", "🍴 Food", "🎭 Culture", "🏨 Hotels"]
)

# -------------------------------------------------------------------
# Helper: get image from Unsplash
# -------------------------------------------------------------------
def get_image_url(query: str) -> str:
    if not UNSPLASH_ACCESS_KEY:
        # Fallback: demo image
        return "https://source.unsplash.com/featured/?travel"
    url = f"https://api.unsplash.com/photos/random?query={query}&client_id={UNSPLASH_ACCESS_KEY}"
    r = requests.get(url)
    if r.status_code == 200:
        data = r.json()
        return data.get("urls", {}).get("regular", "https://source.unsplash.com/featured/?travel")
    else:
        return "https://source.unsplash.com/featured/?travel"

# -------------------------------------------------------------------
# Generate AI recommendations
# -------------------------------------------------------------------
def generate_suggestions(city, category):
    prompt = f"You are an expert travel guide. Suggest 3 {category.lower()} to experience in {city}. Include short descriptions and local tips."
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8,
        max_tokens=500
    )
    return response.choices[0].message.content.strip()

# -------------------------------------------------------------------
# UI layout
# -------------------------------------------------------------------
st.title("🗺 AI Tour Guide 2.0")
st.caption("Your personalized travel assistant powered by OpenAI & Unsplash 🌍")

if city:
    st.subheader(f"✨ {category} in {city.title()}")
    with st.spinner("Planning your experience..."):
        try:
            suggestions = generate_suggestions(city, category)
            st.markdown(f"<div class='chat-bubble-bot'>{suggestions}</div>", unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Error: {e}")

    # Destination images
    st.markdown("### 📸 Destination Highlights")
    cols = st.columns(3)
    for i in range(3):
        with cols[i]:
            st.image(get_image_url(city), use_container_width=True)

    # Interactive map
    st.markdown("### 🗺 Map View")
    m = folium.Map(location=[0, 0], zoom_start=2)
    if city:
        try:
            geo = requests.get(f"https://nominatim.openstreetmap.org/search?format=json&q={city}").json()
            if geo:
                lat, lon = float(geo[0]["lat"]), float(geo[0]["lon"])
                m.location = [lat, lon]
                m.zoom_start = 10
                folium.Marker([lat, lon], tooltip=city.title()).add_to(m)
        except:
            pass
    st_folium(m, width=700, height=400)

else:
    st.info("👈 Enter a destination and choose a category to begin your adventure!")

st.markdown("---")
st.caption("Built with ❤ by Bharath Gowda M — AI Tour Guide 2.0")
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
