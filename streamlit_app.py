import streamlit as st
from openai import OpenAI
import json
import os

# Page configuration
st.set_page_config(
    page_title="AI Tour Guide",
    page_icon="🌍",
    layout="wide"
)

# Load offline data
@st.cache_data
def load_offline_data():
    try:
        with open('data/offline_data.json', 'r') as f:
            return json.load(f)
    except:
        return {"destinations": {}, "phrases": {}}

offline_data = load_offline_data()

def get_offline_response(prompt, destination, language):
    """Get offline response based on user query"""
    prompt_lower = prompt.lower()
    
    # If no specific destination is provided, use generic response
    if not destination:
        return get_generic_offline_response(language)
    
    # Check if it's one of our predefined destinations
    if destination in offline_data['destinations']:
        dest_info = offline_data['destinations'][destination]
        
        # Match query type and provide relevant offline info
        if any(word in prompt_lower for word in ['attraction', 'place', 'see', 'visit', 'tour']):
            return get_attractions_response(dest_info, language)
        elif any(word in prompt_lower for word in ['food', 'restaurant', 'eat', 'cuisine', 'meal']):
            return get_food_response(dest_info, language)
        elif any(word in prompt_lower for word in ['transport', 'get around', 'travel', 'bus', 'train', 'metro']):
            return get_transport_response(dest_info, language)
        elif any(word in prompt_lower for word in ['emergency', 'help', 'police', 'hospital', 'doctor']):
            return get_emergency_response(dest_info, language)
        elif any(word in prompt_lower for word in ['hotel', 'stay', 'accommodation', 'sleep']):
            return get_accommodation_response(dest_info, language)
        else:
            return get_general_info_response(dest_info, language)
    else:
        # For custom cities, provide general travel advice
        return get_custom_city_response(destination, prompt_lower, language)

