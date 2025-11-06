"""
Support system handler for Digital Time Capsule bot
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters, CommandHandler, CallbackQueryHandler
from ..database import get_user_data, create_support_ticket, get_user_support_tickets
from ..translations import t
from ..config import SELECTING_ACTION, logger
from ..handlers.main_menu import main_menu_handler

# Define conversation states for support
SUPPORT_START, SUPPORT_SUBJECT, SUPPORT_MESSAGE, SUPPORT_CONFIRMATION = range(4)

async def support_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the support conversation"""
    user = update.effective_user
    user_data = get_user_data(user.id)
    lang = user_data['language_code'] if user_data else 'en'
    
    # Ask user what kind of support they need
    keyboard = [
        [InlineKeyboardButton(t(lang, 'support_general_question'), callback_data='support_general')],
        [InlineKeyboardButton(t(lang, 'support_technical_issue'), callback_data='support_tech')],
        [InlineKeyboardButton(t(lang, 'support_billing_question'), callback_data='support_billing')],
        [InlineKeyboardButton(t(lang, 'support_other'), callback_data='support_other')],
        [InlineKeyboardButton(t(lang, 'back'), callback_data='main_menu')]
    ]
    
    await update.message.reply_text(
        t(lang, 'support_welcome_message'),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return SUPPORT_START


async def support_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the initial support selection"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    user_data = get_user_data(user.id)
    lang = user_data['language_code'] if user_data else 'en'
    
    # Store the support category in context
    category_mapping = {
        'support_general': t(lang, 'support_general_question'),
        'support_tech': t(lang, 'support_technical_issue'), 
        'support_billing': t(lang, 'support_billing_question'),
        'support_other': t(lang, 'support_other')
    }
    
    category_key = query.data
    if category_key in category_mapping:
        context.user_data['support_category'] = category_mapping[category_key]
        
        # Ask for subject
        await query.edit_message_text(
            text=f"{t(lang, 'support_select_subject')}\n\n{t(lang, 'current_selection')} {category_mapping[category_key]}"
        )
        
        return SUPPORT_SUBJECT
    else:
        # Handle main_menu case
        return await main_menu_handler(update, context)


async def support_get_subject(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Get the subject for the support ticket"""
    user = update.effective_user
    user_data = get_user_data(user.id)
    lang = user_data['language_code'] if user_data else 'en'
    
    subject = update.message.text
    
    # Validate subject length
    if len(subject.strip()) < 3:
        await update.message.reply_text(t(lang, 'support_subject_too_short'))
        return SUPPORT_SUBJECT
    
    if len(subject.strip()) > 100:
        await update.message.reply_text(t(lang, 'support_subject_too_long'))
        return SUPPORT_SUBJECT
    
    # Store subject in context
    context.user_data['support_subject'] = subject
    
    # Ask for message details
    await update.message.reply_text(
        t(lang, 'support_enter_message').format(category=context.user_data.get('support_category', 'General')),
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(t(lang, 'back'), callback_data='support_back_to_category')
        ]])
    )
    
    return SUPPORT_MESSAGE


async def support_get_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Get the detailed message for the support ticket"""
    user = update.effective_user
    user_data = get_user_data(user.id)
    lang = user_data['language_code'] if user_data else 'en'
    
    message = update.message.text
    
    # Validate message length
    if len(message.strip()) < 5:
        await update.message.reply_text(t(lang, 'support_message_too_short'))
        return SUPPORT_MESSAGE
    
    if len(message.strip()) > 2000:  # Telegram message limit
        await update.message.reply_text(t(lang, 'support_message_too_long'))
        return SUPPORT_MESSAGE
    
    # Store message in context
    context.user_data['support_message'] = message
    
    # Show confirmation
    confirmation_text = t(lang, 'support_confirmation').format(
        category=context.user_data.get('support_category', 'General'),
        subject=context.user_data['support_subject'],
        message=message[:100] + "..." if len(message) > 100 else message
    )
    
    keyboard = [
        [InlineKeyboardButton(t(lang, 'support_create_ticket'), callback_data='confirm_create_ticket')],
        [InlineKeyboardButton(t(lang, 'support_edit_subject'), callback_data='edit_subject')],
        [InlineKeyboardButton(t(lang, 'support_edit_message'), callback_data='edit_message')],
        [InlineKeyboardButton(t(lang, 'back'), callback_data='support_back_to_category')]
    ]
    
    await update.message.reply_text(
        confirmation_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return SUPPORT_CONFIRMATION


async def support_confirmation_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle support confirmation callbacks"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    user_data = get_user_data(user.id)
    lang = user_data['language_code'] if user_data else 'en'
    
    action = query.data
    
    if action == 'confirm_create_ticket':
        # Create the support ticket
        from ..database import get_user_data_by_telegram_id
        db_user = get_user_data_by_telegram_id(user.id)
        
        if not db_user:
            await query.edit_message_text(t(lang, 'error_occurred'))
            return ConversationHandler.END
        
        ticket_id = create_support_ticket(
            user_id=db_user['id'],
            subject=context.user_data['support_subject'],
            message=context.user_data['support_message']
        )
        
        if ticket_id:
            await query.edit_message_text(
                t(lang, 'support_ticket_created').format(ticket_id=ticket_id)
            )
            
            # Send admin notification if needed (could be implemented later)
            logger.info(f"User {user.id} created support ticket #{ticket_id}")
        else:
            await query.edit_message_text(t(lang, 'support_ticket_creation_failed'))
        
        # Return to main menu
        return await main_menu_handler(update, context)
    
    elif action == 'edit_subject':
        await query.edit_message_text(t(lang, 'support_edit_subject_prompt'))
        return SUPPORT_SUBJECT
    
    elif action == 'edit_message':
        await query.edit_message_text(t(lang, 'support_edit_message_prompt'))
        return SUPPORT_MESSAGE
    
    elif action == 'support_back_to_category':
        # Go back to category selection
        keyboard = [
            [InlineKeyboardButton(t(lang, 'support_general_question'), callback_data='support_general')],
            [InlineKeyboardButton(t(lang, 'support_technical_issue'), callback_data='support_tech')],
            [InlineKeyboardButton(t(lang, 'support_billing_question'), callback_data='support_billing')],
            [InlineKeyboardButton(t(lang, 'support_other'), callback_data='support_other')],
            [InlineKeyboardButton(t(lang, 'back'), callback_data='main_menu')]
        ]
        
        await query.edit_message_text(
            t(lang, 'support_welcome_message'),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        return SUPPORT_START
    
    elif action == 'main_menu':
        return await main_menu_handler(update, context)
    
    return SUPPORT_CONFIRMATION


async def view_support_tickets(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Allow user to view their support tickets"""
    user = update.effective_user
    user_data = get_user_data(user.id)
    lang = user_data['language_code'] if user_data else 'en'
    
    tickets = get_user_support_tickets(user_data['id'])
    
    if not tickets:
        await update.message.reply_text(t(lang, 'no_support_tickets'))
    else:
        ticket_list = t(lang, 'your_support_tickets').format(count=len(tickets))
        for ticket in tickets[:10]:  # Show up to 10 most recent tickets
            status_icon = "🔴" if ticket['status'] == 'open' else "✅"
            ticket_list += f"\n\n{status_icon} #{ticket['id']} - {ticket['subject']}\n"
            ticket_list += f"📅 {ticket['created_at'].strftime('%d.%m.%Y %H:%M')}\n"
            ticket_list += f"📊 {ticket['status'].title()}"
        
        await update.message.reply_text(ticket_list)
    
    # Return to main menu
    return await main_menu_handler(update, context)


def support_conversation_handler():
    """Create and return the support conversation handler"""
    return ConversationHandler(
        entry_points=[CommandHandler('support', support_command)],
        states={
            SUPPORT_START: [
                CallbackQueryHandler(support_start, pattern='^(support_general|support_tech|support_billing|support_other|main_menu)$'),
            ],
            SUPPORT_SUBJECT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, support_get_subject),
                CallbackQueryHandler(support_confirmation_handler, pattern='^support_back_to_category$'),
                CallbackQueryHandler(cancel_support, pattern='^main_menu$')
            ],
            SUPPORT_MESSAGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, support_get_message),
                CallbackQueryHandler(support_confirmation_handler, pattern='^support_back_to_category$'),
                CallbackQueryHandler(cancel_support, pattern='^main_menu$')
            ],
            SUPPORT_CONFIRMATION: [
                CallbackQueryHandler(support_confirmation_handler, 
                                   pattern='^(confirm_create_ticket|edit_subject|edit_message|support_back_to_category|main_menu)$')
            ],
        },
        fallbacks=[
            CommandHandler('cancel', cancel_support),
            CallbackQueryHandler(cancel_support, pattern='^cancel$'),
            CallbackQueryHandler(cancel_support, pattern='^main_menu$')
        ],
        name="support_conversation",
        persistent=False,
        per_message=False
    )


async def cancel_support(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the support conversation and return to main menu"""
    user = update.effective_user
    user_data = get_user_data(user.id)
    lang = user_data['language_code'] if user_data else 'en'
    
    # Clear any stored support data
    if 'support_category' in context.user_data:
        del context.user_data['support_category']
    if 'support_subject' in context.user_data:
        del context.user_data['support_subject'] 
    if 'support_message' in context.user_data:
        del context.user_data['support_message']
    
    query = update.callback_query
    message = update.message
    
    if query:
        await query.answer()
        await query.edit_message_text(t(lang, 'support_cancelled'))
    elif message:
        await message.reply_text(t(lang, 'support_cancelled'))
    
    # Return to main menu
    return await main_menu_handler(update, context)