# src/handlers/create_capsule.py
import uuid
from datetime import datetime, timedelta, timezone
from dateutil.relativedelta import relativedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from sqlalchemy import select, insert, update as sqlalchemy_update
from ..config import (
    SELECTING_ACTION, SELECTING_CONTENT_TYPE, RECEIVING_CONTENT,
    SELECTING_TIME, SELECTING_DATE, SELECTING_RECIPIENT,
    CONFIRMING_CAPSULE, PREMIUM_TIME_LIMIT_DAYS, FREE_TIME_LIMIT_DAYS, logger
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

    # Check quota
    can_create, error_msg = check_user_quota(user_data)
    if not can_create:
        keyboard = [[
            InlineKeyboardButton(t(lang, 'upgrade_subscription'), callback_data='subscription'),
            InlineKeyboardButton(t(lang, 'back'), callback_data='main_menu')
        ]]
        
        error_text = t(lang, 'quota_exceeded', message=error_msg)
        
        if query and query.message:
            try:
                await query.edit_message_text(error_text, reply_markup=InlineKeyboardMarkup(keyboard))
            except:
                await query.message.reply_text(error_text, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            message = update.message or update.effective_message
            if message:
                await message.reply_text(error_text, reply_markup=InlineKeyboardMarkup(keyboard))
        return SELECTING_ACTION

    # Initialize capsule data in context
    context.user_data['capsule'] = {}
    logger.info(f"Starting capsule creation for user {user.id}")

    # Show content type selection
    keyboard = [
        [InlineKeyboardButton(t(lang, 'content_text'), callback_data='type_text')],
        [InlineKeyboardButton(t(lang, 'content_photo'), callback_data='type_photo')],
        [InlineKeyboardButton(t(lang, 'content_video'), callback_data='type_video')],
        [InlineKeyboardButton(t(lang, 'content_document'), callback_data='type_document')],
        [InlineKeyboardButton(t(lang, 'content_voice'), callback_data='type_voice')],
        [InlineKeyboardButton(t(lang, 'cancel'), callback_data='main_menu')]
    ]

    content_text = t(lang, 'select_content_type')
    
    try:
        if query and query.message:
            try:
                await query.edit_message_text(content_text, reply_markup=InlineKeyboardMarkup(keyboard))
            except:
                await query.message.reply_text(content_text, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            message = update.message or update.effective_message
            if message:
                await message.reply_text(content_text, reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        logger.error(f"Error in start_create_capsule: {e}")

    return SELECTING_CONTENT_TYPE

async def select_content_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle content type selection"""
    query = update.callback_query
    if not query:
        return SELECTING_CONTENT_TYPE
        
    await query.answer()

    user = update.effective_user
    user_data = get_user_data(user.id)
    if not user_data:
        return SELECTING_ACTION
        
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
    
    try:
        await query.edit_message_text(instruction_text)
    except Exception as e:
        logger.error(f"Error editing message in select_content_type: {e}")
        await query.message.reply_text(instruction_text)

    return RECEIVING_CONTENT

async def receive_content(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive capsule content"""
    user = update.effective_user
    user_data = get_user_data(user.id)
    
    if not user_data:
        return SELECTING_ACTION
        
    lang = user_data['language_code']
    message = update.message

    if not message:
        logger.error("No message in receive_content")
        return RECEIVING_CONTENT

    # Get capsule data from context
    capsule = context.user_data.get('capsule', {})
    content_type = capsule.get('content_type')
    
    if not content_type:
        logger.error("No content_type in context")
        await message.reply_text(t(lang, 'error_occurred'))
        return RECEIVING_CONTENT

    logger.info(f"Receiving {content_type} content from user {user.id}")

    try:
        if content_type == 'text':
            if not message.text:
                await message.reply_text(t(lang, 'send_content', type=t(lang, 'content_text')))
                return RECEIVING_CONTENT
                
            context.user_data['capsule']['content_text'] = message.text
            context.user_data['capsule']['file_size'] = len(message.text.encode('utf-8'))
            logger.info(f"Stored text content: {len(message.text)} characters")

        else:
            # Handle file content
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
                if message.document.file_name and '.' in message.document.file_name:
                    ext = message.document.file_name.split('.')[-1]
            elif content_type == 'voice' and message.voice:
                file = await message.voice.get_file()
                ext = 'ogg'

            if not file:
                await message.reply_text(t(lang, 'send_content', type=t(lang, f'content_{content_type}')))
                return RECEIVING_CONTENT

            file_size = file.file_size or 0
            logger.info(f"File received: {file_size} bytes, type: {content_type}")

            # Check quota with file size
            can_create, error_msg = check_user_quota(user_data, file_size)
            if not can_create:
                keyboard = [[
                    InlineKeyboardButton(t(lang, 'upgrade_subscription'), callback_data='subscription'),
                    InlineKeyboardButton(t(lang, 'back'), callback_data='main_menu')
                ]]
                await message.reply_text(
                    t(lang, 'quota_exceeded', message=error_msg),
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return SELECTING_ACTION

            # Download and process file
            try:
                file_bytes = await file.download_as_bytearray()
                logger.info(f"File downloaded: {len(file_bytes)} bytes")

                # Encrypt and upload
                s3_key, encrypted_key = encrypt_and_upload_file(bytes(file_bytes), ext)
                
                if not s3_key or not encrypted_key:
                    logger.error("Failed to upload file to S3")
                    await message.reply_text(t(lang, 'error_occurred'))
                    return RECEIVING_CONTENT

                context.user_data['capsule']['s3_key'] = s3_key
                context.user_data['capsule']['file_key'] = encrypted_key
                context.user_data['capsule']['file_size'] = file_size
                logger.info(f"File uploaded successfully: {s3_key}")

            except Exception as e:
                logger.error(f"Error processing file: {e}")
                await message.reply_text(t(lang, 'error_occurred'))
                return RECEIVING_CONTENT

        # Confirm content received
        await message.reply_text(t(lang, 'content_received'))
        
        # Move to time selection
        return await show_time_selection(update, context)

    except Exception as e:
        logger.error(f"Error in receive_content: {e}")
        await message.reply_text(t(lang, 'error_occurred'))
        return RECEIVING_CONTENT

async def show_time_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show time selection menu"""
    user = update.effective_user
    user_data = get_user_data(user.id)
    
    if not user_data:
        return SELECTING_ACTION
        
    lang = user_data['language_code']

    keyboard = [
        [
            InlineKeyboardButton(t(lang, 'time_1hour'), callback_data='time_1h'),
            InlineKeyboardButton(t(lang, 'time_1day'), callback_data='time_1d')
        ],
        [
            InlineKeyboardButton(t(lang, 'time_1week'), callback_data='time_1w'),
            InlineKeyboardButton(t(lang, 'time_1month'), callback_data='time_1m')
        ],
        [
            InlineKeyboardButton(t(lang, 'time_3months'), callback_data='time_3m'),
            InlineKeyboardButton(t(lang, 'time_6months'), callback_data='time_6m')
        ],
        [InlineKeyboardButton(t(lang, 'time_1year'), callback_data='time_1y')],
        [InlineKeyboardButton(t(lang, 'time_custom'), callback_data='time_custom')],
        [InlineKeyboardButton(t(lang, 'cancel'), callback_data='main_menu')]
    ]

    time_text = t(lang, 'select_time')
    
    try:
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(time_text, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_text(time_text, reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        logger.error(f"Error in show_time_selection: {e}")
        await update.effective_message.reply_text(time_text, reply_markup=InlineKeyboardMarkup(keyboard))

    return SELECTING_TIME

async def select_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle time selection"""
    query = update.callback_query
    if not query:
        return SELECTING_TIME
        
    await query.answer()

    user = update.effective_user
    user_data = get_user_data(user.id)
    if not user_data:
        return SELECTING_ACTION
        
    lang = user_data['language_code']
    time_option = query.data.replace('time_', '')

    if time_option == 'custom':
        await query.edit_message_text(t(lang, 'enter_date'))
        return SELECTING_DATE

    # Calculate delivery time with proper timezone handling
    now = datetime.now(timezone.utc)
    
    try:
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
        else:
            logger.error(f"Unknown time option: {time_option}")
            return SELECTING_TIME

        # Check if time is within user's limit
        is_premium = user_data['subscription_status'] == 'premium'
        max_days = PREMIUM_TIME_LIMIT_DAYS if is_premium else FREE_TIME_LIMIT_DAYS

        days_diff = (delivery_time - now).days
        if days_diff > max_days:
            await query.edit_message_text(
                t(lang, 'date_too_far', days=FREE_TIME_LIMIT_DAYS, years=25),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(t(lang, 'back'), callback_data='back_to_time')
                ]])
            )
            return SELECTING_TIME

        context.user_data['capsule']['delivery_time'] = delivery_time
        logger.info(f"Delivery time set: {delivery_time}")

        return await show_recipient_selection(update, context)
        
    except Exception as e:
        logger.error(f"Error in select_time: {e}")
        await query.edit_message_text(t(lang, 'error_occurred'))
        return SELECTING_TIME

async def show_recipient_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show recipient selection menu"""
    user = update.effective_user
    user_data = get_user_data(user.id)
    if not user_data:
        return SELECTING_ACTION
        
    lang = user_data['language_code']

    keyboard = [
        [InlineKeyboardButton(t(lang, 'recipient_self'), callback_data='recipient_self')],
        [InlineKeyboardButton(t(lang, 'recipient_user'), callback_data='recipient_user')],
        [InlineKeyboardButton(t(lang, 'recipient_group'), callback_data='recipient_group')],
        [InlineKeyboardButton(t(lang, 'cancel'), callback_data='main_menu')]
    ]

    recipient_text = t(lang, 'select_recipient')
    
    try:
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(recipient_text, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.effective_message.reply_text(recipient_text, reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        logger.error(f"Error in show_recipient_selection: {e}")

    return SELECTING_RECIPIENT

async def select_recipient(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle recipient selection"""
    query = update.callback_query
    message = update.message
    
    user = update.effective_user
    user_data = get_user_data(user.id)
    if not user_data:
        return SELECTING_ACTION
        
    lang = user_data['language_code']
    
    if query:
        await query.answer()
        recipient_type = query.data.replace('recipient_', '')

        if recipient_type == 'self':
            context.user_data['capsule']['recipient_type'] = 'self'
            context.user_data['capsule']['recipient_id'] = user.id
            logger.info(f"Recipient set to self for user {user.id}")
            return await show_confirmation(update, context)
            
        elif recipient_type in ['user', 'group']:
            context.user_data['capsule']['recipient_type'] = recipient_type
            context.user_data['waiting_for_recipient'] = True
            
            instruction_key = 'enter_user_id_instruction' if recipient_type == 'user' else 'enter_group_id_instruction'
            
            await query.edit_message_text(
                t(lang, instruction_key),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(t(lang, 'cancel'), callback_data='main_menu')
                ]])
            )
            return SELECTING_RECIPIENT

    elif message and message.text and context.user_data.get('waiting_for_recipient'):
        try:
            recipient_input = message.text.strip()
            recipient_type = context.user_data['capsule']['recipient_type']
            
            # Parse recipient ID based on type
            if recipient_type == 'group':
                if not recipient_input.startswith('-') and recipient_input.isdigit():
                    recipient_input = '-' + recipient_input
                recipient_id = recipient_input
            else:  # user
                if recipient_input.startswith('@'):
                    recipient_input = recipient_input[1:]
                
                if recipient_input.isdigit():
                    recipient_id = int(recipient_input)
                else:
                    recipient_id = '@' + recipient_input

            context.user_data['capsule']['recipient_id'] = recipient_id
            context.user_data.pop('waiting_for_recipient', None)
            
            logger.info(f"Recipient set: {recipient_type} -> {recipient_id}")
            return await show_confirmation(update, context)

        except Exception as e:
            logger.error(f"Error parsing recipient ID: {e}")
            await message.reply_text(t(lang, 'invalid_recipient_id'))
            return SELECTING_RECIPIENT

    return SELECTING_RECIPIENT

