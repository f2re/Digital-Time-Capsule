#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Digital Time Capsule - Telegram Bot
Full-featured time capsule bot with encryption, S3 storage, and payments
"""

import os
import logging
import uuid
import asyncio
from datetime import datetime, timedelta
from io import BytesIO
from typing import Optional, Dict, Any

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from cryptography.fernet import Fernet
from dotenv import load_dotenv

from sqlalchemy import (
    create_engine, MetaData, Table, Column, Integer, String,
    DateTime, ForeignKey, Boolean, BigInteger, Text, select,
    insert, update, and_, LargeBinary, Float
)
from sqlalchemy.exc import SQLAlchemyError

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, 
    LabeledPrice, Message, User, Chat
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ConversationHandler, MessageHandler, filters,
    ContextTypes, PreCheckoutQueryHandler
)
from telegram.error import TelegramError

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from dateutil.relativedelta import relativedelta

# ============================================================================
# CONFIGURATION & LOGGING
# ============================================================================

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Environment variables
BOT_TOKEN = os.getenv('BOT_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///time_capsule.db')
MASTER_KEY = os.getenv('MASTER_KEY')  # For encrypting file keys
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

# ============================================================================
# CONSTANTS
# ============================================================================

# Conversation states
(SELECTING_ACTION, SELECTING_CONTENT_TYPE, RECEIVING_CONTENT,
 SELECTING_TIME, SELECTING_DATE, SELECTING_RECIPIENT,
 CONFIRMING_CAPSULE, VIEWING_CAPSULES, MANAGING_SUBSCRIPTION) = range(9)

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

# ============================================================================
# DATABASE SETUP
# ============================================================================

engine = create_engine(DATABASE_URL, echo=False)
metadata = MetaData()

# Users table
users = Table('users', metadata,
    Column('id', Integer, primary_key=True),
    Column('telegram_id', BigInteger, unique=True, nullable=False, index=True),
    Column('username', String(255)),
    Column('first_name', String(255)),
    Column('language_code', String(10), default='ru'),
    Column('subscription_status', String(50), default='free'),
    Column('subscription_expires', DateTime, nullable=True),
    Column('created_at', DateTime, default=datetime.utcnow),
    Column('total_storage_used', BigInteger, default=0),
    Column('capsule_count', Integer, default=0)
)

# Capsules table
capsules = Table('capsules', metadata,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id'), nullable=False),
    Column('capsule_uuid', String(36), unique=True, nullable=False, index=True),
    Column('content_type', String(50), nullable=False),
    Column('content_text', Text, nullable=True),
    Column('file_key', LargeBinary, nullable=True),  # Encrypted file key
    Column('s3_key', String(500), nullable=True),
    Column('file_size', BigInteger, default=0),
    Column('recipient_type', String(50), nullable=False),  # 'self', 'user', 'group'
    Column('recipient_id', BigInteger, nullable=True),
    Column('delivery_time', DateTime, nullable=False),
    Column('created_at', DateTime, default=datetime.utcnow),
    Column('delivered', Boolean, default=False),
    Column('delivered_at', DateTime, nullable=True),
    Column('message', Text, nullable=True)  # Optional message with the capsule
)

# Payments table
payments = Table('payments', metadata,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id'), nullable=False),
    Column('payment_type', String(50), nullable=False),  # 'stars', 'provider'
    Column('amount', Float, nullable=False),
    Column('currency', String(10), nullable=False),
    Column('subscription_type', String(50), nullable=False),  # 'single', 'yearly'
    Column('payment_id', String(255), unique=True, nullable=False),
    Column('successful', Boolean, default=False),
    Column('created_at', DateTime, default=datetime.utcnow)
)

metadata.create_all(engine)

# ============================================================================
# S3 CLIENT SETUP
# ============================================================================

def get_s3_client():
    """Initialize and return S3 client for Yandex Object Storage"""
    try:
        return boto3.client(
            service_name='s3',
            endpoint_url='https://storage.yandexcloud.net',
            aws_access_key_id=YANDEX_ACCESS_KEY,
            aws_secret_access_key=YANDEX_SECRET_KEY,
            region_name=YANDEX_REGION,
            config=Config(signature_version='s3v4')
        )
    except Exception as e:
        logger.error(f"Failed to create S3 client: {e}")
        return None

# ============================================================================
# TRANSLATIONS
# ============================================================================

TRANSLATIONS = {
    'ru': {
        'start_welcome': '🕰 Добро пожаловать в Digital Time Capsule!\n\nЯ помогу вам создать капсулу времени - отправить сообщение в будущее себе, другу или группе!',
        'main_menu': '📋 Главное меню',
        'create_capsule': '✨ Создать капсулу',
        'my_capsules': '📦 Мои капсулы',
        'subscription': '💎 Подписка',
        'settings': '⚙️ Настройки',
        'help': '❓ Помощь',
        'language': '🌐 Язык: Русский',
        'select_content_type': '📝 Выберите тип содержимого капсулы:',
        'content_text': '📄 Текст',
        'content_photo': '🖼 Фото',
        'content_video': '🎥 Видео',
        'content_document': '📎 Документ',
        'content_voice': '🎤 Голосовое сообщение',
        'back': '◀️ Назад',
        'cancel': '❌ Отмена',
        'send_content': 'Отправьте {type}:',
        'content_received': '✅ Содержимое получено!',
        'select_time': '⏰ Когда доставить капсулу?',
        'time_1hour': '1 час',
        'time_1day': '1 день',
        'time_1week': '1 неделя',
        'time_1month': '1 месяц',
        'time_3months': '3 месяца',
        'time_6months': '6 месяцев',
        'time_1year': '1 год',
        'time_custom': '📅 Выбрать дату',
        'enter_date': 'Введите дату в формате ДД.ММ.ГГГГ ЧЧ:ММ\nНапример: 31.12.2025 23:59',
        'invalid_date': '❌ Неверный формат даты. Попробуйте снова.',
        'date_too_far': '❌ Эта дата слишком далеко для вашего тарифа.\n\nБесплатный: до {days} дней\nПремиум: до {years} лет',
        'select_recipient': '👤 Кому отправить капсулу?',
        'recipient_self': '👤 Себе',
        'recipient_user': '👥 Другому пользователю',
        'recipient_group': '👨‍👩‍👧‍👦 В группу',
        'enter_user_id': 'Введите @username или ID пользователя:',
        'enter_group_id': 'Добавьте меня в группу и отправьте /group_id',
        'user_not_found': '❌ Пользователь не найден',
        'confirm_capsule': '✨ Подтвердите создание капсулы:\n\n📦 Тип: {type}\n⏰ Доставка: {time}\n👤 Получатель: {recipient}\n\nВсе верно?',
        'confirm_yes': '✅ Да, создать!',
        'confirm_no': '❌ Нет, отменить',
        'capsule_created': '🎉 Капсула создана!\n\nВаша капсула будет доставлена {time}',
        'capsule_cancelled': '❌ Создание капсулы отменено',
        'quota_exceeded': '⚠️ Превышен лимит!\n\n{message}\n\nОбновите подписку для снятия ограничений.',
        'upgrade_subscription': '⬆️ Обновить подписку',
        'no_capsules': 'У вас пока нет капсул',
        'capsule_list': '📦 Ваши капсулы ({count}/{limit}):',
        'capsule_item': '{emoji} {type} → {recipient}\nДоставка: {time}\nСоздана: {created}',
        'delete_capsule': '🗑 Удалить',
        'view_details': '👁 Подробнее',
        'subscription_info': '💎 Ваша подписка: {tier}\n\n{details}',
        'free_tier_details': '📊 Статистика:\n• Капсулы: {count}/{limit}\n• Хранилище: {used}/{total}\n• Срок хранения: до {days} дней',
        'premium_tier_details': '📊 Статистика:\n• Капсулы: {count} (безлимит)\n• Хранилище: {used}/{total}\n• Срок хранения: до {years} лет\n• Истекает: {expires}',
        'buy_premium_single': '💳 Одна капсула - {price}₽',
        'buy_premium_year': '💳 Год подписки - {price}₽',
        'buy_stars_single': '⭐ Одна капсула - {stars} звезд',
        'buy_stars_year': '⭐ Год подписки - {stars} звезд',
        'language_changed': '🌐 Язык изменен на русский',
        'help_text': '❓ Помощь\n\nDigital Time Capsule позволяет создавать капсулы времени - сообщения, которые будут доставлены в будущем.\n\n🔐 Безопасность:\n• Все файлы шифруются\n• Хранение в Yandex S3\n• Никто не может прочитать ваши капсулы\n\n📋 Команды:\n/start - Главное меню\n/create - Создать капсулу\n/capsules - Мои капсулы\n/subscription - Подписка\n/help - Помощь',
        'delivery_title': '🎁 Капсула времени!',
        'delivery_text': 'Вы получили капсулу времени!\n\nСоздана: {created}\nОт: {sender}',
        'error_occurred': '❌ Произошла ошибка. Попробуйте позже.',
        'file_too_large': '❌ Файл слишком большой!\n\nМаксимальный размер:\n• Бесплатно: 10 МБ на все капсулы\n• Премиум: 1 ГБ на все капсулы',
    },
    'en': {
        'start_welcome': '🕰 Welcome to Digital Time Capsule!\n\nI will help you create time capsules - send messages to the future to yourself, a friend, or a group!',
        'main_menu': '📋 Main Menu',
        'create_capsule': '✨ Create Capsule',
        'my_capsules': '📦 My Capsules',
        'subscription': '💎 Subscription',
        'settings': '⚙️ Settings',
        'help': '❓ Help',
        'language': '🌐 Language: English',
        'select_content_type': '📝 Select capsule content type:',
        'content_text': '📄 Text',
        'content_photo': '🖼 Photo',
        'content_video': '🎥 Video',
        'content_document': '📎 Document',
        'content_voice': '🎤 Voice Message',
        'back': '◀️ Back',
        'cancel': '❌ Cancel',
        'send_content': 'Send {type}:',
        'content_received': '✅ Content received!',
        'select_time': '⏰ When to deliver the capsule?',
        'time_1hour': '1 hour',
        'time_1day': '1 day',
        'time_1week': '1 week',
        'time_1month': '1 month',
        'time_3months': '3 months',
        'time_6months': '6 months',
        'time_1year': '1 year',
        'time_custom': '📅 Choose date',
        'enter_date': 'Enter date in format DD.MM.YYYY HH:MM\nExample: 31.12.2025 23:59',
        'invalid_date': '❌ Invalid date format. Try again.',
        'date_too_far': '❌ This date is too far for your plan.\n\nFree: up to {days} days\nPremium: up to {years} years',
        'select_recipient': '👤 Who will receive the capsule?',
        'recipient_self': '👤 Myself',
        'recipient_user': '👥 Another user',
        'recipient_group': '👨‍👩‍👧‍👦 To a group',
        'enter_user_id': 'Enter @username or user ID:',
        'enter_group_id': 'Add me to the group and send /group_id',
        'user_not_found': '❌ User not found',
        'confirm_capsule': '✨ Confirm capsule creation:\n\n📦 Type: {type}\n⏰ Delivery: {time}\n👤 Recipient: {recipient}\n\nIs everything correct?',
        'confirm_yes': '✅ Yes, create!',
        'confirm_no': '❌ No, cancel',
        'capsule_created': '🎉 Capsule created!\n\nYour capsule will be delivered on {time}',
        'capsule_cancelled': '❌ Capsule creation cancelled',
        'quota_exceeded': '⚠️ Limit exceeded!\n\n{message}\n\nUpgrade your subscription to remove limits.',
        'upgrade_subscription': '⬆️ Upgrade Subscription',
        'no_capsules': 'You have no capsules yet',
        'capsule_list': '📦 Your capsules ({count}/{limit}):',
        'capsule_item': '{emoji} {type} → {recipient}\nDelivery: {time}\nCreated: {created}',
        'delete_capsule': '🗑 Delete',
        'view_details': '👁 Details',
        'subscription_info': '💎 Your subscription: {tier}\n\n{details}',
        'free_tier_details': '📊 Statistics:\n• Capsules: {count}/{limit}\n• Storage: {used}/{total}\n• Storage period: up to {days} days',
        'premium_tier_details': '📊 Statistics:\n• Capsules: {count} (unlimited)\n• Storage: {used}/{total}\n• Storage period: up to {years} years\n• Expires: {expires}',
        'buy_premium_single': '💳 Single capsule - {price}₽',
        'buy_premium_year': '💳 Yearly subscription - {price}₽',
        'buy_stars_single': '⭐ Single capsule - {stars} stars',
        'buy_stars_year': '⭐ Yearly subscription - {stars} stars',
        'language_changed': '🌐 Language changed to English',
        'help_text': '❓ Help\n\nDigital Time Capsule lets you create time capsules - messages that will be delivered in the future.\n\n🔐 Security:\n• All files are encrypted\n• Stored in Yandex S3\n• No one can read your capsules\n\n📋 Commands:\n/start - Main menu\n/create - Create capsule\n/capsules - My capsules\n/subscription - Subscription\n/help - Help',
        'delivery_title': '🎁 Time Capsule!',
        'delivery_text': 'You received a time capsule!\n\nCreated: {created}\nFrom: {sender}',
        'error_occurred': '❌ An error occurred. Try again later.',
        'file_too_large': '❌ File is too large!\n\nMax size:\n• Free: 10 MB for all capsules\n• Premium: 1 GB for all capsules',
    }
}

def t(lang: str, key: str, **kwargs) -> str:
    """Get translated text"""
    text = TRANSLATIONS.get(lang, TRANSLATIONS['en']).get(key, key)
    return text.format(**kwargs) if kwargs else text

# ============================================================================
# DATABASE HELPER FUNCTIONS
# ============================================================================

def get_or_create_user(telegram_user: User) -> Optional[int]:
    """Get or create user in database, return user ID"""
    try:
        with engine.connect() as conn:
            # Check if user exists
            result = conn.execute(
                select(users.c.id).where(users.c.telegram_id == telegram_user.id)
            ).first()

            if result:
                return result[0]

            # Create new user
            result = conn.execute(
                insert(users).values(
                    telegram_id=telegram_user.id,
                    username=telegram_user.username,
                    first_name=telegram_user.first_name,
                    language_code=telegram_user.language_code or 'en'
                )
            )
            conn.commit()
            return result.inserted_primary_key[0]
    except Exception as e:
        logger.error(f"Error in get_or_create_user: {e}")
        return None

def get_user_data(telegram_id: int) -> Optional[Dict]:
    """Get user data from database"""
    try:
        with engine.connect() as conn:
            result = conn.execute(
                select(users).where(users.c.telegram_id == telegram_id)
            ).first()

            if result:
                return dict(result._mapping)
            return None
    except Exception as e:
        logger.error(f"Error in get_user_data: {e}")
        return None

def update_user_language(telegram_id: int, lang: str) -> bool:
    """Update user language"""
    try:
        with engine.connect() as conn:
            conn.execute(
                update(users)
                .where(users.c.telegram_id == telegram_id)
                .values(language_code=lang)
            )
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Error updating language: {e}")
        return False

def check_user_quota(user_data: Dict, file_size: int = 0) -> tuple[bool, str]:
    """
    Check if user can create a capsule
    Returns (can_create, error_message)
    """
    is_premium = user_data['subscription_status'] == PREMIUM_TIER

    # Check capsule count
    capsule_limit = PREMIUM_CAPSULE_LIMIT if is_premium else FREE_CAPSULE_LIMIT
    if user_data['capsule_count'] >= capsule_limit:
        return False, f"Capsule limit reached: {capsule_limit}"

    # Check storage
    storage_limit = PREMIUM_STORAGE_LIMIT if is_premium else FREE_STORAGE_LIMIT
    if user_data['total_storage_used'] + file_size > storage_limit:
        used_mb = user_data['total_storage_used'] / (1024 * 1024)
        limit_mb = storage_limit / (1024 * 1024)
        return False, f"Storage limit reached: {used_mb:.1f}/{limit_mb:.1f} MB"

    return True, ""

# ============================================================================
# S3 & ENCRYPTION HELPERS
# ============================================================================

def encrypt_and_upload_file(file_bytes: bytes, file_extension: str) -> tuple[Optional[str], Optional[bytes]]:
    """
    Encrypt file and upload to S3
    Returns (s3_key, encrypted_file_key)
    """
    try:
        # Generate unique key for this file
        file_key = Fernet.generate_key()
        file_cipher = Fernet(file_key)

        # Encrypt file content
        encrypted_content = file_cipher.encrypt(file_bytes)

        # Generate S3 key
        s3_key = f"capsules/{uuid.uuid4()}.{file_extension}.enc"

        # Upload to S3
        s3_client = get_s3_client()
        if not s3_client:
            logger.error("S3 client not available")
            return None, None

        s3_client.put_object(
            Bucket=YANDEX_BUCKET_NAME,
            Key=s3_key,
            Body=encrypted_content
        )

        # Encrypt the file key with master key
        encrypted_file_key = master_cipher.encrypt(file_key)

        logger.info(f"File uploaded to S3: {s3_key}")
        return s3_key, encrypted_file_key

    except Exception as e:
        logger.error(f"Error in encrypt_and_upload_file: {e}")
        return None, None

def download_and_decrypt_file(s3_key: str, encrypted_file_key: bytes) -> Optional[bytes]:
    """
    Download file from S3 and decrypt
    Returns decrypted file bytes
    """
    try:
        # Decrypt the file key
        file_key = master_cipher.decrypt(encrypted_file_key)
        file_cipher = Fernet(file_key)

        # Download from S3
        s3_client = get_s3_client()
        if not s3_client:
            return None

        response = s3_client.get_object(
            Bucket=YANDEX_BUCKET_NAME,
            Key=s3_key
        )
        encrypted_content = response['Body'].read()

        # Decrypt file
        decrypted_content = file_cipher.decrypt(encrypted_content)

        logger.info(f"File downloaded and decrypted: {s3_key}")
        return decrypted_content

    except Exception as e:
        logger.error(f"Error in download_and_decrypt_file: {e}")
        return None

# ============================================================================
# BOT HANDLERS - START & MAIN MENU
# ============================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start command handler"""
    user = update.effective_user
    user_id = get_or_create_user(user)

    if not user_id:
        await update.message.reply_text("Error creating user. Please try again.")
        return ConversationHandler.END

    user_data = get_user_data(user.id)
    lang = user_data['language_code']

    await update.message.reply_text(
        t(lang, 'start_welcome'),
        reply_markup=get_main_menu_keyboard(lang)
    )

    return SELECTING_ACTION

