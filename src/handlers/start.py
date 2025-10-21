# src/handlers/start.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from ..database import get_user_data, users
from ..translations import t
from ..config import SELECTING_LANG, SELECTING_ACTION, logger
from .main_menu import get_main_menu_keyboard
from sqlalchemy import insert
from ..database import engine

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start command handler - shows language selection for new users"""
    user = update.effective_user
    
    # Check if user exists
    user_data = get_user_data(user.id)
    
    if not user_data:
        # New user - show language selection
        keyboard = [
            [InlineKeyboardButton('🇷🇺 Русский', callback_data='set_lang_ru')],
            [InlineKeyboardButton('🇬🇧 English', callback_data='set_lang_en')]
        ]
        
        await update.message.reply_text(
            "🌐 Выберите язык / Select language:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return SELECTING_LANG
    else:
        # Existing user - show main menu
        lang = user_data['language_code']
        await update.message.reply_text(
            t(lang, 'start_welcome'),
            reply_markup=get_main_menu_keyboard(lang)
        )
        return SELECTING_ACTION

async def select_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle language selection for new users"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    selected_lang = query.data.replace('set_lang_', '')  # 'ru' or 'en'
    
    # Create user with selected language
    try:
        with engine.connect() as conn:
            conn.execute(
                insert(users).values(
                    telegram_id=user.id,
                    username=user.username,
                    first_name=user.first_name,
                    language_code=selected_lang
                )
            )
            conn.commit()
        
        # Show welcome message in selected language
        await query.edit_message_text(
            t(selected_lang, 'start_welcome'),
            reply_markup=get_main_menu_keyboard(selected_lang)
        )
        
        logger.info(f"New user {user.id} registered with language: {selected_lang}")
        return SELECTING_ACTION
        
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        await query.edit_message_text("Error. Please try /start again.")
        return ConversationHandler.END