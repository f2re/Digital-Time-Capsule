# src/handlers/help.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from ..database import get_user_data
from ..image_menu import send_menu_with_image
from ..translations import t

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command"""
    user = update.effective_user
    user_data = get_user_data(user.id)
    lang = user_data['language_code'] if user_data else 'en'
    help_text = t(lang, 'help_text')
    keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(t(lang, 'back'), callback_data='main_menu')
        ]])

    await send_menu_with_image(
        update=update,
        context=context,
        image_key='help',  # Uses assets/help.png
        caption=help_text,
        keyboard=keyboard,
        parse_mode='HTML'
    )
