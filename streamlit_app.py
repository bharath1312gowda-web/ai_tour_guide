import os
import re
import json
import time
import requests
import streamlit as st
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
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

# Load .env
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY", "")

# Setup directories
DATA_DIR = "data"
CITIES_DIR = os.path.join(DATA_DIR, "cities")
os.makedirs(CITIES_DIR, exist_ok=True)

# Streamlit config
st.set_page_config(page_title="AI Tour Guide", layout="wide")
st.title("🌎 AI Tour Guide — Online + Offline")

# --------------------------
# HELPER FUNCTIONS
# --------------------------
def safe_key(s): return "".join(c for c in s.lower().strip().replace(" ", "") if c.isalnum() or c in "-")

def is_online():
    try:
        requests.get("https://www.google.com", timeout=2)
        return True
    except:
        return False

def make_placeholder_map_image(city, lat=None, lon=None, dest_path=None):
    img = Image.new("RGB", (800, 400), (245,245,245))
    d = ImageDraw.Draw(img)
    d.text((20, 20), f"{city.title()}", fill=(0,0,0))
    if lat and lon:
        d.text((20, 60), f"Lat: {lat:.3f}, Lon: {lon:.3f}", fill=(80,80,80))
    if dest_path: img.save(dest_path)
    return img

def geocode_city(city):
    try:
        r = requests.get("https://nominatim.openstreetmap.org/search",
                         params={"q": city, "format": "json", "limit": 1},
                         headers={"User-Agent": "ai-tour-guide"}, timeout=8)
        data = r.json()
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except:
        return None, None
    return None, None

def fetch_unsplash_urls(city, n=3):
    if not UNSPLASH_ACCESS_KEY: return []
    try:
        r = requests.get("https://api.unsplash.com/search/photos",
                         params={"query": city, "per_page": n, "client_id": UNSPLASH_ACCESS_KEY}, timeout=8)
        results = r.json().get("results", [])
        return [p["urls"]["regular"] for p in results[:n]]
    except:
        return []

def gpt_reply(city, user_text):
    if not OPENAI_API_KEY or not OpenAI: return None
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        prompt = f"You are a travel guide. The user asked: '{user_text}'. Talk about {city} — attractions, culture, and food. Be friendly and brief."
        r = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300
        )
        return r.choices[0].message.content.strip()
    except:
        return None

def speak(text, lang="en"):
    try:
        tts = gTTS(text=text, lang=lang)
        p = os.path.join(DATA_DIR, f"tts_{int(time.time())}.mp3")
        tts.save(p)
        st.audio(open(p, "rb").read())
    except: pass

# --------------------------
# OFFLINE CITY DB
# --------------------------
OFFLINE_CITIES = {
    "bengaluru": {"info": "Bengaluru — tech capital, great weather, and gardens.", "spots": ["Cubbon Park", "Lalbagh"]},
    "mysuru": {"info": "Mysuru — royal heritage city.", "spots": ["Mysore Palace", "Brindavan Gardens"]},
    "coorg": {"info": "Coorg — coffee plantations & misty hills.", "spots": ["Abbey Falls", "Dubare Camp"]},
}

# --------------------------
# SIDEBAR
# --------------------------
online = is_online()
st.sidebar.markdown(f"*Status:* {'🟢 Online' if online else '🔴 Offline'}")

voice_lang = st.sidebar.selectbox("Voice language", ["en", "hi", "kn"], index=0)

