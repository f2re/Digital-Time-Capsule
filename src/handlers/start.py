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
    engine
)
from sqlalchemy import select

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /start command with username capsule activation"""
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

    # Show main menu
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
                result = conn.execute(
                    select(capsules.c.delivery_time, capsules.c.user_id)
                    .where(capsules.c.capsule_uuid == capsule_uuid)
                ).first()

            if result:
                delivery_time, sender_id = result
                sender_data = get_user_by_internal_id(sender_id)
                sender_name = sender_data.get('first_name', 'Anonymous') if sender_data else 'Anonymous'
                delivery_time_str = delivery_time.strftime("%d.%m.%Y %H:%M")

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