def get_custom_city_response(city_name, prompt, language):
    """Provide responses for custom cities entered by users"""
    prompt_lower = prompt.lower()
    
    responses = {
        "en": {
            "attractions": f"**{city_name.title()} - Top Attractions**\n\nFor {city_name}, I recommend:\n• Researching popular landmarks and museums\n• Checking local tourism websites\n• Visiting historical sites\n• Exploring natural attractions\n\n💡 **Tip**: Use online travel guides or ask locals for the best places to visit!",
            "food": f"**{city_name.title()} - Local Food**\n\nIn {city_name}, you should try:\n• Local specialty dishes\n• Traditional restaurants\n• Street food markets\n• Regional cuisine\n\n💡 **Tip**: Ask locals for restaurant recommendations for authentic experiences!",
            "transport": f"**{city_name.title()} - Transportation**\n\nGetting around {city_name}:\n• Public transportation (buses, trains)\n• Taxis or ride-sharing services\n• Walking in city centers\n• Bike rentals if available\n\n💡 **Tip**: Check local transportation apps for routes and schedules!",
            "emergency": f"**{city_name.title()} - Emergency Information**\n\nGeneral emergency contacts:\n• Police: 112 (EU) or 911 (US/CA)\n• Ambulance: 112 (EU) or 911 (US/CA)\n• Fire: 112 (EU) or 911 (US/CA)\n\n🚨 **Important**: Learn local emergency numbers for {city_name}!",
            "general": f"**{city_name.title()} - Travel Guide**\n\nWelcome to {city_name}! As a popular travel destination, here are some general tips:\n• Research local customs and culture\n• Learn basic phrases in the local language\n• Check weather conditions before your trip\n• Be aware of local laws and regulations\n\n💡 For specific information about {city_name}, I recommend checking official tourism websites or travel guides."
        },
        "es": {
            "attractions": f"**{city_name.title()} - Principales Atracciones**\n\nPara {city_name}, recomiendo:\n• Investigar monumentos y museos populares\n• Consultar sitios web de turismo local\n• Visitar sitios históricos\n• Explorar atracciones naturales\n\n💡 **Consejo**: ¡Usa guías de viaje en línea o pregunta a los locales por los mejores lugares para visitar!",
            "food": f"**{city_name.title()} - Comida Local**\n\nEn {city_name}, deberías probar:\n• Platos especialidades locales\n• Restaurantes tradicionales\n• Mercados de comida callejera\n• Cocina regional\n\n💡 **Consejo**: ¡Pregunta a los locales por recomendaciones de restaurantes para experiencias auténticas!",
            "transport": f"**{city_name.title()} - Transporte**\n\nMoverse por {city_name}:\n• Transporte público (autobuses, trenes)\n• Taxis o servicios de ride-sharing\n• Caminar en centros urbanos\n• Alquiler de bicicletas si está disponible\n\n💡 **Consejo**: ¡Consulta aplicaciones de transporte local para rutas y horarios!",
            "emergency": f"**{city_name.title()} - Información de Emergencia**\n\nContactos de emergencia generales:\n• Policía: 112 (UE) o 911 (EEUU/CA)\n• Ambulancia: 112 (UE) o 911 (EEUU/CA)\n• Bomberos: 112 (UE) o 911 (EEUU/CA)\n\n🚨 **Importante**: ¡Aprende los números de emergencia locales para {city_name}!",
            "general": f"**{city_name.title()} - Guía de Viaje**\n\n¡Bienvenido a {city_name}! Como destino turístico popular, aquí hay algunos consejos generales:\n• Investiga costumbres y cultura local\n• Aprende frases básicas en el idioma local\n• Verifica las condiciones climáticas antes de tu viaje\n• Ten en cuenta las leyes y regulaciones locales\n\n💡 Para información específica sobre {city_name}, recomiendo consultar sitios web de turismo oficiales o guías de viaje."
        },
        "fr": {
            "attractions": f"**{city_name.title()} - Principales Attractions**\n\nPour {city_name}, je recommande :\n• Rechercher les monuments et musées populaires\n• Consulter les sites Web touristiques locaux\n• Visiter les sites historiques\n• Explorer les attractions naturelles\n\n💡 **Astuce** : Utilisez des guides de voyage en ligne ou demandez aux habitants les meilleurs endroits à visiter !",
            "food": f"**{city_name.title()} - Nourriture Locale**\n\nÀ {city_name}, vous devriez essayer :\n• Plats spécialités locales\n• Restaurants traditionnels\n• Marchés de rue\n• Cuisine régionale\n\n💡 **Astuce** : Demandez aux habitants des recommandations de restaurants pour des expériences authentiques !",
            "transport": f"**{city_name.title()} - Transport**\n\nSe déplacer à {city_name} :\n• Transport public (bus, trains)\n• Taxis ou services de covoiturage\n• Marche dans les centres-villes\n• Location de vélos si disponible\n\n💡 **Astuce** : Consultez les applications de transport local pour les itinéraires et les horaires !",
            "emergency": f"**{city_name.title()} - Informations d'Urgence**\n\nContacts d'urgence généraux :\n• Police : 112 (UE) ou 911 (États-Unis/Canada)\n• Ambulance : 112 (UE) ou 911 (États-Unis/Canada)\n• Pompiers : 112 (UE) ou 911 (États-Unis/Canada)\n\n🚨 **Important** : Apprenez les numéros d'urgence locaux pour {city_name} !",
            "general": f"**{city_name.title()} - Guide de Voyage**\n\nBienvenue à {city_name} ! En tant que destination touristique populaire, voici quelques conseils généraux :\n• Recherchez les coutumes et la culture locales\n• Apprenez des phrases de base dans la langue locale\n• Vérifiez les conditions météorologiques avant votre voyage\n• Soyez conscient des lois et réglementations locales\n\n💡 Pour des informations spécifiques sur {city_name}, je recommande de consulter les sites Web touristiques officiels ou les guides de voyage."
        },
        "ja": {
            "attractions": f"**{city_name.title()} - 主なアトラクション**\n\n{city_name}については、以下をお勧めします：\n• 人気のランドマークや博物館を調査する\n• 現地の観光サイトを確認する\n• 史跡を訪れる\n• 自然のアトラクションを探索する\n\n💡 **ヒント**：オンライン旅行ガイドを利用するか、地元の人に最高の場所を聞いてみてください！",
            "food": f"**{city_name.title()} - 地元の食べ物**\n\n{city_name}では、以下を試すべきです：\n• 地元の特産料理\n• 伝統的なレストラン\n• 屋台市場\n• 地域の料理\n\n💡 **ヒント**：本格的な体験のために、地元の人にレストランのおすすめを聞いてみてください！",
            "transport": f"**{city_name.title()} - 交通手段**\n\n{city_name}の移動方法：\n• 公共交通機関（バス、電車）\n• タクシーまたはライドシェアサービス\n• 市街地の散歩\n• 利用可能な場合は自転車レンタル\n\n💡 **ヒント**：ルートとスケジュールについては、現地の交通アプリを確認してください！",
            "emergency": f"**{city_name.title()} - 緊急情報**\n\n一般的な緊急連絡先：\n• 警察：112（EU）または911（米国/カナダ）\n• 救急車：112（EU）または911（米国/カナダ）\n• 消防：112（EU）または911（米国/カナダ）\n\n🚨 **重要**：{city_name}の現地の緊急番号を学んでください！",
            "general": f"**{city_name.title()} - 旅行ガイド**\n\n{city_name}へようこそ！人気の旅行先として、以下は一般的なヒントです：\n• 現地の習慣と文化を調査する\n• 現地の言語で基本的なフレーズを学ぶ\n• 旅行前に天候条件を確認する\n• 現地の法律と規制に注意する\n\n💡 {city_name}に関する具体的な情報については、公式の観光サイトや旅行ガイドを確認することをお勧めします。"
        },
        "zh": {
            "attractions": f"**{city_name.title()} - 主要景点**\n\n对于{city_name}，我推荐：\n• 研究热门地标和博物馆\n• 查看当地旅游网站\n• 参观历史遗址\n• 探索自然景点\n\n💡 **提示**：使用在线旅行指南或询问当地人最佳游览地点！",
            "food": f"**{city_name.title()} - 当地美食**\n\n在{city_name}，您应该尝试：\n• 当地特色菜肴\n• 传统餐厅\n• 街头小吃市场\n• 区域美食\n\n💡 **提示**：向当地人询问餐厅推荐以获得真实体验！",
            "transport": f"**{city_name.title()} - 交通方式**\n\n在{city_name}出行：\n• 公共交通（巴士、火车）\n• 出租车或拼车服务\n• 在市中心步行\n• 如有可用则租用自行车\n\n💡 **提示**：查看当地交通应用程序了解路线和时间表！",
            "emergency": f"**{city_name.title()} - 紧急信息**\n\n一般紧急联系人：\n• 警察：112（欧盟）或911（美国/加拿大）\n• 救护车：112（欧盟）或911（美国/加拿大）\n• 消防：112（欧盟）或911（美国/加拿大）\n\n🚨 **重要**：学习{city_name}的当地紧急号码！",
            "general": f"**{city_name.title()} - 旅行指南**\n\n欢迎来到{city_name}！作为热门旅游目的地，以下是一些一般提示：\n• 研究当地风俗文化\n• 学习当地语言的基本短语\n• 旅行前查看天气状况\n• 注意当地法律法规\n\n💡 关于{city_name}的具体信息，我建议查看官方旅游网站或旅行指南。"
        }
    }
    
    lang_responses = responses.get(language, responses["en"])
    
    if any(word in prompt for word in ['attraction', 'place', 'see', 'visit', 'tour']):
        return lang_responses["attractions"]
    elif any(word in prompt for word in ['food', 'restaurant', 'eat', 'cuisine', 'meal']):
        return lang_responses["food"]
    elif any(word in prompt for word in ['transport', 'get around', 'travel', 'bus', 'train', 'metro']):
        return lang_responses["transport"]
    elif any(word in prompt for word in ['emergency', 'help', 'police', 'hospital', 'doctor']):
        return lang_responses["emergency"]
    else:
        return lang_responses["general"]

