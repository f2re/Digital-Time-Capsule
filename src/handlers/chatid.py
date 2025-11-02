# src/handlers/chatid.py
from telegram import Update
from telegram.ext import ContextTypes
from ..database import get_user_data
from ..translations import t


async def chatid_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /chatid command - returns the current chat ID"""
    user = update.effective_user
    user_data = get_user_data(user.id)
    lang = user_data['language_code'] if user_data and 'language_code' in user_data else 'en'
    
    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type
    
    # Prepare response message
    response_message = t(lang, 'chatid_info', chat_id=chat_id, chat_type=chat_type)
    
    await update.message.reply_text(response_message, parse_mode='HTML')