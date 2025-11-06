"""
Admin handlers for Digital Time Capsule bot
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    CallbackQueryHandler, MessageHandler, filters
)
from ..database import (
    get_open_support_tickets, get_support_ticket, get_ticket_responses,
    add_ticket_response, update_support_ticket_status, get_user_data_by_telegram_id,
    get_user_by_internal_id
)
from ..translations import t
from ..config import ADMIN_IDS

# Conversation states
ADMIN_LISTING_TICKETS, ADMIN_VIEWING_TICKET, ADMIN_AWAITING_REPLY = range(10, 13)

def is_admin(user_id: int) -> bool:
    """Check if a user is an admin"""
    return user_id in ADMIN_IDS

async def admin_tickets_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the admin_tickets conversation"""
    user = update.effective_user
    if not is_admin(user.id):
        return ConversationHandler.END

    user_data = get_user_data_by_telegram_id(user.id)
    lang = user_data['language_code'] if user_data else 'en'

    open_tickets = get_open_support_tickets()

    if not open_tickets:
        await update.message.reply_text(t(lang, 'no_open_tickets'))
        return ConversationHandler.END

    keyboard = []
    for ticket in open_tickets:
        button_text = f"Ticket #{ticket['id']} - {ticket['subject']}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"admin_view_ticket_{ticket['id']}")])
    
    keyboard.append([InlineKeyboardButton(t(lang, 'close'), callback_data='admin_close_tickets')])

    await update.message.reply_text(
        t(lang, 'select_ticket_to_view'),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ADMIN_LISTING_TICKETS

async def admin_view_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Admin views a specific ticket"""
    query = update.callback_query
    await query.answer()

    ticket_id = int(query.data.split('_')[3])
    user = query.from_user
    user_data = get_user_data_by_telegram_id(user.id)
    lang = user_data['language_code'] if user_data else 'en'

    # Admins can view any ticket, so we don't check user_id
    ticket = get_support_ticket(ticket_id, user_id=None)
    if not ticket:
        await query.edit_message_text(t(lang, 'ticket_not_found'))
        return ConversationHandler.END

    context.user_data['current_admin_ticket_id'] = ticket_id
    responses = get_ticket_responses(ticket_id)
    ticket_owner = get_user_by_internal_id(ticket['user_id'])

    message = (
        f"<b>Ticket #{ticket['id']}</b> by {ticket_owner['first_name']} (@{ticket_owner['username']})\n"
        f"<b>Subject:</b> {ticket['subject']}\n"
        f"<b>Status:</b> {ticket['status'].title()}\n\n"
        f"<b>Original Message:</b>\n{ticket['message']}\n\n"
        f"""--- <b>Conversation</b> ---
"""
    )

    for response in responses:
        author = "Admin" if response['is_admin_response'] else "User"
        message += f"<b>{author}</b> ({response['created_at'].strftime('%Y-%m-%d %H:%M')} UTC):\n{response['message']}\n\n"

    keyboard = [
        [InlineKeyboardButton(t(lang, 'reply_to_ticket'), callback_data=f"admin_reply_ticket_{ticket_id}")],
        [InlineKeyboardButton(t(lang, 'close_ticket'), callback_data=f"admin_close_ticket_{ticket_id}")],
        [InlineKeyboardButton(t(lang, 'back_to_list'), callback_data='admin_list_tickets')]
    ]

    await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    return ADMIN_VIEWING_TICKET

async def admin_prompt_for_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Prompt admin to enter their reply"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    user_data = get_user_data_by_telegram_id(user.id)
    lang = user_data['language_code'] if user_data else 'en'

    await query.edit_message_text(t(lang, 'enter_your_reply'))
    return ADMIN_AWAITING_REPLY

async def admin_receive_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive and save the admin's reply"""
    admin_user = update.effective_user
    admin_user_data = get_user_data_by_telegram_id(admin_user.id)
    lang = admin_user_data['language_code'] if admin_user_data else 'en'
    ticket_id = context.user_data.get('current_admin_ticket_id')

    if not ticket_id:
        await update.message.reply_text(t(lang, 'error_occurred'))
        return ConversationHandler.END

    # Add the admin's reply to the ticket
    response_id = add_ticket_response(ticket_id, admin_user_data['id'], update.message.text, is_admin=True)
    
    if response_id:
        await update.message.reply_text(t(lang, 'reply_sent'))

        # Notify user with the actual reply content
        ticket = get_support_ticket(ticket_id, user_id=None)
        ticket_owner = get_user_by_internal_id(ticket['user_id'])
        
        try:
            # Send notification to user with the admin's reply
            notification_message = f"📨 Ответ на ваше обращение #{ticket_id}\n\n{update.message.text}\n\nЕсли это не решает ваш вопрос, ответьте на это сообщение."
            await context.bot.send_message(
                chat_id=ticket_owner['telegram_id'],
                text=notification_message
            )
        except Exception as e:
            logger.error(f"Failed to send message to user {ticket_owner['telegram_id']}: {e}")
            await update.message.reply_text("⚠️ Не удалось отправить сообщение пользователю, но ответ сохранен в обращении.")
    else:
        await update.message.reply_text("❌ Не удалось сохранить ответ.")

    return await admin_tickets_command(update, context)

async def admin_close_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Close a ticket"""
    query = update.callback_query
    await query.answer()
    
    ticket_id = int(query.data.split('_')[3])
    update_support_ticket_status(ticket_id, 'closed')
    
    await query.edit_message_text(f"Ticket #{ticket_id} has been closed.")
    
    # Notify user
    ticket = get_support_ticket(ticket_id, user_id=None)
    ticket_owner = get_user_by_internal_id(ticket['user_id'])
    try:
        await context.bot.send_message(
            chat_id=ticket_owner['telegram_id'],
            text=f"Ваше обращение в поддержку #{ticket_id} закрыто администратором."
        )
    except Exception as e:
        logger.error(f"Failed to send message to user {ticket_owner['telegram_id']}: {e}")

    return await admin_tickets_command(update, context)


async def admin_close_tickets_view(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Close the admin ticket view"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Ticket view closed.")
    return ConversationHandler.END

def admin_handlers():
    """Create and return the admin conversation handler"""
    return [
        ConversationHandler(
            entry_points=[CommandHandler('admin_tickets', admin_tickets_command)],
            states={
                ADMIN_LISTING_TICKETS: [
                    CallbackQueryHandler(admin_view_ticket, pattern='^admin_view_ticket_'),
                    CallbackQueryHandler(admin_close_tickets_view, pattern='^admin_close_tickets$')
                ],
                ADMIN_VIEWING_TICKET: [
                    CallbackQueryHandler(admin_prompt_for_reply, pattern='^admin_reply_ticket_'),
                    CallbackQueryHandler(admin_close_ticket, pattern='^admin_close_ticket_'),
                    CallbackQueryHandler(admin_tickets_command, pattern='^admin_list_tickets$')
                ],
                ADMIN_AWAITING_REPLY: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, admin_receive_reply)
                ]
            },
            fallbacks=[CommandHandler('cancel', admin_close_tickets_view)],
            name="admin_tickets_conversation",
            persistent=False
        )
    ]