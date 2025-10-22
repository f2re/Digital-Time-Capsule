# src/handlers/start.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from ..database import get_or_create_user, update_user_language,get_user_data
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
        lang = user_data['language_code']
        with open(WELCOME_IMAGE_PATH, 'rb') as photo_file:
            await update.message.reply_photo(
                photo=photo_file,
                caption=t(lang, 'start_welcome_full'),
                reply_markup=get_main_menu_keyboard(lang),
                parse_mode='HTML'
            )
        return SELECTING_ACTION

async def select_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle language selection"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    selected_lang = query.data.replace('set_lang_', '')  # 'ru' or 'en'
    
    # Update user language
    if update_user_language(user.id, selected_lang):
        # Show welcome message in selected language
        await query.edit_message_text(
            t(selected_lang, 'start_welcome'),
            reply_markup=get_main_menu_keyboard(selected_lang)
        )
        
        logger.info(f"User {user.id} selected language: {selected_lang}")
        return SELECTING_ACTION
    else:
        await query.edit_message_text("Error setting language. Please try /start again.")
        return ConversationHandler.END