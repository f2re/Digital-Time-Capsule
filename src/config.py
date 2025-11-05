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

# ========== SELLER INFORMATION ==========
SELLER_NAME_RU = os.getenv('SELLER_NAME_RU', 'Самозанятый')
SELLER_NAME_EN = os.getenv('SELLER_NAME_EN', 'Self-employed')
SELLER_INN = os.getenv('SELLER_INN', '0000000000000')
SELLER_LOCATION_RU = os.getenv('SELLER_LOCATION_RU', 'Москва')
SELLER_LOCATION_EN = os.getenv('SELLER_LOCATION_EN', 'Moscow')

# ========== CONTACT INFORMATION ==========
SUPPORT_EMAIL = os.getenv('SUPPORT_EMAIL', 'support@example.com')
REFUND_EMAIL = os.getenv('REFUND_EMAIL', 'refunds@example.com')
SUPPORT_TELEGRAM = os.getenv('SUPPORT_TELEGRAM', 'BotUsername')
SUPPORT_TELEGRAM_URL = os.getenv('SUPPORT_TELEGRAM_URL', f'https://t.me/{SUPPORT_TELEGRAM}')  # For backward compatibility
SUPPORT_HOURS_RU = os.getenv('SUPPORT_HOURS_RU', 'Пн-Пт: 10:00-18:00 МСК')
SUPPORT_HOURS_EN = os.getenv('SUPPORT_HOURS_EN', 'Mon-Fri: 10:00-18:00 MSK')
WEBSITE_URL = os.getenv('WEBSITE_URL', 'https://yourwebsite.com')

# ========== LEGAL INFORMATION ==========
RETURN_DAYS = int(os.getenv('RETURN_DAYS', '14'))
RETURN_DAYS_PREMIUM = int(os.getenv('RETURN_DAYS_PREMIUM', '3'))
RESPONSE_TIME_HOURS = int(os.getenv('RESPONSE_TIME_HOURS', '24'))
DELIVERY_ACCURACY_MINUTES = int(os.getenv('DELIVERY_ACCURACY_MINUTES', '5'))

# ========== LEGAL REQUISITES (for backward compatibility) ==========
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
 SELECTING_IDEAS_CATEGORY, SELECTING_IDEA_TEMPLATE, EDITING_IDEA_CONTENT,
 EDITING_IDEA_DATE) = range(19)  # Add new state

# Subscription tiers
FREE_TIER = 'free'
PREMIUM_TIER = 'premium'

# Storage limits
FREE_STORAGE_LIMIT = int(os.getenv('FREE_STORAGE_LIMIT', str(100 * 1024 * 1024)))  # 100 MB
PREMIUM_STORAGE_LIMIT = int(os.getenv('PREMIUM_STORAGE_LIMIT', str(500 * 1024 * 1024)))  # 500 MB

# Time limits
FREE_TIME_LIMIT_DAYS = int(os.getenv('FREE_TIME_LIMIT_DAYS', '365'))
PREMIUM_TIME_LIMIT_DAYS = int(os.getenv('PREMIUM_TIME_LIMIT_DAYS', str(365 * 25)))  # 25 years

# Single capsule pricing (Stars, RUB, USD)
CAPSULE_PRICE_STARS = int(os.getenv('CAPSULE_PRICE_STARS', '4'))
CAPSULE_PRICE_RUB = float(os.getenv('CAPSULE_PRICE_RUB', '100'))  # 100 RUB
CAPSULE_PRICE_USD = float(os.getenv('CAPSULE_PRICE_USD', '1.2'))  # $1.20

# Capsule packs with progressive discounts - PRESERVING EXISTING CAPSULE_PACKS FUNCTIONALITY
# NOTE: Keeping low values for development/testing as in original
CAPSULE_PACKS = {
    'pack_3': {
        'price_stars': int(os.getenv('PACK_3_STARS', '1')),  # Development value
        'price_rub': float(os.getenv('PACK_3_RUB', '150')),  # 150 RUB
        'price_usd': float(os.getenv('PACK_3_USD', '1.50')),  # $1.50
        'count': 3,
        'discount': int(os.getenv('PACK_3_DISCOUNT', '17'))  # 17% discount
    },
    'pack_10': {
        'price_stars': int(os.getenv('PACK_10_STARS', '1')),  # Development value
        'price_rub': float(os.getenv('PACK_10_RUB', '510')),  # 510 RUB
        'price_usd': float(os.getenv('PACK_10_USD', '6.0')),  # $6.00
        'count': 10,
        'discount': int(os.getenv('PACK_10_DISCOUNT', '25'))  # 25% discount
    },
    'pack_25': {
        'price_stars': int(os.getenv('PACK_25_STARS', '1')),  # Development value
        'price_rub': float(os.getenv('PACK_25_RUB', '1275')),  # 1275 RUB
        'price_usd': float(os.getenv('PACK_25_USD', '15.0')),  # $15.00
        'count': 25,
        'discount': int(os.getenv('PACK_25_DISCOUNT', '35'))  # 35% discount
    },
    'pack_100': {
        'price_stars': int(os.getenv('PACK_100_STARS', '1')),  # Development value
        'price_rub': float(os.getenv('PACK_100_RUB', '4250')),  # 4250 RUB
        'price_usd': float(os.getenv('PACK_100_USD', '50.0')),  # $50.00
        'count': 100,
        'discount': int(os.getenv('PACK_100_DISCOUNT', '45'))  # 45% discount
    }
}

# Premium subscription pricing
PREMIUM_MONTH_STARS = int(os.getenv('PREMIUM_MONTH_STARS', '1'))  # Development value
PREMIUM_MONTH_RUB = float(os.getenv('PREMIUM_MONTH_RUB', '750'))  # 750 RUB
PREMIUM_MONTH_USD = float(os.getenv('PREMIUM_MONTH_USD', '9.0'))  # $9.00
PREMIUM_MONTH_CAPSULES = int(os.getenv('PREMIUM_MONTH_CAPSULES', '20'))

PREMIUM_YEAR_STARS = int(os.getenv('PREMIUM_YEAR_STARS', '1'))  # Development value
PREMIUM_YEAR_RUB = float(os.getenv('PREMIUM_YEAR_RUB', '7500'))  # 7500 RUB
PREMIUM_YEAR_USD = float(os.getenv('PREMIUM_YEAR_USD', '90.0'))  # $90.00
PREMIUM_YEAR_CAPSULES = int(os.getenv('PREMIUM_YEAR_CAPSULES', '240'))

# Capsule limits
FREE_CAPSULE_LIMIT = int(os.getenv('FREE_CAPSULE_LIMIT', '0'))
FREE_STARTER_CAPSULES = int(os.getenv('FREE_STARTER_CAPSULES', '3'))
PREMIUM_CAPSULE_LIMIT = int(os.getenv('PREMIUM_CAPSULE_LIMIT', '999999'))

# Supported content types
SUPPORTED_TYPES = ['text', 'photo', 'video', 'document', 'voice', 'audio']