def get_generic_offline_response(language):
    """Generic response when no destination is selected"""
    responses = {
        "en": "🌍 **Welcome to AI Tour Guide!**\n\nPlease enter any city name in the sidebar to get travel information about:\n• Top attractions\n• Local food\n• Transportation\n• Emergency contacts\n• Travel tips\n\nYou can ask about any city worldwide!",
        "es": "🌍 **¡Bienvenido a AI Tour Guide!**\n\nIngresa cualquier nombre de ciudad en la barra lateral para obtener información de viaje sobre:\n• Principales atracciones\n• Comida local\n• Transporte\n• Contactos de emergencia\n• Consejos de viaje\n\n¡Puedes preguntar sobre cualquier ciudad del mundo!",
        "fr": "🌍 **Bienvenue dans AI Tour Guide !**\n\nEntrez n'importe quel nom de ville dans la barre latérale pour obtenir des informations de voyage sur :\n• Principales attractions\n• Nourriture locale\n• Transport\n• Contacts d'urgence\n• Conseils de voyage\n\nVous pouvez vous renseigner sur n'importe quelle ville dans le monde !",
        "ja": "🌍 **AI Tour Guideへようこそ！**\n\nサイドバーに任意の都市名を入力して、以下の旅行情報を入手してください：\n• 主なアトラクション\n• 地元の食べ物\n• 交通手段\n• 緊急連絡先\n• 旅行のヒント\n\n世界中のどの都市についても質問できます！",
        "zh": "🌍 **欢迎使用 AI Tour Guide！**\n\n在侧边栏输入任何城市名称以获取有关以下旅行信息：\n• 主要景点\n• 当地美食\n• 交通方式\n• 紧急联系人\n• 旅行提示\n\n您可以询问世界上的任何城市！"
    }
    return responses.get(language, responses["en"])

