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
    Column('capsule_count', Integer, default=0),
    Column('capsule_balance', Integer, default=0),
    Column('timezone', String(50), default='UTC')  # User's timezone
)


# Capsules table
capsules = Table('capsules', metadata,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id'), nullable=False),
    Column('capsule_uuid', String(36), unique=True, nullable=False, index=True),
    Column('content_type', String(50), nullable=False),
    Column('content_text', Text, nullable=True),
    Column('file_key', LargeBinary, nullable=True),
    Column('s3_key', String(500), nullable=True),
    Column('file_size', BigInteger, default=0),
    Column('recipient_type', String(50), nullable=False),
    Column('recipient_id', BigInteger, nullable=True),
    Column('recipient_username', String(255), nullable=True),
    Column('delivery_time', DateTime, nullable=False),
    Column('created_at', DateTime, default=datetime.utcnow),
    Column('delivered', Boolean, default=False),
    Column('delivered_at', DateTime, nullable=True),
    Column('activated_at', DateTime, nullable=True),
    Column('message', Text, nullable=True)
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

transactions = Table(
    'transactions', metadata,
    Column('id', Integer, primary_key=True),
    Column('user_id', BigInteger, ForeignKey('users.id')),
    Column('transaction_type', String(50)),  # 'single', 'pack_3', 'pack_10', 'pack_25', 'pack_100', 'premium_month', 'premium_year'
    Column('stars_paid', Integer),
    Column('capsules_added', Integer, default=0),
    Column('created_at', DateTime, default=datetime.utcnow),
    Column('telegram_payment_charge_id', String(255), unique=True)
)


def init_db():
    """Initialize the database"""
    metadata.create_all(engine)
    logger.info("Database tables initialized")

# src/database.py

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

            # Create new user with 3 starter capsules
            from .config import FREE_STARTER_CAPSULES  # Import at function level to avoid circular imports
            from .timezone_utils import get_timezone_for_language  # Import at function level to avoid circular imports

            # Determine timezone based on user's language
            user_lang = telegram_user.language_code or 'en'
            timezone_str = get_timezone_for_language(user_lang)

            result = conn.execute(
                insert(users).values(
                    telegram_id=telegram_user.id,
                    username=telegram_user.username,
                    first_name=telegram_user.first_name,
                    language_code=user_lang,
                    timezone=timezone_str,  # Set user's timezone
                    capsule_balance=FREE_STARTER_CAPSULES  # Give 3 free capsules!
                )
            )
            conn.commit()

            user_id = result.inserted_primary_key[0]
            logger.info(f"✅ New user {telegram_user.id} created with {FREE_STARTER_CAPSULES} starter capsules and timezone {timezone_str}")

            return user_id

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
    Returns (can_create, error_message_key)
    """
    # Check capsule balance
    capsule_balance = user_data.get('capsule_balance', 0)
    if capsule_balance <= 0:
        return False, "no_capsule_balance"

    # Check storage
    is_premium = user_data['subscription_status'] == PREMIUM_TIER
    storage_limit = PREMIUM_STORAGE_LIMIT if is_premium else FREE_STORAGE_LIMIT

    if user_data['total_storage_used'] + file_size > storage_limit:
        return False, "storage_limit_reached"

    return True, ""


def delete_capsule(capsule_id: int):
    """Delete a capsule from the database"""
    try:
        with engine.connect() as conn:
            conn.execute(
                capsules.delete().where(capsules.c.id == capsule_id)
            )
            conn.commit()
            logger.info(f"Capsule {capsule_id} deleted from database")
    except Exception as e:
        logger.error(f"Error deleting capsule {capsule_id} from database: {e}")

def get_user_stats(telegram_id: int) -> Optional[Dict]:
    """Get comprehensive user statistics"""
    try:
        with engine.connect() as conn:
            # Get user data
            user_result = conn.execute(
                select(users).where(users.c.telegram_id == telegram_id)
            ).first()

            if not user_result:
                return None

            user_dict = dict(user_result._mapping)

            # Count active (undelivered) capsules
            active_capsules = conn.execute(
                select(capsules.c.id)
                .where(capsules.c.user_id == user_dict['id'])
                .where(capsules.c.delivered == False)
            ).rowcount

            # Count delivered capsules
            delivered_capsules = conn.execute(
                select(capsules.c.id)
                .where(capsules.c.user_id == user_dict['id'])
                .where(capsules.c.delivered == True)
            ).rowcount

            # Calculate storage usage in MB
            storage_mb = user_dict['total_storage_used'] / (1024 * 1024)
            max_storage_mb = (PREMIUM_STORAGE_LIMIT if user_dict['subscription_status'] == 'premium'
                            else FREE_STORAGE_LIMIT) / (1024 * 1024)

            return {
                'user_data': user_dict,
                'capsules_total': user_dict['capsule_count'],
                'capsules_active': active_capsules,
                'capsules_delivered': delivered_capsules,
                'storage_used_mb': round(storage_mb, 1),
                'storage_max_mb': round(max_storage_mb, 0),
                'subscription': user_dict['subscription_status']
            }

    except Exception as e:
        logger.error(f"Error getting user stats: {e}")
        return None

def update_user_storage(user_id: int, size_change: int) -> bool:
    """Update user's total storage used (can be positive or negative)"""
    try:
        with engine.connect() as conn:
            conn.execute(
                sqlalchemy_update(users)
                .where(users.c.id == user_id)
                .values(total_storage_used=users.c.total_storage_used + size_change)
            )
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Error updating user storage: {e}")
        return False

def increment_user_capsule_count(user_id: int) -> bool:
    """Increment user's capsule count"""
    try:
        with engine.connect() as conn:
            conn.execute(
                sqlalchemy_update(users)
                .where(users.c.id == user_id)
                .values(capsule_count=users.c.capsule_count + 1)
            )
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Error incrementing capsule count: {e}")
        return False

def decrement_user_capsule_count(user_id: int) -> bool:
    """Decrement user's capsule count"""
    try:
        with engine.connect() as conn:
            conn.execute(
                sqlalchemy_update(users)
                .where(users.c.id == user_id)
                .values(capsule_count=users.c.capsule_count - 1)
            )
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Error decrementing capsule count: {e}")
        return False

def get_user_capsules(user_id: int, limit: int = 50, offset: int = 0) -> Optional[list]:
    """Get user's capsules with pagination"""
    try:
        with engine.connect() as conn:
            result = conn.execute(
                select(capsules)
                .where(capsules.c.user_id == user_id)
                .order_by(capsules.c.created_at.desc())
                .limit(limit)
                .offset(offset)
            ).fetchall()

            return [dict(row._mapping) for row in result] if result else []

    except Exception as e:
        logger.error(f"Error getting user capsules: {e}")
        return None

def get_capsule_by_id(capsule_id: int) -> Optional[Dict]:
    """Get a specific capsule by ID"""
    try:
        with engine.connect() as conn:
            result = conn.execute(
                select(capsules).where(capsules.c.id == capsule_id)
            ).first()

            return dict(result._mapping) if result else None

    except Exception as e:
        logger.error(f"Error getting capsule by ID: {e}")
        return None

def mark_capsule_delivered(capsule_id: int) -> bool:
    """Mark a capsule as delivered"""
    try:
        with engine.connect() as conn:
            conn.execute(
                sqlalchemy_update(capsules)
                .where(capsules.c.id == capsule_id)
                .values(
                    delivered=True,
                    delivered_at=datetime.utcnow()
                )
            )
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Error marking capsule as delivered: {e}")
        return False

def delete_capsule_and_update_user(capsule_id: int, user_id: int) -> tuple[bool, int]:
    """Delete a capsule and update user's storage/count. Returns (success, file_size)"""
    try:
        with engine.connect() as conn:
            # Get capsule info first
            capsule_result = conn.execute(
                select(capsules.c.file_size)
                .where(capsules.c.id == capsule_id)
                .where(capsules.c.user_id == user_id)
            ).first()

            if not capsule_result:
                return False, 0

            file_size = capsule_result[0] or 0

            # Delete the capsule
            conn.execute(
                capsules.delete()
                .where(capsules.c.id == capsule_id)
                .where(capsules.c.user_id == user_id)
            )

            # Update user statistics
            conn.execute(
                sqlalchemy_update(users)
                .where(users.c.id == user_id)
                .values(
                    capsule_count=users.c.capsule_count - 1,
                    total_storage_used=users.c.total_storage_used - file_size
                )
            )

            conn.commit()
            return True, file_size

    except Exception as e:
        logger.error(f"Error deleting capsule and updating user: {e}")
        return False, 0

# Add to database.py

def create_capsule(user_id: int, capsule_data: Dict) -> Optional[int]:
    """
    Create a new capsule and return its ID
    NOW SUPPORTS: recipient_username for @username delivery
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(
                insert(capsules).values(
                    user_id=user_id,
                    capsule_uuid=capsule_data['capsule_uuid'],
                    content_type=capsule_data['content_type'],
                    content_text=capsule_data.get('content_text'),
                    file_key=capsule_data.get('file_key'),
                    s3_key=capsule_data.get('s3_key'),
                    file_size=capsule_data.get('file_size', 0),
                    recipient_type=capsule_data['recipient_type'],
                    recipient_id=capsule_data.get('recipient_id'),  # Can be NULL for usernames
                    recipient_username=capsule_data.get('recipient_username'),  # NEW!
                    delivery_time=capsule_data['delivery_time'],
                    message=capsule_data.get('message')
                )
            )
            conn.commit()
            capsule_id = result.inserted_primary_key[0]

            # Update user statistics
            file_size = capsule_data.get('file_size', 0)
            conn.execute(
                sqlalchemy_update(users)
                .where(users.c.id == user_id)
                .values(
                    capsule_count=users.c.capsule_count + 1,
                    total_storage_used=users.c.total_storage_used + file_size
                )
            )
            conn.commit()

            return capsule_id
    except Exception as e:
        logger.error(f"Error creating capsule: {e}")
        return None


def check_and_activate_username_capsules(telegram_id: int, username: str) -> int:
    """
    Check if any capsules are waiting for this username and activate them
    Called when user starts the bot
    Returns: Number of capsules activated
    """
    if not username:
        return 0

    try:
        with engine.connect() as conn:
            # Find all pending capsules for this username
            result = conn.execute(
                select(capsules.c.id, capsules.c.capsule_uuid, capsules.c.delivery_time)
                .where(capsules.c.recipient_username == username.lower())
                .where(capsules.c.recipient_id == None)  # Not yet activated
                .where(capsules.c.delivered == False)
            ).fetchall()

            if not result:
                return 0

            activated_count = 0
            for row in result:
                capsule_id, capsule_uuid, delivery_time = row

                # Activate the capsule
                conn.execute(
                    sqlalchemy_update(capsules)
                    .where(capsules.c.id == capsule_id)
                    .values(
                        recipient_id=telegram_id,
                        activated_at=datetime.utcnow()
                    )
                )
                activated_count += 1

                logger.info(f"✓ Capsule {capsule_uuid} activated for @{username} (telegram_id: {telegram_id})")

            conn.commit()
            return activated_count

    except Exception as e:
        logger.error(f"Error checking username capsules: {e}")
        return 0


def get_pending_capsules_by_username(username: str) -> list:
    """Get capsules waiting for a specific username to activate"""
    try:
        with engine.connect() as conn:
            result = conn.execute(
                select(capsules)
                .where(capsules.c.recipient_username == username.lower())
                .where(capsules.c.recipient_id == None)
                .where(capsules.c.delivered == False)
            ).fetchall()

            return [dict(row._mapping) for row in result]
    except Exception as e:
        logger.error(f"Error getting pending capsules by username: {e}")
        return []


def update_subscription(user_id: int, subscription_type: str, expires_at: Optional[datetime] = None) -> bool:
    """Update user's subscription status"""
    try:
        with engine.connect() as conn:
            conn.execute(
                sqlalchemy_update(users)
                .where(users.c.id == user_id)
                .values(
                    subscription_status=subscription_type,
                    subscription_expires=expires_at
                )
            )
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Error updating subscription: {e}")
        return False

def get_pending_capsules() -> list:
    """Get all capsules that should be delivered now"""
    try:
        with engine.connect() as conn:
            result = conn.execute(
                select(capsules)
                .where(capsules.c.delivered == False)
                .where(capsules.c.delivery_time <= datetime.utcnow())
            ).fetchall()

            return [dict(row._mapping) for row in result] if result else []

    except Exception as e:
        logger.error(f"Error getting pending capsules: {e}")
        return []

def record_payment(user_id: int, payment_data: Dict) -> Optional[int]:
    """Record a payment transaction"""
    try:
        with engine.connect() as conn:
            result = conn.execute(
                insert(payments).values(
                    user_id=user_id,
                    payment_type=payment_data['payment_type'],
                    amount=payment_data['amount'],
                    currency=payment_data['currency'],
                    subscription_type=payment_data['subscription_type'],
                    payment_id=payment_data['payment_id'],
                    successful=payment_data.get('successful', False)
                )
            )
            conn.commit()
            return result.inserted_primary_key[0]

    except Exception as e:
        logger.error(f"Error recording payment: {e}")
        return None


def add_capsules_to_balance(user_id: int, capsule_count: int) -> bool:
    """Add capsules to user's balance"""
    try:
        with engine.connect() as conn:
            conn.execute(
                sqlalchemy_update(users)
                .where(users.c.id == user_id)
                .values(capsule_balance=users.c.capsule_balance + capsule_count)
            )
            conn.commit()
            logger.info(f"Added {capsule_count} capsules to user {user_id} balance")
            return True
    except Exception as e:
        logger.error(f"Error adding capsules to balance: {e}")
        return False

def deduct_capsule_from_balance(user_id: int) -> bool:
    """Deduct one capsule from user's balance"""
    try:
        with engine.connect() as conn:
            # Check current balance
            result = conn.execute(
                select(users.c.capsule_balance)
                .where(users.c.id == user_id)
            ).first()

            if not result or result[0] <= 0:
                return False

            conn.execute(
                sqlalchemy_update(users)
                .where(users.c.id == user_id)
                .values(capsule_balance=users.c.capsule_balance - 1)
            )
            conn.commit()
            logger.info(f"Deducted 1 capsule from user {user_id} balance")
            return True
    except Exception as e:
        logger.error(f"Error deducting capsule from balance: {e}")
        return False

def get_user_capsule_balance(user_id: int) -> int:
    """Get user's capsule balance"""
    try:
        with engine.connect() as conn:
            result = conn.execute(
                select(users.c.capsule_balance)
                .where(users.c.id == user_id)
            ).first()
            return result[0] if result else 0
    except Exception as e:
        logger.error(f"Error getting capsule balance: {e}")
        return 0

def record_capsule_transaction(user_id: int, transaction_type: str, stars_paid: int,
                               capsules_added: int, payment_charge_id: str) -> Optional[int]:
    """Record a capsule purchase transaction"""
    try:
        with engine.connect() as conn:
            result = conn.execute(
                insert(transactions).values(
                    user_id=user_id,
                    transaction_type=transaction_type,
                    stars_paid=stars_paid,
                    capsules_added=capsules_added,
                    telegram_payment_charge_id=payment_charge_id,
                    created_at=datetime.utcnow()
                )
            )
            conn.commit()
            return result.inserted_primary_key[0]
    except Exception as e:
        logger.error(f"Error recording capsule transaction: {e}")
        return None

def debug_user_balance(telegram_id: int):
    """Debug function to check user balance"""
    try:
        with engine.connect() as conn:
            result = conn.execute(
                select(users.c.capsule_balance, users.c.subscription_status)
                .where(users.c.telegram_id == telegram_id)
            ).first()

            if result:
                logger.info(f"DEBUG: User {telegram_id} - Balance: {result[0]}, Status: {result[1]}")
                return result[0]
            else:
                logger.warning(f"DEBUG: User {telegram_id} not found")
                return None
    except Exception as e:
        logger.error(f"DEBUG Error: {e}")
        return None

# src/database.py

def get_pending_capsules_for_user(user_telegram_id: int):
    """Get all activated capsules waiting for delivery to this user"""
    try:
        with engine.connect() as conn:
            result = conn.execute(
                select(capsules)
                .where(capsules.c.recipient_id == str(user_telegram_id))
                .where(capsules.c.delivered == False)
            ).fetchall()

            return [dict(row._mapping) for row in result]

    except Exception as e:
        logger.error(f"Error fetching pending capsules: {e}")
        return []


def activate_capsule_for_recipient(capsule_uuid: str, recipient_telegram_id: int) -> bool:
    """
    Activate capsule when recipient starts bot via deep link.
    Delivery time remains as originally scheduled.
    """
    try:
        with engine.connect() as conn:
            # Check if capsule exists
            result = conn.execute(
                select(capsules.c.id, capsules.c.user_id, capsules.c.delivery_time)
                .where(capsules.c.capsule_uuid == capsule_uuid)
                .where(capsules.c.delivered == False)
            ).first()

            if not result:
                logger.warning(f"Capsule {capsule_uuid} not found")
                return False

            capsule_id, sender_id, delivery_time = result

            # Update capsule with recipient's telegram ID and mark as activated
            conn.execute(
                sqlalchemy_update(capsules)
                .where(capsules.c.capsule_uuid == capsule_uuid)
                .values(
                    recipient_id=str(recipient_telegram_id),
                    activated_at=datetime.utcnow(),
                    message='Activated by recipient'
                )
            )
            conn.commit()

            logger.info(f"✅ Capsule {capsule_uuid} activated by user {recipient_telegram_id}")
            logger.info(f"   Will deliver at: {delivery_time}")

            return True

    except Exception as e:
        logger.error(f"Error activating capsule: {e}")
        return False


def get_user_by_internal_id(internal_id: int):
    """Get user data by internal database ID (not telegram_id)"""
    try:
        with engine.connect() as conn:
            result = conn.execute(
                select(users).where(users.c.id == internal_id)
            ).first()

            if result:
                return dict(result._mapping)
            return None

    except Exception as e:
        logger.error(f"Error getting user by internal ID: {e}")
        return None


def refund_capsule_to_balance(user_id: int) -> bool:
    """Refund one capsule to user's balance (for failed transactions)"""
    try:
        with engine.connect() as conn:
            conn.execute(
                sqlalchemy_update(users)
                .where(users.c.id == user_id)
                .values(capsule_balance=users.c.capsule_balance + 1)
            )
            conn.commit()
            logger.info(f"✅ Refunded 1 capsule to user {user_id} balance")
            return True
    except Exception as e:
        logger.error(f"Error refunding capsule: {e}")
        return False

def get_user_data_by_telegram_id(telegram_id: int) -> Optional[Dict]:
    """Get user data by telegram ID"""
    try:
        with engine.connect() as conn:
            result = conn.execute(
                select(users).where(users.c.telegram_id == telegram_id)
            ).first()

            if result:
                return dict(result._mapping)
            return None
    except Exception as e:
        logger.error(f"Error getting user data by telegram_id: {e}")
        return None
