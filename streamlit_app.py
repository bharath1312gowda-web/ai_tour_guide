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

# Optional imports (graceful fallback)
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
# CONFIG / PATHS
# -----------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY", "")
DATA_DIR = "data"
CITIES_DIR = os.path.join(DATA_DIR, "cities")
os.makedirs(CITIES_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# Streamlit page
st.set_page_config(page_title="AI Tour Guide", layout="wide")
st.title("🌍 AI Tour Guide — Interactive, Online + Offline Ready")

# -----------------------
# OFFLINE SAMPLE DATABASE
# -----------------------
OFFLINE_CITIES = {
    "bengaluru": {
        "info": "Bengaluru — the tech capital of India, known for gardens, cafés, and a lively startup scene.",
        "spots": ["Cubbon Park", "Lalbagh Botanical Garden", "Vidhana Soudha", "Church Street"]
    },
    "mysuru": {
        "info": "Mysuru — royal city famous for the Mysore Palace, Dasara festival, and sandalwood crafts.",
        "spots": ["Mysore Palace", "Chamundi Hills", "Brindavan Gardens"]
    },
    "mangaluru": {
        "info": "Mangaluru — coastal city known for beaches, temples and seafood.",
        "spots": ["Panambur Beach", "Kadri Manjunatha Temple", "St. Aloysius Chapel"]
    },
    "udupi": {
        "info": "Udupi — temple town famous for Krishna Matha and coastal cuisine.",
        "spots": ["Sri Krishna Matha", "Malpe Beach", "St. Mary's Island"]
    },
    "coorg": {
        "info": "Coorg (Kodagu) — hill station known for coffee estates and waterfalls.",
        "spots": ["Abbey Falls", "Dubare Elephant Camp", "Raja's Seat"]
    },
    "chikmagalur": {
        "info": "Chikmagalur — coffee country and trekking destination.",
        "spots": ["Mullayanagiri", "Hebbe Falls", "Baba Budangiri"]
    },
    "hampi": {
        "info": "Hampi — UNESCO World Heritage site with ruins of the Vijayanagara Empire.",
        "spots": ["Virupaksha Temple", "Vittala Temple", "Matanga Hill"]
    },
    "gokarna": {
        "info": "Gokarna — relaxed beaches and spiritual temples.",
        "spots": ["Om Beach", "Kudle Beach", "Mahabaleshwar Temple"]
    }
}

# -----------------------
# UTILITIES
# -----------------------
def safe_key(s: str) -> str:
    """Normalize a city name into a safe folder key."""
    return "".join(c for c in s.lower().strip().replace(" ", "") if (c.isalnum() or c in "-"))

def is_online(timeout: float = 2.0) -> bool:
    """Quick network check."""
    try:
        requests.get("https://www.google.com", timeout=timeout)
        return True
    except Exception:
        return False

def make_placeholder_map_image(city: str, lat=None, lon=None, dest_path: str = None, w=900, h=480) -> Image.Image:
    """Create a simple placeholder 'map' image and optionally save it."""
    img = Image.new("RGB", (w, h), (245, 245, 245))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 22)
    except Exception:
        font = None
    draw.text((20, 20), f"{city.title()}", fill=(30, 30, 30), font=font)
    if lat is not None and lon is not None:
        draw.text((20, 60), f"Coordinates: {lat:.5f}, {lon:.5f}", fill=(80, 80, 80), font=font)
    # grid background to resemble a map
    for x in range(20, w - 20, 60):
        draw.line(((x, 120), (x, h - 20)), fill=(230, 230, 230))
    for y in range(120, h - 20, 60):
        draw.line(((20, y), (w - 20, y)), fill=(230, 230, 230))
    if dest_path:
        try:
            img.save(dest_path)
        except Exception:
            pass
    return img

def geocode_city(city: str):
    """Return (lat, lon) using Nominatim. Returns (None, None) on failure."""
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": city, "format": "json", "limit": 1},
            headers={"User-Agent": "ai-tour-guide"},
            timeout=8,
        )
        r.raise_for_status()
        data = r.json()
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception:
        return None, None
    return None, None

def fetch_unsplash_urls(city: str, n: int = 3):
    """Return list of Unsplash image URLs (requires UNSPLASH_ACCESS_KEY)."""
    if not UNSPLASH_ACCESS_KEY:
        return []
    try:
        r = requests.get(
            "https://api.unsplash.com/search/photos",
            params={"query": city, "per_page": n, "client_id": UNSPLASH_ACCESS_KEY},
            timeout=8,
        )
        r.raise_for_status()
        results = r.json().get("results", [])
        return [it["urls"]["regular"] for it in results[:n] if "urls" in it]
    except Exception:
        return []

