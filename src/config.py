# src/config.py
import os
import logging
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Logging configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Environment variables
BOT_TOKEN = os.getenv('BOT_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///time_capsule.db')
MASTER_KEY = os.getenv('MASTER_KEY')
YANDEX_ACCESS_KEY = os.getenv('YANDEX_ACCESS_KEY')
YANDEX_SECRET_KEY = os.getenv('YANDEX_SECRET_KEY')
YANDEX_BUCKET_NAME = os.getenv('YANDEX_BUCKET_NAME')
YANDEX_REGION = os.getenv('YANDEX_REGION', 'ru-central1')
PAYMENT_PROVIDER_TOKEN = os.getenv('PAYMENT_PROVIDER_TOKEN')

# Validate configuration
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found in environment variables")
if not MASTER_KEY:
    MASTER_KEY = Fernet.generate_key().decode()
    logger.warning(f"Generated new MASTER_KEY: {MASTER_KEY}")
    logger.warning("Please add this to your .env file!")

# Initialize Fernet cipher for key encryption
master_cipher = Fernet(MASTER_KEY.encode())

# Conversation states
(SELECTING_LANG, SELECTING_ACTION, SELECTING_CONTENT_TYPE, RECEIVING_CONTENT,
 SELECTING_TIME, SELECTING_DATE, SELECTING_RECIPIENT,
CONFIRMING_CAPSULE, VIEWING_CAPSULES, MANAGING_SUBSCRIPTION, MANAGING_SETTINGS) = range(11)

# Subscription tiers
FREE_TIER = 'free'
PREMIUM_TIER = 'premium'


# Storage limits (updated as per requirements)
FREE_STORAGE_LIMIT = 100 * 1024 * 1024  # 100 MB
PREMIUM_STORAGE_LIMIT = 500 * 1024 * 1024  # 500 MB

# Time limits
FREE_TIME_LIMIT_DAYS = 365  # 1 year
PREMIUM_TIME_LIMIT_DAYS = 365 * 25  # 25 years

# Single capsule pricing (unified for all content types)
CAPSULE_PRICE_STARS = 4
CAPSULE_PRICE_RUBLES = 6.8

# Capsule packs with progressive discounts
CAPSULE_PACKS = {
    'pack_3': {
        'price_stars': 10,
        'price_rubles': 17,
        'count': 3,
        'discount': 17
    },
    'pack_10': {
        'price_stars': 30,
        'price_rubles': 51,
        'count': 10,
        'discount': 25
    },
    'pack_25': {
        'price_stars': 65,
        'price_rubles': 110.5,
        'count': 25,
        'discount': 35
    },
    'pack_100': {
        'price_stars': 220,
        'price_rubles': 374,
        'count': 100,
        'discount': 45
    }
}

# Premium subscription pricing
PREMIUM_MONTH_STARS = 60
PREMIUM_MONTH_RUBLES = 102
PREMIUM_MONTH_CAPSULES = 20  # Included capsules per month

PREMIUM_YEAR_STARS = 600
PREMIUM_YEAR_RUBLES = 1020
PREMIUM_YEAR_CAPSULES = 240  # Included capsules per year (20*12)

# Legacy compatibility (can be removed after migration)
PREMIUM_SINGLE_PRICE = CAPSULE_PRICE_RUBLES  # For backward compatibility
PREMIUM_YEAR_PRICE = PREMIUM_YEAR_RUBLES
PREMIUM_SINGLE_STARS = CAPSULE_PRICE_STARS
PREMIUM_YEAR_STARS = PREMIUM_YEAR_STARS

# Capsule limits (free users need to buy, premium get included)
FREE_CAPSULE_LIMIT = 0  # Free users must purchase capsules
FREE_STARTER_CAPSULES = 3
PREMIUM_CAPSULE_LIMIT = 999999  # Effectively unlimited

# Supported content types
SUPPORTED_TYPES = ['text', 'photo', 'video', 'document', 'voice', 'audio']
