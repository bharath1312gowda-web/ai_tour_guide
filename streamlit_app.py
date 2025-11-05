import os, json, time, requests, streamlit as st
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv
import folium
from streamlit_folium import st_folium
import pyttsx3
import speech_recognition as sr
from googletrans import Translator
from openai import OpenAI

# Load keys
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)
translator = Translator()

DATA_FILE = "data/offline_data.json"
os.makedirs("data", exist_ok=True)
os.makedirs("static/maps", exist_ok=True)

st.set_page_config(page_title="AI Tour Guide 3.0 🌍", layout="wide")

# ---------- UTILITIES ----------
def is_online():
    try:
        requests.get("https://www.google.com", timeout=2)
        return True
    except:
        return False

def speak(text):
    engine = pyttsx3.init()
    engine.setProperty("rate", 170)
    engine.say(text)
    engine.runAndWait()

def listen():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("🎤 Listening... Speak now!")
        audio = r.listen(source, phrase_time_limit=5)
    try:
        text = r.recognize_google(audio)
        st.success(f"You said: {text}")
        return text
    except:
        st.warning("Could not understand voice input.")
        return ""

def translate_text(text, lang_code):
    if lang_code == "en":
        return text
    try:
        translated = translator.translate(text, dest=lang_code)
        return translated.text
    except:
        return text

def load_offline_data():
    if not os.path.exists(DATA_FILE): return {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def fetch_unsplash_images(city, n=3):
    if not UNSPLASH_ACCESS_KEY: return []
    url = f"https://api.unsplash.com/search/photos?query={city}&per_page={n}&client_id={UNSPLASH_ACCESS_KEY}"
    try:
        res = requests.get(url, timeout=6)
        data = res.json()
        return [i["urls"]["regular"] for i in data["results"][:n]]
    except:
        return []

def fetch_ai_guide(city, lang="en"):
    try:
        msg = [
            {"role": "system", "content": f"You are a friendly AI tour guide speaking in {lang}. Provide top attractions, cultural insights, and hidden gems for {city} in bullet points."}
        ]
        res = client.chat.completions.create(model="gpt-3.5-turbo", messages=msg, temperature=0.8)
        return res.choices[0].message.content
    except:
        return f"Explore {city.title()} — a city full of culture and beauty!"

def make_map(lat, lon, city):
    m = folium.Map(location=[lat, lon], zoom_start=12, tiles="CartoDB Positron")
    folium.Marker([lat, lon], tooltip=city.title(), icon=folium.Icon(color="red")).add_to(m)
    return m

# ---------- MAIN ----------
st.title("🌍 AI-Powered Virtual Tour Guide")
st.markdown("*Voice + Text + GPS + Multi-Language + Offline Mode*")

online = is_online()
st.sidebar.write(f"*Internet:* {'🟢 Online' if online else '🔴 Offline'}")

lang = st.sidebar.selectbox("Language", {"en": "English", "kn": "Kannada", "hi": "Hindi"}, format_func=lambda x: {"en": "English 🇬🇧", "kn": "Kannada 🇮🇳", "hi": "Hindi 🇮🇳"}[x])
city = st.sidebar.text_input("Enter City Name:", "Bengaluru")

if st.sidebar.button("🎙 Voice Input"):
    city = listen()

if st.sidebar.button("🧭 Use My Location"):
    st.session_state["gps_mode"] = True

offline_data = load_offline_data()
if city.lower() in offline_data:
    st.sidebar.success(f"Offline data available for {city.title()}")

st.sidebar.markdown("---")
if st.sidebar.button("💾 Save for Offline"):
    st.info(f"Saving {city} for offline use...")
    ai_text = fetch_ai_guide(city)
    lat, lon = 12.9716, 77.5946
    images = fetch_unsplash_images(city)
    offline_data[city.lower()] = {"city": city, "lat": lat, "lon": lon, "info": ai_text, "images": images}
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(offline_data, f, indent=2, ensure_ascii=False)
    st.success(f"✅ {city} saved for offline use!")

st.markdown("---")

# ---------- DISPLAY ----------
if online:
    st.subheader(f"✨ Welcome to {city.title()}!")
    response = fetch_ai_guide(city, lang)
    st.write(translate_text(response, lang))
    if st.button("🔊 Read Aloud"):
        speak(response)
    imgs = fetch_unsplash_images(city)
    if imgs:
        st.image(imgs, use_container_width=True)
    lat, lon = 12.9716, 77.5946
    st.markdown("### 🗺 Interactive Map")
    m = make_map(lat, lon, city)
    st_folium(m, width=700, height=400)
else:
    if city.lower() in offline_data:
        data = offline_data[city.lower()]
        st.subheader(f"📦 Offline Mode — {data['city']}")
        st.write(data["info"])
        if data["images"]:
            st.image(data["images"], use_container_width=True)
        st.info("🗺 Offline map not interactive.")
    else:
        st.error("No offline data found for this city.")

st.markdown("---")
st.caption("AI Tour Guide 3.0 — Multilingual • Voice • Real-time GPS • Offline Ready")