def download_image(url: str, dest_path: str) -> bool:
    """Download an image by URL to dest_path. Return True on success."""
    try:
        r = requests.get(url, timeout=12)
        r.raise_for_status()
        img = Image.open(BytesIO(r.content)).convert("RGB")
        img.save(dest_path, format="JPEG", quality=85)
        return True
    except Exception:
        return False

def gpt_reply(city: str, user_text: str, model: str = "gpt-3.5-turbo"):
    """Call OpenAI ChatCompletion (if available). Returns string or None."""
    if not OPENAI_API_KEY or OpenAI is None:
        return None
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        prompt = (
            f"You are a knowledgeable local tour guide. The user asked: '{user_text}'. "
            f"Provide 3 concise, actionable recommendations for {city}. Include food, attractions, and a hidden gem. End with a short follow-up question."
        )
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
            temperature=0.8,
        )
        try:
            return resp.choices[0].message.content.strip()
        except Exception:
            try:
                return resp.choices[0].text.strip()
            except Exception:
                return str(resp)
    except Exception:
        return None

def speak(text: str, lang: str = "en"):
    """Use gTTS to synthesize speech and play audio (best-effort)."""
    if not text:
        return
    try:
        tts = gTTS(text=text, lang=lang)
        tmp = os.path.join(DATA_DIR, f"tts_{int(time.time())}.mp3")
        tts.save(tmp)
        st.audio(open(tmp, "rb").read())
    except Exception:
        # Ignore TTS errors silently to avoid breaking UI
        pass

def load_context():
    ctx_path = os.path.join(DATA_DIR, "context.json")
    if os.path.exists(ctx_path):
        try:
            return json.load(open(ctx_path, "r", encoding="utf-8"))
        except Exception:
            return {}
    return {}

