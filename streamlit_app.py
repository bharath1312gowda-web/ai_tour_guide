# streamlit_app.py
import os
import json
import time
import requests
import streamlit as st
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv

# Optional OpenAI import (only used if online and key present)
try:
    from openai import OpenAI
except Exception:
    OpenAI = None

# -----------------------
# Config & paths
# -----------------------
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

# -----------------------
# Helpers: file DB load/save + cleanup
# -----------------------
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
    """
    Remove entries that look like non-city artifacts (e.g., top-level keys 'destinations', 'phrases', etc.)
    Keep entries that have at least a 'city' string and 'categories' dict.
    """
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

# -----------------------
# Network / OpenAI helpers
# -----------------------
def is_online(timeout=2.0):
    try:
        requests.get("https://www.google.com", timeout=timeout)
        return True
    except Exception:
        return False

def safe_filename(s):
    return "".join(c for c in s.lower().strip().replace(" ", "") if (c.isalnum() or c in "-"))

def get_openai_client():
    if not OPENAI_API_KEY or OpenAI is None:
        return None
    try:
        return OpenAI(api_key=OPENAI_API_KEY)
    except Exception:
        return None

def fetch_suggestions_openai(city, category, model="gpt-3.5-turbo"):
    client = get_openai_client()
    if client is None:
        raise RuntimeError("OpenAI client not configured or missing key.")
    prompt = (
        f"You are a travel guide. Provide 3 short {category.lower()} suggestions for {city}. "
        "Return JSON array of objects with keys: name, description, tip."
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=500
    )
    txt = resp.choices[0].message.content
    try:
        parsed = json.loads(txt)
        if isinstance(parsed, list):
            return parsed
    except Exception:
        # fallback: parse lines
        lines = [l.strip() for l in txt.splitlines() if l.strip()]
        items = []
        for i, line in enumerate(lines[:3]):
            items.append({"name": f"Suggestion {i+1}", "description": line, "tip": ""})
        return items
    return []

# -----------------------
# Unsplash helpers
# -----------------------
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

# -----------------------
# Geocoding + static map
# -----------------------
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

def fetch_static_map_bytes(lat, lon, zoom=12, w=800, h=400):
    try:
        map_url = f"https://staticmap.openstreetmap.de/staticmap.php?center={lat},{lon}&zoom={zoom}&size={w}x{h}&markers={lat},{lon},red-pushpin"
        r = requests.get(map_url, timeout=10)
        r.raise_for_status()
        return r.content
    except Exception:
        return None

def fetch_and_save_map(lat, lon, dest_path, zoom=12, w=800, h=400):
    b = fetch_static_map_bytes(lat, lon, zoom=zoom, w=w, h=h)
    if b:
        with open(dest_path, "wb") as f:
            f.write(b)
        return True
    return False

# -----------------------
# Offline store logic
# -----------------------
def store_city_offline(city, category, suggestions, lat=None, lon=None, image_urls=None):
    key = safe_filename(city)
    entry = offline_db.get(key, {"city": city, "categories": {}, "images": [], "map_image": None, "lat": lat, "lon": lon})
    # merge categories
    cats = entry.get("categories", {})
    cats[category.lower()] = suggestions
    entry["categories"] = cats
    entry["lat"] = lat or entry.get("lat")
    entry["lon"] = lon or entry.get("lon")
    # download images
    if image_urls:
        for idx, url in enumerate(image_urls, start=1):
            fname = f"{key}{int(time.time())}{idx}.jpg"
            dest = os.path.join(IMAGES_DIR, fname)
            ok = download_and_save_image(url, dest)
            if ok:
                entry.setdefault("images", []).append(dest)
    # fetch & save map
    if entry.get("lat") and entry.get("lon"):
        map_fname = os.path.join(MAPS_DIR, f"{key}_map.png")
        ok = fetch_and_save_map(entry["lat"], entry["lon"], map_fname)
        if ok:
            entry["map_image"] = map_fname
    offline_db[key] = entry
    save_offline_db(offline_db)
    return key

# -----------------------
# UI
# -----------------------
st.set_page_config(page_title="AI Tour Guide (Online+Offline)", layout="wide")
st.title("AI Tour Guide — Online & Offline")
st.write("Runs online when available. Use 'Download for offline' to save a city.")

online = is_online()
st.sidebar.markdown(f"*Network:* {'Online' if online else 'Offline'}")

mode = st.sidebar.radio("Mode", ["Auto (use network)", "Force Online", "Force Offline"])
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

# Management area
st.sidebar.markdown("---")
st.sidebar.header("Manage stored cities")
for key in list(offline_db.keys()):
    entry = offline_db[key]
    name = entry.get("city", key)
    if st.sidebar.button(f"Download JSON: {key}"):
        st.sidebar.download_button(f"Download {key}.json", json.dumps(entry, indent=2, ensure_ascii=False), file_name=f"{key}.json", mime="application/json")
    if st.sidebar.button(f"Remove: {key}"):
        # remove files
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
        st.experimental_rerun()

