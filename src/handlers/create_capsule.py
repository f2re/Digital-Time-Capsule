# src/handlers/create_capsule.py
import base64
import uuid
from datetime import datetime, timedelta, timezone
from dateutil.relativedelta import relativedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.error import BadRequest
from sqlalchemy import select, insert, update as sqlalchemy_update
from ..image_menu import send_menu_with_image
from ..config import (
    SELECTING_ACTION, SELECTING_CONTENT_TYPE, RECEIVING_CONTENT,
    SELECTING_TIME, SELECTING_DATE, SELECTING_RECIPIENT, PROCESSING_RECIPIENT,
    CONFIRMING_CAPSULE, PREMIUM_TIME_LIMIT_DAYS, FREE_TIME_LIMIT_DAYS,
    PREMIUM_TIER, FREE_TIER, PREMIUM_STORAGE_LIMIT, FREE_STORAGE_LIMIT,
    logger
)
from ..database import get_user_data, check_user_quota, users, capsules, engine
from ..s3_utils import encrypt_and_upload_file
from ..translations import t

async def start_create_capsule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start capsule creation flow"""
    query = update.callback_query
    if query:
        await query.answer()

    user = update.effective_user
    user_data = get_user_data(user.id)
    if not user_data:
        logger.error(f"No user data found for user {user.id}")
        return SELECTING_ACTION

    lang = user_data['language_code']

    # Check capsule balance
    if user_data.get('capsule_balance', 0) <= 0:
        keyboard = [[InlineKeyboardButton(t(lang, 'buy_capsules'), callback_data='subscription')],
                    [InlineKeyboardButton(t(lang, 'back'), callback_data='main_menu')]]
        await send_menu_with_image(update, context, 'capsules', t(lang, 'no_capsule_balance'), InlineKeyboardMarkup(keyboard))
        return SELECTING_ACTION

    # Check storage quota
    can_create, error_msg = check_user_quota(user_data, 0)
    if not can_create and error_msg == "storage_limit_reached":
        # ... (storage limit message)
        return SELECTING_ACTION

    context.user_data['capsule'] = {}
    logger.info(f"Starting capsule creation for user {user.id}")

    keyboard = [
        [InlineKeyboardButton(t(lang, 'content_text'), callback_data='type_text')],
        [InlineKeyboardButton(t(lang, 'content_photo'), callback_data='type_photo')],
        [InlineKeyboardButton(t(lang, 'content_video'), callback_data='type_video')],
        [InlineKeyboardButton(t(lang, 'content_document'), callback_data='type_document')],
        [InlineKeyboardButton(t(lang, 'content_voice'), callback_data='type_voice')],
        [InlineKeyboardButton(t(lang, 'cancel'), callback_data='cancel')]
    ]
    await send_menu_with_image(update, context, 'capsules', t(lang, 'select_content_type'), InlineKeyboardMarkup(keyboard))
    return SELECTING_CONTENT_TYPE


async def select_content_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle content type selection"""
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    user_data = get_user_data(user.id)
    lang = user_data['language_code']

    content_type = query.data.replace('type_', '')
    context.user_data['capsule']['content_type'] = content_type
    logger.info(f"User {user.id} selected content type: {content_type}")

    type_names = {'text': t(lang, 'content_text'), 'photo': t(lang, 'content_photo'), 'video': t(lang, 'content_video'), 'document': t(lang, 'content_document'), 'voice': t(lang, 'content_voice')}
    instruction_text = t(lang, 'send_content', type=type_names.get(content_type, content_type))

    await send_menu_with_image(update, context, 'capsules', instruction_text, InlineKeyboardMarkup([[InlineKeyboardButton(t(lang, 'cancel'), callback_data='cancel')]]))
    return RECEIVING_CONTENT