def save_context(ctx: dict):
    ctx_path = os.path.join(DATA_DIR, "context.json")
    json.dump(ctx, open(ctx_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

# -----------------------
# DIAGNOSTIC SIDEBAR: absolute paths & saved folders
# -----------------------
st.sidebar.markdown("### Debug & Offline Storage")
abs_data_dir = os.path.abspath(DATA_DIR)
st.sidebar.write("App cwd:", os.getcwd())
st.sidebar.write("data absolute path:", abs_data_dir)
cities_root = os.path.join(abs_data_dir, "cities")
st.sidebar.write("cities root:", cities_root)
if os.path.exists(cities_root):
    saved = sorted([d for d in os.listdir(cities_root) if os.path.isdir(os.path.join(cities_root, d))])
    if not saved:
        st.sidebar.info("No saved city folders (use 'Download for offline').")
    else:
        st.sidebar.markdown("Saved city folders:")
        for f in saved:
            p = os.path.join(cities_root, f)
            try:
                files = sorted(os.listdir(p))
                st.sidebar.write(f"- {f} — {', '.join(files) if files else '(empty)'}")
            except Exception as e:
                st.sidebar.write(f"- {f} — read error: {e}")
else:
    st.sidebar.warning("No data/cities folder exists yet. Use the Download tool to create one.")

# -----------------------
# SIDEBAR: controls (download / list)
# -----------------------
online = is_online()
st.sidebar.markdown("---")
st.sidebar.markdown(f"*Network status:* {'🟢 Online' if online else '🔴 Offline'}")
voice_lang = st.sidebar.selectbox("TTS language", ["en", "hi", "kn"], index=0)

st.sidebar.markdown("---")
dl_city = st.sidebar.text_input("Download city for offline (exact name):", value="")
if st.sidebar.button("Download for offline"):
    if not dl_city.strip():
        st.sidebar.error("Enter a city name to download.")
    else:
        k = safe_key(dl_city)
        folder = os.path.join(CITIES_DIR, k)
        os.makedirs(folder, exist_ok=True)
        # meta.json
        meta = {
            "city": dl_city,
            "info": OFFLINE_CITIES.get(k, {}).get("info", f"{dl_city.title()} — saved offline."),
            "spots": OFFLINE_CITIES.get(k, {}).get("spots", []),
            "saved_at": time.time()
        }
        try:
            json.dump(meta, open(os.path.join(folder, "meta.json"), "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        except Exception:
            pass
        saved_images = 0
        if online and UNSPLASH_ACCESS_KEY:
            urls = fetch_unsplash_urls(dl_city, n=4)
            for i, url in enumerate(urls, start=1):
                dest = os.path.join(folder, f"img_{i}.jpg")
                if download_image(url, dest):
                    saved_images += 1
        # geocode + placeholder map
        lat, lon = (None, None)
        if online:
            lat, lon = geocode_city(dl_city)
        map_path = os.path.join(folder, "map.png")
        make_placeholder_map_image(dl_city, lat or 0.0, lon or 0.0, dest_path=map_path)
        st.sidebar.success(f"Saved {dl_city} offline — images: {saved_images} — folder: {folder}")

st.sidebar.markdown("---")
st.sidebar.markdown("### Saved offline cities")
folders = sorted([d for d in os.listdir(CITIES_DIR) if os.path.isdir(os.path.join(CITIES_DIR, d))]) if os.path.exists(CITIES_DIR) else []
if not folders:
    st.sidebar.info("No saved cities. Use Download for offline.")
else:
    for f in folders:
        st.sidebar.write("•", f)

# -----------------------
# SPEECH BUTTON (populates query param 'q')
# -----------------------
st.components.v1.html(
    """
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
""",
    height=90,
)

# -----------------------
# PERSISTENT CONTEXT
# -----------------------
context = load_context()
if "chat" not in context:
    context["chat"] = []
if "last_city" not in context:
    context["last_city"] = None

# -----------------------
# QUERY PARAMS (speech)
# -----------------------
params = st.query_params
speech_q = params.get("q", [""])[0] if "q" in params else ""

# -----------------------
# RENDER EXISTING CHAT
# -----------------------
for msg in context.get("chat", []):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# -----------------------
# CHAT INPUT (avoid value= to support older Streamlit)
# -----------------------
user_input = st.chat_input("Ask anything about a place (e.g., 'Tell me about Mysuru')...")

# If chat_input empty but we have a speech query, use it once and clear query params
if not user_input and speech_q:
    user_input = speech_q
    try:
        st.experimental_set_query_params()
    except Exception:
        pass

# -----------------------
# ROBUST SAVED FOLDER LOOKUP
# -----------------------
def find_saved_city_folder(query: str):
    """Try exact key, substring match, and meta.json city field to locate saved folder."""
    if not query:
        return None
    key = safe_key(query)
    root = os.path.join(DATA_DIR, "cities")
    if not os.path.isdir(root):
        return None
    # exact key
    candidate = os.path.join(root, key)
    if os.path.isdir(candidate):
        return candidate
    # substring in folder names
    for fn in os.listdir(root):
        if key in fn:
            p = os.path.join(root, fn)
            if os.path.isdir(p):
                return p
    # meta.json city field match
    for fn in os.listdir(root):
        p = os.path.join(root, fn)
        meta = os.path.join(p, "meta.json")
        if os.path.exists(meta):
            try:
                m = json.load(open(meta, "r", encoding="utf-8"))
                meta_city = m.get("city", "")
                if key in safe_key(meta_city):
                    return p
            except Exception:
                continue
    return None

# -----------------------
# HANDLE USER MESSAGE
# -----------------------
if user_input:
    # append user message
    context.setdefault("chat", []).append({"role": "user", "content": user_input})
    save_context(context)
    with st.chat_message("user"):
        st.markdown(user_input)

    # basic detection
    lower = user_input.lower().strip()
    greetings = ["hi", "hello", "hey", "namaste", "good morning", "good evening"]
    detected_city = None
    # check known offline city words first
    for k in list(OFFLINE_CITIES.keys()):
        if k in lower:
            detected_city = k
            break
    # try explicit pattern "in <city>"
    if not detected_city:
        m = re.search(r"\b(?:in|at|around)\s+([a-z\s]+)", lower)
        if m:
            detected_city = m.group(1).strip()

    # if still not detected, try to find saved folder by substring match
    if not detected_city:
        # attempt to find any saved folder name within the user input
        for f in folders:
            if f in lower:
                detected_city = f
                break

    assistant_text = ""

    # greeting
    if any(lower == g or lower.startswith(g + " ") for g in greetings) and len(lower.split()) <= 3:
        assistant_text = (
            "👋 Hey! I'm your AI Tour Guide. You can ask about a city (e.g., 'Tell me about Mysuru'), "
            "ask for food places, or say 'Download for offline' in the sidebar to save a city."
        )
    else:
        # If we have detected_city or last city in context, use that
        city_for_answer = detected_city or context.get("last_city")
        # If nothing, ask user to clarify
        if not city_for_answer:
            assistant_text = "I couldn't detect a city. Try: 'Tell me about Mysuru' or 'Places to see in Udupi'."
        else:
            # Normalize key
            city_key = safe_key(city_for_answer)
            context["last_city"] = city_key
            save_context(context)
            # Try online GPT if available
            reply = None
            if online and OPENAI_API_KEY and OpenAI is not None:
                reply = gpt_reply(city_for_answer, user_input)
            if reply:
                assistant_text = reply
            else:
                # prefer saved meta.json if exists
                saved_folder = find_saved_city_folder(city_for_answer)
                if saved_folder:
                    meta_path = os.path.join(saved_folder, "meta.json")
                    if os.path.exists(meta_path):
                        try:
                            meta = json.load(open(meta_path, "r", encoding="utf-8"))
                            assistant_text = meta.get("info") or meta.get("city") or f"{city_for_answer.title()} — info saved offline."
                        except Exception:
                            assistant_text = f"{city_for_answer.title()} — saved offline (meta unreadable)."
                    else:
                        # fallback to built-in offline DB if present
                        assistant_text = OFFLINE_CITIES.get(city_key, {}).get("info", f"{city_for_answer.title()} — basic offline info.")
                else:
                    # no saved folder — fallback to built-in DB
                    assistant_text = OFFLINE_CITIES.get(city_key, {}).get("info", f"{city_for_answer.title()} — no online AI available and not saved offline.")

    # display assistant message
    with st.chat_message("assistant"):
        st.markdown(assistant_text)
        # speak (best-effort)
        try:
            speak(assistant_text, lang=voice_lang)
        except Exception:
            pass

    # append assistant to context
    context.setdefault("chat", []).append({"role": "assistant", "content": assistant_text})
    save_context(context)

    # After responding, try to show images and map for last_city
    last_city = context.get("last_city")
    if last_city:
        st.markdown("---")
        st.markdown(f"### 📸 Images — {last_city.title()}")
        saved_folder = find_saved_city_folder(last_city)
        shown_any = False
        # show saved images if folder exists
        if saved_folder:
            image_files = sorted([fn for fn in os.listdir(saved_folder) if fn.lower().endswith((".jpg", ".jpeg", ".png")) and fn.lower() != "map.png"])
            if image_files:
                cols = st.columns(min(3, len(image_files)))
                for i, fn in enumerate(image_files):
                    path = os.path.join(saved_folder, fn)
                    try:
                        with cols[i % len(cols)]:
                            st.image(Image.open(path), width='stretch')
                        shown_any = True
                    except Exception:
                        continue
        # if none saved and online, fetch Unsplash temporarily
        if not shown_any and online:
            urls = fetch_unsplash_urls(last_city, n=3)
            if urls:
                cols = st.columns(len(urls))
                for i, url in enumerate(urls):
                    try:
                        r = requests.get(url, timeout=8)
                        r.raise_for_status()
                        img = Image.open(BytesIO(r.content))
                        with cols[i % len(cols)]:
                            st.image(img, width='stretch')
                        shown_any = True
                    except Exception:
                        continue
        if not shown_any:
            st.info("No images available for this city (saved offline or Unsplash). Use 'Download for offline' in the sidebar to save images and a placeholder map.")

        # Map display (prefer folium when online)
        st.markdown(f"### 🗺 Map — {last_city.title()}")
        lat, lon = (None, None)
        if online:
            lat, lon = geocode_city(last_city)
        # If online and folium available and coords present -> interactive map
        if online and FOLIUM_OK and lat and lon:
            try:
                m = folium.Map(location=[lat, lon], zoom_start=12, tiles="CartoDB Positron")
                folium.Marker([lat, lon], tooltip=last_city.title()).add_to(m)
                st_folium(m, width=700, height=420)
            except Exception:
                # fallback to saved map or placeholder
                map_path = os.path.join(saved_folder, "map.png") if saved_folder else None
                if map_path and os.path.exists(map_path):
                    st.image(map_path, width='stretch')
                else:
                    placeholder = make_placeholder_map_image(last_city, lat or 0.0, lon or 0.0)
                    st.image(placeholder, width='stretch')
        else:
            # offline or folium not available -> show saved map if exists else placeholder
            map_path = os.path.join(saved_folder, "map.png") if saved_folder else None
            if map_path and os.path.exists(map_path):
                try:
                    st.image(Image.open(map_path), width='stretch')
                except Exception:
                    st.info("Saved map exists but could not be displayed.")
            else:
                placeholder = make_placeholder_map_image(last_city, lat or 0.0, lon or 0.0)
                st.image(placeholder, width='stretch')

# -----------------------
# FOOTER
# -----------------------
st.markdown("---")
st.caption("AI Tour Guide — Interactive, dynamic, and offline-ready. Use the sidebar to download cities for offline access.")