def get_main_menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Generate main menu keyboard"""
    keyboard = [
        [InlineKeyboardButton(t(lang, 'create_capsule'), callback_data='create')],
        [InlineKeyboardButton(t(lang, 'my_capsules'), callback_data='capsules')],
        [InlineKeyboardButton(t(lang, 'subscription'), callback_data='subscription')],
        [
            InlineKeyboardButton(t(lang, 'settings'), callback_data='settings'),
            InlineKeyboardButton(t(lang, 'help'), callback_data='help')
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

async def main_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle main menu button clicks"""
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    user_data = get_user_data(user.id)
    lang = user_data['language_code']

    action = query.data

    if action == 'create':
        return await start_create_capsule(update, context)
    elif action == 'capsules':
        return await show_capsules(update, context)
    elif action == 'subscription':
        return await show_subscription(update, context)
    elif action == 'settings':
        return await show_settings(update, context)
    elif action == 'help':
        await query.edit_message_text(
            t(lang, 'help_text'),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(t(lang, 'back'), callback_data='main_menu')
            ]])
        )
        return SELECTING_ACTION
    elif action == 'main_menu':
        await query.edit_message_text(
            t(lang, 'main_menu'),
            reply_markup=get_main_menu_keyboard(lang)
        )
        return SELECTING_ACTION

    return SELECTING_ACTION

