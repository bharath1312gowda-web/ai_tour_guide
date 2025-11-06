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

# optional OpenAI import
try:
    from openai import OpenAI
except Exception:
    OpenAI = None

# optional folium
try:
    import folium
    from streamlit_folium import st_folium
    FOLIUM_OK = True
except Exception:
    FOLIUM_OK = False

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY", "")

# dirs
DATA_DIR = "data"
OSM_CACHE_DIR = os.path.join(DATA_DIR, "cities")
os.makedirs(OSM_CACHE_DIR, exist_ok=True)

# basic offline DB (Karnataka) — used if no internet or no GPT
OFFLINE_CITIES = {
    "bengaluru": {"info":"Bengaluru — the tech capital of India, known for parks, cafes and a lively food scene.",
                  "spots":["Cubbon Park","Lalbagh Botanical Garden","Vidhana Soudha","Church Street"]},
    "mysuru": {"info":"Mysuru — royal city famous for Mysore Palace, Dasara and sandalwood.",
               "spots":["Mysore Palace","Chamundi Hills","Brindavan Gardens"]},
    "mangaluru": {"info":"Mangaluru — coastal city known for beaches, temples and seafood.",
                  "spots":["Panambur Beach","Kadri Temple","St. Aloysius Chapel"]},
    "udupi": {"info":"Udupi — temple town famous for Krishna Matha and coastal food.",
              "spots":["Sri Krishna Matha","Malpe Beach","St. Mary’s Island"]},
    "coorg": {"info":"Coorg (Kodagu) — hill station with coffee estates and waterfalls.",
              "spots":["Abbey Falls","Dubare Elephant Camp","Raja's Seat"]},
    "chikmagalur": {"info":"Chikmagalur — coffee country and trekking paradise.",
                    "spots":["Mullayanagiri","Hebbe Falls","Baba Budangiri"]},
    "hampi": {"info":"Hampi — UNESCO site with Vijayanagara ruins and stone temples.",
              "spots":["Virupaksha Temple","Vittala Temple","Matanga Hill"]},
    "gokarna": {"info":"Gokarna — relaxed coastal town with spiritual temples and beaches.",
                "spots":["Om Beach","Kudle Beach","Mahabaleshwar Temple"]}
}

# helpers -------------------------------------------------------------------
def is_online(timeout=2.0):
    try:
        requests.get("https://www.google.com", timeout=timeout)
        return True
    except:
        return False

def safe_key(s):
    return "".join(c for c in s.lower().strip().replace(" ", "") if (c.isalnum() or c in "-"))

def load_context():
    p = os.path.join(DATA_DIR, "context.json")
    if os.path.exists(p):
        try:
            return json.load(open(p, "r", encoding="utf-8"))
        except:
            return {}
    return {}

def save_context(ctx):
    p = os.path.join(DATA_DIR, "context.json")
    json.dump(ctx, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

context = load_context()
if "chat" not in context: context["chat"] = []
if "last_city" not in context: context["last_city"] = None

def detect_city(text):
    if not text: return None
    text_l = text.lower()
    # check known offline cities
    for c in OFFLINE_CITIES.keys():
        if c in text_l:
            return c
    # check "in <city>" pattern
    m = re.search(r"\b(?:in|at|around)\s+([a-z\s]+)", text_l)
    if m:
        candidate = m.group(1).strip()
        # return candidate (may not be in OFFLINE_CITIES)
        return candidate
    return None

def offline_info(city):
    key = city.lower()
    if key in OFFLINE_CITIES:
        d = OFFLINE_CITIES[key]
        spots_text = "\n".join(f"- {s}" for s in d["spots"])
        return f"{city.title()}** — {d['info']}\n\n*Must visit:*\n{spots_text}"
    else:
        return None

def fetch_unsplash_urls(city, n=3):
    if not UNSPLASH_ACCESS_KEY:
        return []
    try:
        r = requests.get("https://api.unsplash.com/search/photos",
                         params={"query": city, "per_page": n, "client_id": UNSPLASH_ACCESS_KEY}, timeout=8)
        r.raise_for_status()
        data = r.json().get("results", [])[:n]
        return [it["urls"]["regular"] for it in data if "urls" in it]
    except:
        return []

def download_image(url, dest_path):
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        img = Image.open(BytesIO(r.content)).convert("RGB")
        img.save(dest_path, format="JPEG", quality=85)
        return True
    except:
        return False

def make_placeholder_map_image(city, lat=None, lon=None, dest_path=None, w=800, h=480):
    img = Image.new("RGB", (w, h), (245,245,245))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 20)
    except:
        font = None
    title = f"{city.title()}"
    coord = f"{lat:.5f}, {lon:.5f}" if (lat and lon) else ""
    draw.rectangle(((10,10),(w-10,60)), outline=(200,200,200))
    draw.text((20,20), title, fill=(30,30,30), font=font)
    if coord:
        draw.text((20,80), coord, fill=(80,80,80), font=font)
    # simple grid to look like map
    for x in range(0,w,50):
        draw.line(((x,120),(x,h-20)), fill=(230,230,230))
    for y in range(120,h-20,50):
        draw.line(((10,y),(w-10,y)), fill=(230,230,230))
    if dest_path:
        img.save(dest_path)
    return img

