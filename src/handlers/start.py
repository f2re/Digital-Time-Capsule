# src/handlers/start.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from ..translations import t
from ..config import SELECTING_LANG, SELECTING_ACTION, logger
from .main_menu import get_main_menu_keyboard
import os
from ..image_menu import send_menu_with_image
import base64
from ..database import (
    get_or_create_user,
    get_user_data,
    get_pending_capsules_for_user,
    activate_capsule_for_recipient,
    get_user_by_internal_id,
    update_user_language,  # ADD THIS IMPORT
    capsules,
    engine,
    update_user_onboarding_stage,
    get_capsule_by_uuid  # NEW IMPORT
)
from sqlalchemy import select
from datetime import datetime
import random

# Onboarding message variants
ONBOARDING_GREETING_VARIANTS = {
    'A': {
        'ru': 'Привет 👋\n\nОтправь сообщение в будущее — себе, близкому человеку или тому, кого ещё не встретил\n\nЭто займёт 30 секунд',
        'en': 'Hi 👋\n\nSend a message to the future — to yourself, a loved one, or someone you haven\'t met yet\n\nIt takes 30 seconds'
    },
    'B': {
        'ru': 'Что ты почувствуешь через год?\n\nЯ сохраню твои слова и верну их в нужный момент 💫\n\nСоздать первую капсулу?',
        'en': 'What will you feel in a year?\n\nI\'ll save your words and return them at the right moment 💫\n\nCreate first capsule?'
    },
    'C': {
        'ru': 'Доброе утро!\n\nХрани воспоминания, мечты, обещания\nОткрывай их в нужный момент\n\nПопробовать бесплатно',
        'en': 'Good morning!\n\nStore memories, dreams, promises\nOpen them at the right moment\n\nTry for free'
    },
    'D': {
        'ru': 'Сколько важных моментов ты потерял за этот год?\n\nБольше ни одного 🔐\n\nСоздать капсулу',
        'en': 'How many important moments have you lost this year?\n\nNot one more 🔐\n\nCreate capsule'
    }
}

# Time-based greeting variations
ONBOARDING_TIME_GREETINGS = {
    'morning': {
        'ru': 'Доброе утро! ☀️',
        'en': 'Good morning! ☀️'
    },
    'afternoon': {
        'ru': 'Добрый день! 🌤',
        'en': 'Good afternoon! 🌤'
    },
    'evening': {
        'ru': 'Добрый вечер! 🌙',
        'en': 'Good evening! 🌙'
    }
}

async def show_main_menu_with_image(update: Update, context: ContextTypes.DEFAULT_TYPE, user_data: dict = None) -> int:
    """
    Show main menu with welcome image
    """
    user = update.effective_user

    if not user_data:
        user_data = get_user_data(user.id)

    if not user_data:
        logger.error(f"User data not found for {user.id}")
        return SELECTING_ACTION

    lang = user_data['language_code']
    caption_text = t(lang, 'start_welcome_full')
    keyboard = get_main_menu_keyboard(lang)

    # Use new helper function
    await send_menu_with_image(
        update=update,
        context=context,
        image_key='welcome',  # Uses assets/welcome.png
        caption=caption_text,
        keyboard=keyboard,
        parse_mode='HTML'
    )

    return SELECTING_ACTION

def get_time_of_day() -> str:
    """Get the time of day based on current hour"""
    current_hour = datetime.now().hour
    if 5 <= current_hour < 12:
        return 'morning'
    elif 12 <= current_hour < 18:
        return 'afternoon'
    else:
        return 'evening'

def assign_random_variant() -> str:
    """Randomly assign an onboarding variant for A/B testing"""
    return random.choice(list(ONBOARDING_GREETING_VARIANTS.keys()))