# ============================================================================
# CREATE CAPSULE FLOW
# ============================================================================

async def start_create_capsule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start capsule creation flow"""
    query = update.callback_query
    user = update.effective_user
    user_data = get_user_data(user.id)
    lang = user_data['language_code']

    # Check quota
    can_create, error_msg = check_user_quota(user_data)
    if not can_create:
        keyboard = [[
            InlineKeyboardButton(t(lang, 'upgrade_subscription'), callback_data='subscription'),
            InlineKeyboardButton(t(lang, 'back'), callback_data='main_menu')
        ]]
        await query.edit_message_text(
            t(lang, 'quota_exceeded', message=error_msg),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return SELECTING_ACTION

    # Initialize capsule data in context
    context.user_data['capsule'] = {}

    # Show content type selection
    keyboard = [
        [InlineKeyboardButton(t(lang, 'content_text'), callback_data='type_text')],
        [InlineKeyboardButton(t(lang, 'content_photo'), callback_data='type_photo')],
        [InlineKeyboardButton(t(lang, 'content_video'), callback_data='type_video')],
        [InlineKeyboardButton(t(lang, 'content_document'), callback_data='type_document')],
        [InlineKeyboardButton(t(lang, 'content_voice'), callback_data='type_voice')],
        [InlineKeyboardButton(t(lang, 'cancel'), callback_data='main_menu')]
    ]

    await query.edit_message_text(
        t(lang, 'select_content_type'),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    return SELECTING_CONTENT_TYPE

async def select_content_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle content type selection"""
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    user_data = get_user_data(user.id)
    lang = user_data['language_code']

    content_type = query.data.replace('type_', '')
    context.user_data['capsule']['content_type'] = content_type

    type_names = {
        'text': t(lang, 'content_text'),
        'photo': t(lang, 'content_photo'),
        'video': t(lang, 'content_video'),
        'document': t(lang, 'content_document'),
        'voice': t(lang, 'content_voice')
    }

    await query.edit_message_text(
        t(lang, 'send_content', type=type_names.get(content_type, content_type))
    )

    return RECEIVING_CONTENT

