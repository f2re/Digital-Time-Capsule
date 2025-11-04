from telegram import Update
from telegram.ext import ContextTypes
from ..database import get_user_data
from ..translations import t

async def chatid_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /chatid command - returns chat ID, user ID, and other useful info"""
    user = update.effective_user
    chat = update.effective_chat

    # Get user data for language
    user_data = get_user_data(user.id)
    lang = user_data['language_code'] if user_data and 'language_code' in user_data else 'en'

    # Collect all relevant IDs and info
    chat_id = chat.id
    user_id = user.id
    chat_type = chat.type
    username = f"@{user.username}" if user.username else "No username"
    first_name = user.first_name or "No name"

    # Additional context for groups
    if chat_type in ['group', 'supergroup']:
        chat_title = chat.title or "Unnamed group"
        member_count = await context.bot.get_chat_member_count(chat_id) if chat_type == 'supergroup' else "Unknown"

        response_message = t(lang, 'chatid_info_group',
                           chat_id=chat_id,
                           user_id=user_id,
                           chat_type=chat_type,
                           chat_title=chat_title,
                           username=username,
                           first_name=first_name,
                           member_count=member_count)
    else:
        # Private chat
        response_message = t(lang, 'chatid_info_private',
                           chat_id=chat_id,
                           user_id=user_id,
                           chat_type=chat_type,
                           username=username,
                           first_name=first_name)

    await update.message.reply_text(response_message, parse_mode='HTML')

async def userid_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /userid command - returns just the user ID (quick reference)"""
    user = update.effective_user
    user_data = get_user_data(user.id)
    lang = user_data['language_code'] if user_data and 'language_code' in user_data else 'en'

    response_message = t(lang, 'userid_info', user_id=user.id)

    await update.message.reply_text(response_message, parse_mode='HTML')
