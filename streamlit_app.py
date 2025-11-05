import os
import streamlit as st
from PIL import Image

# --------------------------
# Config
# --------------------------
st.set_page_config(page_title="AI Tour Guide (Offline)", layout="wide")
st.title("🗺 AI Tour Guide — Offline Mode")
st.caption("Demo / offline version — uses local images and preset suggestions.")

# --------------------------
# Simple offline dataset (add more entries here)
# --------------------------
OFFLINE_DATA = {
    "mangalore": {
        "places": [
            {"name": "Panambur Beach", "desc": "Popular beach with camel rides and sunsets."},
            {"name": "Kadri Manjunath Temple", "desc": "Ancient temple with beautiful architecture."},
            {"name": "Sultan Battery", "desc": "Historic watchtower with coastal views."}
        ],
        "food": [
            {"name": "Neer Dosa", "desc": "Light rice crepe, a local specialty."},
            {"name": "Mangalore Fish Curry", "desc": "Spicy and tangy coastal curry."}
        ],
        "culture": [
            {"name": "Yakshagana Performance", "desc": "Traditional dance-drama of Karnataka."}
        ],
        "hotels": [
            {"name": "Seaside Resort", "desc": "Comfortable stay near the beach."}
        ]
    },
    "bengaluru": {
        "places": [
            {"name": "Cubbon Park", "desc": "Large green park in the city center."},
            {"name": "Bangalore Palace", "desc": "Historic palace with Tudor-style architecture."},
            {"name": "Lalbagh Botanical Garden", "desc": "Famous botanical garden with glasshouse."}
        ],
        "food": [
            {"name": "Idli & Vada", "desc": "Classic South Indian breakfast."},
            {"name": "Street Biryani", "desc": "Local biryani spots in the city."}
        ],
        "culture": [
            {"name": "Rangashankara", "desc": "Popular theatre for local plays."}
        ],
        "hotels": [
            {"name": "City Comfort Hotel", "desc": "Central location and good service."}
        ]
    }
}

# --------------------------
# Helpers
# --------------------------
def local_image_paths_for(city_name):
    city = city_name.lower().replace(" ", "")
    base_dir = os.path.join("static", "images")
    paths = []
    if not os.path.isdir(base_dir):
        return paths
    for i in range(1, 7):
        for ext in ("jpg", "jpeg", "png", "webp"):
            fname = f"{city}_{i}.{ext}"
            fpath = os.path.join(base_dir, fname)
            if os.path.exists(fpath):
                paths.append(fpath)
                break
    return paths

def show_local_images(paths):
    if not paths:
        st.info("No local images found for this destination. Add images to static/images/ named cityname_1.jpg, cityname_2.jpg, ...")
        return
    cols = st.columns(min(3, len(paths)))
    for i, p in enumerate(paths):
        try:
            img = Image.open(p)
            with cols[i % len(cols)]:
                st.image(img, use_column_width=True)
        except Exception as e:
            st.error(f"Failed to load image {p}: {e}")

# --------------------------
# Sidebar controls and popular buttons
# --------------------------
with st.sidebar:
    st.header("Search (Offline)")
    city_input = st.text_input("Enter destination (e.g., Mangalore, Bengaluru):")
    category = st.selectbox("Explore", ["Places", "Food", "Culture", "Hotels"])
    st.markdown("---")
    st.write("Popular (click to fill):")
    if st.button("Mangalore"):
        city_input = "mangalore"
    if st.button("Bengaluru"):
        city_input = "bengaluru"
    if st.button("Add sample city"):
        # quick demo: show sample city without editing code
        city_input = "mangalore"
    st.markdown("---")
    st.write("Local images folder: static/images/ - name like mangalore_1.jpg")

# Keep city_input consistent if set by buttons
# (streamlit text_input won't update automatically from button assignment,
# so reassign to a session_state value)
if "city_value" not in st.session_state:
    st.session_state.city_value = city_input
else:
    # update only when user typed or button clicked
    if city_input and city_input != st.session_state.city_value:
        st.session_state.city_value = city_input

city = st.session_state.city_value

# --------------------------
# Main content (always shows something)
# --------------------------
if not city:
    st.info("Welcome! Try clicking a popular city on the sidebar or type a destination.")
    # show a quick sample card grid so page isn't empty
    st.markdown("### Example: Quick Look")
    for sample_city in ["Mangalore", "Bengaluru"]:
        st.subheader(sample_city)
        st.write("Click the city button in the sidebar to view offline suggestions and images.")
else:
    st.header(f"{city.title()} — Offline Suggestions")
    data = OFFLINE_DATA.get(city.lower())
    if data:
        cat_key = category.lower()
        items = data.get(cat_key, [])
        if items:
            for item in items:
                st.subheader(item["name"])
                st.write(item["desc"])
        else:
            st.info(f"No {category} data available for {city.title()} in offline dataset.")
    else:
        st.warning("This destination is not in the offline database. You can add it to OFFLINE_DATA in the script.")

    st.markdown("---")
    st.markdown("### 📸 Local Images")
    img_paths = local_image_paths_for(city)
    show_local_images(img_paths)

    st.markdown("---")
    st.markdown("### 🗺 Offline Map / Location")
    st.info("Interactive online maps are disabled in offline mode.")
    # show local static map image if exists
    map_local_path = os.path.join("static", "maps", f"{city.lower()}_map.png")
    if os.path.exists(map_local_path):
        try:
            st.image(map_local_path, use_column_width=True)
        except Exception as e:
            st.error("Local map image found but couldn't be displayed.")
    else:
        st.write("No local map image found. To show a map offline place a file at:")
        st.code(f"static/maps/{city.lower()}_map.png")

# --------------------------
# End (footer removed)
# --------------------------
