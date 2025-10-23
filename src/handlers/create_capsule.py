# src/handlers/create_capsule.py
import uuid
from datetime import datetime, timedelta, timezone
from dateutil.relativedelta import relativedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from ..config import (
    SELECTING_ACTION, SELECTING_CONTENT_TYPE, RECEIVING_CONTENT,
    SELECTING_TIME, SELECTING_DATE, SELECTING_RECIPIENT,
    CONFIRMING_CAPSULE, PREMIUM_TIME_LIMIT_DAYS, FREE_TIME_LIMIT_DAYS
)
from ..database import get_user_data, check_user_quota, users, capsules, engine
from ..s3_utils import encrypt_and_upload_file
from ..translations import t
from sqlalchemy import insert, update as sqlalchemy_update
from ..config import logger

async def start_create_capsule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start capsule creation flow"""
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    user_data = get_user_data(user.id)
    lang = user_data['language_code']

    # Check quota
    can_create, error_msg = check_user_quota(user_data)
    if not can_create:
        keyboard = [[
            InlineKeyboardButton(t(lang, 'upgrade_subscription'), callback_data='subscription'),
            InlineKeyboardButton(t(lang, 'back'), callback_data='main_menu')
        ]]
        await query.edit_message_caption(
            caption=t(lang, 'quota_exceeded', message=error_msg),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return SELECTING_ACTION

    # Initialize capsule data in context
    context.user_data['capsule'] = {}

    # Show content type selection
    keyboard = [
        [InlineKeyboardButton(t(lang, 'content_text'), callback_data='type_text')],
        [InlineKeyboardButton(t(lang, 'content_photo'), callback_data='type_photo')],
        [InlineKeyboardButton(t(lang, 'content_video'), callback_data='type_video')],
        [InlineKeyboardButton(t(lang, 'content_document'), callback_data='type_document')],
        [InlineKeyboardButton(t(lang, 'content_voice'), callback_data='type_voice')],
        [InlineKeyboardButton(t(lang, 'cancel'), callback_data='main_menu')]
    ]

    await query.edit_message_caption(
        caption=t(lang, 'select_content_type'),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

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

    type_names = {
        'text': t(lang, 'content_text'),
        'photo': t(lang, 'content_photo'),
        'video': t(lang, 'content_video'),
        'document': t(lang, 'content_document'),
        'voice': t(lang, 'content_voice')
    }

    await query.edit_message_caption(
        caption=t(lang, 'send_content', type=type_names.get(content_type, content_type))
    )

    return RECEIVING_CONTENT

async def receive_content(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive capsule content"""
    user = update.effective_user
    user_data = get_user_data(user.id)
    lang = user_data['language_code']

    content_type = context.user_data['capsule']['content_type']
    message = update.message

    try:
        if content_type == 'text':
            if not message.text:
                await message.reply_text(t(lang, 'error_occurred'))
                return RECEIVING_CONTENT
            context.user_data['capsule']['content_text'] = message.text
            context.user_data['capsule']['file_size'] = len(message.text.encode('utf-8'))

        else:
            # Handle file content
            file = None
            if content_type == 'photo' and message.photo:
                file = await message.photo[-1].get_file()
                ext = 'jpg'
            elif content_type == 'video' and message.video:
                file = await message.video.get_file()
                ext = 'mp4'
            elif content_type == 'document' and message.document:
                file = await message.document.get_file()
                ext = message.document.file_name.split('.')[-1] if '.' in message.document.file_name else 'bin'
            elif content_type == 'voice' and message.voice:
                file = await message.voice.get_file()
                ext = 'ogg'

            if not file:
                await message.reply_text(t(lang, 'error_occurred'))
                return RECEIVING_CONTENT

            file_size = file.file_size

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

            # Download file
            file_bytes = await file.download_as_bytearray()

            # Encrypt and upload
            s3_key, encrypted_key = encrypt_and_upload_file(bytes(file_bytes), ext)
            if not s3_key or not encrypted_key:
                await message.reply_text(t(lang, 'error_occurred'))
                return RECEIVING_CONTENT

            context.user_data['capsule']['s3_key'] = s3_key
            context.user_data['capsule']['file_key'] = encrypted_key
            context.user_data['capsule']['file_size'] = file_size

        # Move to time selection
        await message.reply_text(
            t(lang, 'content_received'),
        )
        return await show_time_selection(update, context)

    except Exception as e:
        logger.error(f"Error receiving content: {e}")
        await message.reply_text(t(lang, 'error_occurred'))
        return RECEIVING_CONTENT