async def receive_content(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive capsule content"""
    user = update.effective_user
    user_data = get_user_data(user.id)
    lang = user_data['language_code']

    content_type = context.user_data['capsule']['content_type']
    message = update.message

    try:
        if content_type == 'text':
            if not message.text:
                await message.reply_text(t(lang, 'error_occurred'))
                return RECEIVING_CONTENT
            context.user_data['capsule']['content_text'] = message.text
            context.user_data['capsule']['file_size'] = len(message.text.encode('utf-8'))

        else:
            # Handle file content
            file = None
            if content_type == 'photo' and message.photo:
                file = await message.photo[-1].get_file()
                ext = 'jpg'
            elif content_type == 'video' and message.video:
                file = await message.video.get_file()
                ext = 'mp4'
            elif content_type == 'document' and message.document:
                file = await message.document.get_file()
                ext = message.document.file_name.split('.')[-1] if '.' in message.document.file_name else 'bin'
            elif content_type == 'voice' and message.voice:
                file = await message.voice.get_file()
                ext = 'ogg'

            if not file:
                await message.reply_text(t(lang, 'error_occurred'))
                return RECEIVING_CONTENT

            file_size = file.file_size

            # Check quota with file size
            can_create, error_msg = check_user_quota(user_data, file_size)
            if not can_create:
                keyboard = [[
                    InlineKeyboardButton(t(lang, 'upgrade_subscription'), callback_data='subscription'),
                    InlineKeyboardButton(t(lang, 'back'), callback_data='main_menu')
                ]]
                await message.reply_text(
                    t(lang, 'quota_exceeded', message=error_msg),
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return SELECTING_ACTION

            # Download file
            file_bytes = await file.download_as_bytearray()

            # Encrypt and upload
            s3_key, encrypted_key = encrypt_and_upload_file(bytes(file_bytes), ext)
            if not s3_key or not encrypted_key:
                await message.reply_text(t(lang, 'error_occurred'))
                return RECEIVING_CONTENT

            context.user_data['capsule']['s3_key'] = s3_key
            context.user_data['capsule']['file_key'] = encrypted_key
            context.user_data['capsule']['file_size'] = file_size

        # Move to time selection
        await message.reply_text(
            t(lang, 'content_received'),
        )
        return await show_time_selection(update, context)

    except Exception as e:
        logger.error(f"Error receiving content: {e}")
        await message.reply_text(t(lang, 'error_occurred'))
        return RECEIVING_CONTENT

async def show_time_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show time selection menu"""
    user = update.effective_user
    user_data = get_user_data(user.id)
    lang = user_data['language_code']

    keyboard = [
        [
            InlineKeyboardButton(t(lang, 'time_1hour'), callback_data='time_1h'),
            InlineKeyboardButton(t(lang, 'time_1day'), callback_data='time_1d')
        ],
        [
            InlineKeyboardButton(t(lang, 'time_1week'), callback_data='time_1w'),
            InlineKeyboardButton(t(lang, 'time_1month'), callback_data='time_1m')
        ],
        [
            InlineKeyboardButton(t(lang, 'time_3months'), callback_data='time_3m'),
            InlineKeyboardButton(t(lang, 'time_6months'), callback_data='time_6m')
        ],
        [InlineKeyboardButton(t(lang, 'time_1year'), callback_data='time_1y')],
        [InlineKeyboardButton(t(lang, 'time_custom'), callback_data='time_custom')],
        [InlineKeyboardButton(t(lang, 'cancel'), callback_data='main_menu')]
    ]

    if update.callback_query:
        await update.callback_query.message.reply_text(
            t(lang, 'select_time'),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text(
            t(lang, 'select_time'),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    return SELECTING_TIME

async def select_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle time selection"""
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    user_data = get_user_data(user.id)
    lang = user_data['language_code']

    time_option = query.data.replace('time_', '')

    if time_option == 'custom':
        await query.edit_message_text(t(lang, 'enter_date'))
        return SELECTING_DATE

    # Calculate delivery time
    now = datetime.utcnow()
    delivery_time = None

    time_map = {
        '1h': timedelta(hours=1),
        '1d': timedelta(days=1),
        '1w': timedelta(weeks=1),
        '1m': relativedelta(months=1),
        '3m': relativedelta(months=3),
        '6m': relativedelta(months=6),
        '1y': relativedelta(years=1)
    }

    if time_option in ['1h', '1d', '1w']:
        delivery_time = now + time_map[time_option]
    else:
        delivery_time = now + time_map[time_option]

    # Check if time is within user's limit
    is_premium = user_data['subscription_status'] == PREMIUM_TIER
    max_days = PREMIUM_TIME_LIMIT_DAYS if is_premium else FREE_TIME_LIMIT_DAYS

    if (delivery_time - now).days > max_days:
        await query.edit_message_text(
            t(lang, 'date_too_far', days=FREE_TIME_LIMIT_DAYS, years=25),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(t(lang, 'back'), callback_data='back_to_time')
            ]])
        )
        return SELECTING_TIME

    context.user_data['capsule']['delivery_time'] = delivery_time

    return await show_recipient_selection(update, context)

async def select_custom_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle custom date input"""
    user = update.effective_user
    user_data = get_user_data(user.id)
    lang = user_data['language_code']

    try:
        # Parse date
        date_str = update.message.text.strip()
        delivery_time = datetime.strptime(date_str, '%d.%m.%Y %H:%M')

        # Check if in future
        if delivery_time <= datetime.utcnow():
            await update.message.reply_text(t(lang, 'invalid_date'))
            return SELECTING_DATE

        # Check time limit
        is_premium = user_data['subscription_status'] == PREMIUM_TIER
        max_days = PREMIUM_TIME_LIMIT_DAYS if is_premium else FREE_TIME_LIMIT_DAYS

        if (delivery_time - datetime.utcnow()).days > max_days:
            await update.message.reply_text(
                t(lang, 'date_too_far', days=FREE_TIME_LIMIT_DAYS, years=25)
            )
            return SELECTING_DATE

        context.user_data['capsule']['delivery_time'] = delivery_time

        return await show_recipient_selection(update, context)

    except ValueError:
        await update.message.reply_text(t(lang, 'invalid_date'))
        return SELECTING_DATE

async def show_recipient_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show recipient selection menu"""
    user = update.effective_user
    user_data = get_user_data(user.id)
    lang = user_data['language_code']

    keyboard = [
        [InlineKeyboardButton(t(lang, 'recipient_self'), callback_data='recipient_self')],
        [InlineKeyboardButton(t(lang, 'recipient_user'), callback_data='recipient_user')],
        [InlineKeyboardButton(t(lang, 'recipient_group'), callback_data='recipient_group')],
        [InlineKeyboardButton(t(lang, 'cancel'), callback_data='main_menu')]
    ]

    if update.callback_query:
        await update.callback_query.edit_message_text(
            t(lang, 'select_recipient'),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text(
            t(lang, 'select_recipient'),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    return SELECTING_RECIPIENT

async def select_recipient(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle recipient selection"""
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    user_data = get_user_data(user.id)
    lang = user_data['language_code']

    recipient_type = query.data.replace('recipient_', '')

    if recipient_type == 'self':
        context.user_data['capsule']['recipient_type'] = 'self'
        context.user_data['capsule']['recipient_id'] = user.id
        return await show_confirmation(update, context)
    elif recipient_type == 'user':
        context.user_data['capsule']['recipient_type'] = 'user'
        await query.edit_message_text(t(lang, 'enter_user_id'))
        return SELECTING_RECIPIENT
    elif recipient_type == 'group':
        context.user_data['capsule']['recipient_type'] = 'group'
        await query.edit_message_text(t(lang, 'enter_group_id'))
        return SELECTING_RECIPIENT

    return SELECTING_RECIPIENT

async def show_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show capsule confirmation"""
    user = update.effective_user
    user_data = get_user_data(user.id)
    lang = user_data['language_code']

    capsule = context.user_data['capsule']

    # Format recipient
    recipient_text = ""
    if capsule['recipient_type'] == 'self':
        recipient_text = t(lang, 'recipient_self')
    else:
        recipient_text = f"{capsule['recipient_type']}: {capsule.get('recipient_id', 'Unknown')}"

    # Format time
    time_text = capsule['delivery_time'].strftime('%d.%m.%Y %H:%M')

    keyboard = [
        [InlineKeyboardButton(t(lang, 'confirm_yes'), callback_data='confirm_yes')],
        [InlineKeyboardButton(t(lang, 'confirm_no'), callback_data='main_menu')]
    ]

    if update.callback_query:
        await update.callback_query.edit_message_text(
            t(lang, 'confirm_capsule', 
              type=capsule['content_type'],
              time=time_text,
              recipient=recipient_text),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text(
            t(lang, 'confirm_capsule',
              type=capsule['content_type'],
              time=time_text,
              recipient=recipient_text),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    return CONFIRMING_CAPSULE

async def confirm_capsule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Create the capsule in database"""
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    user_data = get_user_data(user.id)
    lang = user_data['language_code']

    capsule_data = context.user_data['capsule']

    try:
        with engine.connect() as conn:
            # Insert capsule
            result = conn.execute(
                insert(capsules).values(
                    user_id=user_data['id'],
                    capsule_uuid=str(uuid.uuid4()),
                    content_type=capsule_data['content_type'],
                    content_text=capsule_data.get('content_text'),
                    file_key=capsule_data.get('file_key'),
                    s3_key=capsule_data.get('s3_key'),
                    file_size=capsule_data.get('file_size', 0),
                    recipient_type=capsule_data['recipient_type'],
                    recipient_id=capsule_data.get('recipient_id'),
                    delivery_time=capsule_data['delivery_time']
                )
            )

            # Update user stats
            conn.execute(
                update(users)
                .where(users.c.id == user_data['id'])
                .values(
                    capsule_count=users.c.capsule_count + 1,
                    total_storage_used=users.c.total_storage_used + capsule_data.get('file_size', 0)
                )
            )

            conn.commit()

            capsule_id = result.inserted_primary_key[0]

            # Schedule delivery
            scheduler = context.application.bot_data.get('scheduler')
            if scheduler:
                scheduler.add_job(
                    deliver_capsule,
                    trigger=DateTrigger(run_date=capsule_data['delivery_time']),
                    args=[context.application.bot, capsule_id],
                    id=f"capsule_{capsule_id}",
                    replace_existing=True
                )

        time_text = capsule_data['delivery_time'].strftime('%d.%m.%Y %H:%M')
        await query.edit_message_text(
            t(lang, 'capsule_created', time=time_text),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(t(lang, 'main_menu'), callback_data='main_menu')
            ]])
        )

        # Clear capsule data
        context.user_data.pop('capsule', None)

    except Exception as e:
        logger.error(f"Error creating capsule: {e}")
        await query.edit_message_text(
            t(lang, 'error_occurred'),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(t(lang, 'main_menu'), callback_data='main_menu')
            ]])
        )

    return SELECTING_ACTION