def get_attractions_response(dest_info, language):
    """Get attractions information for predefined cities"""
    attractions = "\n".join([f"🏛️ {attr}" for attr in dest_info.get('attractions', [])])
    tips = "\n".join([f"💡 {tip}" for tip in dest_info.get('tips', [])[:3]])
    
    responses = {
        "en": f"**{dest_info['name']} - Top Attractions**\n\n{attractions}\n\n**Travel Tips:**\n{tips}",
        "es": f"**{dest_info['name']} - Principales Atracciones**\n\n{attractions}\n\n**Consejos de Viaje:**\n{tips}",
        "fr": f"**{dest_info['name']} - Principales Attractions**\n\n{attractions}\n\n**Conseils de Voyage:**\n{tips}",
        "ja": f"**{dest_info['name']} - 主なアトラクション**\n\n{attractions}\n\n**旅行のヒント:**\n{tips}",
        "zh": f"**{dest_info['name']} - 主要景点**\n\n{attractions}\n\n**旅行提示:**\n{tips}"
    }
    return responses.get(language, responses["en"])

def get_food_response(dest_info, language):
    """Get food information for predefined cities"""
    food_items = "\n".join([f"🍽️ {dish}" for dish in dest_info.get('food', {}).get('popular_dishes', [])])
    tips = dest_info.get('food', {}).get('dining_tips', [])
    dining_tips = "\n".join([f"💡 {tip}" for tip in tips]) if tips else "• Try local restaurants for authentic experience"
    
    responses = {
        "en": f"**{dest_info['name']} - Local Food**\n\n**Popular Dishes:**\n{food_items}\n\n**Dining Tips:**\n{dining_tips}",
        "es": f"**{dest_info['name']} - Comida Local**\n\n**Platos Populares:**\n{food_items}\n\n**Consejos Gastronómicos:**\n{dining_tips}",
        "fr": f"**{dest_info['name']} - Nourriture Locale**\n\n**Plats Populaires:**\n{food_items}\n\n**Conseils de Restaurant:**\n{dining_tips}",
        "ja": f"**{dest_info['name']} - 地元の食べ物**\n\n**人気料理:**\n{food_items}\n\n**食事のヒント:**\n{dining_tips}",
        "zh": f"**{dest_info['name']} - 当地美食**\n\n**热门菜肴:**\n{food_items}\n\n**用餐提示:**\n{dining_tips}"
    }
    return responses.get(language, responses["en"])

def get_transport_response(dest_info, language):
    """Get transportation information for predefined cities"""
    transport = dest_info.get('transportation', {})
    transport_info = "\n".join([f"🚗 {key.replace('_', ' ').title()}: {value}" for key, value in transport.items()])
    
    responses = {
        "en": f"**{dest_info['name']} - Transportation**\n\n{transport_info}",
        "es": f"**{dest_info['name']} - Transporte**\n\n{transport_info}",
        "fr": f"**{dest_info['name']} - Transport**\n\n{transport_info}",
        "ja": f"**{dest_info['name']} - 交通手段**\n\n{transport_info}",
        "zh": f"**{dest_info['name']} - 交通方式**\n\n{transport_info}"
    }
    return responses.get(language, responses["en"])