async def show_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show capsule confirmation"""
    user = update.effective_user
    user_data = get_user_data(user.id)
    if not user_data:
        return SELECTING_ACTION
        
    lang = user_data['language_code']
    
    capsule = context.user_data.get('capsule', {})
    
    if not capsule or 'delivery_time' not in capsule:
        logger.error(f"Invalid capsule data in context for user {user.id}: {capsule}")
        await update.effective_message.reply_text(t(lang, "error_occurred"))
        return SELECTING_ACTION
    
    # Format recipient
    recipient_text = ""
    if capsule['recipient_type'] == "self":
        recipient_text = t(lang, "recipient_self")
    else:
        recipient_text = f"{capsule['recipient_type']}: {capsule.get('recipient_id', 'Unknown')}"
    
    # Format time
    time_text = capsule['delivery_time'].strftime("%d.%m.%Y %H:%M")
    
    keyboard = [
        [InlineKeyboardButton(t(lang, "confirm_yes"), callback_data="confirm_yes")],
        [InlineKeyboardButton(t(lang, "confirm_no"), callback_data="main_menu")]
    ]
    
    confirmation_text = t(lang, "confirm_capsule",
                         type=capsule.get('content_type', 'unknown'),
                         time=time_text,
                         recipient=recipient_text)
    
    try:
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(confirmation_text, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.effective_message.reply_text(confirmation_text, reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        logger.error(f"Error in show_confirmation: {e}")
    
    return CONFIRMING_CAPSULE

async def confirm_capsule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Create the capsule in database"""
    query = update.callback_query
    if not query:
        return CONFIRMING_CAPSULE
        
    await query.answer()

    user = update.effective_user
    user_data = get_user_data(user.id)
    if not user_data:
        return SELECTING_ACTION
        
    lang = user_data['language_code']
    capsule_data = context.user_data.get('capsule', {})

    if not capsule_data:
        logger.error(f"No capsule data found for user {user.id}")
        await query.edit_message_text(t(lang, 'error_occurred'))
        return SELECTING_ACTION

    try:
        # Create capsule in database
        with engine.connect() as conn:
            # Insert capsule
            result = conn.execute(
                insert(capsules).values(
                    user_id=user_data['id'],
                    capsule_uuid=str(uuid.uuid4()),
                    content_type=capsule_data['content_type'],
                    content_text=capsule_data.get('content_text'),
                    file_key=capsule_data.get('file_key'),
                    s3_key=capsule_data.get('s3_key'),
                    file_size=capsule_data.get('file_size', 0),
                    recipient_type=capsule_data['recipient_type'],
                    recipient_id=capsule_data.get('recipient_id'),
                    delivery_time=capsule_data['delivery_time']
                )
            )

            # Update user stats
            conn.execute(
                sqlalchemy_update(users)
                .where(users.c.id == user_data['id'])
                .values(
                    capsule_count=users.c.capsule_count + 1,
                    total_storage_used=users.c.total_storage_used + capsule_data.get('file_size', 0)
                )
            )

            conn.commit()
            
            capsule_id = result.inserted_primary_key[0]
            logger.info(f"Capsule created successfully: ID {capsule_id} for user {user.id}")

            # Schedule delivery
            try:
                scheduler = context.application.bot_data.get('scheduler')
                if scheduler:
                    from ..scheduler import deliver_capsule
                    from apscheduler.triggers.date import DateTrigger
                    scheduler.add_job(
                        deliver_capsule,
                        trigger=DateTrigger(run_date=capsule_data['delivery_time']),
                        args=[context.application.bot, capsule_id],
                        id=f"capsule_{capsule_id}",
                        replace_existing=True
                    )
                    logger.info(f"Scheduled delivery for capsule {capsule_id}")
            except Exception as e:
                logger.error(f"Error scheduling capsule delivery: {e}")

        time_text = capsule_data['delivery_time'].strftime('%d.%m.%Y %H:%M')
        success_text = t(lang, 'capsule_created', time=time_text)
        
        await query.edit_message_text(
            success_text,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(t(lang, 'main_menu'), callback_data='main_menu')
            ]])
        )

        # Clear capsule data
        context.user_data.pop('capsule', None)
        context.user_data.pop('waiting_for_recipient', None)

    except Exception as e:
        logger.error(f"Error creating capsule: {e}")
        await query.edit_message_text(
            t(lang, 'error_occurred'),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(t(lang, 'main_menu'), callback_data='main_menu')
            ]])
        )

    return SELECTING_ACTION

# Placeholder functions for missing functionality
async def select_custom_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle custom date input"""
    # Implementation for custom date selection
    return SELECTING_TIME

async def show_user_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show list of users"""
    # Implementation for user list
    return SELECTING_RECIPIENT