# Main explore area
col1, col2 = st.columns([2,1])
with col1:
    st.header("Explore")
    if not city_input:
        st.info("Type a city in the sidebar and click Search (or choose a stored offline city).")
    else:
        city = city_input.strip()
        st.subheader(f"{city.title()} — {category}")

        if not online:
            key = safe_filename(city)
            if key in offline_db:
                entry = offline_db[key]
                items = entry.get("categories", {}).get(category.lower(), [])
                if items:
                    st.write(f"Showing offline stored {len(items)} items.")
                    for it in items:
                        st.markdown(f"{it.get('name')}**  \n{it.get('description')}  \n*Tip:* {it.get('tip','-')}")
                else:
                    st.warning("No stored items for this category in offline data.")
                imgs = entry.get("images", [])
                if imgs:
                    st.markdown("### Images (offline)")
                    cols = st.columns(min(3,len(imgs)))
                    for i, p in enumerate(imgs):
                        try:
                            img = Image.open(p)
                            with cols[i%len(cols)]:
                                st.image(img, use_container_width=True)
                        except Exception:
                            st.write("Could not open image", p)
                map_img = entry.get("map_image")
                if map_img and os.path.exists(map_img):
                    st.markdown("### Map (offline)")
                    try:
                        st.image(map_img, use_container_width=True)
                    except:
                        st.write("Saved map exists but couldn't be displayed.")
                else:
                    st.info("No offline map stored for this city.")
            else:
                st.error("City not available offline. Use online mode to download it for offline use.")
        else:
            # online flow
            lat, lon = geocode_city(city)
            if lat and lon:
                st.write(f"Location: {lat:.6f}, {lon:.6f}")
            else:
                st.info("Could not geocode the city automatically.")

            suggestions = None
            openai_error = None
            if OPENAI_API_KEY:
                try:
                    with st.spinner("Fetching suggestions from OpenAI..."):
                        suggestions = fetch_suggestions_openai(city, category)
                except Exception as e:
                    # check for insufficient_quota in message
                    msg = str(e)
                    if "insufficient_quota" in msg or "quota" in msg.lower() or "429" in msg:
                        openai_error = "OpenAI quota exceeded or key restricted (429). Suggestions unavailable."
                    else:
                        openai_error = f"OpenAI error: {e}"
                    suggestions = None

            if openai_error:
                st.error(openai_error)

            if suggestions:
                st.markdown("### Suggestions")
                if isinstance(suggestions, list):
                    for it in suggestions:
                        name = it.get("name", "Item")
                        desc = it.get("description", "")
                        tip = it.get("tip", "")
                        st.markdown(f"{name}**  \n{desc}  \n*Tip:* {tip}")
                else:
                    st.write(suggestions)
            else:
                st.markdown("### Example suggestions (fallback)")
                st.write(f"{category} suggestions for {city.title()} will appear here once you fetch online or download the city for offline use.")

            # Unsplash images
            images_shown = []
            if UNSPLASH_ACCESS_KEY:
                try:
                    urls = fetch_unsplash_image_urls(city, count=3)
                    if urls:
                        cols = st.columns(3)
                        for i, u in enumerate(urls):
                            try:
                                r = requests.get(u, timeout=8)
                                r.raise_for_status()
                                img = Image.open(BytesIO(r.content))
                                with cols[i%3]:
                                    st.image(img, use_container_width=True)
                                images_shown.append(u)
                            except Exception:
                                continue
                except Exception:
                    st.info("Could not fetch Unsplash images.")
            else:
                st.info("Unsplash key not configured. Images will be placeholders or offline files.")

            # Live static map (fetch bytes and display)
            if lat and lon:
                st.markdown("### Map (live)")
                map_bytes = fetch_static_map_bytes(lat, lon, zoom=12, w=800, h=400)
                if map_bytes:
                    try:
                        st.image(Image.open(BytesIO(map_bytes)), use_container_width=True)
                    except Exception:
                        st.write("Map fetched but couldn't be displayed as image.")
                else:
                    st.info("Could not fetch live static map at this time.")

            # download for offline
            if btn_download:
                st.info("Preparing to download and save city for offline use...")
                # suggestions to store
                if isinstance(suggestions, list) and suggestions:
                    suggestions_to_store = suggestions
                else:
                    suggestions_to_store = [
                        {"name": f"{category} 1", "description": f"Popular {category.lower()} spot in {city}.", "tip": "Local tip."},
                        {"name": f"{category} 2", "description": "Another recommended place.", "tip": "Local tip."},
                        {"name": f"{category} 3", "description": "Hidden gem.", "tip": "Local tip."}
                    ]
                image_urls = fetch_unsplash_image_urls(city, count=3) if UNSPLASH_ACCESS_KEY else []
                key = store_city_offline(city, category, suggestions_to_store, lat=lat, lon=lon, image_urls=image_urls)
                st.success(f"Saved {city} to offline DB (key: {key})")
                st.experimental_rerun()

with col2:
    st.header("Quick actions")
    st.write("Use the sidebar for search/gallery/manage.")
    st.markdown("### Offline cities stored")
    if offline_db:
        for k, v in offline_db.items():
            st.write(f"- *{v.get('city', k).title()}*")
    else:
        st.write("No cities stored offline yet.")

st.markdown("---")
st.caption("AI Tour Guide — online + offline storage enabled.")
