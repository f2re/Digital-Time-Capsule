# src/handlers/delete_capsule.py
from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy import select
from ..database import engine, capsules, delete_capsule as db_delete_capsule
from ..s3_utils import delete_file_from_s3
from ..translations import t
from .view_capsules import show_capsules
from ..image_menu import send_menu_with_image

async def delete_capsule_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle capsule deletion"""
    query = update.callback_query
    await query.answer()

    capsule_id = int(query.data.split('_')[1])

    try:
        # Get capsule data to check for S3 key
        from ..database import get_capsule_s3_key
        s3_key = await get_capsule_s3_key(capsule_id)

        if s3_key:
            delete_file_from_s3(s3_key)

        # Delete from database
        db_delete_capsule(capsule_id)

        # Show updated capsule list
        return await show_capsules(update, context)

    except Exception as e:
        # Handle error
        user_data = context.user_data
        lang = user_data.get('language_code', 'en')
        try:
            await query.edit_message_text(t(lang, "error_occurred"))
        except Exception:
            # Fallback if edit_message_text fails (e.g., original message has no text)
            try:
                await query.edit_message_caption(caption=t(lang, "error_occurred"))
            except Exception:
                # If both fail, send a new message
                await query.message.reply_text(t(lang, "error_occurred"))
        return -1