# ============================================================================
# CAPSULE DELIVERY
# ============================================================================

async def deliver_capsule(bot, capsule_id: int):
    """Deliver a time capsule"""
    try:
        with engine.connect() as conn:
            # Get capsule data
            capsule_row = conn.execute(
                select(capsules, users)
                .join(users, capsules.c.user_id == users.c.id)
                .where(capsules.c.id == capsule_id)
            ).first()

            if not capsule_row:
                logger.error(f"Capsule {capsule_id} not found")
                return

            capsule_data = dict(capsule_row._mapping)
            sender_name = capsule_data['first_name'] or capsule_data['username'] or 'Anonymous'

            # Get recipient
            recipient_id = capsule_data['recipient_id']
            lang = capsule_data['language_code']

            # Prepare message
            delivery_text = t(lang, 'delivery_text',
                            created=capsule_data['created_at'].strftime('%d.%m.%Y %H:%M'),
                            sender=sender_name)

            # Send content based on type
            if capsule_data['content_type'] == 'text':
                await bot.send_message(
                    chat_id=recipient_id,
                    text=f"{t(lang, 'delivery_title')}\n\n{delivery_text}\n\n{capsule_data['content_text']}"
                )
            else:
                # Download and decrypt file
                file_bytes = download_and_decrypt_file(
                    capsule_data['s3_key'],
                    capsule_data['file_key']
                )

                if file_bytes:
                    file_obj = BytesIO(file_bytes)

                    if capsule_data['content_type'] == 'photo':
                        await bot.send_photo(
                            chat_id=recipient_id,
                            photo=file_obj,
                            caption=delivery_text
                        )
                    elif capsule_data['content_type'] == 'video':
                        await bot.send_video(
                            chat_id=recipient_id,
                            video=file_obj,
                            caption=delivery_text
                        )
                    elif capsule_data['content_type'] == 'document':
                        await bot.send_document(
                            chat_id=recipient_id,
                            document=file_obj,
                            caption=delivery_text
                        )
                    elif capsule_data['content_type'] == 'voice':
                        await bot.send_voice(
                            chat_id=recipient_id,
                            voice=file_obj,
                            caption=delivery_text
                        )

            # Mark as delivered
            conn.execute(
                update(capsules)
                .where(capsules.c.id == capsule_id)
                .values(delivered=True, delivered_at=datetime.utcnow())
            )
            conn.commit()

            logger.info(f"Capsule {capsule_id} delivered successfully")

    except Exception as e:
        logger.error(f"Error delivering capsule {capsule_id}: {e}")

