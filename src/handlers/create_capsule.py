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
        storage_limit = FREE_STORAGE_LIMIT if user_data['subscription_status'] == FREE_TIER else PREMIUM_STORAGE_LIMIT
        keyboard = [[InlineKeyboardButton(t(lang, 'back'), callback_data='main_menu')]]
        await send_menu_with_image(update, context, 'capsules',
                                  t(lang, 'storage_limit_reached', limit=f"{storage_limit // (1024*1024)} MB"),
                                  InlineKeyboardMarkup(keyboard))
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

    type_names = {
        'text': t(lang, 'content_text'),
        'photo': t(lang, 'content_photo'),
        'video': t(lang, 'content_video'),
        'document': t(lang, 'content_document'),
        'voice': t(lang, 'content_voice')
    }
    instruction_text = t(lang, 'send_content', type=type_names.get(content_type, content_type))

    keyboard = [[InlineKeyboardButton(t(lang, 'cancel'), callback_data='cancel')]]
    await send_menu_with_image(update, context, 'capsules', instruction_text, InlineKeyboardMarkup(keyboard))
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
        elif content_type == 'document' and message.document:
            file = await message.document.get_file()
            ext = message.document.file_name.split('.')[-1] if message.document.file_name and '.' in message.document.file_name else 'bin'
        elif content_type == 'voice' and message.voice:
            file = await message.voice.get_file()
            ext = 'ogg'

        if not file:
            await message.reply_text(t(lang, 'send_content', type=t(lang, f'content_{content_type}')))
            return RECEIVING_CONTENT

        # Check file size before uploading
        if file.file_size and file.file_size > 50 * 1024 * 1024:  # 50MB limit
            await message.reply_text(t(lang, 'file_too_large'))
            return RECEIVING_CONTENT

        # Check storage quota
        user_data_fresh = get_user_data(user.id)
        can_create, error_msg = check_user_quota(user_data_fresh, file.file_size or 0)
        if not can_create:
            if error_msg == "storage_limit_reached":
                storage_limit = FREE_STORAGE_LIMIT if user_data_fresh['subscription_status'] == FREE_TIER else PREMIUM_STORAGE_LIMIT
                await message.reply_text(t(lang, 'storage_limit_reached', limit=f"{storage_limit // (1024*1024)} MB"))
            else:
                await message.reply_text(t(lang, 'error_occurred'))
            return ConversationHandler.END

        try:
            file_bytes = await file.download_as_bytearray()
            s3_key, encrypted_key = encrypt_and_upload_file(bytes(file_bytes), ext)
            context.user_data['capsule']['s3_key'] = s3_key
            context.user_data['capsule']['file_key'] = encrypted_key
            context.user_data['capsule']['file_size'] = file.file_size or 0
        except Exception as e:
            logger.error(f"Error uploading file for user {user.id}: {e}")
            await message.reply_text(t(lang, 'error_occurred'))
            return ConversationHandler.END

    await message.reply_text(t(lang, 'content_received'))
    return await show_time_selection(update, context)


