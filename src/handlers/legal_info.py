# src/handlers/legal_info.py

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from ..database import get_user_data
from ..translations import t
from ..config import MANAGING_LEGAL_INFO, SELECTING_ACTION, SUPPORT_EMAIL, SUPPORT_TELEGRAM_URL, LEGAL_REQUISITES_RU, LEGAL_REQUISITES_EN
from .main_menu import main_menu_handler
from ..image_menu import send_menu_with_image

def get_legal_info_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Generate legal info menu keyboard"""
    keyboard = [
        [InlineKeyboardButton(t(lang, 'legal_contacts'), callback_data='legal_contacts')],
        [InlineKeyboardButton(t(lang, 'legal_requisites'), callback_data='legal_requisites')],
        [InlineKeyboardButton(t(lang, 'legal_terms'), callback_data='legal_terms')],
        [InlineKeyboardButton(t(lang, 'legal_refund'), callback_data='legal_refund')],
        [InlineKeyboardButton(t(lang, 'back'), callback_data='main_menu')]
    ]
    return InlineKeyboardMarkup(keyboard)

async def show_legal_info_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show the legal information menu."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    lang = user_data.get('language_code', 'en')
    legal_text = t(lang, 'legal_info_title')
    await send_menu_with_image(
        update=update,
        context=context,
        image_key='legal',  # Uses assets/legal.png
        caption=legal_text,
        keyboard=get_legal_info_keyboard(lang),
        parse_mode='HTML'
    )
    return MANAGING_LEGAL_INFO

async def legal_info_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle legal info menu button clicks"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    lang = user_data.get('language_code', 'en')

    action = query.data

    if action == 'legal_info_menu':
        return await show_legal_info_menu(update, context)

    text = ""
    if action == 'legal_contacts':
        text = t(lang, 'legal_contacts_text', email=SUPPORT_EMAIL, telegram_url=SUPPORT_TELEGRAM_URL)
    elif action == 'legal_requisites':
        text = LEGAL_REQUISITES_RU if lang == 'ru' else LEGAL_REQUISITES_EN
    elif action == 'legal_terms':
        text = t(lang, 'legal_terms_text')
    elif action == 'legal_refund':
        text = t(lang, 'legal_refund_text', telegram_url=SUPPORT_TELEGRAM_URL)
    else:
        # If it's not a recognized legal content action, return to avoid processing
        return MANAGING_LEGAL_INFO

    await send_menu_with_image(
        update=update,
        context=context,
        image_key='legal',  # Uses assets/legal.png
        caption=text,
        keyboard=InlineKeyboardMarkup([[InlineKeyboardButton(t(lang, 'back'), callback_data='legal_info_menu')]]),
        parse_mode='HTML'
    )
    return MANAGING_LEGAL_INFO
