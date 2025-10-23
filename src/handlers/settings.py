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
    
    if not userdata:
        return SELECTING_ACTION
        
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
    
    try:
        if query and query.message:
            # Try to edit as text first, then as caption
            try:
                await query.edit_message_text(
                    text=t(lang, "settings"),
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except:
                try:
                    await query.edit_message_caption(
                        caption=t(lang, "settings"),
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                except:
                    # Last resort - send new message
                    await query.message.reply_text(
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
    except Exception as e:
        logger.error(f"Error in show_settings: {e}")
    
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
