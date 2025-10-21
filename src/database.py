# src/database.py
from datetime import datetime
from typing import Optional, Dict
from sqlalchemy import (
    create_engine, MetaData, Table, Column, Integer, String,
    DateTime, ForeignKey, Boolean, BigInteger, Text, select,
    insert, update as sqlalchemy_update, LargeBinary, Float
)
from telegram import User
from .config import DATABASE_URL, logger, PREMIUM_TIER, PREMIUM_CAPSULE_LIMIT, FREE_CAPSULE_LIMIT, PREMIUM_STORAGE_LIMIT, FREE_STORAGE_LIMIT

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

def init_db():
    """Initialize the database"""
    metadata.create_all(engine)

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
                sqlalchemy_update(users)
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