def get_emergency_response(dest_info, language):
    """Get emergency information for predefined cities"""
    emergency = dest_info.get('emergency', {})
    emergency_info = "\n".join([f"📞 {key.replace('_', ' ').title()}: **{value}**" for key, value in emergency.items()])
    
    responses = {
        "en": f"**{dest_info['name']} - Emergency Contacts**\n\n{emergency_info}\n\n🚨 In case of emergency, stay calm and describe your location clearly.",
        "es": f"**{dest_info['name']} - Contactos de Emergencia**\n\n{emergency_info}\n\n🚨 En caso de emergencia, mantén la calma y describe tu ubicación claramente.",
        "fr": f"**{dest_info['name']} - Contacts d'Urgence**\n\n{emergency_info}\n\n🚨 En cas d'urgence, restez calme et décrivez clairement votre emplacement.",
        "ja": f"**{dest_info['name']} - 緊急連絡先**\n\n{emergency_info}\n\n🚨 緊急時は落ち着いて、自分の場所を明確に説明してください。",
        "zh": f"**{dest_info['name']} - 紧急联系人**\n\n{emergency_info}\n\n🚨 遇到紧急情况时，请保持冷静并清楚描述您的位置。"
    }
    return responses.get(language, responses["en"])

def get_accommodation_response(dest_info, language):
    """Get accommodation information for predefined cities"""
    tips = "\n".join([f"🏨 {tip}" for tip in dest_info.get('tips', []) if any(word in tip.lower() for word in ['hotel', 'stay', 'accommodation', 'sleep'])])
    if not tips:
        tips = "• Book in advance during peak season\n• Read recent reviews before booking\n• Consider location proximity to attractions"
    
    responses = {
        "en": f"**{dest_info['name']} - Accommodation Tips**\n\n{tips}",
        "es": f"**{dest_info['name']} - Consejos de Alojamiento**\n\n{tips}",
        "fr": f"**{dest_info['name']} - Conseils d'Hébergement**\n\n{tips}",
        "ja": f"**{dest_info['name']} - 宿泊のヒント**\n\n{tips}",
        "zh": f"**{dest_info['name']} - 住宿提示**\n\n{tips}"
    }
    return responses.get(language, responses["en"])

def get_general_info_response(dest_info, language):
    """Get general destination information for predefined cities"""
    basic_info = dest_info.get('basic_info', 'No additional information available.')
    tips = "\n".join([f"💡 {tip}" for tip in dest_info.get('tips', [])[:3]])
    
    responses = {
        "en": f"**{dest_info['name']}**\n\n{basic_info}\n\n**Quick Tips:**\n{tips}",
        "es": f"**{dest_info['name']}**\n\n{basic_info}\n\n**Consejos Rápidos:**\n{tips}",
        "fr": f"**{dest_info['name']}**\n\n{basic_info}\n\n**Conseils Rapides:**\n{tips}",
        "ja": f"**{dest_info['name']}**\n\n{basic_info}\n\n**簡単なヒント:**\n{tips}",
        "zh": f"**{dest_info['name']}**\n\n{basic_info}\n\n**快速提示:**\n{tips}"
    }
    return responses.get(language, responses["en"])

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! I'm your AI tour guide. How can I help you today?"}
    ]
if 'destination' not in st.session_state:
    st.session_state.destination = ''
if 'language' not in st.session_state:
    st.session_state.language = 'en'
if 'api_key_configured' not in st.session_state:
    st.session_state.api_key_configured = False

