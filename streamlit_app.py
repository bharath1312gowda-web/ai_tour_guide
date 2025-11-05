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
# Utilities
# -----------------------
def save_offline_db(db):
    with open(OFFLINE_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)

def load_offline_db():
    if os.path.exists(OFFLINE_DATA_FILE):
        try:
            with open(OFFLINE_DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

offline_db = load_offline_db()

def is_online(timeout=2.0):
    """Quick internet check"""
    try:
        requests.get("https://www.google.com", timeout=timeout)
        return True
    except Exception:
        return False

def safe_filename(s):
    return "".join(c for c in s.lower().strip().replace(" ", "") if (c.isalnum() or c in "-"))

# -----------------------
# OpenAI helper
# -----------------------
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
        raise RuntimeError("OpenAI client not configured.")
    prompt = (
        f"You are a helpful travel guide. Provide 3 short {category.lower()} suggestions for the city "
        f"{city}. For each item give a short description (one sentence) and one local tip. Output as JSON array "
        f"of objects with keys: name, description, tip."
    )
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role":"user","content":prompt}],
            temperature=0.7,
            max_tokens=500
        )
        txt = resp.choices[0].message.content
        # Try parse JSON from model; fallback to plain text wrap
        try:
            parsed = json.loads(txt)
            return parsed
        except Exception:
            # Fallback: simple split by lines to create items
            lines = [l.strip() for l in txt.splitlines() if l.strip()]
            items = []
            for i, line in enumerate(lines[:3]):
                items.append({"name": f"Suggestion {i+1}", "description": line, "tip": ""})
            return items
    except Exception as e:
        raise

# -----------------------
# Unsplash helper
# -----------------------
def fetch_unsplash_image_urls(query, count=3):
    """Return list of image URLs from Unsplash (requires UNSPLASH_ACCESS_KEY)."""
    if not UNSPLASH_ACCESS_KEY:
        return []
    url = "https://api.unsplash.com/search/photos"
    headers = {"Accept-Version": "v1"}
    params = {"query": query, "per_page": count, "orientation": "landscape", "client_id": UNSPLASH_ACCESS_KEY}
    try:
        r = requests.get(url, params=params, headers=headers, timeout=8)
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
    """Return (lat, lon) using Nominatim"""
    try:
        r = requests.get("https://nominatim.openstreetmap.org/search", params={"q": city, "format": "json", "limit": 1}, headers={"User-Agent":"ai-tour-guide-app"}, timeout=8)
        r.raise_for_status()
        data = r.json()
        if data:
            lat = float(data[0]["lat"]); lon = float(data[0]["lon"])
            return lat, lon
    except Exception:
        pass
    return None, None

def fetch_static_map_image(lat, lon, zoom=12, w=800, h=400, dest_path=None):
    """
    Fetch static map image from staticmap.openstreetmap.de
    Example: https://staticmap.openstreetmap.de/staticmap.php?center=LAT,LON&zoom=12&size=800x400&markers=LAT,LON,red-pushpin
    """
    try:
        map_url = f"https://staticmap.openstreetmap.de/staticmap.php?center={lat},{lon}&zoom={zoom}&size={w}x{h}&markers={lat},{lon},red-pushpin"
        r = requests.get(map_url, timeout=10)
        r.raise_for_status()
        if dest_path:
            with open(dest_path, "wb") as f:
                f.write(r.content)
            return True
        return r.content
    except Exception:
        return False

