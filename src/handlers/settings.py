# src/handlers/settings.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from ..database import get_user_data, update_user_language
from ..translations import t
from ..config import SELECTING_ACTION, MANAGING_SETTINGS, logger

async def show_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show settings menu"""
    query = update.callback_query
    if query:
        await query.answer()
    
    user = update.effective_user
    userdata = get_user_data(user.id)
    lang = userdata['language_code']
    
    keyboard = [
        [
            InlineKeyboardButton(
                ("✅ " if lang == "ru" else "") + "🇷🇺 Русский",
                callback_data="set_lang_ru"
            ),
            InlineKeyboardButton(
                ("✅ " if lang == "en" else "") + "🇬🇧 English",
                callback_data="set_lang_en"
            )
        ],
        [InlineKeyboardButton(t(lang, "back"), callback_data="main_menu")]
    ]
    
    # Send message based on context
    if query and query.message:
        await query.edit_message_caption(
            caption=t(lang, "settings"),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        message = update.message or update.effective_message
        if message:
            await message.reply_text(
                t(lang, "settings"),
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    
    return MANAGING_SETTINGS

async def language_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle language selection"""
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    lang = "ru" if query.data == "set_lang_ru" else "en"
    
    update_user_language(user.id, lang)
    
    # Refresh settings menu
    return await show_settings(update, context)

