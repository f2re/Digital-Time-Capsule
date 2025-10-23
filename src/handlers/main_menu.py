# src/handlers/main_menu.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from ..database import get_user_data
from ..translations import t
from ..config import SELECTING_ACTION, logger
from .create_capsule import start_create_capsule
from .view_capsules import show_capsules
from .subscription import show_subscription
from .settings import show_settings

def get_main_menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Generate main menu keyboard"""
    keyboard = [
        [InlineKeyboardButton(t(lang, 'create_capsule'), callback_data='create')],
        [InlineKeyboardButton(t(lang, 'my_capsules'), callback_data='capsules')],
        [InlineKeyboardButton(t(lang, 'subscription'), callback_data='subscription')],
        [
            InlineKeyboardButton(t(lang, 'settings'), callback_data='settings'),
            InlineKeyboardButton(t(lang, 'help'), callback_data='help')
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

async def safe_edit_message(query, text, keyboard):
    """Safely edit message, trying different methods"""
    try:
        await query.edit_message_text(
            text=text,
            reply_markup=keyboard
        )
    except:
        try:
            await query.edit_message_caption(
                caption=text,
                reply_markup=keyboard
            )
        except:
            # Last resort - send new message
            await query.message.reply_text(
                text,
                reply_markup=keyboard
            )

async def main_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle main menu button clicks"""
    query = update.callback_query
    if query:
        await query.answer()

    user = update.effective_user
    user_data = get_user_data(user.id)
    
    if not user_data:
        return SELECTING_ACTION
        
    lang = user_data['language_code']
    action = query.data if query else None

    if action == 'create':
        return await start_create_capsule(update, context)
    elif action == 'capsules':
        return await show_capsules(update, context)
    elif action == 'subscription':
        return await show_subscription(update, context)
    elif action == 'settings':
        return await show_settings(update, context)
    elif action == 'help':
        if query:
            await safe_edit_message(
                query, 
                t(lang, 'help_text'),
                InlineKeyboardMarkup([[
                    InlineKeyboardButton(t(lang, 'back'), callback_data='main_menu')
                ]])
            )
        return SELECTING_ACTION
    elif action == 'main_menu':
        if query:
            await safe_edit_message(
                query,
                t(lang, 'main_menu'),
                get_main_menu_keyboard(lang)
            )
        return SELECTING_ACTION

    return SELECTING_ACTION
