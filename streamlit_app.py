import os, re, json, requests, streamlit as st
from io import BytesIO
from PIL import Image
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

# -----------------------------
# CONFIGURATION
# -----------------------------
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")

st.set_page_config(page_title="AI Tour Guide", layout="wide")
st.title("🌍 AI Tour Guide — Online + Offline + Voice (2025 Edition)")

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

# -----------------------------
# OFFLINE KARNATAKA DATA
# -----------------------------
OFFLINE_CITIES = {
    "bengaluru": {
        "info": "Bengaluru, the Silicon Valley of India, is known for its pleasant weather, gardens, and tech culture.",
        "spots": [
            "Cubbon Park — peaceful greenery in the heart of the city",
            "Lalbagh Botanical Garden — 240-acre garden with a glasshouse",
            "Vidhana Soudha — iconic government building",
            "Church Street — food, art, and nightlife hub"
        ]
    },
    "mysuru": {
        "info": "Mysuru, the royal city of Karnataka, is known for its palaces, yoga, and sandalwood craft.",
        "spots": [
            "Mysore Palace — majestic Indo-Saracenic architecture",
            "Chamundi Hills — panoramic city view",
            "Brindavan Gardens — musical fountain show near KRS dam"
        ]
    },
    "mangaluru": {
        "info": "Mangaluru is a coastal city known for pristine beaches, temples, and spicy seafood.",
        "spots": [
            "Panambur Beach — sunset and watersports",
            "Kadri Manjunath Temple — ancient architecture",
            "St. Aloysius Chapel — artistic frescoes"
        ]
    },
    "udupi": {
        "info": "Udupi is a spiritual and coastal destination famous for the Krishna Temple and South Indian cuisine.",
        "spots": [
            "Sri Krishna Matha — revered temple with golden chariot",
            "Malpe Beach — gateway to St. Mary’s Island",
            "Manipal — cultural and educational hub"
        ]
    },
    "coorg": {
        "info": "Coorg, or Kodagu, is a hill station known for coffee plantations, waterfalls, and cool weather.",
        "spots": [
            "Abbey Falls — surrounded by coffee estates",
            "Dubare Elephant Camp — close wildlife encounters",
            "Raja’s Seat — sunset viewpoint"
        ]
    },
    "chikmagalur": {
        "info": "Chikmagalur is a mountain paradise famous for its coffee, hills, and trekking.",
        "spots": [
            "Mullayanagiri — highest peak in Karnataka",
            "Hebbe Falls — hidden amidst dense forest",
            "Baba Budangiri — trek and spiritual site"
        ]
    },
    "hampi": {
        "info": "Hampi, a UNESCO World Heritage Site, showcases ruins of the Vijayanagara Empire.",
        "spots": [
            "Virupaksha Temple — 7th-century spiritual center",
            "Vittala Temple — home to the iconic stone chariot",
            "Matanga Hill — stunning sunrise viewpoint"
        ]
    },
    "gokarna": {
        "info": "Gokarna blends spirituality with scenic beaches and peace.",
        "spots": [
            "Om Beach — shaped like the Om symbol",
            "Kudle Beach — calm and serene escape",
            "Mahabaleshwar Temple — historic Shiva temple"
        ]
    }
}

# -----------------------------
# UTILITIES
# -----------------------------
def is_online():
    try:
        requests.get("https://www.google.com", timeout=2)
        return True
    except:
        return False

def detect_city(text):
    text = text.lower()
    for c in OFFLINE_CITIES.keys():
        if c in text:
            return c
    m = re.search(r"in\s+([a-z\s]+)", text)
    return m.group(1).strip() if m else text.strip().split()[0]

def geocode(city):
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": city, "format": "json", "limit": 1},
            headers={"User-Agent": "ai-tour-guide"},
            timeout=8,
        )
        d = r.json()
        if d:
            return float(d[0]["lat"]), float(d[0]["lon"])
    except:
        return None, None
    return None, None

def fetch_unsplash(city):
    if not UNSPLASH_ACCESS_KEY:
        return []
    try:
        r = requests.get(
            "https://api.unsplash.com/search/photos",
            params={"query": city, "per_page": 3, "client_id": UNSPLASH_ACCESS_KEY},
            timeout=8,
        )
        return [p["urls"]["regular"] for p in r.json().get("results", [])]
    except:
        return []

def fetch_gpt(city, lang="English"):
    if not (OPENAI_API_KEY and OpenAI):
        return None
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        prompt = f"As a travel guide, describe {city} with 3 interesting highlights in {lang}."
        r = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
        )
        return r.choices[0].message.content.strip()
    except:
        return None

def tts_play(text, lang="en"):
    try:
        t = gTTS(text=text, lang=lang)
        fp = os.path.join(DATA_DIR, "voice.mp3")
        t.save(fp)
        st.audio(open(fp, "rb").read())
    except:
        st.warning("Voice output unavailable.")

# -----------------------------
# MAIN APP
# -----------------------------
online = is_online()
st.sidebar.success("🟢 Online" if online else "🔴 Offline")
lang = st.sidebar.selectbox("Voice language", ["en", "hi", "kn"], index=0)

# 🎤 Voice Input
st.components.v1.html("""
<div>
<button id="mic" style="padding:6px;">🎤 Speak</button>
<script>
const b=document.getElementById('mic');
b.onclick=()=>{
 const r=new(window.SpeechRecognition||window.webkitSpeechRecognition)();
 r.lang='en-IN';
 r.onresult=e=>{
  const q=e.results[0][0].transcript;
  const u=new URL(window.location);u.searchParams.set('q',q);
  window.location=u.toString();
 };
 r.start();
};
</script>
</div>
""", height=50)

params = st.query_params
speech_input = params.get("q", [""])[0] if "q" in params else ""
query = st.text_input("Ask or say something:", speech_input)

if query:
    city = detect_city(query)
    st.subheader(f"🏙 {city.title()}")

    info = ""
    if city in OFFLINE_CITIES:
        base = OFFLINE_CITIES[city]
        info = f"{base['info']}\n\n*Must Visit:*\n- " + "\n- ".join(base["spots"])
    elif online:
        gpt_text = fetch_gpt(city)
        info = gpt_text or f"{city.title()} is a wonderful place to explore with culture and scenic spots."
    else:
        info = f"{city.title()} data unavailable offline."

    st.markdown("### 📖 Recommendations")
    st.write(info)
    tts_play(info, lang)

    imgs = fetch_unsplash(city) if online else []
    if imgs:
        st.markdown("### 🖼 Images")
        cols = st.columns(len(imgs))
        for i, url in enumerate(imgs):
            with cols[i % len(cols)]:
                st.image(url, width='stretch')

    lat, lon = geocode(city)
    if lat and lon:
        st.markdown("### 🗺 Map")
        if FOLIUM_OK:
            m = folium.Map(location=[lat, lon], zoom_start=12)
            folium.Marker([lat, lon], tooltip=city.title()).add_to(m)
            st_folium(m, width=700, height=400)
        else:
            st.info(f"Coordinates: {lat}, {lon}")

st.markdown("---")
st.caption("AI Tour Guide — Smart, Voice-Enabled, and Offline Ready")
