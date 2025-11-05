import os, json, time, requests, streamlit as st
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
from gtts import gTTS
from openai import OpenAI
try:
    import folium
    from streamlit_folium import st_folium
    FOLIUM_OK = True
except Exception:
    FOLIUM_OK = False

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

def safe_rerun():
    try:
        st.experimental_rerun()
    except Exception:
        try:
            st.experimental_set_query_params(_refresh=int(time.time()))
        except Exception:
            pass
        st.markdown("<meta http-equiv='refresh' content='0'>", unsafe_allow_html=True)

def save_offline_db(db):
    with open(OFFLINE_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)

def load_offline_db():
    if not os.path.exists(OFFLINE_DATA_FILE):
        return {}
    try:
        with open(OFFLINE_DATA_FILE, "r", encoding="utf-8") as f:
            db = json.load(f)
            return db if isinstance(db, dict) else {}
    except Exception:
        return {}

def clean_offline_db(db):
    clean = {}
    for k, v in db.items():
        try:
            if isinstance(v, dict) and isinstance(v.get("city"), str) and isinstance(v.get("categories", {}), dict):
                clean[k] = v
        except Exception:
            continue
    return clean

offline_db = load_offline_db()
offline_db = clean_offline_db(offline_db)
save_offline_db(offline_db)

def is_online(timeout=2.0):
    try:
        requests.get("https://www.google.com", timeout=timeout)
        return True
    except Exception:
        return False

def safe_filename(s):
    return "".join(c for c in s.lower().strip().replace(" ", "") if (c.isalnum() or c in "-"))

def get_openai_client():
    if not OPENAI_API_KEY:
        return None
    try:
        return OpenAI(api_key=OPENAI_API_KEY)
    except Exception:
        return None

def fetch_openai_text(prompt, system=None, model="gpt-3.5-turbo"):
    client = get_openai_client()
    if client is None:
        return None
    try:
        messages = []
        if system:
            messages.append({"role":"system","content":system})
        messages.append({"role":"user","content":prompt})
        resp = client.chat.completions.create(model=model, messages=messages, temperature=0.7, max_tokens=500)
        return resp.choices[0].message.content
    except Exception:
        return None

def translate_via_openai(text, target_lang_code):
    if not OPENAI_API_KEY or target_lang_code == "en":
        return text
    system = f"You are a translator. Translate the following text to {target_lang_code} and return only the translated text."
    out = fetch_openai_text(text, system=system)
    return out or text

def fetch_unsplash_image_urls(query, count=3):
    if not UNSPLASH_ACCESS_KEY:
        return []
    url = "https://api.unsplash.com/search/photos"
    params = {"query": query, "per_page": count, "orientation": "landscape", "client_id": UNSPLASH_ACCESS_KEY}
    try:
        r = requests.get(url, params=params, timeout=8)
        r.raise_for_status()
        data = r.json()
        results = data.get("results", [])[:count]
        return [item["urls"]["regular"] for item in results if "urls" in item]
    except Exception:
        return []

def download_and_save_image(url, dest_path):
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        img = Image.open(BytesIO(r.content)).convert("RGB")
        img.save(dest_path, format="JPEG", quality=85)
        return True
    except Exception:
        return False

def geocode_city(city):
    try:
        r = requests.get("https://nominatim.openstreetmap.org/search", params={"q": city, "format": "json", "limit": 1}, headers={"User-Agent":"ai-tour-guide-app"}, timeout=8)
        r.raise_for_status()
        data = r.json()
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception:
        return None, None
    return None, None