# ============================================================================
# VIEW CAPSULES
# ============================================================================

async def show_capsules(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show user's capsules"""
    query = update.callback_query
    user = update.effective_user
    user_data = get_user_data(user.id)
    lang = user_data['language_code']

    try:
        with engine.connect() as conn:
            capsule_rows = conn.execute(
                select(capsules)
                .where(and_(
                    capsules.c.user_id == user_data['id'],
                    capsules.c.delivered == False
                ))
                .order_by(capsules.c.delivery_time)
            ).fetchall()

            if not capsule_rows:
                await query.edit_message_text(
                    t(lang, 'no_capsules'),
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(t(lang, 'main_menu'), callback_data='main_menu')
                    ]])
                )
                return SELECTING_ACTION

            is_premium = user_data['subscription_status'] == PREMIUM_TIER
            limit = PREMIUM_CAPSULE_LIMIT if is_premium else FREE_CAPSULE_LIMIT

            # Build capsules list
            capsules_text = t(lang, 'capsule_list', count=len(capsule_rows), limit=limit) + '\n\n'

            content_emoji = {
                'text': '📄',
                'photo': '🖼',
                'video': '🎥',
                'document': '📎',
                'voice': '🎤'
            }

            keyboard = []
            for cap in capsule_rows[:10]:  # Show max 10
                cap_dict = dict(cap._mapping)
                emoji = content_emoji.get(cap_dict['content_type'], '📦')

                recipient = cap_dict['recipient_type']
                if cap_dict['recipient_type'] == 'self':
                    recipient = t(lang, 'recipient_self')

                item_text = t(lang, 'capsule_item',
                            emoji=emoji,
                            type=cap_dict['content_type'],
                            recipient=recipient,
                            time=cap_dict['delivery_time'].strftime('%d.%m.%Y %H:%M'),
                            created=cap_dict['created_at'].strftime('%d.%m.%Y'))

                capsules_text += f"{item_text}\n\n"

                keyboard.append([
                    InlineKeyboardButton(
                        f"{emoji} {cap_dict['delivery_time'].strftime('%d.%m %H:%M')}",
                        callback_data=f"view_{cap_dict['id']}"
                    ),
                    InlineKeyboardButton(
                        t(lang, 'delete_capsule'),
                        callback_data=f"delete_{cap_dict['id']}"
                    )
                ])

            keyboard.append([InlineKeyboardButton(t(lang, 'main_menu'), callback_data='main_menu')])

            await query.edit_message_text(
                capsules_text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    except Exception as e:
        logger.error(f"Error showing capsules: {e}")
        await query.edit_message_text(
            t(lang, 'error_occurred'),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(t(lang, 'main_menu'), callback_data='main_menu')
            ]])
        )

    return VIEWING_CAPSULES

