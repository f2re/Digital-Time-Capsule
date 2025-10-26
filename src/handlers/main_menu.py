# src/handlers/main_menu.py

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from ..database import get_user_data
from ..translations import t
from ..config import SELECTING_ACTION, logger

def get_main_menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Generate main menu keyboard"""
    keyboard = [
        [InlineKeyboardButton(f"📝 {t(lang, 'create_capsule')}", callback_data='create')],
        [InlineKeyboardButton(f"📦 {t(lang, 'my_capsules')}", callback_data='capsules')],
        [InlineKeyboardButton(f"💎 {t(lang, 'subscription')}", callback_data='subscription')],
        [
            InlineKeyboardButton(f"⚙️ {t(lang, 'settings')}", callback_data='settings'),
            InlineKeyboardButton(f"❓ {t(lang, 'help')}", callback_data='help')
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

async def main_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle main menu button clicks"""
    from .create_capsule import start_create_capsule
    from .view_capsules import show_capsules
    from .subscription import show_subscription
    from .settings import show_settings
    from .start import show_main_menu_with_image

    query = update.callback_query
    if query:
        await query.answer()

    user = update.effective_user
    user_data = get_user_data(user.id)

    if not user_data:
        logger.error(f"User data not found for {user.id}")
        return SELECTING_ACTION

    lang = user_data['language_code']
    action = query.data if query else None

    logger.info(f"Main menu action: {action} from user {user.id}")

    # Route to specific handlers
    if action == 'create':
        return await start_create_capsule(update, context)

    elif action == 'capsules':
        return await show_capsules(update, context)

    elif action == 'subscription':
        return await show_subscription(update, context)

    elif action == 'settings':
        return await show_settings(update, context)

    elif action == 'help':
        # Show help text, then return to main menu button
        if query:
            try:
                await query.edit_message_text(
                    t(lang, 'help_text'),
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(t(lang, 'back'), callback_data='main_menu')
                    ]]),
                    parse_mode='Markdown'
                )
            except:
                await query.message.reply_text(
                    t(lang, 'help_text'),
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(t(lang, 'back'), callback_data='main_menu')
                    ]]),
                    parse_mode='Markdown'
                )
        return SELECTING_ACTION

    elif action in ('main_menu', 'cancel', 'confirm_no'):
        # ALWAYS return to BIG MENU with image
        return await show_main_menu_with_image(update, context, user_data)

    return SELECTING_ACTION
