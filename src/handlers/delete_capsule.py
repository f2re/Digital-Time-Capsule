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
        with engine.connect() as conn:
            # Get capsule data to check for S3 key
            capsule_data = conn.execute(
                select(capsules.c.s3_key)
                .where(capsules.c.id == capsule_id)
            ).first()

            if capsule_data and capsule_data.s3_key:
                delete_file_from_s3(capsule_data.s3_key)

            # Delete from database
            db_delete_capsule(capsule_id)

            # Show updated capsule list
            return await show_capsules(update, context)

    except Exception as e:
        # Handle error
        user_data = context.user_data
        lang = user_data.get('language_code', 'en')
        await query.edit_message_text(t(lang, "error_occurred"))
        return -1