# -----------------------
# Offline management
# -----------------------
def store_city_offline(city, category, suggestions, lat=None, lon=None, image_urls=None):
    """
    suggestions: list of dicts (name, description, tip)
    image_urls: list of remote URLs (we will download)
    """
    key = safe_filename(city)
    city_entry = {
        "city": city,
        "categories": {
            category.lower(): suggestions
        },
        "lat": lat,
        "lon": lon,
        "images": []
    }
    # download images to static/images/<key>_1.jpg ...
    if image_urls:
        for idx, url in enumerate(image_urls, start=1):
            fname = f"{key}_{idx}.jpg"
            dest = os.path.join(IMAGES_DIR, fname)
            ok = download_and_save_image(url, dest)
            if ok:
                city_entry["images"].append(dest)
    # fetch static map and save
    if lat and lon:
        map_fname = os.path.join(MAPS_DIR, f"{key}_map.png")
        ok = fetch_static_map_image(lat, lon, dest_path=map_fname)
        if ok:
            city_entry["map_image"] = map_fname
        else:
            city_entry["map_image"] = None
    # merge into offline_db
    existing = offline_db.get(key, {})
    # merge categories
    existing_cats = existing.get("categories", {})
    existing_cats.update(city_entry["categories"])
    existing["city"] = city
    existing["categories"] = existing_cats
    existing["lat"] = lat or existing.get("lat")
    existing["lon"] = lon or existing.get("lon")
    # images: keep existing plus new
    existing_images = existing.get("images", [])
    existing_images += city_entry.get("images", [])
    existing["images"] = existing_images
    if "map_image" in city_entry:
        existing["map_image"] = city_entry["map_image"]
    offline_db[key] = existing
    save_offline_db(offline_db)
    return key

# -----------------------
# UI
# -----------------------
st.set_page_config(page_title="AI Tour Guide (Online + Offline)", layout="wide")
st.title("AI Tour Guide — Online & Offline")
st.write("This app runs in online mode when connected. Use Download for offline to store a city for offline use.")

online = is_online()
st.sidebar.markdown(f"*Network:* {'Online' if online else 'Offline'}")

mode = st.sidebar.radio("Mode", ["Auto (online when available)", "Force Online", "Force Offline"])
if mode == "Force Online":
    online = True
elif mode == "Force Offline":
    online = False

# Sidebar inputs
st.sidebar.header("Search / Download")
city_input = st.sidebar.text_input("City (e.g., Mangalore, Bengaluru)", value="")
category = st.sidebar.selectbox("Category", ["Places", "Food", "Culture", "Hotels"])
btn_search = st.sidebar.button("Search")
btn_download = st.sidebar.button("Download for offline (save city)")

# Show list of stored offline cities
st.sidebar.markdown("---")
st.sidebar.write("Offline cities stored:")
for k, v in offline_db.items():
    st.sidebar.write(f"- {v.get('city',k).title()}")

