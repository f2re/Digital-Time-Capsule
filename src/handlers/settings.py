# src/handlers/settings.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from ..database import get_user_data, update_user_language
from ..translations import t
from ..config import SELECTING_ACTION, logger

async def show_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show settings menu"""
    query = update.callback_query
    if query:
        await query.answer()
    
    user = update.effective_user
    userdata = get_user_data(user.id)
    lang = userdata['language_code']
    
    keyboard = [
        [InlineKeyboardButton(
            "🇷🇺 Русский" if lang == "en" else "🇬🇧 English",
            callback_data="toggle_lang"
        )],
        [InlineKeyboardButton(t(lang, "back"), callback_data="main_menu")]
    ]
    
    # Send message based on context
    if query and query.message:
        await query.edit_message_text(
            t(lang, "settings"),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        message = update.message or update.effective_message
        if message:
            await message.reply_text(
                t(lang, "settings"),
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    
    return SELECTING_ACTION

async def toggle_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Toggle user language in settings"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    user_data = get_user_data(user.id)
    current_lang = user_data['language_code']
    
    # Switch language
    new_lang = 'en' if current_lang == 'ru' else 'ru'
    
    # Update in database
    if update_user_language(user.id, new_lang):
        # Show settings menu with new language
        other_lang_text = '🇬🇧 English' if new_lang == 'ru' else '🇷🇺 Русский'
        keyboard = [
            [InlineKeyboardButton(other_lang_text, callback_data='toggle_lang')],
            [InlineKeyboardButton(t(new_lang, 'back'), callback_data='main_menu')]
        ]
        
        await query.edit_message_text(
            f"{t(new_lang, 'language_changed')}\n\n{t(new_lang, 'settings')}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        logger.info(f"User {user.id} changed language to: {new_lang}")
    else:
        await query.edit_message_text(t(current_lang, 'error_occurred'))
        
    return SELECTING_ACTION
