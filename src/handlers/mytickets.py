"""
Handler for viewing and replying to user's support tickets
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    CallbackQueryHandler, MessageHandler, filters
)
from ..database import (
    get_user_support_tickets, get_support_ticket, get_ticket_responses,
    add_ticket_response, get_user_data_by_telegram_id
)
from ..translations import t
from ..config import ADMIN_IDS

# Conversation states
LISTING_TICKETS, VIEWING_TICKET, AWAITING_REPLY = range(3)

async def my_tickets_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the my_tickets conversation"""
    user = update.effective_user
    user_data = get_user_data_by_telegram_id(user.id)
    lang = user_data['language_code'] if user_data else 'en'

    tickets = get_user_support_tickets(user_data['id'])

    if not tickets:
        await update.message.reply_text(t(lang, 'no_support_tickets'))
        return ConversationHandler.END

    keyboard = []
    for ticket in tickets:
        status_icon = "🔴" if ticket['status'] == 'open' else "✅"
        button_text = f"{status_icon} #{ticket['id']} - {ticket['subject']}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"view_ticket_{ticket['id']}")])
    
    keyboard.append([InlineKeyboardButton(t(lang, 'close'), callback_data='close_tickets')])

    await update.message.reply_text(
        t(lang, 'select_ticket_to_view'),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return LISTING_TICKETS

async def view_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """View a specific ticket and its conversation history"""
    query = update.callback_query
    await query.answer()

    ticket_id = int(query.data.split('_')[2])
    user = query.from_user
    user_data = get_user_data_by_telegram_id(user.id)
    lang = user_data['language_code'] if user_data else 'en'

    ticket = get_support_ticket(ticket_id, user_data['id'])
    if not ticket:
        await query.edit_message_text(t(lang, 'ticket_not_found'))
        return ConversationHandler.END

    context.user_data['current_ticket_id'] = ticket_id
    responses = get_ticket_responses(ticket_id)

    message = (
        f"<b>Ticket #{ticket['id']}</b>\n"
        f"<b>Subject:</b> {ticket['subject']}\n"
        f"<b>Status:</b> {ticket['status'].title()}\n\n"
        f"<b>Original Message:</b>\n{ticket['message']}\n\n"
        f"""--- <b>Conversation</b> ---
"""
    )

    for response in responses:
        author = "Admin" if response['is_admin_response'] else "You"
        message += f"<b>{author}</b> ({response['created_at'].strftime('%Y-%m-%d %H:%M')} UTC):\n{response['message']}\n\n"

    keyboard = [
        [InlineKeyboardButton(t(lang, 'reply_to_ticket'), callback_data=f"reply_ticket_{ticket_id}")],
        [InlineKeyboardButton(t(lang, 'close_ticket'), callback_data=f"close_user_ticket_{ticket_id}")],
        [InlineKeyboardButton(t(lang, 'back_to_list'), callback_data='list_tickets')]
    ]

    await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    return VIEWING_TICKET

async def prompt_for_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Prompt the user to enter their reply"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    user_data = get_user_data_by_telegram_id(user.id)
    lang = user_data['language_code'] if user_data else 'en'

    await query.edit_message_text(t(lang, 'enter_your_reply'))
    return AWAITING_REPLY

async def receive_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive and save the user's reply"""
    user = update.effective_user
    user_data = get_user_data_by_telegram_id(user.id)
    lang = user_data['language_code'] if user_data else 'en'
    ticket_id = context.user_data.get('current_ticket_id')

    if not ticket_id:
        await update.message.reply_text(t(lang, 'error_occurred'))
        return ConversationHandler.END

    # Add the user's reply to the ticket
    response_id = add_ticket_response(ticket_id, user_data['id'], update.message.text, is_admin=False)
    
    if response_id:
        await update.message.reply_text(t(lang, 'reply_sent'))

        # Notify admins with the actual message content
        from ..config import logger
        for admin_id in ADMIN_IDS:
            try:
                admin_notification = f"📨 Новый ответ в обращении #{ticket_id} от {user.first_name} (@{user.username or 'no_username'}):\n\n{update.message.text}"
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=admin_notification
                )
            except Exception as e:
                logger.error(f"Failed to send message to admin {admin_id}: {e}")
    else:
        await update.message.reply_text("❌ Не удалось сохранить ответ.")

    return await my_tickets_command(update, context)

async def close_tickets_view(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Close the ticket view"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Ticket view closed.")
    return ConversationHandler.END

async def close_user_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Close a ticket from user side"""
    query = update.callback_query
    await query.answer()
    
    ticket_id = context.user_data.get('current_ticket_id')
    if not ticket_id:
        await query.edit_message_text("❌ Не удалось найти обращение.")
        return ConversationHandler.END

    from ..database import close_support_ticket, get_user_data_by_telegram_id
    user = query.from_user
    user_data = get_user_data_by_telegram_id(user.id)
    
    success = close_support_ticket(ticket_id, user_data['id'])

    if success:
        await query.edit_message_text(f"✅ Обращение #{ticket_id} закрыто.")
        
        # Notify admins that the ticket was closed by user
        from ..config import ADMIN_IDS, logger
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=f"ℹ️ Пользователь закрыл обращение #{ticket_id}"
                )
            except Exception as e:
                logger.error(f"Failed to notify admin {admin_id} about ticket closure: {e}")
    else:
        await query.edit_message_text("❌ Не удалось закрыть обращение.")

    # Return to ticket list
    from ..database import get_user_support_tickets
    tickets = get_user_support_tickets(user_data['id'])

    if not tickets:
        await query.message.reply_text("У вас нет обращений в поддержку.")
        return ConversationHandler.END

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    from ..translations import t
    
    keyboard = []
    for ticket in tickets:
        status_icon = "🔴" if ticket['status'] == 'open' else "✅"
        button_text = f"{status_icon} #{ticket['id']} - {ticket['subject']}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"view_ticket_{ticket['id']}")])
    
    keyboard.append([InlineKeyboardButton(t(user_data['language_code'], 'close'), callback_data='close_tickets')])

    await query.edit_message_text(
        t(user_data['language_code'], 'select_ticket_to_view'),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return LISTING_TICKETS


def my_tickets_handler():
    """Create and return the my_tickets conversation handler"""
    return ConversationHandler(
        entry_points=[CommandHandler('mytickets', my_tickets_command)],
        states={
            LISTING_TICKETS: [
                CallbackQueryHandler(view_ticket, pattern='^view_ticket_'),
                CallbackQueryHandler(close_tickets_view, pattern='^close_tickets$')
            ],
            VIEWING_TICKET: [
                CallbackQueryHandler(prompt_for_reply, pattern='^reply_ticket_'),
                CallbackQueryHandler(close_user_ticket, pattern='^close_user_ticket_'),
                CallbackQueryHandler(my_tickets_command, pattern='^list_tickets$')
            ],
            AWAITING_REPLY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_reply)
            ]
        },
        fallbacks=[CommandHandler('cancel', close_tickets_view)],
        name="mytickets_conversation",
        persistent=False
    )