# Main area
col1, col2 = st.columns([2,1])
with col1:
    st.header("Explore")
    if not city_input:
        st.info("Type a city in the sidebar and click *Search* (or choose a stored offline city).")
    else:
        city = city_input.strip()
        st.subheader(f"{city.title()} — {category}")
        if not online:
            # offline mode: show from local DB if exists
            key = safe_filename(city)
            if key in offline_db:
                entry = offline_db[key]
                # show cached categories if present
                items = entry.get("categories", {}).get(category.lower(), [])
                if items:
                    st.write(f"Showing offline stored {len(items)} items.")
                    for it in items:
                        st.markdown(f"{it.get('name')}**  \n{it.get('description')}  \n*Tip:* {it.get('tip','-')}")
                else:
                    st.warning("No stored items for this category in offline data.")
                # show saved images
                imgs = entry.get("images", [])
                if imgs:
                    st.markdown("### Images (offline)")
                    cols = st.columns(min(3,len(imgs)))
                    for i, p in enumerate(imgs):
                        try:
                            img = Image.open(p)
                            with cols[i%len(cols)]:
                                st.image(img, use_column_width=True)
                        except Exception:
                            st.write("Could not open image", p)
                # show saved map image
                map_img = entry.get("map_image")
                if map_img and os.path.exists(map_img):
                    st.markdown("### Map (offline)")
                    try:
                        st.image(map_img, use_column_width=True)
                    except:
                        st.write("Saved map exists but could not be displayed.")
                else:
                    st.info("No offline map stored for this city.")
                # download JSON for this city
                if st.button(f"Download stored JSON for {entry.get('city')}"):
                    st.download_button(f"Download {entry.get('city')}.json", json.dumps(entry, indent=2, ensure_ascii=False), file_name=f"{key}.json", mime="application/json")
            else:
                st.error("City not available offline. Use online mode to download it for offline use.")
        else:
            # online mode
            # First, try to fetch geocode
            lat, lon = geocode_city(city)
            if lat and lon:
                st.write(f"Location: {lat:.6f}, {lon:.6f}")
            else:
                st.info("Could not geocode the city automatically.")

            # If OpenAI available, fetch suggestions
            suggestions = None
            if OPENAI_API_KEY:
                try:
                    with st.spinner("Fetching suggestions from OpenAI..."):
                        suggestions = fetch_suggestions_openai(city, category)
                except Exception as e:
                    st.error(f"OpenAI error: {e}")
            else:
                st.info("OpenAI API key not configured. Using local fallback suggestions.")

            if suggestions:
                # show results
                st.markdown("### Suggestions")
                # expect suggestions to be list of dicts
                if isinstance(suggestions, list):
                    for it in suggestions:
                        name = it.get("name") if isinstance(it, dict) else str(it)
                        desc = it.get("description","") if isinstance(it, dict) else ""
                        tip = it.get("tip","") if isinstance(it, dict) else ""
                        st.markdown(f"{name}**  \n{desc}  \n*Tip:* {tip}")
                else:
                    st.write(suggestions)
            else:
                # fallback local quick examples
                st.markdown("### Example suggestions (fallback)")
                st.write(f"{category} suggestions for {city.title()} will appear here once you fetch online or download the city for offline use.")

            # show Unsplash images if key present
            images_shown = []
            if UNSPLASH_ACCESS_KEY:
                try:
                    with st.spinner("Fetching Unsplash images..."):
                        urls = fetch_unsplash_image_urls(city, count=3)
                        if urls:
                            cols = st.columns(3)
                            for i, u in enumerate(urls):
                                try:
                                    r = requests.get(u, timeout=8)
                                    img = Image.open(BytesIO(r.content))
                                    images_shown.append(u)
                                    with cols[i%3]:
                                        st.image(img, use_column_width=True)
                                except Exception:
                                    continue
                except Exception:
                    st.info("Could not fetch Unsplash images.")
            else:
                st.info("Unsplash key not configured. You can still download a city with placeholder images.")

            # show online static map (if geocoded)
            if lat and lon:
                try:
                    st.markdown("### Map (live)")
                    # embed an OSM static map image
                    tmp_map_url = f"https://staticmap.openstreetmap.de/staticmap.php?center={lat},{lon}&zoom=12&size=800x400&markers={lat},{lon},red-pushpin"
                    st.image(tmp_map_url, use_column_width=True)
                except Exception:
                    st.info("Could not display live map image.")

            # BUTTONS: download for offline (store)
            if btn_download:
                # Prepare suggestions list for storage
                suggestions_to_store = []
                if isinstance(suggestions, list) and suggestions:
                    suggestions_to_store = suggestions
                else:
                    # create fallback simple list
                    suggestions_to_store = [
                        {"name": f"{category} 1", "description": f"Popular {category.lower()} spot in {city}.", "tip": "Local tip."},
                        {"name": f"{category} 2", "description": "Another recommended place.", "tip": "Local tip."},
                        {"name": f"{category} 3", "description": "Hidden gem.", "tip": "Local tip."}
                    ]
                # fetch images URLs from Unsplash if key present
                image_urls = []
                if UNSPLASH_ACCESS_KEY:
                    image_urls = fetch_unsplash_image_urls(city, count=3)
                # download and store
                st.info("Downloading and saving city data for offline use...")
                key = store_city_offline(city, category, suggestions_to_store, lat=lat, lon=lon, image_urls=image_urls)
                st.success(f"Saved {city} to offline DB with key: {key}")
                st.experimental_rerun()

# Footer area: list stored cities with download and remove options
st.sidebar.markdown("---")
st.sidebar.header("Manage stored cities")
for key, entry in list(offline_db.items()):
    name = entry.get("city", key)
    st.sidebar.write(f"{name.title()}")
    if st.sidebar.button(f"Download JSON: {key}"):
        st.sidebar.download_button(f"Download {key}.json", json.dumps(entry, indent=2, ensure_ascii=False), file_name=f"{key}.json", mime="application/json")
    if st.sidebar.button(f"Remove: {key}"):
        try:
            # remove images and map files if they exist
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
            st.sidebar.success(f"Removed {key}")
            st.experimental_rerun()
        except Exception as e:
            st.sidebar.error(f"Could not remove {key}: {e}")

st.markdown("---")
st.caption("AI Tour Guide — online + offline storage enabled.")
