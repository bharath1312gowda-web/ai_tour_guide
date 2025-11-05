import os
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv

# -----------------------------
# 🔹 Load local .env (for testing)
# -----------------------------
load_dotenv()

# -----------------------------
# 🔹 Get API Key (works locally & on Streamlit Cloud)
# -----------------------------
api_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
if not api_key or api_key == "your_api_key_here":
    st.error("❌ Missing OpenAI API key. Please add it to .streamlit/secrets.toml or .env")
    st.stop()

# Initialize client
client = OpenAI(api_key=api_key)

# -----------------------------
# 🔹 Streamlit Page Config
# -----------------------------
st.set_page_config(page_title="AI Tour Guide 🌍", layout="centered")

st.title("🌍 AI Tour Guide")
st.caption("Your personal AI travel guide that proactively suggests amazing experiences!")

# -----------------------------
# 🔹 Sidebar for User Input
# -----------------------------
st.sidebar.header("🎯 Choose Your Guide")
guide_type = st.sidebar.selectbox(
    "Select Guide Type:",
    ["Adventure Guide Alex", "Cultural Guide Clara", "Foodie Guide Frank", "Family Guide Fiona", "Luxury Guide Leo"]
)

destination = st.sidebar.text_input("Enter Your Destination (e.g., Paris, Tokyo, Dubai, Bengaluru)")
user_interest = st.sidebar.text_area("Tell us your interests (e.g., beaches, temples, nightlife, street food)")

# -----------------------------
# 🔹 Information Section (separated)
# -----------------------------
st.markdown("### 🎒 Your Personal Tour Guide Can:")
st.markdown("""
- 🌍 *Proactively suggest* must-see attractions and hidden gems  
- 🍴 *Recommend restaurants* and local food experiences  
- 🗺 *Create personalized itineraries* based on your interests  
- 📸 *Suggest photo spots* and best times to visit  
- 🧭 *Adapt to travel styles* (adventure, luxury, family, etc.)  
- 🌐 *Work with any city worldwide*
""")

st.markdown("---")

st.markdown("### 🧑‍🤝‍🧑 Meet Your Guides:")
cols = st.columns(5)
with cols[0]:
    st.image("https://cdn-icons-png.flaticon.com/512/206/206864.png", width=50)
    st.write("*Adventure Guide Alex* — Loves outdoor activities, hiking, and thrilling experiences.")
with cols[1]:
    st.image("https://cdn-icons-png.flaticon.com/512/4140/4140048.png", width=50)
    st.write("*Cultural Guide Clara* — Expert in history, art, and local traditions.")
with cols[2]:
    st.image("https://cdn-icons-png.flaticon.com/512/2922/2922561.png", width=50)
    st.write("*Foodie Guide Frank* — Food expert who knows all the best local eateries.")
with cols[3]:
    st.image("https://cdn-icons-png.flaticon.com/512/2922/2922506.png", width=50)
    st.write("*Family Guide Fiona* — Great with kids and family-friendly adventures.")
with cols[4]:
    st.image("https://cdn-icons-png.flaticon.com/512/2922/2922510.png", width=50)
    st.write("*Luxury Guide Leo* — Focuses on premium and comfort travel.")

st.markdown("---")

# -----------------------------
# 🔹 AI Tour Suggestion Generator
# -----------------------------
if st.button("✨ Generate Tour Plan"):
    if not destination:
        st.warning("Please enter a destination to continue.")
    else:
        with st.spinner("Creating your personalized tour plan..."):
            prompt = f"""
            You are {guide_type}, an AI tour guide.
            Create a personalized travel guide for {destination}.
            The user is interested in {user_interest if user_interest else "general sightseeing"}.
            Include:
            - 3 must-see attractions
            - 2 local food experiences
            - 1 cultural or hidden gem recommendation
            - A short summary paragraph about the destination
            """
            
            try:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}]
                )
                result = response.choices[0].message.content
                st.success(f"Here’s your personalized tour plan for {destination}:")
                st.markdown(result)
            except Exception as e:
                st.error(f"⚠ Error: {str(e)}")

# -----------------------------
# 🔹 Footer
# -----------------------------
st.markdown("---")
st.caption("Made with ❤ by Bharath Gowda M | T John Institute of Technology")
