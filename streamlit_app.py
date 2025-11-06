# streamlit_app.py
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

# Optional imports (graceful fallback if not installed)
try:
    from openai import OpenAI
except Exception:
    OpenAI = None

try:
    import folium
    from streamlit_folium import st_folium
    FOLIUM_OK = True
except Exception:
    FOLIUM_OK = False

load_dotenv()

# -----------------------
# CONFIG
# -----------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY", "")

DATA_DIR = "data"
CITIES_DIR = os.path.join(DATA_DIR, "cities")  # saved offline city folders
os.makedirs(CITIES_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

st.set_page_config(page_title="AI Tour Guide", layout="wide")
st.title("🌍 AI Tour Guide — Interactive & Offline Ready")

# -----------------------
# OFFLINE DATA (Karnataka samples)
# -----------------------
OFFLINE_CITIES = {
    "bengaluru": {
        "info": "Bengaluru — the tech capital of India, known for pleasant weather, gardens and a lively café scene.",
        "spots": ["Cubbon Park", "Lalbagh Botanical Garden", "Vidhana Soudha", "Church Street"]
    },
    "mysuru": {
        "info": "Mysuru — royal city famous for Mysore Palace, Dasara festival and sandalwood crafts.",
        "spots": ["Mysore Palace", "Chamundi Hills", "Brindavan Gardens"]
    },
    "mangaluru": {
        "info": "Mangaluru — coastal city known for beaches, temples and seafood.",
        "spots": ["Panambur Beach", "Kadri Manjunatha Temple", "St. Aloysius Chapel"]
    },
    "udupi": {
        "info": "Udupi — temple town, famous for Krishna Matha and coastal cuisine.",
        "spots": ["Sri Krishna Matha", "Malpe Beach", "St. Mary's Island"]
    },
    "coorg": {
        "info": "Coorg (Kodagu) — hill station famous for coffee plantations, waterfalls and misty hills.",
        "spots": ["Abbey Falls", "Dubare Elephant Camp", "Raja's Seat"]
    },
    "chikmagalur": {
        "info": "Chikmagalur — coffee country with scenic treks and waterfalls.",
        "spots": ["Mullayanagiri", "Hebbe Falls", "Baba Budangiri"]
    },
    "hampi": {
        "info": "Hampi — UNESCO World Heritage site with spectacular Vijayanagara ruins.",
        "spots": ["Virupaksha Temple", "Vittala Temple", "Matanga Hill"]
    },
    "gokarna": {
        "info": "Gokarna — serene beaches and spiritual atmosphere, popular with plodders and pilgrims.",
        "spots": ["Om Beach", "Kudle Beach", "Mahabaleshwar Temple"]
    }
}

# -----------------------
# UTILITIES
# -----------------------
def is_online(timeout=2.0):
    try:
        requests.get("https://www.google.com", timeout=timeout)
        return True
    except:
        return False

def safe_key(s: str) -> str:
    return "".join(c for c in s.lower().strip().replace(" ", "") if (c.isalnum() or c in "-"))

def load_context():
    p = os.path.join(DATA_DIR, "context.json")
    if os.path.exists(p):
        try:
            return json.load(open(p, "r", encoding="utf-8"))
        except:
            return {}
    return {}

def save_context(ctx: dict):
    p = os.path.join(DATA_DIR, "context.json")
    json.dump(ctx, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

def detect_city(text: str):
    if not text:
        return None
    s = text.lower()
    # Check known offline cities first
    for c in OFFLINE_CITIES.keys():
        if c in s:
            return c
    # Look for 'in <city>' or 'at <city>'
    m = re.search(r"\b(?:in|at|around)\s+([a-z\s]+)", s)
    if m:
        return m.group(1).strip()
    # No detection
    return None

def offline_info(city: str):
    key = city.lower()
    if key in OFFLINE_CITIES:
        d = OFFLINE_CITIES[key]
        spots_text = "\n".join(f"- {p}" for p in d["spots"])
        return f"{city.title()}** — {d['info']}\n\n*Must visit:*\n{spots_text}"
    return None

def geocode_city(city: str):
    try:
        r = requests.get("https://nominatim.openstreetmap.org/search",
                         params={"q": city, "format":"json", "limit":1},
                         headers={"User-Agent":"ai-tour-guide"}, timeout=8)
        r.raise_for_status()
        data = r.json()
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except:
        return None, None
    return None, None

def fetch_unsplash_urls(city: str, n: int = 3):
    if not UNSPLASH_ACCESS_KEY:
        return []
    try:
        r = requests.get("https://api.unsplash.com/search/photos",
                         params={"query": city, "per_page": n, "client_id": UNSPLASH_ACCESS_KEY}, timeout=8)
        r.raise_for_status()
        results = r.json().get("results", [])[:n]
        return [it["urls"]["regular"] for it in results if "urls" in it]
    except:
        return []

def download_image(url: str, dest: str) -> bool:
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        img = Image.open(BytesIO(r.content)).convert("RGB")
        img.save(dest, format="JPEG", quality=85)
        return True
    except:
        return False

def make_placeholder_map_image(city: str, lat=None, lon=None, dest_path=None, w=900, h=480):
    img = Image.new("RGB", (w, h), (245,245,245))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 22)
    except:
        font = None
    title = f"{city.title()}"
    coord = f"{lat:.5f}, {lon:.5f}" if (lat and lon) else ""
    y = 20
    draw.text((20, y), title, fill=(30,30,30), font=font)
    y += 40
    if coord:
        draw.text((20, y), coord, fill=(80,80,80), font=font)
    # grid
    for x in range(10, w-10, 60):
        draw.line(((x, 120), (x, h-20)), fill=(230,230,230))
    for y in range(120, h-20, 60):
        draw.line(((10, y), (w-10, y)), fill=(230,230,230))
    if dest_path:
        try:
            img.save(dest_path)
        except:
            pass
    return img

def gpt_reply(city: str, user_text: str, model: str = "gpt-3.5-turbo"):
    if not OPENAI_API_KEY or OpenAI is None:
        return None
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        prompt = (
            f"You are a warm, dynamic and professional tour guide. The user said: '{user_text}'. "
            f"Provide 3 concise, specific recommendations about {city}. End with one follow-up question. Use a friendly tone and emojis."
        )
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role":"user", "content": prompt}],
            max_tokens=400,
            temperature=0.8
        )
        # try both response shapes
        try:
            return resp.choices[0].message.content.strip()
        except:
            try:
                return resp.choices[0].text.strip()
            except:
                return str(resp)
    except:
        return None

