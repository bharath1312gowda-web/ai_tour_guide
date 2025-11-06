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

# Optional OpenAI / folium imports (graceful fallback)
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
st.title("🌍 AI Tour Guide — Offline Verification Build")

# Offline sample data (used if GPT / Unsplash not available)
OFFLINE_CITIES = {
    "bengaluru": {"info": "Bengaluru — tech hub with parks and cafés.", "spots": ["Cubbon Park", "Lalbagh"]},
    "mysuru": {"info": "Mysuru — royal city.", "spots": ["Mysore Palace", "Chamundi Hills"]},
    "coorg": {"info": "Coorg — coffee and hills.", "spots": ["Abbey Falls", "Raja's Seat"]},
}

# -----------------------
# UTILITIES
# -----------------------
def safe_key(s: str) -> str:
    return "".join(c for c in s.lower().strip().replace(" ", "") if (c.isalnum() or c in "-"))

def make_dir_for_city(city_name: str) -> str:
    key = safe_key(city_name)
    folder = os.path.join(CITIES_DIR, key)
    os.makedirs(folder, exist_ok=True)
    return folder

def make_placeholder_map_image(city: str, lat=None, lon=None, dest_path=None, w=900, h=480):
    img = Image.new("RGB", (w, h), (245,245,245))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 20)
    except Exception:
        font = None
    title = f"{city.title()}"
    coord = f"{lat:.5f}, {lon:.5f}" if (lat is not None and lon is not None) else ""
    draw.text((20, 20), title, fill=(30,30,30), font=font)
    if coord:
        draw.text((20, 60), coord, fill=(80,80,80), font=font)
    # light grid
    for x in range(20, w-20, 60):
        draw.line(((x, 120), (x, h-20)), fill=(230,230,230))
    for y in range(120, h-20, 60):
        draw.line(((20, y), (w-20, y)), fill=(230,230,230))
    if dest_path:
        try:
            img.save(dest_path)
        except Exception:
            pass
    return img

def geocode_city(city: str):
    try:
        r = requests.get("https://nominatim.openstreetmap.org/search",
                         params={"q": city, "format":"json", "limit":1},
                         headers={"User-Agent":"ai-tour-guide"}, timeout=8)
        r.raise_for_status()
        data = r.json()
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception:
        return None, None
    return None, None

def fetch_unsplash_urls(city: str, n=3):
    if not UNSPLASH_ACCESS_KEY:
        return []
    try:
        r = requests.get("https://api.unsplash.com/search/photos",
                         params={"query": city, "per_page": n, "client_id": UNSPLASH_ACCESS_KEY}, timeout=8)
        r.raise_for_status()
        results = r.json().get("results", [])[:n]
        return [it["urls"]["regular"] for it in results if "urls" in it]
    except Exception:
        return []

def download_image(url: str, dest: str) -> bool:
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        img = Image.open(BytesIO(r.content)).convert("RGB")
        img.save(dest, format="JPEG", quality=85)
        return True
    except Exception:
        return False

def speak(text: str, lang: str = "en"):
    if not text:
        return
    try:
        tts = gTTS(text=text, lang=lang)
        tmp = os.path.join(DATA_DIR, f"tts_{int(time.time())}.mp3")
        tts.save(tmp)
        st.audio(open(tmp, "rb").read())
    except Exception:
        pass

# -----------------------
# UI: Sidebar - Offline management + debug
# -----------------------
online = True
try:
    requests.get("https://www.google.com", timeout=2.0)
except Exception:
    online = False

st.sidebar.markdown(f"*Network:* {'🟢 Online' if online else '🔴 Offline'}")
st.sidebar.markdown("Save a city for offline + inspect saved files below.")

