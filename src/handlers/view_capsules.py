# src/handlers/view_capsules.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from sqlalchemy import select, and_
from ..database import get_user_data, capsules, engine
from ..image_menu import send_menu_with_image
from ..translations import t
from ..config import SELECTING_ACTION, VIEWING_CAPSULES, PREMIUM_CAPSULE_LIMIT, FREE_CAPSULE_LIMIT, logger

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

async def show_capsules(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show user's capsules"""
    query = update.callback_query
    if query:
        await query.answer()

    user = update.effective_user
    userdata = get_user_data(user.id)

    if not userdata:
        return SELECTING_ACTION

    lang = userdata['language_code']

    try:
        with engine.connect() as conn:
            capsule_rows = conn.execute(
                select(capsules)
                .where(and_(
                    capsules.c.user_id == userdata['id'],
                    capsules.c.delivered == False
                ))
                .order_by(capsules.c.delivery_time)
            ).fetchall()

            keyboard = [[InlineKeyboardButton(t(lang, "main_menu"), callback_data="main_menu")]]

            if not capsule_rows:
                text = t(lang, "no_capsules")
            else:
                is_premium = userdata['subscription_status'] == 'premium'
                limit = PREMIUM_CAPSULE_LIMIT if is_premium else FREE_CAPSULE_LIMIT

                text = t(lang, "capsule_list", count=len(capsule_rows), limit=limit)

                content_emoji = {
                    "text": "📝",
                    "photo": "📷",
                    "video": "🎥",
                    "document": "📎",
                    "voice": "🎙️"
                }

                capsule_keyboard = []
                for cap in capsule_rows[:10]:  # Show max 10
                    cap_dict = dict(cap._mapping)
                    emoji = content_emoji.get(cap_dict['content_type'], "📦")

                    recipient = cap_dict['recipient_type']
                    if cap_dict['recipient_type'] == "self":
                        recipient = t(lang, "recipient_self")

                    item_text = t(lang, "capsule_item",
                                emoji=emoji,
                                type=cap_dict['content_type'],
                                recipient=recipient,
                                time=cap_dict['delivery_time'].strftime("%d.%m.%Y %H:%M"),
                                created=cap_dict['created_at'].strftime("%d.%m.%Y"))

                    text += f"\n{item_text}"

                    capsule_keyboard.append([
                        InlineKeyboardButton(
                            f"{emoji} {cap_dict['delivery_time'].strftime('%d.%m %H:%M')}",
                            callback_data=f"view_{cap_dict['id']}"
                        ),
                        InlineKeyboardButton(
                            t(lang, "delete_capsule"),
                            callback_data=f"delete_{cap_dict['id']}"
                        )
                    ])

                keyboard = capsule_keyboard + keyboard

            await send_menu_with_image(
                update=update,
                context=context,
                image_key='capsules',  # Uses assets/capsules.png
                caption=text,
                keyboard=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )

            return VIEWING_CAPSULES

    except Exception as e:
        logger.error(f"Error showing capsules: {e}")
        keyboard = [[InlineKeyboardButton(t(lang, "main_menu"), callback_data="main_menu")]]

        # Send error message based on context
        if query and query.message:
            await safe_edit_message(query, t(lang, "error_occurred"), InlineKeyboardMarkup(keyboard))
        else:
            message = update.message or update.effective_message
            if message:
                await message.reply_text(
                    t(lang, "error_occurred"),
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )

        return SELECTING_ACTION
