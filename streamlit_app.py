import streamlit as st
import openai

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="AI Tour Guide",
    page_icon="🌍",
    layout="wide"
)

# =========================
# OPENAI API KEY
# =========================
# Make sure you set your API key in Streamlit Cloud secrets or replace below
openai.api_key = st.secrets.get("OPENAI_API_KEY", "your_api_key_here")

# =========================
# HEADER SECTION
# =========================
st.title("🌍 AI Tour Guide")
st.markdown("""
Welcome to your *AI-powered travel companion!*  
Plan your perfect trip with smart recommendations for attractions, food, and experiences — all tailored to your interests.
""")

# =========================
# USER INPUT
# =========================
st.markdown("---")
st.header("🧭 Plan Your Next Destination")

destination = st.text_input("Enter a destination (city or place):", placeholder="e.g., Mangalore, Mysore, Coorg")
style = st.selectbox("Choose your travel style:", ["Adventure", "Cultural", "Foodie", "Family", "Luxury"])

# =========================
# BUTTON TO GENERATE
# =========================
if st.button("✨ Generate Tour Plan"):
    if not destination.strip():
        st.warning("Please enter a destination first.")
    else:
        with st.spinner("Generating your AI travel guide..."):
            prompt = f"""
            You are an AI Tour Guide. Create a detailed and fun travel guide for {destination}.
            Focus on {style.lower()} style travel. Include:
            - Top 5 attractions with short descriptions
            - Local food and restaurant recommendations
            - Hidden gems or lesser-known experiences
            - 1-day sample itinerary
            - Short travel tips
            """

            try:
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=800,
                    temperature=0.8
                )

                guide_text = response["choices"][0]["message"]["content"]
                st.markdown("### 🗺 Your AI Tour Plan")
                st.markdown(guide_text)

            except Exception as e:
                st.error(f"❌ Error: {e}")
else:
    st.info("Enter your destination and click *Generate Tour Plan* to begin!")

# =========================
# INFORMATION SECTIONS
# =========================

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

st.markdown("<br>", unsafe_allow_html=True)

st.markdown("## 👨‍🏫 Meet Your Guides:")
cols = st.columns(5)
guides = [
    ("🏔 Adventure Guide Alex", "Loves outdoor activities, hiking, and thrilling experiences."),
    ("🎭 Cultural Guide Clara", "Expert in history, art, and local traditions."),
    ("🍜 Foodie Guide Frank", "Food expert who knows all the best local eateries."),
    ("👨‍👩‍👧 Family Guide Fiona", "Great with kids and family-friendly activities."),
    ("💎 Luxury Guide Leo", "Focuses on premium experiences and luxury travel."),
]
for i, (name, desc) in enumerate(guides):
    with cols[i]:
        st.markdown(
            f"""
            <div style="background-color:#f8f9fa; padding:15px; border-radius:15px; text-align:center; box-shadow:0px 2px 6px rgba(0,0,0,0.1);">
                <h3>{name}</h3>
                <p style="color:#555;">{desc}</p>
            </div>
            """,
            unsafe_allow_html=True
        )

st.markdown("---")
st.markdown("🌟 *AI Tour Guide* — Built with ❤ using Streamlit.")
