import os, re, json, requests, streamlit as st
from io import BytesIO
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
st.title("🌎 AI Tour Guide — Online + Offline Mode")

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

# -------------------------
# OFFLINE CITY DATABASE
# -------------------------
OFFLINE_CITIES = {
    "bengaluru": {
        "info": "Bengaluru — the tech capital of India, known for its parks, cafés, and cool climate.",
        "spots": ["Cubbon Park", "Lalbagh", "Vidhana Soudha", "Church Street"]
    },
    "mysuru": {
        "info": "Mysuru is famous for its royal heritage and grand Mysore Palace.",
        "spots": ["Mysore Palace", "Chamundi Hills", "Brindavan Gardens"]
    },
    "mangaluru": {
        "info": "Mangaluru — a coastal city known for beaches, temples, and seafood.",
        "spots": ["Panambur Beach", "Kadri Temple", "St. Aloysius Chapel"]
    },
    "coorg": {
        "info": "Coorg — the Scotland of India, known for its coffee estates and waterfalls.",
        "spots": ["Abbey Falls", "Dubare Elephant Camp", "Raja’s Seat"]
    },
    "udupi": {
        "info": "Udupi — a serene temple town and birthplace of South Indian cuisine.",
        "spots": ["Sri Krishna Matha", "Malpe Beach", "St. Mary’s Island"]
    },
    "chikmagalur": {
        "info": "Chikmagalur — a lush hill station known for coffee and trekking trails.",
        "spots": ["Mullayanagiri", "Hebbe Falls", "Baba Budangiri"]
    },
    "gokarna": {
        "info": "Gokarna — peaceful beaches and temples, a perfect escape from the city.",
        "spots": ["Om Beach", "Kudle Beach", "Mahabaleshwar Temple"]
    },
    "hampi": {
        "info": "Hampi — ancient ruins of the Vijayanagara Empire, a UNESCO World Heritage Site.",
        "spots": ["Virupaksha Temple", "Vittala Temple", "Matanga Hill"]
    }
}

# -------------------------
# HELPERS
# -------------------------
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
    return m.group(1).strip() if m else None

def get_offline_info(city):
    data = OFFLINE_CITIES.get(city)
    if not data:
        return f"Sorry, I don’t have offline info for {city.title()} yet."
    info = f"{city.title()}** — {data['info']}\n\n*Must Visit:*"
    for s in data["spots"]:
        info += f"\n- {s}"
    return info

def gpt_guide(city, user_input, lang="English"):
    if not (OPENAI_API_KEY and OpenAI):
        return None
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        prompt = f"You are a dynamic travel guide. User asked: '{user_input}'. Respond about {city}, give 3-4 recommendations, and ask a question back."
        r = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
        )
        return r.choices[0].message.content.strip()
    except:
        return None

def speak_text(text, lang="en"):
    try:
        tts = gTTS(text=text, lang=lang)
        path = os.path.join(DATA_DIR, "voice.mp3")
        tts.save(path)
        st.audio(open(path, "rb").read())
    except:
        pass

def get_unsplash(city):
    if not UNSPLASH_ACCESS_KEY:
        return []
    try:
        r = requests.get(
            "https://api.unsplash.com/search/photos",
            params={"query": city, "client_id": UNSPLASH_ACCESS_KEY, "per_page": 3},
            timeout=8,
        )
        return [p["urls"]["regular"] for p in r.json().get("results", [])]
    except:
        return []

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

# -------------------------
# MAIN APP
# -------------------------
online = is_online()
status = "🟢 Online Mode" if online else "🔴 Offline Mode"
st.sidebar.info(f"*Status:* {status}")
st.sidebar.markdown("Offline data available for Karnataka cities.")

lang = st.sidebar.selectbox("Voice language", ["en", "hi", "kn"], index=0)

st.markdown("#### 💬 Talk to your AI Tour Guide below!")

if "chat" not in st.session_state:
    st.session_state.chat = []
if "last_city" not in st.session_state:
    st.session_state.last_city = None

user_input = st.chat_input("Ask about any place...")

if user_input:
    st.session_state.chat.append({"role": "user", "content": user_input})

for message in st.session_state.chat:
    with st.chat_message(message["role"]):
        st.write(message["content"])

if user_input:
    greeting_words = ["hi", "hello", "hey", "namaste", "yo"]
    city = detect_city(user_input)
    ai_reply = ""

    with st.chat_message("assistant"):
        if any(word in user_input.lower() for word in greeting_words):
            ai_reply = (
                "👋 Hey there, traveler! I’m your AI Tour Guide.\n"
                "You can ask things like ‘Show me places in Coorg’ or ‘What to see in Mysuru’."
            )

        elif city or st.session_state.last_city:
            current_city = city or st.session_state.last_city
            st.session_state.last_city = current_city

            if online:
                ai_reply = gpt_guide(current_city, user_input) or get_offline_info(current_city)
            else:
                ai_reply = get_offline_info(current_city)

        else:
            ai_reply = (
                "🤔 I didn’t quite get that. Try saying ‘Tell me about Mangaluru’ or ‘Best places in Coorg’."
            )

        st.markdown(ai_reply)
        speak_text(ai_reply, lang)
        st.session_state.chat.append({"role": "assistant", "content": ai_reply})

        if st.session_state.last_city:
            city = st.session_state.last_city
            if online:
                imgs = get_unsplash(city)
                if imgs:
                    st.markdown("### 📸 Images")
                    cols = st.columns(len(imgs))
                    for i, url in enumerate(imgs):
                        with cols[i % len(cols)]:
                            st.image(url, width="stretch")

            lat, lon = geocode(city)
            if lat and lon and FOLIUM_OK:
                st.markdown("### 🗺 Map")
                m = folium.Map(location=[lat, lon], zoom_start=12)
                folium.Marker([lat, lon], tooltip=city.title()).add_to(m)
                st_folium(m, width=700, height=400)
            elif not FOLIUM_OK:
                st.warning("🗺 Map module unavailable (folium not installed).")

st.markdown("---")
st.caption(f"AI Tour Guide — {'Offline Ready' if not online else 'Online & Smart'} 🌎")