def speak(text: str, lang: str = "en"):
    if not text:
        return
    try:
        tts = gTTS(text=text, lang=lang)
        tmp = os.path.join(DATA_DIR, f"tts_{int(time.time())}.mp3")
        tts.save(tmp)
        st.audio(open(tmp, "rb").read())
    except:
        # ignore gTTS failures
        pass

# -----------------------
# PERSISTENT CONTEXT
# -----------------------
context = load_context()
if "chat" not in context:
    context["chat"] = []
if "last_city" not in context:
    context["last_city"] = None

# -----------------------
# UI - Sidebar controls
# -----------------------
online = is_online()
status_text = "🟢 Online Mode" if online else "🔴 Offline Mode"
st.sidebar.markdown(f"*Status:* {status_text}")
st.sidebar.markdown("Offline: built-in Karnataka cities available. Use the 'Download for offline' tool to save more cities.")

voice_lang = st.sidebar.selectbox("TTS language", ["en", "hi", "kn"], index=0)

# Download city for offline use
st.sidebar.markdown("---")
dl_city = st.sidebar.text_input("City to download for offline (exact name)", value="")
if st.sidebar.button("Download for offline"):
    if not dl_city.strip():
        st.sidebar.error("Enter a city name to download.")
    else:
        key = safe_key(dl_city)
        folder = os.path.join(CITIES_DIR, key)
        os.makedirs(folder, exist_ok=True)
        # meta.json with basic info (prefer built-in offline data)
        built_info = offline_info(dl_city)
        meta = {
            "city": dl_city,
            "info": built_info or f"{dl_city.title()} — basic saved summary.",
            "saved_at": time.time()
        }
        json.dump(meta, open(os.path.join(folder, "meta.json"), "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        saved_imgs = 0
        if online:
            urls = fetch_unsplash_urls(dl_city, n=4)
            for i, u in enumerate(urls, start=1):
                dest = os.path.join(folder, f"img_{i}.jpg")
                if download_image(u, dest):
                    saved_imgs += 1
        # map placeholder (use geocode when online)
        lat, lon = (None, None)
        if online:
            lat, lon = geocode_city(dl_city)
        map_path = os.path.join(folder, "map.png")
        make_placeholder_map_image(dl_city, lat or 0.0, lon or 0.0, dest_path=map_path)
        st.sidebar.success(f"Saved offline: {dl_city} — images: {saved_imgs} — folder: {folder}")

# -----------------------
# Speech capture widget (populate query param 'q')
# -----------------------
st.components.v1.html("""
<div style="margin-bottom:8px;">
  <button id="micbtn" style="padding:6px;">🎤 Speak</button>
  <script>
  const b=document.getElementById('micbtn');
  b.onclick=()=>{
    const R = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!R) { alert('Speech recognition not supported in this browser.'); return; }
    const r = new R();
    r.lang = 'en-IN';
    r.onresult = (ev) => {
      const text = ev.results[0][0].transcript;
      const url = new URL(window.location);
      url.searchParams.set('q', text);
      window.location = url.toString();
    };
    r.start();
  };
  </script>
</div>
""", height=80)

# -----------------------
# Read speech query from URL (but do not prefill chat_input with value=)
# -----------------------
params = st.query_params
speech_q = params.get("q", [""])[0] if "q" in params else ""

# -----------------------
# Render existing chat
# -----------------------
for msg in context.get("chat", []):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# -----------------------
# Collect user input (st.chat_input WITHOUT value= to avoid TypeError)
# -----------------------
user_input = st.chat_input("Ask anything about a place (or say hi)...")

# If chat_input returns empty but we have speech text, use it once
if not user_input and speech_q:
    user_input = speech_q
    # clear query params so speech is used once
    try:
        st.experimental_set_query_params()
    except:
        pass

# -----------------------
# Handle user message
# -----------------------
if user_input:
    # append user message to context and persist
    context.setdefault("chat", []).append({"role": "user", "content": user_input})
    save_context(context)

    lower = user_input.lower().strip()
    greetings = ["hi", "hello", "hey", "namaste", "good morning", "good evening"]

    # Determine city: explicit mention or last remembered
    city_detected = detect_city(user_input)
    current_city = city_detected or context.get("last_city")

    assistant_text = ""

    # 1) Greetings / small talk
    if any(w == lower or lower.startswith(w + " ") for w in greetings) and len(lower.split()) <= 3:
        assistant_text = (
            "👋 Hey there, traveler! I'm your Dynamic AI Tour Guide. "
            "Tell me a city you want to explore (e.g., Mysuru, Coorg, Udupi), or ask what you'd like to do (food, beaches, temples)."
        )

    # 2) If we have a city (detected now or previous), provide travel info
    elif current_city:
        # normalize store
        current_city_key = current_city.lower()
        context["last_city"] = current_city_key
        save_context(context)

        # Try GPT if online & configured; fall back to saved meta or built-in offline info
        reply = None
        if online and OPENAI_API_KEY and OpenAI is not None:
            reply = gpt_reply(current_city, user_input)

        if reply:
            assistant_text = reply
        else:
            # check saved meta in data/cities/<city>/meta.json
            folder = os.path.join(CITIES_DIR, safe_key(current_city))
            meta_path = os.path.join(folder, "meta.json")
            if os.path.exists(meta_path):
                try:
                    meta = json.load(open(meta_path, "r", encoding="utf-8"))
                    assistant_text = meta.get("info") or offline_info(current_city) or f"{current_city.title()} — basic info."
                except:
                    assistant_text = offline_info(current_city) or f"{current_city.title()} — basic info."
            else:
                assistant_text = offline_info(current_city) or f"{current_city.title()} — basic info."

    # 3) No city and not a greeting — ask for clarification
    else:
        assistant_text = (
            "I couldn't detect a city in your message. Try: 'Tell me about Mysuru' or 'Best beaches in Mangaluru'."
        )

    # Display assistant message and speak
    with st.chat_message("assistant"):
        st.markdown(assistant_text)
        # speak (non-blocking)
        try:
            speak(assistant_text, lang=voice_lang)
        except:
            pass

    # Save assistant message
    context.setdefault("chat", []).append({"role": "assistant", "content": assistant_text})
    save_context(context)

    # Show images & map related to last city (if available)
    last_city = context.get("last_city")
    if last_city:
        # folder containing offline saved data for city
        folder = os.path.join(CITIES_DIR, safe_key(last_city))
        st.markdown("---")
        st.markdown(f"### 📸 Images — {last_city.title()}")

        shown_any = False
        # 1) Priority: saved images in folder
        if os.path.isdir(folder):
            imgs = sorted([os.path.join(folder, fn) for fn in os.listdir(folder)
                           if fn.lower().endswith((".png", ".jpg", ".jpeg")) and "map" not in fn.lower()])
            if imgs:
                cols = st.columns(min(3, len(imgs)))
                for i, p in enumerate(imgs):
                    try:
                        with cols[i % len(cols)]:
                            st.image(Image.open(p), width='stretch')
                        shown_any = True
                    except:
                        continue

        # 2) If none saved and online, fetch Unsplash temporarily
        if not shown_any and online:
            urls = fetch_unsplash_urls(last_city, n=3)
            if urls:
                cols = st.columns(min(3, len(urls)))
                for i, u in enumerate(urls):
                    try:
                        r = requests.get(u, timeout=8)
                        r.raise_for_status()
                        img = Image.open(BytesIO(r.content))
                        with cols[i % len(cols)]:
                            st.image(img, width='stretch')
                        shown_any = True
                    except:
                        continue

        if not shown_any:
            st.info("No images available for this city. Use 'Download for offline' in the sidebar to save images and a placeholder map.")

        # Map area
        st.markdown(f"### 🗺 Map — {last_city.title()}")
        lat, lon = (None, None)
        # prefer live geocode if online
        if online:
            lat, lon = geocode_city(last_city)
        # Prefer interactive folium map if available and online coordinates exist
        if online and FOLIUM_OK and lat and lon:
            try:
                m = folium.Map(location=[lat, lon], zoom_start=12, tiles="CartoDB Positron")
                folium.Marker([lat, lon], tooltip=last_city.title()).add_to(m)
                st_folium(m, width=700, height=420)
            except Exception:
                # fallback to saved map image or placeholder
                map_path = os.path.join(folder, "map.png")
                if os.path.exists(map_path):
                    try:
                        st.image(Image.open(map_path), width='stretch')
                    except:
                        st.info("Saved map exists but couldn't be displayed.")
                else:
                    placeholder = make_placeholder_map_image(last_city, lat or 0.0, lon or 0.0)
                    st.image(placeholder, width='stretch')
        else:
            # offline or folium missing -> show saved map if exists, else placeholder
            map_path = os.path.join(folder, "map.png")
            if os.path.exists(map_path):
                try:
                    st.image(Image.open(map_path), width='stretch')
                except:
                    st.info("Saved map exists but couldn't be displayed.")
            else:
                placeholder = make_placeholder_map_image(last_city, lat or 0.0, lon or 0.0)
                st.image(placeholder, width='stretch')

# -----------------------
# Footer
# -----------------------
st.markdown("---")
st.caption("AI Tour Guide — Interactive, context-aware, and offline-ready. Use the sidebar to download cities for offline use.")
