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

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")

st.set_page_config(page_title="AI Tour Guide", layout="wide")
st.title("🌍 AI Tour Guide — Smart + Offline + Voice")

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

# ✅ Detailed Offline Karnataka Data
OFFLINE_CITIES = {
    "bengaluru": {
        "info": "Bengaluru, the Silicon Valley of India, is known for its gardens, nightlife, and tech culture.",
        "spots": [
            "Cubbon Park – a peaceful green oasis in the heart of the city",
            "Lalbagh Botanical Garden – home to the iconic glasshouse and exotic flora",
            "Vidhana Soudha – a grand architectural marvel of Karnataka’s government",
            "Church Street – buzzing with cafés, art, and music"
        ]
    },
    "mysuru": {
        "info": "Mysuru is a royal heritage city famous for its palaces, yoga, and sandalwood.",
        "spots": [
            "Mysore Palace – majestic Indo-Saracenic architecture and light show",
            "Chamundi Hills – offers panoramic views and temples",
            "Brindavan Gardens – musical fountain by KRS dam"
        ]
    },
    "mangaluru": {
        "info": "Mangaluru is a vibrant coastal city known for beaches, temples, and seafood.",
        "spots": [
            "Panambur Beach – perfect for sunsets and water sports",
            "Kadri Manjunatha Temple – ancient temple with unique architecture",
            "St. Aloysius Chapel – famous for intricate frescoes"
        ]
    },
    "udupi": {
        "info": "Udupi is a temple town famous for its Krishna Temple, beaches, and authentic South Indian cuisine.",
        "spots": [
            "Sri Krishna Matha – ancient temple with spiritual charm",
            "Malpe Beach – golden sands and St. Mary’s Island boat rides",
            "Manipal – educational hub with scenic viewpoints"
        ]
    },
    "coorg": {
        "info": "Coorg, the Scotland of India, is a hill station surrounded by coffee plantations and misty hills.",
        "spots": [
            "Abbey Falls – scenic waterfall amidst coffee estates",
            "Dubare Elephant Camp – enjoy elephant interactions",
            "Raja’s Seat – sunset viewpoint with valley panorama"
        ]
    },
    "chikmagalur": {
        "info": "Chikmagalur is a mountain paradise famous for coffee, waterfalls, and treks.",
        "spots": [
            "Mullayanagiri – the highest peak in Karnataka",
            "Hebbe Falls – hidden amidst coffee estates",
            "Baba Budangiri – trekking and spiritual significance"
        ]
    },
    "hampi": {
        "info": "Hampi is a UNESCO World Heritage Site filled with ruins of the Vijayanagara Empire.",
        "spots": [
            "Virupaksha Temple – spiritual heart of Hampi",
            "Vittala Temple – home to the iconic Stone Chariot",
            "Matanga Hill – best sunrise point in Hampi"
        ]
    },
    "gokarna": {
        "info": "Gokarna is a coastal town blending spirituality with beach vibes.",
        "spots": [
            "Om Beach – shaped like the Om symbol, great for water sports",
            "Kudle Beach – peaceful and scenic stretch for relaxation",
            "Mahabaleshwar Temple – ancient Shiva temple near the coast"
        ]
    }
}

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
        r = requests.get("https://nominatim.openstreetmap.org/search",
            params={"q": city, "format": "json", "limit": 1},
            headers={"User-Agent": "tour-guide"}, timeout=8)
        d = r.json()
        if d: return float(d[0]["lat"]), float(d[0]["lon"])
    except:
        return None, None
    return None, None

def fetch_unsplash(city):
    if not UNSPLASH_ACCESS_KEY:
        return []
    try:
        r = requests.get("https://api.unsplash.com/search/photos",
            params={"query": city, "per_page": 3, "client_id": UNSPLASH_ACCESS_KEY}, timeout=8)
        return [p["urls"]["regular"] for p in r.json().get("results", [])]
    except:
        return []

def fetch_gpt(city, lang="English"):
    if not (OPENAI_API_KEY and OpenAI):
        return None
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        prompt = f"As a travel guide, describe {city} with 3 short highlights in {lang}."
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

# ---------------------------------------
# UI
# ---------------------------------------
online = is_online()
st.sidebar.success("🟢 Online" if online else "🔴 Offline")
lang = st.sidebar.selectbox("Voice language", ["en", "hi", "kn"], index=0)

st.components.v1.html("""
<div>
<button id="mic">🎤 Speak</button>
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
</script></div>
""", height=50)

params = st.experimental_get_query_params()
speech_input = params.get("q", [""])[0]
query = st.text_input("Ask about a place:", speech_input)

if query:
    city = detect_city(query)
    st.subheader(f"🏙 {city.title()}")

    info = ""
    if city in OFFLINE_CITIES:
        base = OFFLINE_CITIES[city]
        info = f"{base['info']}\n\n*Must Visit:*\n- " + "\n- ".join(base["spots"])
    elif online:
        gpt_text = fetch_gpt(city)
        info = gpt_text or f"{city.title()} is a wonderful place to visit in India."

    st.markdown("### 📖 Recommendations")
    st.write(info)
    tts_play(info, lang)

    imgs = fetch_unsplash(city) if online else []
    if imgs:
        st.markdown("### 🖼 Images")
        cols = st.columns(len(imgs))
        for i, url in enumerate(imgs):
            with cols[i % len(cols)]:
                st.image(url, use_container_width=True)

    lat, lon = geocode(city)
    if lat and lon:
        st.markdown("### 🗺 Map")
        if FOLIUM_OK:
            m = folium.Map(location=[lat, lon], zoom_start=12)
            folium.Marker([lat, lon], tooltip=city.title()).add_to(m)
            st_folium(m, width=700, height=400)
        else:
            st.info(f"Location: {lat}, {lon}")
