import os
import json
import time
import math
import requests
import streamlit as st
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

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

st.set_page_config(page_title="AI Tour Guide — Updated", layout="wide")
st.title("AI Tour Guide — Updated")

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

def get_openai_client():
    if not OPENAI_API_KEY or OpenAI is None:
        return None
    try:
        return OpenAI(api_key=OPENAI_API_KEY)
    except Exception:
        return None

def fetch_openai_suggestions_plain(city, category, model="gpt-3.5-turbo"):
    client = get_openai_client()
    if client is None:
        return None
    prompt = f"Provide 3 concise {category} suggestions for {city} as bullet points (one suggestion per line)."
    try:
        resp = client.chat.completions.create(model=model, messages=[{"role":"user","content":prompt}], temperature=0.7, max_tokens=400)
        # streaming vs non-streaming safe access
        text = ""
        try:
            text = resp.choices[0].message.content
        except Exception:
            try:
                text = resp.choices[0].text
            except Exception:
                text = str(resp)
        return text
    except Exception:
        return None

def fetch_unsplash_image_urls(query, count=3):
    if not UNSPLASH_ACCESS_KEY:
        return []
    try:
        r = requests.get(
            "https://api.unsplash.com/search/photos",
            params={"query": query, "per_page": count, "orientation": "landscape", "client_id": UNSPLASH_ACCESS_KEY},
            timeout=8,
        )
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
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": city, "format": "json", "limit": 1},
            headers={"User-Agent": "ai-tour-guide-app"},
            timeout=8,
        )
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
                        canvas.paste(Image.new("RGB", (tile_size, tile_size), (240, 240, 240)), (rx * tile_size, ry * tile_size))
                except Exception:
                    canvas.paste(Image.new("RGB", (tile_size, tile_size), (240, 240, 240)), (rx * tile_size, ry * tile_size))
        cx = (canvas.width - w) // 2
        cy = (canvas.height - h) // 2
        return canvas.crop((cx, cy, cx + w, cy + h))
    except Exception:
        return None

def generate_placeholder_map(city, lat, lon, w=800, h=400):
    img = Image.new("RGB", (w, h), (230, 230, 230))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 24)
    except Exception:
        font = None
    text = f"{city}\n{lat:.6f}, {lon:.6f}"
    draw.multiline_text((20, 20), text, fill=(40, 40, 40), font=font)
    return img

def fetch_and_save_map(lat, lon, dest_path, zoom=12, w=800, h=400):
    img = fetch_tile_image(lat, lon, zoom=zoom, w=w, h=h)
    if img:
        img.save(dest_path, format="PNG")
        return True
    return False

def store_city_offline(city, category, suggestions, lat=None, lon=None, image_urls=None, uploaded_paths=None):
    db = offline_db
    key = safe_filename(city)
    entry = db.get(key, {"city": city, "categories": {}, "images": [], "map_image": None, "lat": lat, "lon": lon})
    cats = entry.get("categories", {})
    cats[category.lower()] = suggestions
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
    db[key] = entry
    save_offline_db(db)
    return key

offline_db = load_offline_db()

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
uploaded_files = st.sidebar.file_uploader("Upload images for this city (optional)", accept_multiple_files=True, type=["jpg", "jpeg", "png"])
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
        suggestions_to_store = [{"name": f"{category} 1", "description": f"Popular {category.lower()} spot in {query_city}.", "tip": ""}]
        if OPENAI_API_KEY and online:
            ai_text = fetch_openai_suggestions_plain(query_city, category)
            if ai_text:
                suggestions_to_store = [{"name": "AI suggestions", "description": ai_text, "tip": ""}]
        image_urls = fetch_unsplash_image_urls(query_city, count=3) if UNSPLASH_ACCESS_KEY else []
        key = store_city_offline(query_city, category, suggestions_to_store, lat=lat, lon=lon, image_urls=image_urls, uploaded_paths=uploaded_saved_paths)
        st.sidebar.success(f"Saved {query_city} as {key}")
        offline_db = load_offline_db()

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