# ============================================================================
# SUBSCRIPTION MANAGEMENT
# ============================================================================

async def show_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show subscription information"""
    query = update.callback_query
    user = update.effective_user
    user_data = get_user_data(user.id)
    lang = user_data['language_code']

    is_premium = user_data['subscription_status'] == PREMIUM_TIER

    if is_premium:
        used_mb = user_data['total_storage_used'] / (1024 * 1024)
        total_mb = PREMIUM_STORAGE_LIMIT / (1024 * 1024)
        expires = user_data['subscription_expires'].strftime('%d.%m.%Y') if user_data['subscription_expires'] else 'Never'

        details = t(lang, 'premium_tier_details',
                   count=user_data['capsule_count'],
                   used=f"{used_mb:.1f} MB",
                   total=f"{total_mb:.0f} MB",
                   years=25,
                   expires=expires)
    else:
        used_mb = user_data['total_storage_used'] / (1024 * 1024)
        total_mb = FREE_STORAGE_LIMIT / (1024 * 1024)

        details = t(lang, 'free_tier_details',
                   count=user_data['capsule_count'],
                   limit=FREE_CAPSULE_LIMIT,
                   used=f"{used_mb:.1f} MB",
                   total=f"{total_mb:.0f} MB",
                   days=365)

    info_text = t(lang, 'subscription_info',
                  tier=PREMIUM_TIER if is_premium else FREE_TIER,
                  details=details)

    keyboard = []
    if not is_premium:
        keyboard = [
            [InlineKeyboardButton(
                t(lang, 'buy_premium_single', price=PREMIUM_SINGLE_PRICE),
                callback_data='buy_single_rub'
            )],
            [InlineKeyboardButton(
                t(lang, 'buy_premium_year', price=PREMIUM_YEAR_PRICE),
                callback_data='buy_year_rub'
            )],
            [InlineKeyboardButton(
                t(lang, 'buy_stars_single', stars=PREMIUM_SINGLE_STARS),
                callback_data='buy_single_stars'
            )],
            [InlineKeyboardButton(
                t(lang, 'buy_stars_year', stars=PREMIUM_YEAR_STARS),
                callback_data='buy_year_stars'
            )]
        ]

    keyboard.append([InlineKeyboardButton(t(lang, 'main_menu'), callback_data='main_menu')])

    await query.edit_message_text(
        info_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    return MANAGING_SUBSCRIPTION

async def handle_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle payment button clicks"""
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    user_data = get_user_data(user.id)
    lang = user_data['language_code']

    payment_type = query.data  # e.g., 'buy_single_rub', 'buy_year_stars'

    # Placeholder for payment processing
    # In production, integrate with Telegram Payment API

    await query.edit_message_text(
        "Payment integration coming soon!\n\nFor now, contact @admin for premium access.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(t(lang, 'main_menu'), callback_data='main_menu')
        ]])
    )

    return SELECTING_ACTION

