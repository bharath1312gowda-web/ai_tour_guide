import os
import re
import json
import time
import math
import requests
import streamlit as st
from io import BytesIO
from PIL import Image, ImageDraw
from gtts import gTTS
from dotenv import load_dotenv

try:
    from openai import OpenAI
except:
    OpenAI = None

try:
    import folium
    from streamlit_folium import st_folium
    FOLIUM_OK = True
except:
    FOLIUM_OK = False

# ----------------------------------------------------
# SETUP
# ----------------------------------------------------
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")

DATA_DIR = "data"
IMAGES_DIR = os.path.join("static", "images")
MAPS_DIR = os.path.join("static", "maps")
OFFLINE_DATA_FILE = os.path.join(DATA_DIR, "offline_data.json")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(MAPS_DIR, exist_ok=True)

st.set_page_config(page_title="AI Tour Guide", layout="wide")

# ----------------------------------------------------
# HELPERS
# ----------------------------------------------------
def is_online(timeout=2):
    try:
        requests.get("https://www.google.com", timeout=timeout)
        return True
    except:
        return False

def safe_filename(s):
    return "".join(c for c in s.lower().strip().replace(" ", "") if c.isalnum() or c in "-")

def load_offline():
    if not os.path.exists(OFFLINE_DATA_FILE):
        return {}
    try:
        return json.load(open(OFFLINE_DATA_FILE, "r", encoding="utf-8"))
    except:
        return {}

def save_offline(data):
    json.dump(data, open(OFFLINE_DATA_FILE, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

def geocode_city(city):
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": city, "format": "json", "limit": 1},
            headers={"User-Agent": "ai-tour-guide"},
            timeout=8,
        )
        data = r.json()
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except:
        return None, None
    return None, None

def fetch_unsplash_images(city, n=3):
    if not UNSPLASH_ACCESS_KEY:
        return []
    try:
        res = requests.get(
            "https://api.unsplash.com/search/photos",
            params={"query": city, "per_page": n, "client_id": UNSPLASH_ACCESS_KEY},
            timeout=8,
        )
        res.raise_for_status()
        data = res.json().get("results", [])
        return [d["urls"]["regular"] for d in data[:n]]
    except:
        return []

def fetch_map(lat, lon):
    try:
        m = folium.Map(location=[lat, lon], zoom_start=12)
        folium.Marker([lat, lon]).add_to(m)
        return m
    except:
        return None

def tts_play(text, lang="en"):
    try:
        t = gTTS(text=text, lang=lang)
        fp = os.path.join(DATA_DIR, "tts.mp3")
        t.save(fp)
        st.audio(open(fp, "rb").read())
    except Exception as e:
        st.warning(f"TTS failed: {e}")

def fetch_openai(city, category, lang):
    if not OPENAI_API_KEY or not OpenAI:
        return None
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        prompt = f"You are a friendly AI tour guide. Give 3 short {category} recommendations for {city}, each 1 sentence long. Reply in {lang}."
        r = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
        )
        return r.choices[0].message.content.strip()
    except Exception:
        return None

# ----------------------------------------------------
# LOAD DB AND UI
# ----------------------------------------------------
db = load_offline()
online = is_online()

st.sidebar.header("Settings")
st.sidebar.markdown(f"*Network:* {'🟢 Online' if online else '🔴 Offline'}")

mode = st.sidebar.radio("Mode", ["Auto", "Force Online", "Force Offline"])
if mode == "Force Online": online = True
if mode == "Force Offline": online = False

category = st.sidebar.selectbox("Category", ["Places", "Food", "Culture", "Hotels"])
tts_lang = st.sidebar.selectbox("Voice Language", ["en", "hi", "kn"], index=0)

st.title("🌍 AI Tour Guide with Voice & Smart City Detection")

# ----------------------------------------------------
# INPUT
# ----------------------------------------------------
st.markdown("Type or speak about a place — e.g. 'Tell me about Mysore palaces'")
st.components.v1.html("""
<div>
<button id="mic" style="padding:6px;">🎤 Speak</button>
<script>
const btn=document.getElementById('mic');
btn.onclick=()=>{
  const rec=new(window.SpeechRecognition||window.webkitSpeechRecognition)();
  rec.lang='en-IN';
  rec.onresult=(e)=>{
    const t=e.results[0][0].transcript;
    const url=new URL(window.location);
    url.searchParams.set('q',t);
    window.location=url.toString();
  };
  rec.start();
};
</script>
</div>""", height=50)

params = st.experimental_get_query_params()
speech_input = params.get("q", [""])[0]
user_text = st.text_input("Ask or say something:", speech_input)

if user_text:
    match = re.search(r"in\s+([A-Za-z\s]+)", user_text)
    city = match.group(1).strip() if match else user_text.split()[0]
    st.subheader(f"🗺 City Detected: *{city.title()}*")

    if online:
        text = fetch_openai(city, category, tts_lang)
        if not text:
            text = f"{category} highlights in {city}: 1) Main attraction 2) Famous food 3) Hidden gem."
    else:
        key = safe_filename(city)
        text = db.get(key, {}).get("text", f"{category} highlights in {city}: stored data not found.")

    st.markdown("### 📖 Recommendations")
    st.write(text)
    tts_play(text, lang=tts_lang)

    # ------------------------
    # IMAGES + MAP
    # ------------------------
    st.markdown("### 🖼 Images")
    imgs = []
    if online:
        imgs = fetch_unsplash_images(city, 3)
    if imgs:
        cols = st.columns(3)
        for i, url in enumerate(imgs):
            with cols[i % 3]:
                st.image(url, use_container_width=True)
    else:
        st.info("No images available.")

    lat, lon = geocode_city(city)
    if lat and lon:
        st.markdown("### 🗺 Map")
        if FOLIUM_OK:
            m = fetch_map(lat, lon)
            st_folium(m, width=700, height=400)
        else:
            st.write(f"Coordinates: {lat}, {lon}")

    # ------------------------
    # STORE OFFLINE
    # ------------------------
    key = safe_filename(city)
    db[key] = {"city": city, "text": text, "lat": lat, "lon": lon}
    save_offline(db)

st.markdown("---")
st.caption("Offline-ready AI Tour Guide — detects city name, speaks, and stores automatically.")
