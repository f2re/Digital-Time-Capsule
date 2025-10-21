# src/handlers/view_capsules.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from sqlalchemy import select, and_
from ..database import get_user_data, capsules, engine
from ..translations import t
from ..config import SELECTING_ACTION, VIEWING_CAPSULES, PREMIUM_CAPSULE_LIMIT, FREE_CAPSULE_LIMIT, logger

async def show_capsules(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show user's capsules"""
    query = update.callback_query
    if query:
        await query.answer()
    
    user = update.effective_user
    userdata = get_user_data(user.id)
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
            
            if not capsule_rows:
                keyboard = [[InlineKeyboardButton(t(lang, "main_menu"), callback_data="main_menu")]]
                
                # Send message based on context
                if query and query.message:
                    await query.edit_message_text(
                        t(lang, "no_capsules"),
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                else:
                    message = update.message or update.effective_message
                    if message:
                        await message.reply_text(
                            t(lang, "no_capsules"),
                            reply_markup=InlineKeyboardMarkup(keyboard)
                        )
                return SELECTING_ACTION
            
            is_premium = userdata['subscription_status'] == 'premium'
            limit = PREMIUM_CAPSULE_LIMIT if is_premium else FREE_CAPSULE_LIMIT
            
            capsules_text = t(lang, "capsule_list", count=len(capsule_rows), limit=limit)
            
            content_emoji = {
                "text": "📝",
                "photo": "📷",
                "video": "🎥",
                "document": "📎",
                "voice": "🎙️"
            }
            
            keyboard = []
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
                
                capsules_text += f"\n{item_text}"
                
                keyboard.append([
                    InlineKeyboardButton(
                        f"{emoji} {cap_dict['delivery_time'].strftime('%d.%m %H:%M')}",
                        callback_data=f"view_{cap_dict['id']}"
                    ),
                    InlineKeyboardButton(
                        t(lang, "delete_capsule"),
                        callback_data=f"delete_{cap_dict['id']}"
                    )
                ])
            
            keyboard.append([InlineKeyboardButton(t(lang, "main_menu"), callback_data="main_menu")])
            
            # Send message based on context
            if query and query.message:
                await query.edit_message_text(
                    capsules_text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                message = update.message or update.effective_message
                if message:
                    await message.reply_text(
                        capsules_text,
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
            
            return VIEWING_CAPSULES
            
    except Exception as e:
        logger.error(f"Error showing capsules: {e}")
        keyboard = [[InlineKeyboardButton(t(lang, "main_menu"), callback_data="main_menu")]]
        
        # Send error message based on context
        if query and query.message:
            await query.edit_message_text(
                t(lang, "error_occurred"),
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            message = update.message or update.effective_message
            if message:
                await message.reply_text(
                    t(lang, "error_occurred"),
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        
        return SELECTING_ACTION