def get_onboarding_greeting(variant: str, lang: str, time_of_day: str) -> str:
    """Get personalized greeting based on variant, language and time"""
    time_greeting = ONBOARDING_TIME_GREETINGS.get(time_of_day, {}).get(lang, '')
    variant_greeting = ONBOARDING_GREETING_VARIANTS.get(variant, {}).get(lang, '')
    
    if time_greeting and variant != 'A':  # Variant A has its own greeting
        return f"{time_greeting}\n\n{variant_greeting}"
    return variant_greeting

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /start command with username capsule activation and onboarding"""
    user = update.effective_user

    # Check for deep link parameters
    args = context.args
    if args and len(args) > 0:
        param = args[0]
        if param.startswith('c_'):
            return await handle_capsule_activation(update, context, param)

    # Regular /start flow
    get_or_create_user(user)
    user_data = get_user_data(user.id)

    if not user_data:
        logger.error(f"Failed to create user {user.id}")
        lang = 'en'
        await update.message.reply_text(t(lang, 'error_creating_user'))
        return ConversationHandler.END

    lang = user_data['language_code']

    # Check if user has already completed onboarding
    onboarding_stage = user_data.get('onboarding_stage', 'not_started')
    
    # ⭐ NEW: Check if any capsules are waiting for this username
    if user.username:
        from ..database import check_and_activate_username_capsules
        activated_count = check_and_activate_username_capsules(user.id, user.username)

        if activated_count > 0:
            # Notify user about activated capsules
            await update.message.reply_text(
                t(lang, 'capsules_activated_for_you', count=activated_count),
                parse_mode='HTML'
            )

    # Check pending capsules
    pending_capsules = get_pending_capsules_for_user(user.id)
    pending_count = len(pending_capsules)

    if pending_count > 0:
        await update.message.reply_text(
            t(lang, 'pending_capsules', count=pending_count)
        )

    # Onboarding logic
    if onboarding_stage == 'not_started' or onboarding_stage not in ['completed', 'skipped']:
        # Initialize onboarding if not started
        if onboarding_stage == 'not_started':
            # Assign random onboarding variant for A/B testing
            variant = assign_random_variant()
            
            # Store user's onboarding variant in database
            from ..database import add_user_onboarding
            await add_user_onboarding(user.id, variant, 'start')
            
            # Send personalized onboarding greeting
            time_of_day = get_time_of_day()
            greeting = get_onboarding_greeting(variant, lang, time_of_day)
            await update.message.reply_text(greeting)
            
            logger.info(f"Started onboarding for user {user.id} with username {user.username}, variant {variant}")
            
            # Update onboarding stage
            await update_user_onboarding_stage(user.id, 'greeting_sent')
            
            # Since onboarding continues in a separate conversation, we'll show main menu for now
            # In a full implementation, we'd start a separate onboarding conversation
            return await show_main_menu_with_image(update, context, user_data)
        else:
            # User is in the middle of onboarding, show main menu after greeting
            return await show_main_menu_with_image(update, context, user_data)
    else:
        # User has completed or skipped onboarding, show main menu
        return await show_main_menu_with_image(update, context, user_data)

async def handle_capsule_activation(update: Update, context: ContextTypes.DEFAULT_TYPE, param: str) -> int:
    """Handle capsule activation via deep link"""
    user = update.effective_user

    # Ensure user exists
    get_or_create_user(user)
    user_data = get_user_data(user.id)
    lang = user_data['language_code']

    try:
        # Decode capsule UUID
        encoded_uuid = param.replace('c_', '')
        # Add padding if needed
        padding = 4 - (len(encoded_uuid) % 4)
        if padding != 4:
            encoded_uuid += '=' * padding

        capsule_uuid = base64.urlsafe_b64decode(encoded_uuid).decode()

        # Activate capsule
        success = activate_capsule_for_recipient(capsule_uuid, user.id)

        if success:
            # Get capsule info for confirmation message
            from ..database import capsules, engine
            from sqlalchemy import select

            with engine.connect() as conn:
                capsule_data = get_capsule_by_uuid(capsule_uuid)

            if capsule_data:
                sender_data = get_user_by_internal_id(capsule_data['user_id'])
                sender_name = sender_data.get('first_name', 'Anonymous') if sender_data else 'Anonymous'
                delivery_time_str = capsule_data['delivery_time'].strftime("%d.%m.%Y %H:%M")

                message_text = t(lang, 'capsule_activated_success',
                                delivery_time=delivery_time_str,
                                sender_name=sender_name)
            else:
                message_text = t(lang, 'capsule_activated_success',
                                delivery_time='soon',
                                sender_name='Anonymous')

            await update.message.reply_text(message_text, parse_mode='HTML')
        else:
            await update.message.reply_text(t(lang, 'capsule_already_activated'))

    except Exception as e:
        logger.error(f"Error activating capsule: {e}")
        await update.message.reply_text(t(lang, 'capsule_not_found'))

    # Show main menu - FIXED: Pass user_data
    return await show_main_menu_with_image(update, context, user_data)

async def select_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle language selection"""
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    selected_lang = query.data.replace('set_lang_', '')  # 'ru' or 'en'

    # Update user language
    if update_user_language(user.id, selected_lang):
        logger.info(f"User {user.id} selected language: {selected_lang}")
        # Show main menu with image - FIXED: get user_data properly
        user_data = get_user_data(user.id)
        return await show_main_menu_with_image(update, context, user_data)
    else:
        await query.edit_message_caption(caption=t(selected_lang, 'error_setting_language'))
        return ConversationHandler.END
