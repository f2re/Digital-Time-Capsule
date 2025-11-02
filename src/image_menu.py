# src/utils/image_helper.py

import os
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from .config import MENU_IMAGES, DEFAULT_IMAGE, logger


async def send_menu_with_image(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    image_key: str,
    caption: str,
    keyboard: InlineKeyboardMarkup,
    parse_mode: str = 'HTML'
) -> None:
    """
    Universal function to send or edit message with image

    Args:
        update: Telegram update object
        context: Telegram context
        image_key: Key from MENU_IMAGES dict ('welcome', 'capsules', etc.)
        caption: Text caption for the image
        keyboard: InlineKeyboardMarkup for buttons
        parse_mode: Parse mode for caption (HTML or Markdown)
    """
    query = update.callback_query

    # Get image path
    image_path = MENU_IMAGES.get(image_key, DEFAULT_IMAGE)

    # Check if image exists
    if not os.path.exists(image_path):
        logger.warning(f"Image not found: {image_path}, using default")
        image_path = DEFAULT_IMAGE

    try:
        if query:
            # Callback query - need to delete old message and send new
            await query.answer()

            # Try to delete old message
            try:
                await query.message.delete()
            except Exception as e:
                logger.debug(f"Could not delete message: {e}")

            # Send new message with image
            with open(image_path, 'rb') as photo_file:
                await update.effective_chat.send_photo(
                    photo=photo_file,
                    caption=caption,
                    reply_markup=keyboard,
                    parse_mode=parse_mode
                )
        else:
            # Regular message command
            with open(image_path, 'rb') as photo_file:
                await update.effective_message.reply_photo(
                    photo=photo_file,
                    caption=caption,
                    reply_markup=keyboard,
                    parse_mode=parse_mode
                )

    except Exception as e:
        logger.error(f"Error sending image menu: {e}")
        # Fallback to text-only
        try:
            if query:
                await query.edit_message_text(
                    text=caption,
                    reply_markup=keyboard,
                    parse_mode=parse_mode
                )
            else:
                await update.effective_message.reply_text(
                    text=caption,
                    reply_markup=keyboard,
                    parse_mode=parse_mode
                )
        except Exception as e2:
            logger.error(f"Fallback also failed: {e2}")


async def edit_menu_with_image(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    image_key: str,
    caption: str,
    keyboard: InlineKeyboardMarkup,
    parse_mode: str = 'HTML'
) -> None:
    """
    Edit existing message with new image (deletes old, sends new)
    Same as send_menu_with_image but more explicit name for editing
    """
    await send_menu_with_image(update, context, image_key, caption, keyboard, parse_mode)
