# src/handlers/help.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from ..database import get_user_data
from ..translations import t

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command"""
    user = update.effective_user
    user_data = get_user_data(user.id)
    lang = user_data['language_code'] if user_data else 'en'
    
    await update.message.reply_text(
        t(lang, 'help_text'),
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(t(lang, 'back'), callback_data='main_menu')
        ]])
    )