def geocode_city(city):
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

def gpt_reply(city, user_text, model="gpt-3.5-turbo"):
    if not OPENAI_API_KEY or OpenAI is None:
        return None
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        prompt = f"You are a dynamic friendly travel guide. The user asked: '{user_text}'. Provide 3 concise suggestions about {city}. Ask a short follow-up question."
        resp = client.chat.completions.create(model=model, messages=[{"role":"user","content":prompt}], max_tokens=400, temperature=0.8)
        try:
            return resp.choices[0].message.content.strip()
        except:
            return str(resp)
    except Exception:
        return None

def speak(text, lang="en"):
    if not text: return
    try:
        tts = gTTS(text=text, lang=lang)
        tmp = os.path.join(DATA_DIR, f"tts_{int(time.time())}.mp3")
        tts.save(tmp)
        st.audio(open(tmp,"rb").read())
    except Exception:
        # ignore TTS failures
        pass

# UI -----------------------------------------------------------------------
st.set_page_config(page_title="AI Tour Guide — Interactive", layout="wide")
st.title("🌍 AI Tour Guide — Interactive & Offline Ready")

online = is_online()
status = "🟢 Online" if online else "🔴 Offline"
st.sidebar.markdown(f"*Status:* {status}")
st.sidebar.markdown("Offline: preloaded Karnataka cities. Use Download for offline to save more cities.")
voice_lang = st.sidebar.selectbox("Voice language (gTTS)", ["en","hi","kn"], index=0)