# ============================================================================
# SETTINGS
# ============================================================================

async def show_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show settings menu"""
    query = update.callback_query
    user = update.effective_user
    user_data = get_user_data(user.id)
    lang = user_data['language_code']

    keyboard = [
        [InlineKeyboardButton(
            '🇷🇺 Русский' if lang == 'en' else '🇬🇧 English',
            callback_data='toggle_lang'
        )],
        [InlineKeyboardButton(t(lang, 'back'), callback_data='main_menu')]
    ]

    await query.edit_message_text(
        t(lang, 'settings'),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    return SELECTING_ACTION

async def toggle_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Toggle user language"""
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    user_data = get_user_data(user.id)
    current_lang = user_data['language_code']

    new_lang = 'en' if current_lang == 'ru' else 'ru'
    update_user_language(user.id, new_lang)

    await query.edit_message_text(
        t(new_lang, 'language_changed'),
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(t(new_lang, 'main_menu'), callback_data='main_menu')
        ]])
    )

    return SELECTING_ACTION

# ============================================================================
# SCHEDULER INITIALIZATION
# ============================================================================

def init_scheduler(application: Application) -> AsyncIOScheduler:
    """Initialize scheduler and load pending capsules"""
    scheduler = AsyncIOScheduler()

    try:
        with engine.connect() as conn:
            pending_capsules = conn.execute(
                select(capsules)
                .where(and_(
                    capsules.c.delivered == False,
                    capsules.c.delivery_time > datetime.utcnow()
                ))
            ).fetchall()

            for capsule in pending_capsules:
                cap_dict = dict(capsule._mapping)
                scheduler.add_job(
                    deliver_capsule,
                    trigger=DateTrigger(run_date=cap_dict['delivery_time']),
                    args=[application.bot, cap_dict['id']],
                    id=f"capsule_{cap_dict['id']}",
                    replace_existing=True
                )

            logger.info(f"Scheduled {len(pending_capsules)} pending capsules")

    except Exception as e:
        logger.error(f"Error initializing scheduler: {e}")

    scheduler.start()
    return scheduler

# ============================================================================
# MAIN
# ============================================================================

def main():
    """Start the bot"""
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()

    # Initialize scheduler
    scheduler = init_scheduler(application)
    application.bot_data['scheduler'] = scheduler

    # Conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            SELECTING_ACTION: [
                CallbackQueryHandler(main_menu_handler)
            ],
            SELECTING_CONTENT_TYPE: [
                CallbackQueryHandler(select_content_type, pattern='^type_')
            ],
            RECEIVING_CONTENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_content),
                MessageHandler(filters.PHOTO, receive_content),
                MessageHandler(filters.VIDEO, receive_content),
                MessageHandler(filters.Document.ALL, receive_content),
                MessageHandler(filters.VOICE, receive_content)
            ],
            SELECTING_TIME: [
                CallbackQueryHandler(select_time, pattern='^time_')
            ],
            SELECTING_DATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, select_custom_date)
            ],
            SELECTING_RECIPIENT: [
                CallbackQueryHandler(select_recipient, pattern='^recipient_')
            ],
            CONFIRMING_CAPSULE: [
                CallbackQueryHandler(confirm_capsule, pattern='^confirm_yes$')
            ],
            VIEWING_CAPSULES: [
                CallbackQueryHandler(show_capsules, pattern='^capsules$')
            ],
            MANAGING_SUBSCRIPTION: [
                CallbackQueryHandler(handle_payment, pattern='^buy_')
            ]
        },
        fallbacks=[
            CommandHandler('start', start),
            CallbackQueryHandler(main_menu_handler, pattern='^main_menu$'),
            CallbackQueryHandler(toggle_language, pattern='^toggle_lang$')
        ],
        allow_reentry=True
    )

    application.add_handler(conv_handler)

    # Additional commands
    application.add_handler(CommandHandler('create', start_create_capsule))
    application.add_handler(CommandHandler('capsules', show_capsules))
    application.add_handler(CommandHandler('subscription', show_subscription))
    application.add_handler(CommandHandler('help', main_menu_handler))

    # Start bot
    logger.info("Bot started!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