# input to download city
dl_city = st.sidebar.text_input("City to download for offline", value="")
if st.sidebar.button("Download for offline"):
    if not dl_city.strip():
        st.sidebar.error("Enter a city name (e.g., Mysuru)")
    else:
        folder = make_dir_for_city(dl_city)
        # save meta.json with simple info
        meta = {
            "city": dl_city,
            "saved_at": time.time(),
            "note": "Saved by Download for offline button"
        }
        # prefer built-in offline info if exists
        key = dl_city.lower()
        if key in OFFLINE_CITIES:
            meta["info"] = OFFLINE_CITIES[key]["info"]
            meta["spots"] = OFFLINE_CITIES[key]["spots"]
        else:
            meta["info"] = f"{dl_city.title()} — basic offline summary."

        with open(os.path.join(folder, "meta.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)

        # download images (if Online + Unsplash key)
        saved = 0
        if online and UNSPLASH_ACCESS_KEY:
            urls = fetch_unsplash_urls(dl_city, n=4)
            for i, url in enumerate(urls, start=1):
                dest = os.path.join(folder, f"img_{i}.jpg")
                if download_image(url, dest):
                    saved += 1

        # geocode and create a saved map image (always create)
        lat, lon = (None, None)
        if online:
            lat, lon = geocode_city(dl_city)
        map_path = os.path.join(folder, "map.png")
        make_placeholder_map_image(dl_city, lat or 0.0, lon or 0.0, dest_path=map_path)

        st.sidebar.success(f"Saved '{dl_city}' → folder: {folder} (images: {saved}, map: map.png)")

# show list of saved city folders with debug info
st.sidebar.markdown("---")
st.sidebar.markdown("### Saved offline cities (folders)")
folders = sorted([d for d in os.listdir(CITIES_DIR) if os.path.isdir(os.path.join(CITIES_DIR, d))])
if not folders:
    st.sidebar.info("No saved cities yet. Use Download for offline.")
else:
    for f in folders:
        folder_path = os.path.join(CITIES_DIR, f)
        st.sidebar.markdown(f"- *{f}*")
        # list files inside
        files = sorted(os.listdir(folder_path))
        if files:
            st.sidebar.write(", ".join(files))
        else:
            st.sidebar.write("empty folder")

# -----------------------
# Main UI: chat-like input + show saved data
# -----------------------
st.markdown("## Test saved city display")
st.markdown("Type a city name that you've downloaded (or use a built-in sample like 'Mysuru'/'Bengaluru').")

city_query = st.text_input("Show offline data for city (type exact or partial name):", value="")

if city_query:
    # find best matching saved folder first
    key = safe_key(city_query)
    folder = os.path.join(CITIES_DIR, key)
    found_folder = None
    if os.path.isdir(folder):
        found_folder = folder
    else:
        # attempt fuzzy search among saved folders and built-in offline names
        for f in folders:
            if key in f:
                found_folder = os.path.join(CITIES_DIR, f)
                break
        # if still not found, check built-in offline data
        if not found_folder and city_query.lower() in OFFLINE_CITIES:
            st.info(f"City found in built-in offline DB but not saved to disk. Use sidebar Download for offline to save it.")
            found_folder = None

    if found_folder:
        st.success(f"Showing saved offline data: {found_folder}")
        # show meta.json
        meta_path = os.path.join(found_folder, "meta.json")
        if os.path.exists(meta_path):
            try:
                meta = json.load(open(meta_path, "r", encoding="utf-8"))
                st.markdown("*meta.json*")
                st.json(meta)
            except Exception as e:
                st.warning(f"Could not read meta.json: {e}")
        else:
            st.info("No meta.json found in folder.")

        # show images (exclude map.png)
        imgs = sorted([os.path.join(found_folder, fn) for fn in os.listdir(found_folder)
                       if fn.lower().endswith((".jpg", ".jpeg", ".png")) and fn.lower() != "map.png"])
        if imgs:
            st.markdown("### Saved images")
            cols = st.columns(min(3, len(imgs)))
            for i, p in enumerate(imgs):
                try:
                    with cols[i % len(cols)]:
                        st.image(Image.open(p), width='stretch')
                except Exception as e:
                    st.write("Could not open:", p, "-", e)
        else:
            st.info("No saved images in folder. (Unsplash images download requires UNSPLASH_ACCESS_KEY and being online when you clicked Download.)")

        # show saved map.png
        map_path = os.path.join(found_folder, "map.png")
        if os.path.exists(map_path):
            st.markdown("### Saved map (map.png)")
            try:
                st.image(Image.open(map_path), width='stretch')
            except Exception as e:
                st.warning(f"Map exists but could not be displayed: {e}")
        else:
            st.info("No map.png in folder. The download step always creates a placeholder map; if missing, please re-download the city.")
    else:
        # show built-in offline info if available
        if city_query.lower() in OFFLINE_CITIES:
            d = OFFLINE_CITIES[city_query.lower()]
            st.markdown(f"*Built-in offline info for {city_query.title()}*")
            st.write(d["info"])
            st.markdown("*Spots:*")
            for s in d["spots"]:
                st.write("-", s)
        else:
            st.error("City not saved offline and not found in built-in offline DB. Use the sidebar to Download for offline while online.")

st.markdown("---")
st.caption("This debug view shows exactly which files are saved for each downloaded city. If you still can't see your images or map, check the 'Saved offline cities' list on the left for the folder name and contents.")