# City downloader
st.sidebar.markdown("---")
city_to_download = st.sidebar.text_input("Download city for offline:")
if st.sidebar.button("Download"):
    if not city_to_download.strip():
        st.sidebar.error("Enter a city name first.")
    else:
        key = safe_key(city_to_download)
        folder = os.path.join(CITIES_DIR, key)
        os.makedirs(folder, exist_ok=True)
        meta = {"city": city_to_download, "info": OFFLINE_CITIES.get(key, {}).get("info", f"{city_to_download.title()} info."),
                "spots": OFFLINE_CITIES.get(key, {}).get("spots", []), "saved_at": time.time()}
        json.dump(meta, open(os.path.join(folder, "meta.json"), "w"), indent=2)

        # Download images
        saved = 0
        if online and UNSPLASH_ACCESS_KEY:
            urls = fetch_unsplash_urls(city_to_download)
            for i, url in enumerate(urls, start=1):
                try:
                    img = Image.open(BytesIO(requests.get(url).content))
                    img.save(os.path.join(folder, f"img_{i}.jpg"))
                    saved += 1
                except:
                    pass

        # Save map
        lat, lon = (None, None)
        if online:
            lat, lon = geocode_city(city_to_download)
        make_placeholder_map_image(city_to_download, lat, lon, os.path.join(folder, "map.png"))

        st.sidebar.success(f"Saved {city_to_download} offline with {saved} images.")

# List saved cities
st.sidebar.markdown("### Saved offline cities")
folders = [f for f in os.listdir(CITIES_DIR) if os.path.isdir(os.path.join(CITIES_DIR, f))]
if not folders:
    st.sidebar.info("No cities saved yet.")
else:
    for f in folders:
        st.sidebar.write("📁", f)

# --------------------------
# MAIN CHAT
# --------------------------
if "chat" not in st.session_state: st.session_state.chat = []

for msg in st.session_state.chat:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_input = st.chat_input("Ask about any city...")

if user_input:
    st.session_state.chat.append({"role": "user", "content": user_input})
    with st.chat_message("user"): st.markdown(user_input)

    reply = ""
    city = None
    for c in list(OFFLINE_CITIES.keys()) + folders:
        if c in user_input.lower():
            city = c
            break

    if city:
        folder = os.path.join(CITIES_DIR, safe_key(city))
        if online:
            reply = gpt_reply(city, user_input) or f"{city.title()} — info unavailable."
        else:
            meta_path = os.path.join(folder, "meta.json")
            if os.path.exists(meta_path):
                meta = json.load(open(meta_path))
                reply = meta["info"]
            else:
                reply = OFFLINE_CITIES.get(city, {}).get("info", f"{city.title()} info unavailable offline.")
    else:
        reply = "Tell me a city name (e.g., Mysuru, Coorg)."

    with st.chat_message("assistant"):
        st.markdown(reply)
        speak(reply, voice_lang)

    st.session_state.chat.append({"role": "assistant", "content": reply})

    # Show images and map
    if city:
        st.markdown("---")
        st.subheader(f"📸 {city.title()} Highlights")
        imgs = []
        folder = os.path.join(CITIES_DIR, safe_key(city))
        if os.path.isdir(folder):
            imgs = [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith(".jpg")]
        if imgs:
            cols = st.columns(min(3, len(imgs)))
            for i, path in enumerate(imgs):
                with cols[i % len(cols)]:
                    st.image(path, width='stretch')
        elif online:
            urls = fetch_unsplash_urls(city)
            cols = st.columns(min(3, len(urls)))
            for i, url in enumerate(urls):
                with cols[i % len(cols)]:
                    st.image(url, width='stretch')
        else:
            st.info("No images available offline for this city.")

        st.subheader("🗺 Map")
        lat, lon = geocode_city(city) if online else (None, None)
        if online and lat and lon and FOLIUM_OK:
            m = folium.Map(location=[lat, lon], zoom_start=12)
            folium.Marker([lat, lon], tooltip=city.title()).add_to(m)
            st_folium(m, width=700, height=400)
        else:
            map_path = os.path.join(folder, "map.png")
            if os.path.exists(map_path):
                st.image(map_path, width='stretch')
            else:
                st.info("No saved map for this city.")

st.markdown("---")
st.caption("AI Tour Guide — Switches automatically between online (AI + live maps) and offline (saved data).")
