# src/handlers/settings.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from ..database import get_user_data, update_user_language
from ..translations import t
from ..config import SELECTING_ACTION, MANAGING_SETTINGS, logger
from ..image_menu import send_menu_with_image

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

    # Prepare settings text
    settings_text = t(lang, "settings") + "\n\n" + t(lang, "select_language")

    try:
        if query and query.message:
            # Delete old message and send new with image
            try:
                await query.message.delete()
            except:
                pass  # If delete fails, continue anyway
            
            await send_menu_with_image(
                update=update,
                context=context,
                image_key='settings',  # Uses assets/settings.png
                caption=settings_text,
                keyboard=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
        else:
            await send_menu_with_image(
                update=update,
                context=context,
                image_key='settings',  # Uses assets/settings.png
                caption=settings_text,
                keyboard=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
    except Exception as e:
        logger.error(f"Error in show_settings: {e}")
        # Fallback to text-only
        if query:
            try:
                await query.edit_message_text(
                    text=settings_text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except:
                pass
        else:
            await update.effective_message.reply_text(
                settings_text,
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