def fetch_tile_image(lat, lon, zoom=12, w=800, h=400):
    try:
        import math
        n = 2 ** zoom
        xtile = int((lon + 180.0) / 360.0 * n)
        lat_rad = math.radians(lat)
        ytile = int((1.0 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi) / 2.0 * n)
        tile_size = 256
        cols = math.ceil(w / tile_size) + 1
        rows = math.ceil(h / tile_size) + 1
        start_x = xtile - cols // 2
        start_y = ytile - rows // 2
        base_url = "https://cartodb-basemaps-a.global.ssl.fastly.net/light_all"
        canvas = Image.new("RGB", (cols * tile_size, rows * tile_size))
        for rx in range(cols):
            for ry in range(rows):
                tx = start_x + rx
                ty = start_y + ry
                url = f"{base_url}/{zoom}/{tx}/{ty}.png"
                try:
                    r = requests.get(url, timeout=6)
                    if r.status_code == 200:
                        img = Image.open(BytesIO(r.content)).convert("RGB")
                        canvas.paste(img, (rx * tile_size, ry * tile_size))
                    else:
                        blank = Image.new("RGB", (tile_size, tile_size), (240, 240, 240))
                        canvas.paste(blank, (rx * tile_size, ry * tile_size))
                except Exception:
                    blank = Image.new("RGB", (tile_size, tile_size), (240, 240, 240))
                    canvas.paste(blank, (rx * tile_size, ry * tile_size))
        cx = (canvas.width - w) // 2
        cy = (canvas.height - h) // 2
        cropped = canvas.crop((cx, cy, cx + w, cy + h))
        return cropped
    except Exception:
        return None

def generate_placeholder_map(city, lat, lon, w=800, h=400):
    img = Image.new("RGB", (w, h), (230, 230, 230))
    draw = ImageDraw.Draw(img)
    try:
        from PIL import ImageFont
        font = ImageFont.truetype("DejaVuSans.ttf", 28)
    except Exception:
        font = None
    text = f"{city}\n{lat:.6f}, {lon:.6f}"
    draw.multiline_text((20, 20), text, fill=(40,40,40), font=font)
    return img

def fetch_and_save_map(lat, lon, dest_path, zoom=12, w=800, h=400):
    bimg = fetch_tile_image(lat, lon, zoom=zoom, w=w, h=h)
    if bimg:
        bimg.save(dest_path, format="PNG")
        return True
    return False

def store_city_offline(city, category, suggestions, lat=None, lon=None, image_urls=None):
    key = safe_filename(city)
    entry = offline_db.get(key, {"city": city, "categories": {}, "images": [], "map_image": None, "lat": lat, "lon": lon})
    cats = entry.get("categories", {})
    cats[category.lower()] = suggestions
    entry["categories"] = cats
    entry["lat"] = lat or entry.get("lat")
    entry["lon"] = lon or entry.get("lon")
    if image_urls:
        for idx, url in enumerate(image_urls, start=1):
            fname = f"{key}{int(time.time())}{idx}.jpg"
            dest = os.path.join(IMAGES_DIR, fname)
            ok = download_and_save_image(url, dest)
            if ok:
                entry.setdefault("images", []).append(dest)
    if entry.get("lat") and entry.get("lon"):
        map_fname = os.path.join(MAPS_DIR, f"{key}_map.png")
        ok = fetch_and_save_map(entry["lat"], entry["lon"], map_fname)
        if ok:
            entry["map_image"] = map_fname
        else:
            placeholder = generate_placeholder_map(entry["city"], entry["lat"], entry["lon"])
            placeholder.save(map_fname, format="PNG")
            entry["map_image"] = map_fname
    offline_db[key] = entry
    save_offline_db(offline_db)
    return key

st.set_page_config(page_title="AI Tour Guide (Fixed)", layout="wide")
st.title("AI Tour Guide — Fixed (no googletrans/httpx)")
st.markdown("Voice capture via browser, TTS via gTTS, translation via OpenAI if available.")

online = is_online()
st.sidebar.markdown(f"*Network:* {'Online' if online else 'Offline'}")

mode = st.sidebar.radio("Mode", ["Auto", "Force Online", "Force Offline"])
if mode == "Force Online":
    online = True
elif mode == "Force Offline":
    online = False

st.sidebar.header("Search / Download")
city_input = st.sidebar.text_input("City (e.g., Mysore, Mangalore)", value="")
category = st.sidebar.selectbox("Category", ["Places", "Food", "Culture", "Hotels"])
btn_search = st.sidebar.button("Search")
btn_download = st.sidebar.button("Download for offline (save city)")
st.sidebar.markdown("---")
st.sidebar.write("Offline cities stored:")
for k, v in offline_db.items():
    st.sidebar.write(f"- {v.get('city', k).title()}")

