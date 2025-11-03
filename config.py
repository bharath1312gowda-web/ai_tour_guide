import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # API Keys
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    
    # App Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    
    # Feature Flags
    ENABLE_VOICE = True
    ENABLE_GPS = True
    ENABLE_OFFLINE = True
    
    # AI Settings
    AI_MODEL = "gpt-3.5-turbo"
    MAX_TOKENS = 1000
    TEMPERATURE = 0.7
    
    # Voice Settings
    VOICE_RATE = 150
    VOICE_VOLUME = 0.8
    
    # GPS Settings
    DEFAULT_LATITUDE = 40.7128
    DEFAULT_LONGITUDE = -74.0060
