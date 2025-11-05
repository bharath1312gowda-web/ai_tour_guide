import os
import json
import time
import math
import requests
import streamlit as st
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
from gtts import gTTS

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
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")

DATA_DIR = "data"
IMAGES_DIR = os.path.join("static", "images")
MAPS_DIR = os.path.join("static", "maps")
OFFLINE_DATA_FILE = os.path.join(DATA_DIR, "offline_data.json")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(MAPS_DIR, exist_ok=True)

st.set_page_config(page_title="AI Tour Guide — Text + Voice", layout="wide")
st.title("AI Tour Guide — Text suggestions + Voice (TTS)")

def is_online(timeout=2.0):
    try:
        requests.get("https://www.google.com", timeout=timeout)
        return True
    except Exception:
        return False

def safe_filename(s):
    return "".join(c for c in s.lower().strip().replace(" ", "") if (c.isalnum() or c in "-"))

def load_offline_db():
    if not os.path.exists(OFFLINE_DATA_FILE):
        return {}
    try:
        with open(OFFLINE_DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_offline_db(db):
    with open(OFFLINE_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)

offline_db = load_offline_db()

def get_openai_client():
    if not OPENAI_API_KEY or OpenAI is None:
        return None
    try:
        return OpenAI(api_key=OPENAI_API_KEY)
    except Exception:
        return None

def fetch_openai_text(prompt, model="gpt-3.5-turbo"):
    client = get_openai_client()
    if client is None:
        return None
    try:
        messages = [{"role":"user","content":prompt}]
        resp = client.chat.completions.create(model=model, messages=messages, temperature=0.7, max_tokens=500)
        # handle different response shapes
        try:
            return resp.choices[0].message.content
        except Exception:
            try:
                return resp.choices[0].text
            except Exception:
                return str(resp)
    except Exception:
        return None

def fetch_unsplash_image_urls(query, count=3):
    if not UNSPLASH_ACCESS_KEY:
        return []
    try:
        r = requests.get("https://api.unsplash.com/search/photos", params={"query": query, "per_page": count, "orientation":"landscape", "client_id": UNSPLASH_ACCESS_KEY}, timeout=8)
        r.raise_for_status()
        data = r.json().get("results", [])[:count]
        return [d["urls"]["regular"] for d in data if "urls" in d]
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

def save_uploaded_image(file, dest_path):
    try:
        img = Image.open(file).convert("RGB")
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
                        timg = Image.open(BytesIO(r.content)).convert("RGB")
                        canvas.paste(timg, (rx * tile_size, ry * tile_size))
                    else:
                        canvas.paste(Image.new("RGB", (tile_size, tile_size), (240,240,240)), (rx * tile_size, ry * tile_size))
                except Exception:
                    canvas.paste(Image.new("RGB", (tile_size, tile_size), (240,240,240)), (rx * tile_size, ry * tile_size))
        cx = (canvas.width - w) // 2
        cy = (canvas.height - h) // 2
        return canvas.crop((cx, cy, cx + w, cy + h))
    except Exception:
        return None

def generate_placeholder_map(city, lat, lon, w=800, h=400):
    img = Image.new("RGB", (w, h), (230,230,230))
    draw = ImageDraw.Draw(img)
    try:
        from PIL import ImageFont
        font = ImageFont.truetype("DejaVuSans.ttf", 24)
    except Exception:
        font = None
    text = f"{city}\n{lat:.6f}, {lon:.6f}"
    draw.multiline_text((20,20), text, fill=(40,40,40), font=font)
    return img

def fetch_and_save_map(lat, lon, dest_path, zoom=12, w=800, h=400):
    img = fetch_tile_image(lat, lon, zoom=zoom, w=w, h=h)
    if img:
        img.save(dest_path, format="PNG")
        return True
    return False

def store_city_offline(city, category, suggestions_text, lat=None, lon=None, image_urls=None, uploaded_paths=None):
    key = safe_filename(city)
    entry = offline_db.get(key, {"city": city, "categories": {}, "images": [], "map_image": None, "lat": lat, "lon": lon})
    cats = entry.get("categories", {})
    cats[category.lower()] = [{"name":"suggestions","description": suggestions_text, "tip": ""}]
    entry["categories"] = cats
    entry["lat"] = lat or entry.get("lat")
    entry["lon"] = lon or entry.get("lon")
    if image_urls:
        for idx, url in enumerate(image_urls, start=1):
            fname = f"{key}{int(time.time())}{idx}.jpg"
            dest = os.path.join(IMAGES_DIR, fname)
            if download_and_save_image(url, dest):
                entry.setdefault("images", []).append(dest)
    if uploaded_paths:
        for p in uploaded_paths:
            entry.setdefault("images", []).append(p)
    if entry.get("lat") and entry.get("lon"):
        map_fname = os.path.join(MAPS_DIR, f"{key}_map.png")
        if fetch_and_save_map(entry["lat"], entry["lon"], map_fname):
            entry["map_image"] = map_fname
        else:
            placeholder = generate_placeholder_map(entry["city"], entry["lat"], entry["lon"])
            placeholder.save(map_fname, format="PNG")
            entry["map_image"] = map_fname
    offline_db[key] = entry
    save_offline_db(offline_db)
    return key

def tts_play(text, lang_code="en"):
    try:
        if not text or len(text.strip())==0:
            return
        t = gTTS(text=text, lang=lang_code)
        tmp = os.path.join(DATA_DIR, f"tts_{int(time.time())}.mp3")
        t.save(tmp)
        audio_bytes = open(tmp, "rb").read()
        st.audio(audio_bytes)
    except Exception as e:
        st.error("TTS error: " + str(e))

# UI: network & mode
online = is_online()
st.sidebar.markdown(f"*Network:* {'Online' if online else 'Offline'}")
mode = st.sidebar.radio("Mode", ["Auto", "Force Online", "Force Offline"])
if mode == "Force Online":
    online = True
elif mode == "Force Offline":
    online = False

# Sidebar controls
st.sidebar.header("Search / Download")
city_input = st.sidebar.text_input("City (e.g., Mysore, Mangalore)", value="")
category = st.sidebar.selectbox("Category", ["Places", "Food", "Culture", "Hotels"])
uploaded_files = st.sidebar.file_uploader("Upload images for this city (optional)", accept_multiple_files=True, type=["jpg","jpeg","png"])
uploaded_saved_paths = []
if uploaded_files:
    for f in uploaded_files:
        fname = f"{safe_filename(city_input or 'upload')}{int(time.time())}{f.name}"
        dest = os.path.join(IMAGES_DIR, fname)
        if save_uploaded_image(f, dest):
            uploaded_saved_paths.append(dest)
    if uploaded_saved_paths:
        st.sidebar.success(f"Saved {len(uploaded_saved_paths)} uploaded image(s).")

if st.sidebar.button("Download for offline (save city)"):
    query_city = city_input.strip() or ""
    if not query_city:
        st.sidebar.error("Enter a city name first.")
    else:
        lat, lon = geocode_city(query_city)
        suggestions_text = None
        if OPENAI_API_KEY and online:
            prompt = f"Provide 3 concise {category} suggestions for {query_city} as short bullet points."
            suggestions_text = fetch_openai_text(prompt)
        if not suggestions_text:
            suggestions_text = f"{category} suggestions for {query_city}: 1) Popular spot 2) Another spot 3) Hidden gem."
        image_urls = fetch_unsplash_image_urls(query_city, count=3) if UNSPLASH_ACCESS_KEY else []
        key = store_city_offline(query_city, category, suggestions_text, lat=lat, lon=lon, image_urls=image_urls, uploaded_paths=uploaded_saved_paths)
        st.sidebar.success(f"Saved {query_city} as {key}")
        # reload offline_db from disk
        global_offline = load_offline_db()
        offline_db.update(global_offline)

st.sidebar.markdown("---")
st.sidebar.header("Manage stored cities")
for key in list(offline_db.keys()):
    entry = offline_db[key]
    st.sidebar.write(f"- {entry.get('city', key).title()}")
    if st.sidebar.button(f"Download JSON: {key}"):
        st.sidebar.download_button(f"Download {key}.json", json.dumps(entry, indent=2, ensure_ascii=False), file_name=f"{key}.json", mime="application/json")
    if st.sidebar.button(f"Remove: {key}"):
        for p in entry.get("images", []):
            try:
                if os.path.exists(p):
                    os.remove(p)
            except:
                pass
        mp = entry.get("map_image")
        if mp and os.path.exists(mp):
            try:
                os.remove(mp)
            except:
                pass
        offline_db.pop(key, None)
        save_offline_db(offline_db)
        st.experimental_rerun()

# Main layout
col1, col2 = st.columns([2,1])
with col1:
    st.header("Explore")
    # Browser speech capture HTML (populates query param 'speech')
    st.components.v1.html(
        """
        <div style="margin-bottom:8px;">
          <button id="btnSpeak">🎤 Use Speech (populate input)</button>
          <script>
            const btn = document.getElementById('btnSpeak');
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
          </script>
        </div>
        """,
        height=60,
    )

    params = st.experimental_get_query_params()
    speech_text = params.get("speech", [""])[0]
    user_input = st.text_input("Ask about this destination (or use speech):", value=speech_text)
    lang_choice = st.selectbox("TTS language", ["en","hi","kn"], index=0, format_func=lambda x: {"en":"English","hi":"Hindi","kn":"Kannada"}[x])
    model_choice = st.selectbox("Model (OpenAI)", ["gpt-3.5-turbo","gpt-4"], index=0)
    if st.button("Get Suggestions") or user_input:
        query_city = city_input.strip() or "Bengaluru"
        # 1) Try OpenAI if online and key present
        suggestions_text = None
        if online and OPENAI_API_KEY:
            prompt = f"You are a helpful travel guide. For the city {query_city}, give 3 short suggestions for category: {category}. Also include one-line description for each, separated by newlines."
            try:
                suggestions_text = fetch_openai_text(prompt, model=model_choice)
            except Exception as e:
                suggestions_text = None
        # 2) Fallback to offline DB if available
        if not suggestions_text:
            key = safe_filename(query_city)
            if key in offline_db:
                entry = offline_db[key]
                cats = entry.get("categories", {})
                cat_data = cats.get(category.lower())
                if cat_data and isinstance(cat_data, list):
                    # join descriptions
                    parts = []
                    for it in cat_data:
                        name = it.get("name", "")
                        desc = it.get("description", "")
                        parts.append(f"• {name}: {desc}")
                    suggestions_text = "\n".join(parts)
                else:
                    suggestions_text = f"{category} suggestions for {query_city}: 1) Popular spot 2) Another spot 3) Hidden gem."
            else:
                suggestions_text = f"{category} suggestions for {query_city}: 1) Popular spot 2) Another spot 3) Hidden gem."
        # 3) Display text
        st.markdown("### Suggestions")
        st.write(suggestions_text)
        # 4) Play TTS
        # Map language codes: gTTS supports 'en','hi','kn' (kn may have limited quality)
        try:
            tts_play(suggestions_text, lang_code=lang_choice)
        except Exception as e:
            st.error("TTS failed: " + str(e))

    st.markdown("---")
    st.markdown("### Destination details & images")
    query_city = city_input.strip() or "Bengaluru"
    if not is_online():
        key = safe_filename(query_city)
        if key in offline_db:
            entry = offline_db[key]
            st.subheader(f"{entry.get('city')}")
            cats = entry.get("categories", {})
            items = cats.get(category.lower(), [])
            if items:
                for it in items:
                    st.markdown(f"{it.get('name','')}**  \n{it.get('description','')}")
            imgs = entry.get("images", [])
            if imgs:
                st.markdown("Images (offline)")
                cols = st.columns(min(3,len(imgs)))
                for i,p in enumerate(imgs):
                    try:
                        img = Image.open(p)
                        with cols[i%len(cols)]:
                            st.image(img, use_container_width=True)
                    except Exception:
                        pass
            map_img = entry.get("map_image")
            if map_img and os.path.exists(map_img):
                st.markdown("Map (offline)")
                st.image(map_img, use_container_width=True)
            else:
                st.info("No offline map stored.")
        else:
            st.info("No offline data for this city. Use Download for offline in sidebar.")
    else:
        lat, lon = geocode_city(query_city)
        if lat and lon:
            st.write(f"Location: {lat:.6f}, {lon:.6f}")
        else:
            st.info("Could not geocode automatically.")
        # show online Unsplash images + local if present
        image_urls = fetch_unsplash_image_urls(query_city, count=3)
        images_displayed = False
        if image_urls:
            st.markdown("Images (online)")
            cols = st.columns(min(3,len(image_urls)))
            for i, url in enumerate(image_urls):
                try:
                    r = requests.get(url, timeout=8)
                    r.raise_for_status()
                    img = Image.open(BytesIO(r.content))
                    with cols[i%len(cols)]:
                        st.image(img, use_container_width=True)
                    images_displayed = True
                except Exception:
                    continue
        local_key = safe_filename(query_city)
        if local_key in offline_db:
            local_imgs = offline_db[local_key].get("images", [])
            if local_imgs:
                st.markdown("Images (local/offline)")
                cols = st.columns(min(3,len(local_imgs)))
                for i,p in enumerate(local_imgs):
                    try:
                        img = Image.open(p)
                        with cols[i%len(cols)]:
                            st.image(img, use_container_width=True)
                        images_displayed = True
                    except:
                        continue
        if not images_displayed:
            st.info("No images available for this city.")
        if lat and lon:
            st.markdown("Map (live)")
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

with col2:
    st.header("Quick actions")
    st.write("Use sidebar to search/manage/save offline.")
    if offline_db:
        st.write("Offline cities stored:")
        for k,v in offline_db.items():
            st.write(f"- *{v.get('city',k).title()}*")
    else:
        st.write("No cities stored offline yet.")
st.markdown("---")
st.caption("AI Tour Guide — now shows text suggestions and plays TTS (gTTS).")