# Download button to store city locally
st.sidebar.markdown("---")
st.sidebar.markdown("*Offline management*")
dl_city = st.sidebar.text_input("City to download for offline (exact name)", value="")
if st.sidebar.button("Download for offline"):
    if not dl_city.strip():
        st.sidebar.error("Enter a city name to download.")
    else:
        key = safe_key(dl_city)
        folder = os.path.join(OSM_CACHE_DIR, key)
        os.makedirs(folder, exist_ok=True)
        # save info JSON
        info_text = offline_info(dl_city) or f"{dl_city.title()} — basic offline summary."
        meta = {"city": dl_city, "info": info_text, "saved_at": time.time()}
        json.dump(meta, open(os.path.join(folder, "meta.json"), "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        # fetch images from Unsplash (if online)
        saved_images = []
        if online:
            urls = fetch_unsplash_urls(dl_city, n=4)
            for i, u in enumerate(urls, start=1):
                dest = os.path.join(folder, f"img_{i}.jpg")
                if download_image(u, dest):
                    saved_images.append(dest)
        # create placeholder map (use geocode if available)
        lat, lon = (None, None)
        if online:
            lat, lon = geocode_city(dl_city)
        map_path = os.path.join(folder, "map.png")
        make_placeholder_map_image(dl_city, lat or 0.0, lon or 0.0, dest_path=map_path)
        st.sidebar.success(f"Saved offline: {dl_city} ({len(saved_images)} images). Folder: {folder}")

# speech capture integration (populates query param 'q')
st.components.v1.html("""
<div style="margin-bottom:8px;">
  <button id="micbtn">🎤 Speak</button>
  <script>
  const b=document.getElementById('micbtn');
  b.onclick=()=>{
    const r=new (window.SpeechRecognition || window.webkitSpeechRecognition)();
    r.lang='en-IN';
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

# read query from URL if any
params = st.query_params
speech_q = params.get("q", [""])[0] if "q" in params else ""

# chat UI using Streamlit chat components
if "chat" not in context:
    context["chat"] = []
if "last_city" not in context:
    context["last_city"] = None

user_input = st.chat_input("Ask anything about a place (or say hi)...", value=speech_q)

# render existing chat (persisted)
for msg in context["chat"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# handle user message
if user_input:
    # append user message
    context["chat"].append({"role":"user","content":user_input})
    save_context(context)

    # simple intent handling
    greetings = ["hi","hello","hey","namaste","good morning","good evening"]
    lower = user_input.lower().strip()

    # detect city from message or fallback to last_city
    city = detect_city(user_input)
    if not city and context.get("last_city"):
        city = context["last_city"]

    assistant_text = ""
    # greeting
    if any(w in lower for w in greetings) and len(lower.split()) <= 2:
        assistant_text = "👋 Hey! I'm your AI Tour Guide. Tell me a city to explore (e.g., Mysuru, Coorg, Udupi), or ask what you'd like to do (food, beaches, temples)."
    # if a city known offline or provided
    elif city:
        # normalize
        city_key = city.lower()
        context["last_city"] = city_key
        save_context(context)
        # online: try GPT; else offline info or saved meta
        ai_online_text = None
        if online:
            ai_online_text = gpt_reply(city, user_input)  # may be None
        if ai_online_text:
            assistant_text = ai_online_text
        else:
            # try saved meta in data dir first
            folder = os.path.join(OSM_CACHE_DIR, safe_key(city))
            meta_path = os.path.join(folder, "meta.json")
            if os.path.exists(meta_path):
                try:
                    meta = json.load(open(meta_path, "r", encoding="utf-8"))
                    assistant_text = meta.get("info") or offline_info(city) or f"{city.title()} — info saved offline."
                except:
                    assistant_text = offline_info(city) or f"{city.title()} — basic info."
            else:
                assistant_text = offline_info(city) or f"{city.title()} — basic info."
    else:
        assistant_text = "I didn't catch a city there. Try: 'Tell me about Mysuru' or 'Places to see in Udupi'."

    # show assistant answer
    with st.chat_message("assistant"):
        st.markdown(assistant_text)
        speak(assistant_text, lang=voice_lang)
        context["chat"].append({"role":"assistant","content":assistant_text})
        save_context(context)

    # show images and map for last city if available
    if context.get("last_city"):
        city = context["last_city"]
        folder = os.path.join(OSM_CACHE_DIR, safe_key(city))
        st.markdown("---")
        st.markdown(f"### 📸 Images — {city.title()}")

        images_shown = False
        # priority: saved images in folder
        if os.path.isdir(folder):
            imgs = sorted([os.path.join(folder,f) for f in os.listdir(folder) if f.lower().endswith((".png",".jpg",".jpeg")) and "map" not in f])
            if imgs:
                cols = st.columns(min(3, len(imgs)))
                for i, p in enumerate(imgs):
                    try:
                        img = Image.open(p)
                        with cols[i%len(cols)]:
                            st.image(img, width='stretch')
                        images_shown = True
                    except:
                        continue

        # if none saved and online -> fetch from Unsplash temporarily
        if not images_shown and online:
            urls = fetch_unsplash_urls(city, n=3)
            if urls:
                cols = st.columns(len(urls))
                for i, u in enumerate(urls):
                    try:
                        r = requests.get(u, timeout=8)
                        r.raise_for_status()
                        img = Image.open(BytesIO(r.content))
                        with cols[i%len(cols)]:
                            st.image(img, width='stretch')
                        images_shown = True
                    except:
                        continue

        if not images_shown:
            st.info("No images available for this city (saved offline or Unsplash). Use 'Download for offline' in the sidebar to save images and a map.")

        # Map area
        st.markdown(f"### 🗺 Map — {city.title()}")
        lat, lon = geocode_city(city) if online else (None, None)
        # prefer folium when online and installed
        if online and FOLIUM_OK and lat and lon:
            try:
                m = folium.Map(location=[lat, lon], zoom_start=12, tiles="CartoDB Positron")
                folium.Marker([lat, lon], tooltip=city.title()).add_to(m)
                st_folium(m, width=700, height=420)
            except Exception:
                # fall back to saved map or placeholder
                map_path = os.path.join(folder, "map.png")
                if os.path.exists(map_path):
                    st.image(Image.open(map_path), width='stretch')
                else:
                    placeholder = make_placeholder_map_image(city, lat or 0.0, lon or 0.0)
                    st.image(placeholder, width='stretch')
        else:
            # offline or folium not available -> show saved map if exists, else placeholder
            map_path = os.path.join(folder, "map.png")
            if os.path.exists(map_path):
                try:
                    st.image(Image.open(map_path), width='stretch')
                except:
                    st.info("Map image exists but could not be displayed.")
            else:
                # generate placeholder and show it (not saved)
                placeholder = make_placeholder_map_image(city, lat or 0.0, lon or 0.0)
                st.image(placeholder, width='stretch')

# footer
st.markdown("---")
st.caption("AI Tour Guide — interactive, offline-ready. Use the sidebar to download cities for offline use.")