async def show_time_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show time selection menu"""
    user = update.effective_user
    user_data = get_user_data(user.id)
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

    if update.callback_query:
        await update.callback_query.edit_message_text(
            t(lang, 'select_time'),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text(
            t(lang, 'select_time'),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

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
        await query.edit_message_text(t(lang, 'enter_date'))
        return SELECTING_DATE

    # Calculate delivery time
    now = datetime.now(timezone.utc)
    delivery_time = None

    time_map = {
        '1h': timedelta(hours=1),
        '1d': timedelta(days=1),
        '1w': timedelta(weeks=1),
        '1m': relativedelta(months=1),
        '3m': relativedelta(months=3),
        '6m': relativedelta(months=6),
        '1y': relativedelta(years=1)
    }

    if time_option in ['1h', '1d', '1w']:
        delivery_time = now + time_map[time_option]
    else:
        delivery_time = now + time_map[time_option]

    # Check if time is within user's limit
    is_premium = user_data['subscription_status'] == 'premium'
    max_days = PREMIUM_TIME_LIMIT_DAYS if is_premium else FREE_TIME_LIMIT_DAYS

    if (delivery_time - now).days > max_days:
        await query.edit_message_text(
            t(lang, 'date_too_far', days=FREE_TIME_LIMIT_DAYS, years=25),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(t(lang, 'back'), callback_data='back_to_time')
            ]])
        )
        return SELECTING_TIME

    context.user_data['capsule']['delivery_time'] = delivery_time

    return await show_recipient_selection(update, context)

async def select_custom_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle custom date input"""
    user = update.effective_user
    user_data = get_user_data(user.id)
    lang = user_data['language_code']

    try:
        # Parse date
        date_str = update.message.text.strip()
        delivery_time = datetime.strptime(date_str, '%d.%m.%Y %H:%M')

        # Check if in future
        if delivery_time <= datetime.now():
            await update.message.reply_text(t(lang, 'invalid_date'))
            return SELECTING_DATE

        # Check time limit
        is_premium = user_data['subscription_status'] == 'premium'
        max_days = PREMIUM_TIME_LIMIT_DAYS if is_premium else FREE_TIME_LIMIT_DAYS

        if (delivery_time - datetime.now()).days > max_days:
            await update.message.reply_text(
                t(lang, 'date_too_far', days=FREE_TIME_LIMIT_DAYS, years=25)
            )
            return SELECTING_DATE

        context.user_data['capsule']['delivery_time'] = delivery_time

        return await show_recipient_selection(update, context)

    except ValueError:
        await update.message.reply_text(t(lang, 'invalid_date'))
        return SELECTING_DATE


