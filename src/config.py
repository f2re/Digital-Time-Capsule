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

# Limits
FREE_CAPSULE_LIMIT = 3
FREE_STORAGE_LIMIT = 10 * 1024 * 1024  # 10 MB
FREE_TIME_LIMIT_DAYS = 365  # 1 year

PREMIUM_CAPSULE_LIMIT = 999999  # Unlimited
PREMIUM_STORAGE_LIMIT = 1024 * 1024 * 1024  # 1 GB
PREMIUM_TIME_LIMIT_DAYS = 365 * 25  # 25 years

# Pricing (in Telegram Stars and rubles)
PREMIUM_SINGLE_PRICE = 200  # rubles
PREMIUM_YEAR_PRICE = 400  # rubles
PREMIUM_SINGLE_STARS = 20  # Telegram Stars
PREMIUM_YEAR_STARS = 40  # Telegram Stars

# Supported content types
SUPPORTED_TYPES = ['text', 'photo', 'video', 'document', 'voice', 'audio']
