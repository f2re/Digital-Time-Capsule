from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from ..database import get_user_data, engine, users, capsules
from ..translations import t
from ..config import PREMIUM_STORAGE_LIMIT, FREE_STORAGE_LIMIT, logger
from .create_capsule import start_create_capsule
from .view_capsules import show_capsules
from .subscription import show_subscription
from .settings import show_settings
from sqlalchemy import select

async def show_persistent_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show persistent menu that works outside conversation"""
    user = update.effective_user
    user_data = get_user_data(user.id)
    lang = user_data['language_code']
    
    keyboard = [
        [
            InlineKeyboardButton(f"📝 {t(lang, 'create_capsule')}", callback_data='menu_create'),
            InlineKeyboardButton(f"📦 {t(lang, 'my_capsules')}", callback_data='menu_capsules')
        ],
        [
            InlineKeyboardButton(f"💎 {t(lang, 'subscription')}", callback_data='menu_subscription'),
            InlineKeyboardButton(f"⚙️ {t(lang, 'settings')}", callback_data='menu_settings')
        ],
        [
            InlineKeyboardButton(f"❓ {t(lang, 'help')}", callback_data='menu_help'),
            InlineKeyboardButton(f"📊 {t(lang, 'stats')}", callback_data='menu_stats')
        ]
    ]
    
    if update.message:
        await update.message.reply_text(
            t(lang, 'persistent_menu_text'),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    elif update.callback_query:
        try:
            await update.callback_query.edit_message_text(
                t(lang, 'persistent_menu_text'),
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        except:
            await update.callback_query.message.reply_text(
                t(lang, 'persistent_menu_text'),
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )

async def persistent_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle persistent menu button clicks"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    user_data = get_user_data(user.id)
    lang = user_data['language_code']
    
    action = query.data.replace('menu_', '')
    
    if action == 'create':
        # Начинаем conversation для создания капсулы
        context.user_data['capsule'] = {}
        await start_create_capsule(update, context)
    elif action == 'capsules':
        await show_capsules(update, context)
    elif action == 'subscription':
        await show_subscription(update, context)
    elif action == 'settings':
        await show_settings(update, context)
    elif action == 'help':
        await query.edit_message_text(
            t(lang, 'help_text'),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(t(lang, 'back_to_menu'), callback_data='show_menu')
            ]]),
            parse_mode='Markdown'
        )
    elif action == 'stats':
        await show_user_stats(update, context)

async def persistent_main_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle main menu callback outside conversation"""
    return await show_persistent_menu(update, context)

async def show_user_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user statistics"""
    query = update.callback_query
    user = update.effective_user
    user_data = get_user_data(user.id)
    lang = user_data['language_code']
    
    try:
        with engine.connect() as conn:
            # Получаем статистику пользователя
            stats = conn.execute(
                select(users)
                .where(users.c.telegram_id == user.id)
            ).first()
            
            if stats:
                stats_dict = dict(stats._mapping)
                
                # Считаем активные капсулы
                active_capsules_result = conn.execute(
                    select(capsules)
                    .where(capsules.c.user_id == stats_dict['id'])
                    .where(capsules.c.delivered == False)
                )
                active_capsules = len(active_capsules_result.fetchall())
                
                # Форматируем размер хранилища
                storage_mb = stats_dict['total_storage_used'] / (1024 * 1024)
                max_storage_mb = (PREMIUM_STORAGE_LIMIT if stats_dict['subscription_status'] == 'premium' 
                                else FREE_STORAGE_LIMIT) / (1024 * 1024)
                
                stats_text = t(lang, 'user_stats',
                             capsules_total=stats_dict['capsule_count'],
                             capsules_active=active_capsules,
                             storage_used=f"{storage_mb:.1f}",
                             storage_max=f"{max_storage_mb:.0f}",
                             subscription=stats_dict['subscription_status'].upper())
                
                await query.edit_message_text(
                    stats_text,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(t(lang, 'back_to_menu'), callback_data='show_menu')
                    ]]),
                    parse_mode='Markdown'
                )
            
    except Exception as e:
        logger.error(f"Error showing stats: {e}")
        await query.edit_message_text(
            t(lang, 'error_occurred'),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(t(lang, 'back_to_menu'), callback_data='show_menu')
            ]])
        )

async def handle_show_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle show_menu callback"""
    await show_persistent_menu(update, context)