async def select_recipient(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle recipient selection"""
    query = update.callback_query
    message = update.message
    
    # Если это callback query (кнопка)
    if query:
        await query.answer()
        user = update.effective_user
        user_data = get_user_data(user.id)
        lang = user_data['language_code']

        recipient_type = query.data.replace('recipient_', '')

        if recipient_type == 'self':
            context.user_data['capsule']['recipient_type'] = 'self'
            context.user_data['capsule']['recipient_id'] = user.id
            return await show_confirmation(update, context)
        elif recipient_type == 'user':
            context.user_data['capsule']['recipient_type'] = 'user'
            context.user_data['waiting_for_recipient'] = True
            await query.edit_message_text(
                t(lang, 'enter_user_id_instruction'),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(t(lang, 'cancel'), callback_data='main_menu')
                ]])
            )
            return SELECTING_RECIPIENT
        elif recipient_type == 'group':
            context.user_data['capsule']['recipient_type'] = 'group'
            context.user_data['waiting_for_recipient'] = True
            await query.edit_message_text(
                t(lang, 'enter_group_id_instruction'),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(t(lang, 'cancel'), callback_data='main_menu')
                ]])
            )
            return SELECTING_RECIPIENT

    # Если это текстовое сообщение с ID получателя
    elif message and message.text and context.user_data.get('waiting_for_recipient'):
        user = update.effective_user
        user_data = get_user_data(user.id)
        lang = user_data['language_code']

        try:
            # Парсим ID получателя
            recipient_input = message.text.strip()
            
            # Убираем @ если есть
            if recipient_input.startswith('@'):
                recipient_input = recipient_input[1:]
            
            # Для групп ID может начинаться с -
            if context.user_data['capsule']['recipient_type'] == 'group':
                if not recipient_input.startswith('-') and recipient_input.isdigit():
                    recipient_input = '-' + recipient_input
                recipient_id = recipient_input
            else:
                # Для пользователей может быть username или ID
                if recipient_input.isdigit():
                    recipient_id = int(recipient_input)
                else:
                    # Это username, попробуем найти пользователя
                    recipient_id = '@' + recipient_input

            context.user_data['capsule']['recipient_id'] = recipient_id
            context.user_data.pop('waiting_for_recipient', None)
            
            return await show_confirmation(update, context)

        except Exception as e:
            logger.error(f"Error parsing recipient ID: {e}")
            await message.reply_text(
                t(lang, 'invalid_recipient_id'),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(t(lang, 'back'), callback_data='recipient_' + context.user_data['capsule']['recipient_type']),
                    InlineKeyboardButton(t(lang, 'cancel'), callback_data='main_menu')
                ]])
            )
            return SELECTING_RECIPIENT

    return SELECTING_RECIPIENT

async def show_recipient_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show recipient selection menu with user list option"""
    user = update.effective_user
    user_data = get_user_data(user.id)
    lang = user_data['language_code']

    # Добавляем кнопку для выбора пользователей из списка
    keyboard = [
        [InlineKeyboardButton(t(lang, 'recipient_self'), callback_data='recipient_self')],
        [InlineKeyboardButton(t(lang, 'recipient_user'), callback_data='recipient_user')],
        [InlineKeyboardButton(t(lang, 'recipient_user_list'), callback_data='recipient_user_list')],
        [InlineKeyboardButton(t(lang, 'recipient_group'), callback_data='recipient_group')],
        [InlineKeyboardButton(t(lang, 'cancel'), callback_data='main_menu')]
    ]

    if update.callback_query:
        await update.callback_query.edit_message_text(
            t(lang, 'select_recipient_enhanced'),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text(
            t(lang, 'select_recipient_enhanced'),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    return SELECTING_RECIPIENT

# Новая функция для показа списка пользователей
async def show_user_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show list of users who have interacted with the bot"""
    user = update.effective_user
    user_data = get_user_data(user.id)
    lang = user_data['language_code']
    
    try:
        with engine.connect() as conn:
            # Получаем список пользователей (кроме текущего)
            users_result = conn.execute(
                select(users.c.telegram_id, users.c.first_name, users.c.username)
                .where(users.c.telegram_id != user.id)
                .limit(20)  # Ограничиваем количество
            ).fetchall()

            if not users_result:
                keyboard = [[
                    InlineKeyboardButton(t(lang, 'back'), callback_data='create'),
                    InlineKeyboardButton(t(lang, 'cancel'), callback_data='main_menu')
                ]]
                await update.callback_query.edit_message_text(
                    t(lang, 'no_users_found'),
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return SELECTING_RECIPIENT

            # Создаем кнопки для каждого пользователя
            keyboard = []
            for user_row in users_result:
                user_dict = dict(user_row._mapping)
                display_name = user_dict['first_name'] or user_dict['username'] or f"User {user_dict['telegram_id']}"
                keyboard.append([InlineKeyboardButton(
                    display_name,
                    callback_data=f'select_user_{user_dict["telegram_id"]}'
                )])
            
            # Добавляем кнопки навигации
            keyboard.append([
                InlineKeyboardButton(t(lang, 'back'), callback_data='create'),
                InlineKeyboardButton(t(lang, 'cancel'), callback_data='main_menu')
            ])

            await update.callback_query.edit_message_text(
                t(lang, 'select_user_from_list'),
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

            return SELECTING_RECIPIENT

    except Exception as e:
        logger.error(f"Error showing user list: {e}")
        keyboard = [[
            InlineKeyboardButton(t(lang, 'back'), callback_data='create'),
            InlineKeyboardButton(t(lang, 'cancel'), callback_data='main_menu')
        ]]
        await update.callback_query.edit_message_text(
            t(lang, 'error_occurred'),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return SELECTING_RECIPIENT


async def show_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show capsule confirmation"""
    if update.callback_query:
        await update.callback_query.answer()
    
    user = update.effective_user
    userdata = get_user_data(user.id)
    lang = userdata['language_code']
    
    capsule = context.user_data.get('capsule')
    
    if not capsule:
        message = update.message or update.effective_message
        if message:
            await message.reply_text(t(lang, "error_occurred"))
        return SELECTING_ACTION
    
    # Check time limit
    is_premium = userdata['subscription_status'] == 'premium'
    max_days = PREMIUM_TIME_LIMIT_DAYS if is_premium else FREE_TIME_LIMIT_DAYS
    max_time = datetime.now(timezone.utc) + timedelta(days=max_days)
    
    if capsule['delivery_time'] > max_time:
        keyboard = [
            [InlineKeyboardButton(
                t(lang, "upgrade_subscription"), 
                callback_data="subscription"
            )],
            [InlineKeyboardButton(t(lang, "back"), callback_data="main_menu")]
        ]
        
        message = update.message or update.effective_message or update.callback_query.message
        if message:
            await message.reply_text(
                t(lang, "date_too_far", days=FREE_TIME_LIMIT_DAYS // 365, years=PREMIUM_TIME_LIMIT_DAYS // 365),
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
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
    
    # Check if called from callback query or message
    if update.callback_query:
        await update.callback_query.edit_message_text(
            t(lang, "confirm_capsule",
              type=capsule['content_type'],
              time=time_text,
              recipient=recipient_text),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        message = update.message or update.effective_message
        if message:
            await message.reply_text(
                t(lang, "confirm_capsule",
                  type=capsule['content_type'],
                  time=time_text,
                  recipient=recipient_text),
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    
    return CONFIRMING_CAPSULE


async def confirm_capsule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Create the capsule in database"""
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    user_data = get_user_data(user.id)
    lang = user_data['language_code']

    capsule_data = context.user_data['capsule']

    try:
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

            # Schedule delivery
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

        time_text = capsule_data['delivery_time'].strftime('%d.%m.%Y %H:%M')
        await query.edit_message_text(
            t(lang, 'capsule_created', time=time_text),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(t(lang, 'main_menu'), callback_data='main_menu')
            ]])
        )

        # Clear capsule data
        context.user_data.pop('capsule', None)

    except Exception as e:
        logger.error(f"Error creating capsule: {e}")
        await query.edit_message_text(
            t(lang, 'error_occurred'),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(t(lang, 'main_menu'), callback_data='main_menu')
            ]])
        )

    return SELECTING_ACTION