# Sidebar
with st.sidebar:
    st.title("🌍 AI Tour Guide")
    
    # City Input (User can enter ANY city)
    st.subheader("🏙️ Enter Any City")
    city_input = st.text_input("City Name", 
                              placeholder="e.g., Rome, Dubai, Bangkok, Sydney...",
                              help="Enter any city in the world!")
    
    if city_input:
        st.session_state.destination = city_input.lower().strip()
        st.success(f"✅ City set to: {city_input.title()}")
    
    # Quick City Suggestions
    st.subheader("💡 Popular Cities")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Paris", use_container_width=True):
            st.session_state.destination = "paris"
        if st.button("Tokyo", use_container_width=True):
            st.session_state.destination = "tokyo"
    
    with col2:
        if st.button("New York", use_container_width=True):
            st.session_state.destination = "newyork"
        if st.button("London", use_container_width=True):
            st.session_state.destination = "london"
    
    # Language Selection
    st.subheader("🌐 Language")
    language = st.selectbox("Select Language", 
                           ["en", "es", "fr", "ja", "zh"],
                           format_func=lambda x: {
                               "en": "🇺🇸 English",
                               "es": "🇪🇸 Spanish", 
                               "fr": "🇫🇷 French",
                               "ja": "🇯🇵 Japanese",
                               "zh": "🇨🇳 Chinese"
                           }[x])
    st.session_state.language = language
    
    # Quick Actions
    st.subheader("⚡ Quick Actions")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🗺️ Attractions", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": "What are the top attractions here?"})
        if st.button("🍽️ Food", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": "Recommend local food and restaurants"})
    
    with col2:
        if st.button("🚇 Transport", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": "How to get around?"})
        if st.button("🚨 Emergency", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": "Emergency contacts and information"})

    # API Key Configuration (Hidden in expander)
    with st.expander("🔧 Developer Settings"):
        st.info("Configure API key for AI features")
        openai_api_key = st.text_input("OpenAI API Key", type="password", 
                                      help="Get your API key from https://platform.openai.com")
        if openai_api_key:
            st.session_state.api_key_configured = True
            st.session_state.openai_api_key = openai_api_key
            st.success("✅ API key configured!")
        else:
            st.session_state.api_key_configured = False
            if hasattr(st.session_state, 'openai_api_key'):
                del st.session_state.openai_api_key
            st.warning("⚠️ AI features disabled without API key")

# Main Chat Interface
st.title("🌍 AI Tour Guide")
st.markdown("Your intelligent travel companion for **any city worldwide**!")

# Display current city
if st.session_state.destination:
    current_city = st.session_state.destination.title()
    st.info(f"🗺️ Currently exploring: **{current_city}**")
else:
    st.warning("🌍 Please enter a city name in the sidebar to get started!")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask about travel destinations, tips, or recommendations..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Display assistant response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        # Check if API key is available
        openai_api_key = st.session_state.get('openai_api_key', '')
        
        if not openai_api_key:
            # Use offline mode
            full_response = get_offline_response(prompt, st.session_state.destination, st.session_state.language)
            message_placeholder.markdown(full_response)
        else:
            try:
                # Initialize OpenAI client
                client = OpenAI(api_key=openai_api_key)
                
                # Prepare messages for OpenAI with city context
                system_message = f"You are a friendly, knowledgeable tour guide. Respond in {st.session_state.language} language. The user is asking about {st.session_state.destination.title()}. Be helpful and provide practical travel advice."
                
                messages_for_api = [
                    {"role": "system", "content": system_message}
                ] + st.session_state.messages
                
                # Get AI response
                stream = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages_for_api,
                    stream=True,
                    max_tokens=1000,
                    temperature=0.7
                )
                
                # Stream the response
                for chunk in stream:
                    if chunk.choices[0].delta.content is not None:
                        full_response += chunk.choices[0].delta.content
                        message_placeholder.markdown(full_response + "▌")
                
                message_placeholder.markdown(full_response)
                
            except Exception as e:
                # Fallback to offline response
                full_response = get_offline_response(prompt, st.session_state.destination, st.session_state.language)
                message_placeholder.markdown(full_response)
        
        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": full_response})

# Footer
st.markdown("---")
st.markdown("### 💡 How to Use")
st.markdown("""
1. **Enter any city name** in the sidebar
2. **Choose your preferred language**
3. **Ask questions** about attractions, food, transport, etc.
4. **Use quick actions** for common queries
5. **Configure API key** for enhanced AI features
""")

st.markdown("### 🌟 Features")
st.markdown("""
- **Any city worldwide** - Not limited to predefined cities
- **Multi-language support** - English, Spanish, French, Japanese, Chinese
- **Quick actions** - One-click common questions
- **Offline mode** - Works without API key
- **AI-powered** - Enhanced responses with API key
""")
