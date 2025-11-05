import streamlit as st

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="AI Tour Guide",
    page_icon="🌍",
    layout="wide"
)

# =========================
# HEADER SECTION
# =========================
st.title("🌍 AI Tour Guide")
st.markdown("""
Welcome to your *AI-powered travel companion!*  
Plan your perfect trip with smart recommendations for attractions, food, and experiences — all tailored to your interests.
""")

# =========================
# MAIN SECTION (You can connect your logic here)
# =========================
st.markdown("---")
st.header("🧭 Plan Your Next Destination")

destination = st.text_input("Enter a destination (city or place):", placeholder="e.g., Mangalore, Mysore, Coorg")

if destination:
    st.success(f"Showing AI recommendations for *{destination}*...")
    # Add your AI logic or API here for attractions, restaurants, etc.
else:
    st.info("Enter a destination to begin your AI-guided journey!")

# =========================
# TOUR GUIDE INFORMATION
# =========================

# Data for guides
TOUR_GUIDES = {
    "adventure": {
        "icon": "🏔",
        "name": "Adventure Guide Alex",
        "description": "Loves outdoor activities, hiking, and thrilling experiences."
    },
    "culture": {
        "icon": "🎭",
        "name": "Cultural Guide Clara",
        "description": "Expert in history, art, and local traditions."
    },
    "foodie": {
        "icon": "🍜",
        "name": "Foodie Guide Frank",
        "description": "Food lover who knows all the best local eateries."
    },
    "family": {
        "icon": "👨‍👩‍👧",
        "name": "Family Guide Fiona",
        "description": "Perfect for kid-friendly and family-oriented activities."
    },
    "luxury": {
        "icon": "💎",
        "name": "Luxury Guide Leo",
        "description": "Focuses on premium experiences and exclusive destinations."
    }
}

# =========================
# FOOTER SECTIONS
# =========================

# --- SECTION 1: Your Personal Tour Guide Can ---
with st.container():
    st.markdown("---")
    st.markdown("## 🎯 Your Personal Tour Guide Can:")
    st.markdown("""
    - 🗺 *Proactively suggest* must-see attractions and hidden gems  
    - 🍽 *Recommend restaurants* and local food experiences  
    - 🚶 *Create personalized itineraries* based on your interests  
    - 💎 *Share local secrets* and insider tips  
    - 📸 *Suggest photo spots* and best times to visit  
    - 🎭 *Adapt to different travel styles* (adventure, luxury, family, etc.)  
    - 🌍 *Work with any city* worldwide  
    """)

# Add spacing between sections
st.markdown("<br><br>", unsafe_allow_html=True)

# --- SECTION 2: Meet Your Guides ---
with st.container():
    st.markdown("## 👨‍🏫 Meet Your Guides:")

    cols = st.columns(5)
    for i, (guide_type, guide_info) in enumerate(TOUR_GUIDES.items()):
        with cols[i]:
            st.markdown(
                f"""
                <div style="background-color:#f8f9fa; padding:15px; border-radius:15px; text-align:center; box-shadow:0px 2px 6px rgba(0,0,0,0.1);">
                    <h3>{guide_info['icon']} {guide_info['name']}</h3>
                    <p style="color:#555;">{guide_info['description']}</p>
                </div>
                """,
                unsafe_allow_html=True
            )

# =========================
# FOOTER MESSAGE
# =========================
st.markdown("---")
st.markdown("""
🌟 *AI Tour Guide* — Designed to make your journeys smarter and more memorable!  
Built with ❤ using Streamlit.
""")
