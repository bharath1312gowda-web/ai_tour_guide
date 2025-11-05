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
# Simple offline dataset
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
    # Add more cities here...
}

# --------------------------
# Helper functions for offline images
# --------------------------
def local_image_paths_for(city_name):
    """
    Looks in static/images/ for files matching city_name_1.jpg, city_name_2.jpg, ...
    Returns list of existing file paths (up to 6).
    """
    city