st.sidebar.markdown("---")
st.sidebar.header("Manage stored cities")
for key in list(offline_db.keys()):
    entry = offline_db[key]
    name = entry.get("city", key)
    if st.sidebar.button(f"Download JSON: {key}"):
        st.sidebar.download_button(f"Download {key}.json", json.dumps(entry, indent=2, ensure_ascii=False), file_name=f"{key}.json", mime="application/json")
    if st.sidebar.button(f"Remove: {key}"):
        for p in entry.get("images", []):
            try:
                if os.path.exists(p): os.remove(p)
            except: pass
        mp = entry.get("map_image")
        if mp and os.path.exists(mp):
            try: os.remove(mp)
            except: pass
        offline_db.pop(key, None)
        save_offline_db(offline_db)
        safe_rerun()

col1, col2 = st.columns([2,1])
with col1:
    st.header("Explore")
    st.components.v1.html(
        """
        <div>
          <button id="btnSpeak">🎤 Start Speech</button>
          <button id="btnLoc">📍 Share location</button>
          <script>
            const btn = document.getElementById('btnSpeak');
            const btnLoc = document.getElementById('btnLoc');
            btn.onclick = () => {
              const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
              recognition.lang = 'en-IN';
              recognition.onresult = (e) => {
                const t = e.results[0][0].transcript;
                const url = new URL(window.location);
                url.searchParams.set('speech', t);
                window.location = url.toString();
              };
              recognition.start();
            }
            btnLoc.onclick = () => {
              if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition((pos) => {
                  const lat = pos.coords.latitude;
                  const lon = pos.coords.longitude;
                  const url = new URL(window.location);
                  url.searchParams.set('lat', lat);
                  url.searchParams.set('lon', lon);
                  window.location = url.toString();
                }, (err) => { alert('Location denied or unavailable.'); });
              } else { alert('Geolocation not supported.'); }
            }
          </script>
        </div>
        """,
        height=120,
    )
    params = st.experimental_get_query_params()
    speech_text = params.get("speech", [""])[0]
    shared_lat = params.get("lat", [None])[0]
    shared_lon = params.get("lon", [None])[0]
    if speech_text:
        st.info(f"Captured speech: {speech_text}")
    if shared_lat and shared_lon:
        try:
            latf = float(shared_lat); lonf = float(shared_lon)
            st.success(f"Shared location: {latf:.6f}, {lonf:.6f}")
        except:
            latf = lonf = None
    else:
        latf = lonf = None

    st.markdown("---")
    user_input = st.text_input("Ask the guide (or use speech):", value=speech_text)
    lang_choice = st.selectbox("Reply language / TTS", ["en", "hi", "kn"], format_func=lambda x: {"en":"English","hi":"Hindi","kn":"Kannada"}[x])
    model_choice = st.selectbox("Model", ["gpt-3.5-turbo", "gpt-4"], index=0)
    if st.button("Send") or (user_input and btn_search):
        prompt = user_input
        ai_text = ""
        if online and OPENAI_API_KEY:
            try:
                ai_text = fetch_openai_text(prompt, system=f"You are a helpful travel guide and reply concisely in {lang_choice}.")
                if ai_text is None:
                    ai_text = "AI responded with no content."
            except Exception as e:
                ai_text = f"AI unavailable: {e}"
        else:
            ai_text = "Offline fallback: enable OpenAI or download the city for offline content."
        st.markdown(ai_text)
        try:
            tts = gTTS(text=ai_text, lang=lang_choice)
            tmp = os.path.join("data", f"tts_{int(time.time())}.mp3")
            tts.save(tmp)
            audio_bytes = open(tmp, "rb").read()
            st.audio(audio_bytes)
        except Exception as e:
            st.info("TTS not available: " + str(e))

    st.markdown("---")
    query_city = city_input.strip() or "Bengaluru"
    st.subheader(f"{query_city.title()} — {category}")
    if not is_online():
        key = safe_filename(query_city)
        if key in offline_db:
            entry = offline_db[key]
            items = entry.get("categories", {}).get(category.lower(), [])
            if items:
                for it in items:
                    st.markdown(f"{it.get('name')}**  \n{it.get('description')}  \n*Tip:* {it.get('tip','-')}")
            imgs = entry.get("images", [])
            if imgs:
                st.markdown("Images (offline)")
                cols = st.columns(min(3,len(imgs)))
                for i,p in enumerate(imgs):
                    try:
                        img = Image.open(p)
                        with cols[i%len(cols)]: st.image(img, use_container_width=True)
                    except: pass
            map_img = entry.get("map_image")
            if map_img and os.path.exists(map_img):
                st.markdown("Map (offline)")
                try: st.image(map_img, use_container_width=True)
                except: pass
            else:
                st.info("No offline map stored.")
        else:
            st.error("City not stored offline.")
    else:
        lat, lon = (None, None)
        if latf and lonf:
            lat, lon = latf, lonf
        else:
            lat, lon = geocode_city(query_city)
        if lat and lon:
            st.write(f"Location: {lat:.6f}, {lon:.6f}")
        else:
            st.info("Could not geocode automatically.")
        suggestions = None
        if OPENAI_API_KEY and is_online():
            try:
                suggestions = fetch_openai_text(f"Give 3 short {category} suggestions for {query_city}", model=model_choice)
            except Exception:
                suggestions = None
        if suggestions:
            st.markdown(suggestions)
        else:
            st.markdown("Fallback suggestions (offline-style)")
            st.write(f"{category} suggestions will appear here after download or when AI is available.")
        if lat and lon:
            st.markdown("### Map (live)")
            if FOLIUM_OK:
                try:
                    m = folium.Map(location=[lat, lon], zoom_start=12, tiles="CartoDB Positron", attr="© OpenStreetMap contributors | CartoDB")
                    folium.Marker([lat, lon], tooltip=query_city.title()).add_to(m)
                    st_folium(m, width=700, height=400)
                except Exception:
                    img = fetch_tile_image(lat, lon, zoom=12, w=800, h=400)
                    if img:
                        st.image(img, use_container_width=True)
                    else:
                        st.image(generate_placeholder_map(query_city, lat, lon), use_container_width=True)
            else:
                img = fetch_tile_image(lat, lon, zoom=12, w=800, h=400)
                if img:
                    st.image(img, use_container_width=True)
                else:
                    st.image(generate_placeholder_map(query_city, lat, lon), use_container_width=True)

        if btn_download:
            st.info("Downloading city for offline use...")
            if OPENAI_API_KEY and is_online():
                try:
                    suggestions_to_store = fetch_openai_text(f"Give 3 short {category} suggestions for {query_city}", model=model_choice)
                    if suggestions_to_store:
                        # simple wrap when API returns plain text; create structured fallback
                        suggestions_to_store = [{"name":"1","description":suggestions_to_store,"tip":""}]
                except:
                    suggestions_to_store = [
                        {"name": f"{category} 1", "description": f"Popular {category.lower()} spot in {query_city}.", "tip": "Local tip."}
                    ]
            else:
                suggestions_to_store = [
                    {"name": f"{category} 1", "description": f"Popular {category.lower()} spot in {query_city}.", "tip": "Local tip."}
                ]
            image_urls = fetch_unsplash_image_urls(query_city, count=3) if UNSPLASH_ACCESS_KEY else []
            key = store_city_offline(query_city, category, suggestions_to_store, lat=lat, lon=lon, image_urls=image_urls)
            st.success(f"Saved {query_city} to offline DB (key: {key})")
            safe_rerun()

with col2:
    st.header("Quick actions")
    st.write("Use sidebar for search/manage.")
    st.markdown("Offline cities stored:")
    if offline_db:
        for k,v in offline_db.items():
            st.write(f"- *{v.get('city',k).title()}*")
    else:
        st.write("No cities stored offline yet.")
st.markdown("---")
st.caption("AI Tour Guide — Fixed dependencies; use gTTS for TTS and OpenAI for AI/translation.")