col1, col2 = st.columns([2, 1])
with col1:
    st.header("Explore")
    if not city_input:
        st.info("Enter a city in the sidebar and choose a mode.")
    else:
        city = city_input.strip()
        st.subheader(f"{city.title()} — {category}")
        if not online:
            key = safe_filename(city)
            if key in offline_db:
                entry = offline_db[key]
                items = entry.get("categories", {}).get(category.lower(), [])
                if items:
                    for it in items:
                        st.markdown(f"{it.get('name')}**  \n{it.get('description')}  \n*Tip:* {it.get('tip','-')}")
                else:
                    st.warning("No stored items for this category in offline data.")
                imgs = entry.get("images", [])
                if imgs:
                    st.markdown("### Images (offline)")
                    cols = st.columns(min(3, len(imgs)))
                    for i, p in enumerate(imgs):
                        try:
                            img = Image.open(p)
                            with cols[i % len(cols)]:
                                st.image(img, use_container_width=True)
                        except Exception:
                            st.write("Could not open image", p)
                map_img = entry.get("map_image")
                if map_img and os.path.exists(map_img):
                    st.markdown("### Map (offline)")
                    st.image(map_img, use_container_width=True)
                else:
                    st.info("No offline map stored for this city.")
            else:
                st.error("City not available offline. Use online mode to download it for offline use.")
        else:
            lat, lon = geocode_city(city)
            if lat and lon:
                st.write(f"Location: {lat:.6f}, {lon:.6f}")
            else:
                st.info("Could not geocode the city automatically.")
            suggestions_text = None
            if OPENAI_API_KEY and online:
                suggestions_text = fetch_openai_suggestions_plain(city, category)
                if suggestions_text:
                    st.markdown("### AI Suggestions")
                    st.write(suggestions_text)
            if not suggestions_text:
                st.markdown("### Example suggestions (fallback)")
                st.write(f"{category} suggestions for {city.title()} will appear here once you fetch online or download the city for offline use.")
            image_urls = fetch_unsplash_image_urls(city, count=3)
            images_displayed = False
            if image_urls:
                st.markdown("### Images (online)")
                cols = st.columns(min(3, len(image_urls)))
                for i, url in enumerate(image_urls):
                    try:
                        r = requests.get(url, timeout=8)
                        r.raise_for_status()
                        img = Image.open(BytesIO(r.content))
                        with cols[i % len(cols)]:
                            st.image(img, use_container_width=True)
                        images_displayed = True
                    except Exception:
                        continue
            local_key = safe_filename(city)
            if local_key in offline_db:
                local_imgs = offline_db[local_key].get("images", [])
                if local_imgs:
                    st.markdown("### Images (local/offline)")
                    cols = st.columns(min(3, len(local_imgs)))
                    for i, p in enumerate(local_imgs):
                        try:
                            img = Image.open(p)
                            with cols[i % len(cols)]:
                                st.image(img, use_container_width=True)
                            images_displayed = True
                        except:
                            continue
            if not images_displayed:
                st.info("No images available for this city.")
            if lat and lon:
                st.markdown("### Map (live)")
                if FOLIUM_OK:
                    try:
                        m = folium.Map(location=[lat, lon], zoom_start=12, tiles="CartoDB Positron", attr="© OpenStreetMap contributors | CartoDB")
                        folium.Marker([lat, lon], tooltip=city.title()).add_to(m)
                        st_folium(m, width=700, height=400)
                    except Exception:
                        img = fetch_tile_image(lat, lon, zoom=12, w=800, h=400)
                        if img:
                            st.image(img, use_container_width=True)
                        else:
                            st.image(generate_placeholder_map(city, lat, lon), use_container_width=True)
                else:
                    img = fetch_tile_image(lat, lon, zoom=12, w=800, h=400)
                    if img:
                        st.image(img, use_container_width=True)
                    else:
                        st.image(generate_placeholder_map(city, lat, lon), use_container_width=True)

with col2:
    st.header("Quick actions")
    if offline_db:
        st.write("Offline cities stored:")
        for k, v in offline_db.items():
            st.write(f"- *{v.get('city', k).title()}*")
    else:
        st.write("No cities stored offline yet.")
st.markdown("---")
st.caption("AI Tour Guide — images included (uploaded, Unsplash, or local).")