async def show_time_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show time selection menu"""
    user = update.effective_user
    user_data = get_user_data(user.id)
    lang = user_data['language_code']

    # Build keyboard based on subscription status
    keyboard = [
        [InlineKeyboardButton(t(lang, 'time_1hour'), callback_data='time_1h'),
         InlineKeyboardButton(t(lang, 'time_1day'), callback_data='time_1d')],
        [InlineKeyboardButton(t(lang, 'time_1week'), callback_data='time_1w'),
         InlineKeyboardButton(t(lang, 'time_1month'), callback_data='time_1m')],
        [InlineKeyboardButton(t(lang, 'time_3months'), callback_data='time_3m'),
         InlineKeyboardButton(t(lang, 'time_6months'), callback_data='time_6m')],
        [InlineKeyboardButton(t(lang, 'time_1year'), callback_data='time_1y')]
    ]

    keyboard.extend([
        [InlineKeyboardButton(t(lang, 'time_custom'), callback_data='time_custom')],
        [InlineKeyboardButton(t(lang, 'cancel'), callback_data='cancel')]
    ])

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
        keyboard = [[InlineKeyboardButton(t(lang, 'cancel'), callback_data='cancel')]]
        await send_menu_with_image(update, context, 'capsules', t(lang, 'enter_date'), InlineKeyboardMarkup(keyboard))
        return SELECTING_DATE

    now = datetime.now(timezone.utc)
    delivery_time = now

    # Calculate delivery time based on selection
    if time_option == '1h':
        delivery_time = now + timedelta(hours=1)
    elif time_option == '1d':
        delivery_time = now + timedelta(days=1)
    elif time_option == '1w':
        delivery_time = now + timedelta(weeks=1)
    elif time_option == '1m':
        delivery_time = now + relativedelta(months=1)
    elif time_option == '3m':
        delivery_time = now + relativedelta(months=3)
    elif time_option == '6m':
        delivery_time = now + relativedelta(months=6)
    elif time_option == '1y':
        delivery_time = now + relativedelta(years=1)
    elif time_option == '5y':
        delivery_time = now + relativedelta(years=5)
    elif time_option == '10y':
        delivery_time = now + relativedelta(years=10)
    elif time_option == '25y':
        delivery_time = now + relativedelta(years=25)

    # Validate time limits based on subscription
    max_days = PREMIUM_TIME_LIMIT_DAYS if user_data['subscription_status'] == PREMIUM_TIER else FREE_TIME_LIMIT_DAYS
    if (delivery_time - now).days > max_days:
        keyboard = [[InlineKeyboardButton(t(lang, 'upgrade_premium'), callback_data='subscription')],
                    [InlineKeyboardButton(t(lang, 'back'), callback_data='main_menu')]]
        await send_menu_with_image(update, context, 'capsules', t(lang, 'time_limit_exceeded'), InlineKeyboardMarkup(keyboard))
        return SELECTING_ACTION

    context.user_data['capsule']['delivery_time'] = delivery_time
    logger.info(f"Delivery time set: {delivery_time} for user {user.id}")

    return await ask_for_recipient(update, context)


async def select_custom_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle custom date input with timezone support"""
    message = update.message
    user = update.effective_user
    user_data = get_user_data(user.id)
    lang = user_data['language_code']
    user_timezone = user_data.get('timezone', 'UTC')

    if message.text:
        # Parse user input (expecting format like "31.12.2025 23:59")
        date_str = message.text.strip()

        try:
            # Import timezone utilities
            from ..timezone_utils import convert_local_to_utc
            from datetime import datetime
            import re

            # Parse date format DD.MM.YYYY HH:MM (the format mentioned in translations)
            date_pattern = r'^(\d{2})\.(\d{2})\.(\d{4})\s+(\d{2}):(\d{2})$'
            match = re.match(date_pattern, date_str)

            if not match:
                await message.reply_text(t(lang, 'invalid_date'))
                return SELECTING_DATE

            day, month, year, hour, minute = map(int, match.groups())
            local_delivery_time = datetime(year, month, day, hour, minute)

            # Convert from user's local timezone to UTC for storage
            delivery_time = convert_local_to_utc(local_delivery_time, user_timezone)

            # Check if date is in the future
            now_utc = datetime.now(timezone.utc)
            if delivery_time <= now_utc:
                await message.reply_text(t(lang, 'date_must_be_future'))
                return SELECTING_DATE

            # Check if date is too far in the future based on user's subscription
            from ..config import FREE_TIME_LIMIT_DAYS, PREMIUM_TIME_LIMIT_DAYS, PREMIUM_TIER
            max_days = PREMIUM_TIME_LIMIT_DAYS if user_data.get('subscription_status') == PREMIUM_TIER else FREE_TIME_LIMIT_DAYS

            max_allowed_date = now_utc + timedelta(days=max_days)

            if delivery_time > max_allowed_date:
                # Format the max days message based on user's subscription
                await message.reply_text(
                    t(lang, 'date_too_far',
                      days=FREE_TIME_LIMIT_DAYS,
                      years=PREMIUM_TIME_LIMIT_DAYS//365)
                )
                return SELECTING_DATE

            context.user_data['capsule']['delivery_time'] = delivery_time
            logger.info(f"Custom delivery time set: {delivery_time} (user's local: {local_delivery_time} in {user_timezone})")

            return await ask_for_recipient(update, context)

        except ValueError:
            await message.reply_text(t(lang, 'invalid_date'))
            return SELECTING_DATE
        except Exception as e:
            logger.error(f"Error parsing custom date: {e}")
            await message.reply_text(t(lang, 'invalid_date'))
            return SELECTING_DATE

    # If not a text message, reprompt
    await message.reply_text(t(lang, 'enter_date'))
    return SELECTING_DATE


# ============================================================================
# FIXED RECIPIENT FLOW - Updated for python-telegram-bot v20+
# ============================================================================

async def ask_for_recipient(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ask the user to specify the recipient."""
    user = update.effective_user
    user_data = get_user_data(user.id)
    lang = user_data['language_code']

    keyboard = [
        [InlineKeyboardButton(t(lang, 'recipient_self'), callback_data='recipient_self')],
        [InlineKeyboardButton(t(lang, 'cancel'), callback_data='cancel')]
    ]

    await send_menu_with_image(update, context, 'capsules', t(lang, 'forward_prompt'), InlineKeyboardMarkup(keyboard))
    return PROCESSING_RECIPIENT


async def process_recipient(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the user's recipient choice (@username or forwarded message)."""
    message = update.message
    user = update.effective_user
    user_data = get_user_data(user.id)
    lang = user_data['language_code']

    # FIXED: Use the new method to detect forwarded messages in v20+
    # Check multiple ways to detect chat selection
    chat_to_send = None
    is_forwarded = False

    # Method 1: Check if message has forward_origin (new API v21+)
    if hasattr(message, 'forward_origin') and message.forward_origin:
        is_forwarded = True
        # Get the original chat from forward_origin
        if hasattr(message.forward_origin, 'chat'):
            chat_to_send = message.forward_origin.chat
        elif hasattr(message.forward_origin, 'sender_chat'):
            chat_to_send = message.forward_origin.sender_chat

    # Method 2: Legacy support - check if forward_from_chat exists (v20.x)
    elif hasattr(message, 'forward_from_chat') and message.forward_from_chat:
        chat_to_send = message.forward_from_chat
        is_forwarded = True

    # Method 3: Check if user replied to a message in current chat
    elif message.reply_to_message and message.chat.type != 'private':
        # User replied to a message in a group/channel, use current chat
        chat_to_send = message.chat
        is_forwarded = True

    # Method 4: Check if message is from a group/channel (not private)
    elif message.chat.type in ['group', 'supergroup', 'channel'] and not message.text:
        # If user sent any non-text message from group/channel, treat as selection
        chat_to_send = message.chat
        is_forwarded = True

    # Case 1: Detected a chat (forwarded or group message)
    if is_forwarded and chat_to_send:
        logger.info(f"User {user.id} selected chat {chat_to_send.id} ({getattr(chat_to_send, 'title', 'Unknown')})")

        try:
            # Check if bot is a member and has permissions
            bot_member = await context.bot.get_chat_member(chat_to_send.id, context.bot.id)

            if chat_to_send.type == 'channel':
                # For channels, bot needs post permission
                if not (hasattr(bot_member, 'can_post_messages') and bot_member.can_post_messages):
                    logger.warning(f"Bot cannot post in channel {chat_to_send.id}")
                    await message.reply_text(t(lang, 'no_post_rights', chat_title=getattr(chat_to_send, 'title', 'Unknown')))
                    return PROCESSING_RECIPIENT
                context.user_data['capsule']['recipient_type'] = 'channel'
            else:
                # For groups, bot just needs to be a member
                context.user_data['capsule']['recipient_type'] = 'group'

        except BadRequest as e:
            logger.warning(f"Bot access issue for chat {chat_to_send.id}: {e}")
            await message.reply_text(t(lang, 'bot_not_in_chat', chat_title=getattr(chat_to_send, 'title', 'Unknown')))
            return PROCESSING_RECIPIENT
        except Exception as e:
            logger.error(f"Error checking bot membership: {e}")
            await message.reply_text(t(lang, 'error_occurred'))
            return PROCESSING_RECIPIENT

        context.user_data['capsule']['recipient_id'] = chat_to_send.id
        context.user_data['capsule']['recipient_name'] = getattr(chat_to_send, 'title', f"Chat {chat_to_send.id}")
        return await show_confirmation(update, context)

    # Case 2: User sent a username
    elif message and message.text and message.text.startswith('@'):
        username = message.text[1:].lower().strip()
        if not username:
            await message.reply_text(t(lang, 'invalid_username'))
            return PROCESSING_RECIPIENT

        context.user_data['capsule']['recipient_type'] = 'user'
        context.user_data['capsule']['recipient_username'] = username
        context.user_data['capsule']['recipient_id'] = None  # Will be resolved when user starts bot
        logger.info(f"Capsule for @{username} - will activate when they start bot")
        return await show_confirmation(update, context)

    # Case 3: User typed chat ID directly (for advanced users)
    elif message and message.text and message.text.lstrip('-').isdigit():
        try:
            chat_id = int(message.text)
            chat_info = await context.bot.get_chat(chat_id)

            # Check bot permissions
            bot_member = await context.bot.get_chat_member(chat_id, context.bot.id)

            if chat_info.type == 'channel':
                if not (hasattr(bot_member, 'can_post_messages') and bot_member.can_post_messages):
                    await message.reply_text(t(lang, 'no_post_rights', chat_title=getattr(chat_info, 'title', 'Unknown')))
                    return PROCESSING_RECIPIENT
                context.user_data['capsule']['recipient_type'] = 'channel'
            else:
                context.user_data['capsule']['recipient_type'] = 'group'

            context.user_data['capsule']['recipient_id'] = chat_id
            context.user_data['capsule']['recipient_name'] = getattr(chat_info, 'title', f"Chat {chat_id}")
            return await show_confirmation(update, context)

        except (ValueError, BadRequest) as e:
            logger.warning(f"Invalid chat ID {message.text} from user {user.id}: {e}")
            await message.reply_text(t(lang, 'invalid_chat_id'))
            return PROCESSING_RECIPIENT

    # Case 4: Invalid input
    else:
        await message.reply_text(t(lang, 'forward_error'))
        return PROCESSING_RECIPIENT


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

    # Format time display using user's timezone
    from ..timezone_utils import format_time_for_user
    user_timezone = user_data.get('timezone', 'UTC')
    time_text = format_time_for_user(capsule['delivery_time'], user_timezone, lang)

    # Format content type
    content_type_display = t(lang, f"content_{capsule.get('content_type', 'unknown')}")

    keyboard = [
        [InlineKeyboardButton(t(lang, "confirm_yes"), callback_data="confirm_yes")],
        [InlineKeyboardButton(t(lang, "confirm_no"), callback_data="cancel")]
    ]

    confirmation_text = t(lang, "confirm_capsule",
                         type=content_type_display,
                         time=time_text,
                         recipient=recipient_text)

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

    # Validate capsule data
    if not capsule_data.get('delivery_time') or not capsule_data.get('content_type'):
        logger.error(f"Invalid capsule data for user {user.id}: {capsule_data}")
        keyboard = [[InlineKeyboardButton(t(lang, 'main_menu'), callback_data='main_menu')]]
        await send_menu_with_image(update, context, 'capsules', t(lang, 'error_occurred'), InlineKeyboardMarkup(keyboard))
        return SELECTING_ACTION

    capsule_uuid = str(uuid.uuid4())
    recipient_id_value = capsule_data.get('recipient_id')
    recipient_username_value = capsule_data.get('recipient_username')
    recipient_type = capsule_data['recipient_type']

    # Database transaction
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            # Check user balance again
            user_check = conn.execute(select(users.c.capsule_balance).where(users.c.id == userdata['id'])).first()
            if not user_check or user_check.capsule_balance <= 0:
                trans.rollback()
                keyboard = [[InlineKeyboardButton(t(lang, 'buy_capsules'), callback_data='subscription')],
                           [InlineKeyboardButton(t(lang, 'main_menu'), callback_data='main_menu')]]
                await send_menu_with_image(update, context, 'capsules', t(lang, 'insufficient_balance'), InlineKeyboardMarkup(keyboard))
                return SELECTING_ACTION

            # Insert capsule - REMOVED needs_activation field
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
                    delivered=False,
                    created_at=datetime.now(timezone.utc)
                )
            )

            # Update user stats
            conn.execute(
                sqlalchemy_update(users)
                .where(users.c.id == userdata['id'])
                .values(
                    capsule_balance=users.c.capsule_balance - 1,
                    total_storage_used=users.c.total_storage_used + capsule_data.get('file_size', 0)
                )
            )

            trans.commit()
            logger.info(f"Capsule {capsule_uuid} created successfully for user {user.id}")

        except Exception as e:
            trans.rollback()
            logger.error(f"Error creating capsule for user {user.id}: {e}")
            keyboard = [[InlineKeyboardButton(t(lang, 'main_menu'), callback_data='main_menu')]]
            await send_menu_with_image(update, context, 'capsules', t(lang, 'error_occurred'), InlineKeyboardMarkup(keyboard))
            return SELECTING_ACTION

    # Generate success message with user's local time
    from ..timezone_utils import format_time_for_user
    user_timezone = userdata.get('timezone', 'UTC')
    delivery_time_str = format_time_for_user(capsule_data['delivery_time'], user_timezone, lang)

    # Check if this is a username recipient (needs activation)
    needs_activation = (recipient_type == 'user' and recipient_username_value)

    if needs_activation:
        # Generate invite link for username recipients
        bot_info = await context.bot.get_me()
        encoded_uuid = base64.urlsafe_b64encode(capsule_uuid.encode()).decode().rstrip('=')
        invite_link = f"https://t.me/{bot_info.username}?start=c_{encoded_uuid}"
        success_text = t(lang, 'capsule_created_with_link',
                        time=delivery_time_str,
                        username=f"@{recipient_username_value}",
                        invite_link=invite_link)
    elif recipient_type in ('group', 'channel'):
        success_text = t(lang, 'capsule_for_group_created',
                        group_name=capsule_data.get('recipient_name', ''),
                        delivery_time=delivery_time_str)
    else:
        success_text = t(lang, 'capsule_created', time=delivery_time_str)

    keyboard = [[InlineKeyboardButton(t(lang, 'main_menu'), callback_data='main_menu')]]

    # FIXED: Use send_menu_with_image instead of edit_message_text to avoid "no text to edit" error
    await send_menu_with_image(update, context, 'capsules', success_text, InlineKeyboardMarkup(keyboard))

    # Clean up user data
    context.user_data.pop('capsule', None)
    return SELECTING_ACTION


async def cancel_creation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel capsule creation and clean up"""
    query = update.callback_query
    if query:
        await query.answer()

    user = update.effective_user
    user_data = get_user_data(user.id)
    lang = user_data['language_code']

    # Clean up any uploaded files if creation was cancelled
    capsule_data = context.user_data.get('capsule', {})
    if capsule_data.get('s3_key'):
        try:
            from ..s3_utils import delete_from_s3
            delete_from_s3(capsule_data['s3_key'])
            logger.info(f"Cleaned up S3 file {capsule_data['s3_key']} for cancelled capsule")
        except Exception as e:
            logger.warning(f"Failed to clean up S3 file: {e}")

    # Clean up user data
    context.user_data.pop('capsule', None)

    keyboard = [[InlineKeyboardButton(t(lang, 'main_menu'), callback_data='main_menu')]]
    message_text = t(lang, 'creation_cancelled')

    if query:
        # FIXED: Use send_menu_with_image instead of edit_message_text
        await send_menu_with_image(update, context, 'capsules', message_text, InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(message_text, reply_markup=InlineKeyboardMarkup(keyboard))

    return SELECTING_ACTION