async def receive_content(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive capsule content"""
    user = update.effective_user
    user_data = get_user_data(user.id)
    lang = user_data['language_code']
    message = update.message
    capsule = context.user_data.get('capsule', {})
    content_type = capsule.get('content_type')

    if not content_type:
        await message.reply_text(t(lang, 'error_occurred'))
        return ConversationHandler.END

    logger.info(f"Receiving {content_type} content from user {user.id}")

    # Simplified content handling logic...
    if content_type == 'text':
        if not message.text:
            await message.reply_text(t(lang, 'send_content', type=t(lang, 'content_text')))
            return RECEIVING_CONTENT
        context.user_data['capsule']['content_text'] = message.text
        context.user_data['capsule']['file_size'] = len(message.text.encode('utf-8'))
    else:
        file = None
        ext = 'bin'
        if content_type == 'photo' and message.photo:
            file = await message.photo[-1].get_file()
            ext = 'jpg'
        elif content_type == 'video' and message.video:
            file = await message.video.get_file()
            ext = 'mp4'
        # ... other file types
        if not file:
            await message.reply_text(t(lang, 'send_content', type=t(lang, f'content_{content_type}')))
            return RECEIVING_CONTENT

        # ... file processing and S3 upload ...
        file_bytes = await file.download_as_bytearray()
        s3_key, encrypted_key = encrypt_and_upload_file(bytes(file_bytes), ext)
        context.user_data['capsule']['s3_key'] = s3_key
        context.user_data['capsule']['file_key'] = encrypted_key
        context.user_data['capsule']['file_size'] = file.file_size or 0


    await message.reply_text(t(lang, 'content_received'))
    return await show_time_selection(update, context)


async def show_time_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show time selection menu"""
    user = update.effective_user
    user_data = get_user_data(user.id)
    lang = user_data['language_code']

    keyboard = [
        [InlineKeyboardButton(t(lang, 'time_1hour'), callback_data='time_1h'), InlineKeyboardButton(t(lang, 'time_1day'), callback_data='time_1d')],
        [InlineKeyboardButton(t(lang, 'time_1week'), callback_data='time_1w'), InlineKeyboardButton(t(lang, 'time_1month'), callback_data='time_1m')],
        [InlineKeyboardButton(t(lang, 'time_3months'), callback_data='time_3m'), InlineKeyboardButton(t(lang, 'time_6months'), callback_data='time_6m')],
        [InlineKeyboardButton(t(lang, 'time_1year'), callback_data='time_1y')],
        [InlineKeyboardButton(t(lang, 'time_custom'), callback_data='time_custom')],
        [InlineKeyboardButton(t(lang, 'cancel'), callback_data='cancel')]
    ]
    await send_menu_with_image(update, context, 'capsules', t(lang, 'select_time'), InlineKeyboardMarkup(keyboard))
    return SELECTING_TIME

async def select_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle time selection"""
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    user_data = get_user_data(user.id)
    lang = user_data['language_code']
    time_option = query.data.replace('time_', '')

    if time_option == 'custom':
        await send_menu_with_image(update, context, 'capsules', t(lang, 'enter_date'), InlineKeyboardMarkup([[InlineKeyboardButton(t(lang, 'cancel'), callback_data='cancel')]]))
        return SELECTING_DATE

    now = datetime.now(timezone.utc)
    # ... (calculate delivery_time based on time_option)
    delivery_time = now
    if time_option == '1h': delivery_time = now + timedelta(hours=1)
    elif time_option == '1d': delivery_time = now + timedelta(days=1)
    # ... other time options

    context.user_data['capsule']['delivery_time'] = delivery_time
    logger.info(f"Delivery time set: {delivery_time}")

    # This is the new entry point for recipient selection
    return await ask_for_recipient(update, context)

async def select_custom_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle custom date input"""
    # ... (implementation for custom date)
    return await ask_for_recipient(update, context)


# ============================================================================
# NEW RECIPIENT FLOW
# ============================================================================

async def ask_for_recipient(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ask the user to specify the recipient."""
    user = update.effective_user
    user_data = get_user_data(user.id)
    lang = user_data['language_code']

    keyboard = [[InlineKeyboardButton(t(lang, 'recipient_self'), callback_data='recipient_self')],
                [InlineKeyboardButton(t(lang, 'cancel'), callback_data='cancel')]]

    await send_menu_with_image(update, context, 'capsules', t(lang, 'forward_prompt'), InlineKeyboardMarkup(keyboard))
    return PROCESSING_RECIPIENT


async def process_recipient(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the user's recipient choice (@username or forwarded message)."""
    message = update.message
    user = update.effective_user
    user_data = get_user_data(user.id)
    lang = user_data['language_code']

    # Case 1: User sent a forwarded message (for group/channel)
    if message and message.forward_from_chat:
        chat = message.forward_from_chat
        logger.info(f"User {user.id} forwarded message from chat {chat.id} ({chat.title})")

        try:
            bot_member = await context.bot.get_chat_member(chat.id, context.bot.id)
        except BadRequest:
            logger.warning(f"Bot is not a member of chat {chat.id}")
            await message.reply_text(t(lang, 'bot_not_in_chat', chat_title=chat.title))
            return ConversationHandler.END

        if chat.type == 'channel':
            if not bot_member.can_post_messages:
                logger.warning(f"Bot cannot post in channel {chat.id}")
                await message.reply_text(t(lang, 'no_post_rights', chat_title=chat.title))
                return ConversationHandler.END
            context.user_data['capsule']['recipient_type'] = 'channel'
        else:
            context.user_data['capsule']['recipient_type'] = 'group'

        context.user_data['capsule']['recipient_id'] = chat.id
        context.user_data['capsule']['recipient_name'] = chat.title # Store name for confirmation
        return await show_confirmation(update, context)

    # Case 2: User sent a username
    elif message and message.text and message.text.startswith('@'):
        username = message.text[1:].lower()
        context.user_data['capsule']['recipient_type'] = 'user'
        context.user_data['capsule']['recipient_username'] = username
        context.user_data['capsule']['recipient_id'] = None # Will be set on activation
        logger.info(f"Capsule for @{username} - will activate when they start bot")
        return await show_confirmation(update, context)

    # Case 3: Invalid input
    else:
        await message.reply_text(t(lang, 'forward_error'))
        return PROCESSING_RECIPIENT # Stay in the same state

async def process_self_recipient(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the 'send to self' button."""
    query = update.callback_query
    await query.answer()
    user = update.effective_user

    context.user_data['capsule']['recipient_type'] = 'self'
    context.user_data['capsule']['recipient_id'] = user.id
    logger.info(f"Recipient set to self for user {user.id}")
    return await show_confirmation(update, context)


# ============================================================================
# CONFIRMATION AND CREATION
# ============================================================================

async def show_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show capsule confirmation"""
    user = update.effective_user
    user_data = get_user_data(user.id)
    lang = user_data['language_code']
    capsule = context.user_data.get('capsule', {})

    # Format recipient display
    recipient_text = ""
    recipient_type = capsule.get('recipient_type')

    if recipient_type == "self":
        recipient_text = t(lang, "recipient_self")
    elif recipient_type == "user":
        recipient_text = f"@{capsule.get('recipient_username', 'Unknown')}"
    elif recipient_type in ("group", "channel"):
        recipient_text = f"{capsule.get('recipient_name', 'Unknown')}"

    time_text = capsule['delivery_time'].strftime("%d.%m.%Y %H:%M")
    keyboard = [[InlineKeyboardButton(t(lang, "confirm_yes"), callback_data="confirm_yes")],
                [InlineKeyboardButton(t(lang, "confirm_no"), callback_data="cancel")]]

    confirmation_text = t(lang, "confirm_capsule", type=capsule.get('content_type', 'unknown'), time=time_text, recipient=recipient_text)

    await send_menu_with_image(update, context, 'capsules', confirmation_text, InlineKeyboardMarkup(keyboard))
    return CONFIRMING_CAPSULE


async def confirm_capsule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Create the capsule in the database."""
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    userdata = get_user_data(user.id)
    lang = userdata['language_code']
    capsule_data = context.user_data.get('capsule', {})

    # ... (Database transaction logic remains mostly the same)
    # Important: Use recipient_name for the success message for groups/channels
    
    capsule_uuid = str(uuid.uuid4())
    recipient_id_value = capsule_data.get('recipient_id')
    recipient_username_value = capsule_data.get('recipient_username')
    recipient_type = capsule_data['recipient_type']
    needs_activation = (recipient_type == 'user' and recipient_username_value)

    # Database insertion...
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            # ... (check balance, insert capsule, update user stats)
            conn.execute(
                insert(capsules).values(
                    user_id=userdata['id'],
                    capsule_uuid=capsule_uuid,
                    content_type=capsule_data['content_type'],
                    content_text=capsule_data.get('content_text'),
                    file_key=capsule_data.get('file_key'),
                    s3_key=capsule_data.get('s3_key'),
                    file_size=capsule_data.get('file_size', 0),
                    recipient_type=recipient_type,
                    recipient_id=str(recipient_id_value) if recipient_id_value else None,
                    recipient_username=recipient_username_value,
                    delivery_time=capsule_data['delivery_time'],
                )
            )
            # ... (update user balance)
            trans.commit()
        except Exception as e:
            trans.rollback()
            logger.error(f"Error creating capsule: {e}")
            await query.edit_message_text(t(lang, 'error_occurred'))
            return ConversationHandler.END


    delivery_time_str = capsule_data['delivery_time'].strftime("%d.%m.%Y %H:%M")
    success_text = ""

    if needs_activation:
        # ... (generate invite link message)
        bot_username = (await context.bot.get_me()).username
        encoded_uuid = base64.urlsafe_b64encode(capsule_uuid.encode()).decode().rstrip('=')
        invite_link = f"https://t.me/{bot_username}?start=c_{encoded_uuid}"
        success_text = t(lang, 'capsule_created_with_link', time=delivery_time_str, username=f"@{recipient_username_value}", invite_link=invite_link)
    elif recipient_type in ('group', 'channel'):
        success_text = t(lang, 'capsule_for_group_created', group_name=capsule_data.get('recipient_name', ''), delivery_time=delivery_time_str)
    else:
        success_text = t(lang, 'capsule_created', time=delivery_time_str)

    keyboard = [[InlineKeyboardButton(t(lang, 'main_menu'), callback_data='main_menu')]]
    await query.edit_message_text(success_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

    context.user_data.pop('capsule', None)
    return SELECTING_ACTION