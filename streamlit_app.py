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
st.title("🌍 AI Tour Guide — Dynamic Conversational Mode")

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

# --------------------------
# OFFLINE DATABASE
# --------------------------
OFFLINE_CITIES = {
    "bengaluru": {
        "info": "Bengaluru — the tech capital of India, known for its gardens, cafés, and cool weather.",
        "spots": ["Cubbon Park", "Lalbagh", "Vidhana Soudha", "Church Street"]
    },
    "mysuru": {
        "info": "Mysuru is famous for royal heritage, yoga, and sandalwood.",
        "spots": ["Mysore Palace", "Chamundi Hills", "Brindavan Gardens"]
    },
    "mangaluru": {
        "info": "Mangaluru is a vibrant coastal city with beaches, temples, and seafood.",
        "spots": ["Panambur Beach", "Kadri Temple", "St. Aloysius Chapel"]
    },
    "coorg": {
        "info": "Coorg — the Scotland of India, surrounded by coffee plantations and waterfalls.",
        "spots": ["Abbey Falls", "Dubare Elephant Camp", "Raja’s Seat"]
    },
    "udupi": {
        "info": "Udupi — temple town and birthplace of delicious South Indian cuisine.",
        "spots": ["Sri Krishna Matha", "Malpe Beach", "St. Mary’s Island"]
    },
    "chikmagalur": {
        "info": "Chikmagalur is a hill station known for coffee, greenery, and trekking.",
        "spots": ["Mullayanagiri", "Hebbe Falls", "Baba Budangiri"]
    },
    "hampi": {
        "info": "Hampi — ancient ruins of the Vijayanagara Empire, a UNESCO World Heritage Site.",
        "spots": ["Virupaksha Temple", "Vittala Temple", "Matanga Hill"]
    },
    "gokarna": {
        "info": "Gokarna — peaceful beaches and ancient temples, perfect for a spiritual escape.",
        "spots": ["Om Beach", "Kudle Beach", "Mahabaleshwar Temple"]
    }
}

# --------------------------
# HELPERS
# --------------------------
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
    if city in OFFLINE_CITIES:
        data = OFFLINE_CITIES[city]
        recs = "\n".join(f"- {p}" for p in data["spots"])
        return f"{data['info']}\n\nMust Visit:\n{recs}"
    else:
        return f"Sorry, I don’t have offline info for {city.title()} yet."

def gpt_guide(city, user_input, lang="English"):
    if not (OPENAI_API_KEY and OpenAI):
        return None
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        prompt = f"You are a dynamic, friendly tour guide. User said: '{user_input}'. Respond naturally about {city}, include 3 relevant tips or attractions, and ask one follow-up question. Use emojis. Reply in {lang}."
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

# --------------------------
# MAIN APP
# --------------------------
online = is_online()
st.sidebar.success("🟢 Online" if online else "🔴 Offline")
lang = st.sidebar.selectbox("Voice language", ["en", "hi", "kn"], index=0)

st.markdown("#### 💬 Talk to your AI Tour Guide below!")

if "chat" not in st.session_state:
    st.session_state.chat = []
if "last_city" not in st.session_state:
    st.session_state.last_city = None

user_input = st.chat_input("Ask or say something about a place...")

if user_input:
    st.session_state.chat.append({"role": "user", "content": user_input})

for message in st.session_state.chat:
    with st.chat_message(message["role"]):
        st.write(message["content"])

if user_input:
    greeting_words = ["hi", "hello", "hey", "namaste", "yo", "good morning", "good evening"]
    city = detect_city(user_input)
    ai_reply = ""

    with st.chat_message("assistant"):
        if any(word in user_input.lower() for word in greeting_words):
            ai_reply = (
                "👋 Hey there, traveler! I’m your AI Tour Guide. "
                "Tell me a city you’d like to explore — like Mysuru, Coorg, or Gokarna!"
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
                "I didn’t quite get that 🤔. Try saying something like "
                "‘Show me places in Coorg’ or ‘Things to do in Mysuru’."
            )

        st.markdown(ai_reply)
        speak_text(ai_reply, lang)
        st.session_state.chat.append({"role": "assistant", "content": ai_reply})

        if st.session_state.last_city:
            imgs = get_unsplash(st.session_state.last_city) if online else []
            if imgs:
                st.markdown("### 📸 Images")
                cols = st.columns(len(imgs))
                for i, url in enumerate(imgs):
                    with cols[i % len(cols)]:
                        st.image(url, width="stretch")

            lat, lon = geocode(st.session_state.last_city)
            if lat and lon and FOLIUM_OK:
                st.markdown("### 🗺 Map")
                m = folium.Map(location=[lat, lon], zoom_start=12)
                folium.Marker([lat, lon], tooltip=st.session_state.last_city.title()).add_to(m)
                st_folium(m, width=700, height=400)

st.markdown("---")
st.caption("AI Tour Guide — Interactive, Context-Aware, and Offline Ready 🌎")
