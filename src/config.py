# src/config.py

import os
import logging
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

# Logging configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Base assets directory
ASSETS_DIR = os.path.join(os.path.dirname(__file__), '..', 'assets')

# Menu images mapping
MENU_IMAGES = {
    'welcome': os.path.join(ASSETS_DIR, 'welcome.png'),
    'capsules': os.path.join(ASSETS_DIR, 'capsules.png'),
    'help': os.path.join(ASSETS_DIR, 'help.png'),
    'legal': os.path.join(ASSETS_DIR, 'legal.png'),
    'settings': os.path.join(ASSETS_DIR, 'settings.png'),
    'subscription': os.path.join(ASSETS_DIR, 'subscription.png'),
}

# Fallback image if specific not found
DEFAULT_IMAGE = os.path.join(ASSETS_DIR, MENU_IMAGES['welcome'])


# Environment variables
BOT_TOKEN = os.getenv('BOT_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///time_capsule.db')
MASTER_KEY = os.getenv('MASTER_KEY')
YANDEX_ACCESS_KEY = os.getenv('YANDEX_ACCESS_KEY')
YANDEX_SECRET_KEY = os.getenv('YANDEX_SECRET_KEY')
YANDEX_BUCKET_NAME = os.getenv('YANDEX_BUCKET_NAME')
YANDEX_REGION = os.getenv('YANDEX_REGION', 'ru-central1')
PAYMENT_PROVIDER_TOKEN = os.getenv('PAYMENT_PROVIDER_TOKEN')  # For Redsys/Stripe
ADMIN_IDS = [int(id.strip()) for id in os.getenv('ADMIN_IDS', '').split(',') if id.strip()]
SUPPORT_EMAIL = os.getenv('SUPPORT_EMAIL', 'support@example.com')
SUPPORT_TELEGRAM_URL = os.getenv('SUPPORT_TELEGRAM_URL', 'https://t.me/your_support_chat')
LEGAL_REQUISITES_RU = os.getenv('LEGAL_REQUISITES_RU', 'Реквизиты не указаны.')
LEGAL_REQUISITES_EN = os.getenv('LEGAL_REQUISITES_EN', 'Requisites not specified.')

# Validate configuration
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found in environment variables")

if not MASTER_KEY:
    MASTER_KEY = Fernet.generate_key().decode()
    logger.warning(f"Generated new MASTER_KEY: {MASTER_KEY}")
    logger.warning("Please add this to your .env file!")

# Initialize Fernet cipher
master_cipher = Fernet(MASTER_KEY.encode())

# Conversation states - ADDED NEW STATES FOR IDEAS FEATURE
(SELECTING_LANG, SELECTING_ACTION, SELECTING_CONTENT_TYPE, RECEIVING_CONTENT,
 SELECTING_TIME, SELECTING_DATE, SELECTING_RECIPIENT, PROCESSING_RECIPIENT,
 CONFIRMING_CAPSULE, VIEWING_CAPSULES, MANAGING_SUBSCRIPTION, MANAGING_SETTINGS,
 SELECTING_PAYMENT_METHOD, SELECTING_CURRENCY, MANAGING_LEGAL_INFO,
 SELECTING_IDEAS_CATEGORY, SELECTING_IDEA_TEMPLATE, EDITING_IDEA_CONTENT) = range(18)

# Subscription tiers
FREE_TIER = 'free'
PREMIUM_TIER = 'premium'

# Storage limits
FREE_STORAGE_LIMIT = 100 * 1024 * 1024  # 100 MB
PREMIUM_STORAGE_LIMIT = 500 * 1024 * 1024  # 500 MB

# Time limits
FREE_TIME_LIMIT_DAYS = 365
PREMIUM_TIME_LIMIT_DAYS = 365 * 25

# Single capsule pricing (Stars, RUB, USD)
# Note: USD minimum is 50 (cents = $0.50), RUB minimum is ~300 (kopecks = 3.00 RUB)
CAPSULE_PRICE_STARS = 4
CAPSULE_PRICE_RUB = 50.0  # ~$0.60 at current exchange rates
CAPSULE_PRICE_USD = 0.50  # Minimum allowed for USD

# Capsule packs with progressive discounts
CAPSULE_PACKS = {
    'pack_3': {
        'price_stars': 1,
        # 'price_stars': 10,
        'price_rub': 150,  # ~$1.60 at current exchange rates
        'price_usd': 1.50,  # Minimum reasonable for 3-pack
        'count': 3,
        'discount': 17
    },
    'pack_10': {
        'price_stars': 1,
        # 'price_stars': 30,
        'price_rub': 51,
        'price_usd': 0.6,
        'count': 10,
        'discount': 25
    },
    'pack_25': {
        'price_stars': 1,
        # 'price_stars': 65,
        'price_rub': 110.5,
        'price_usd': 1.2,
        'count': 25,
        'discount': 35
    },
    'pack_100': {
        'price_stars': 1,
        # 'price_stars': 220,
        'price_rub': 374,
        'price_usd': 3.8,
        'count': 100,
        'discount': 45
    }
}

# Premium subscription pricing
# PREMIUM_MONTH_STARS = 60
PREMIUM_MONTH_STARS = 1
PREMIUM_MONTH_RUB = 102
PREMIUM_MONTH_USD = 1.04
PREMIUM_MONTH_CAPSULES = 20

PREMIUM_YEAR_STARS = 1
# PREMIUM_YEAR_STARS = 600
PREMIUM_YEAR_RUB = 1020
PREMIUM_YEAR_USD = 10.42
PREMIUM_YEAR_CAPSULES = 240

# Capsule limits
FREE_CAPSULE_LIMIT = 0
FREE_STARTER_CAPSULES = 3
PREMIUM_CAPSULE_LIMIT = 999999

# Supported content types
SUPPORTED_TYPES = ['text', 'photo', 'video', 'document', 'voice', 'audio']