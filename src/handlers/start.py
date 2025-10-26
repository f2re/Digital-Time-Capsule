# src/handlers/start.py

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from ..database import get_or_create_user, update_user_language, get_user_data
from ..translations import t
from ..config import SELECTING_LANG, SELECTING_ACTION, logger
from .main_menu import get_main_menu_keyboard
import os

WELCOME_IMAGE_PATH = os.path.join(
    os.path.dirname(__file__),
    '..', '..',
    'assets',
    'welcome.png'
)

async def show_main_menu_with_image(update: Update, context: ContextTypes.DEFAULT_TYPE, user_data: dict = None) -> int:
    """
    Universal function to show main menu with welcome image
    Works for both new messages and callback queries
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

    query = update.callback_query

    try:
        if query:
            # If it's a callback query, delete old message and send new one with image
            await query.answer()
            try:
                await query.message.delete()
            except:
                pass  # Message might be already deleted

            with open(WELCOME_IMAGE_PATH, 'rb') as photo_file:
                await update.effective_chat.send_photo(
                    photo=photo_file,
                    caption=caption_text,
                    reply_markup=keyboard,
                    parse_mode='HTML'
                )
        else:
            # New message command
            with open(WELCOME_IMAGE_PATH, 'rb') as photo_file:
                await update.message.reply_photo(
                    photo=photo_file,
                    caption=caption_text,
                    reply_markup=keyboard,
                    parse_mode='HTML'
                )
    except Exception as e:
        logger.error(f"Error showing main menu: {e}")
        # Fallback to text-only menu
        await update.effective_message.reply_text(
            caption_text,
            reply_markup=keyboard,
            parse_mode='HTML'
        )

    return SELECTING_ACTION

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start command handler - shows language selection for new users"""
    user = update.effective_user

    # Get or create user
    user_id = get_or_create_user(user)
    if not user_id:
        await update.message.reply_text("An error occurred. Please try again later.")
        return ConversationHandler.END

    user_data = get_user_data(user.id)

    if not user_data:
        # New user - language selection
        keyboard = [
            [InlineKeyboardButton('🇷🇺 Русский', callback_data='set_lang_ru')],
            [InlineKeyboardButton('🇬🇧 English', callback_data='set_lang_en')]
        ]

        with open(WELCOME_IMAGE_PATH, 'rb') as photo_file:
            await update.message.reply_photo(
                photo=photo_file,
                caption="🌐 Выберите язык / Select language:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return SELECTING_LANG

    else:
        # Existing user - show main menu with image
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

        # Show main menu with image
        user_data = get_user_data(user.id)
        return await show_main_menu_with_image(update, context, user_data)
    else:
        await query.edit_message_caption(caption="Error setting language. Please try /start again.")
        return ConversationHandler.END
