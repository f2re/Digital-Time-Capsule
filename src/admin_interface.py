"""
Admin interface for managing feature flags.
This module provides Telegram bot commands and handlers for administrators to manage feature flags.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, ConversationHandler
import logging

from .feature_config import feature_flag_manager, FeatureFlag
from .database import get_user_data_by_telegram_id, get_user_data
from .translations import t

logger = logging.getLogger(__name__)

# Admin conversation states
FEATURE_FLAG_ADMIN, SELECT_FEATURE, SELECT_ACTION = range(3)


async def is_admin(update: Update) -> bool:
    """Check if the user is an admin based on configuration."""
    from .config import ADMIN_IDS
    user_id = update.effective_user.id
    return user_id in ADMIN_IDS


async def admin_feature_flags_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to manage feature flags."""
    if not await is_admin(update):
        lang = update.effective_user.language_code or 'en'
        await update.message.reply_text(t(lang, 'admin_access_denied'))
        return ConversationHandler.END

    lang = update.effective_user.language_code or 'en'
    keyboard = [
        [InlineKeyboardButton(t(lang, 'admin_list_flags_button'), callback_data="list_flags")],
        [InlineKeyboardButton(t(lang, 'admin_check_user_flags_button'), callback_data="check_user_flags")],
        [InlineKeyboardButton(t(lang, 'admin_toggle_global_flag_button'), callback_data="toggle_global_flag")],
        [InlineKeyboardButton(t(lang, 'admin_set_user_flag_button'), callback_data="set_user_flag")],
        [InlineKeyboardButton(t(lang, 'admin_get_feature_status_button'), callback_data="get_feature_status")],
        [InlineKeyboardButton(t(lang, 'admin_cancel_button'), callback_data="cancel_admin")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(t(lang, 'admin_panel_title'), reply_markup=reply_markup)
    return FEATURE_FLAG_ADMIN


async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin callback queries for feature flag management."""
    query = update.callback_query
    await query.answer()

    lang = query.from_user.language_code or 'en'
    
    if not await is_admin(update):
        await query.edit_message_text(t(lang, 'admin_access_denied'))
        return ConversationHandler.END

    data = query.data

    if data == "cancel_admin":
        await query.edit_message_text(t(lang, 'admin_session_cancelled'))
        return ConversationHandler.END

    elif data == "list_flags":
        # List all feature flags and their current status
        message = t(lang, 'admin_all_flags_title') + "\n\n"
        for flag in FeatureFlag:
            config = feature_flag_manager.get_feature_flag(flag)
            status_emoji = t(lang, 'admin_flag_status_enabled') if config['is_enabled'] else t(lang, 'admin_flag_status_disabled')
            message += f"{status_emoji} <code>{flag.value}</code>: {config['is_enabled']} (Rollout: {config['rollout_percentage']}%)\n"
        
        keyboard = [
            [InlineKeyboardButton(t(lang, 'admin_back_button'), callback_data="admin_main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, reply_markup=reply_markup)
        return FEATURE_FLAG_ADMIN

    elif data == "toggle_global_flag":
        # Show feature flags to toggle
        keyboard = []
        for flag in FeatureFlag:
            config = feature_flag_manager.get_feature_flag(flag)
            status_emoji = t(lang, 'admin_flag_status_enabled') if config['is_enabled'] else t(lang, 'admin_flag_status_disabled')
            keyboard.append([InlineKeyboardButton(f"{status_emoji} {flag.value}", callback_data=f"toggle_flag_{flag.value}")])
        
        keyboard.append([InlineKeyboardButton(t(lang, 'admin_back_button'), callback_data="admin_main_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(t(lang, 'admin_toggle_flag_prompt'), reply_markup=reply_markup)

    elif data.startswith("toggle_flag_"):
        flag_name = data.replace("toggle_flag_", "")
        try:
            flag = FeatureFlag(flag_name)
            current_config = feature_flag_manager.get_feature_flag(flag)
            new_state = not current_config['is_enabled']
            
            # Set the new state with 100% rollout by default
            feature_flag_manager.set_feature_flag(flag, new_state, current_config['rollout_percentage'])
            
            status_emoji = t(lang, 'admin_flag_status_enabled') if new_state else t(lang, 'admin_flag_status_disabled')
            state_text = 'enabled' if new_state else 'disabled'
            message = t(lang, 'admin_flag_toggled', 
                       flag=flag.value, 
                       state=state_text, 
                       status_emoji=status_emoji, 
                       new_state=new_state)
            await query.edit_message_text(message)
        except ValueError:
            message = t(lang, 'admin_flag_invalid', flag_name=flag_name)
            await query.edit_message_text(message)
        
        # Show back button
        keyboard = [[InlineKeyboardButton(t(lang, 'admin_back_to_menu_button'), callback_data="admin_main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(t(lang, 'admin_choose_next_action'), reply_markup=reply_markup)
        return FEATURE_FLAG_ADMIN

    elif data == "admin_main_menu":
        # Return to main admin menu
        keyboard = [
            [InlineKeyboardButton(t(lang, 'admin_list_flags_button'), callback_data="list_flags")],
            [InlineKeyboardButton(t(lang, 'admin_check_user_flags_button'), callback_data="check_user_flags")],
            [InlineKeyboardButton(t(lang, 'admin_toggle_global_flag_button'), callback_data="toggle_global_flag")],
            [InlineKeyboardButton(t(lang, 'admin_set_user_flag_button'), callback_data="set_user_flag")],
            [InlineKeyboardButton(t(lang, 'admin_get_feature_status_button'), callback_data="get_feature_status")],
            [InlineKeyboardButton(t(lang, 'admin_cancel_button'), callback_data="cancel_admin")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(t(lang, 'admin_panel_title'), reply_markup=reply_markup)
        return FEATURE_FLAG_ADMIN

    elif data == "check_user_flags":
        # Check feature flags for a specific user
        await query.edit_message_text(t(lang, 'admin_enter_user_id_prompt'))
        # Note: We'll need to handle text input differently, so we'll return SELECT_FEATURE
        # to indicate we're waiting for user ID input
        return SELECT_FEATURE

    elif data == "get_feature_status":
        # Get overall feature status report
        message = t(lang, 'admin_feature_status_report') + "\n\n"
        total_flags = len(list(FeatureFlag))
        enabled_flags = 0
        
        for flag in FeatureFlag:
            config = feature_flag_manager.get_feature_flag(flag)
            if config['is_enabled']:
                enabled_flags += 1
            
            status_emoji = t(lang, 'admin_flag_status_enabled') if config['is_enabled'] else t(lang, 'admin_flag_status_disabled')
            message += f"{status_emoji} {flag.value}: {config['is_enabled']} ({config['rollout_percentage']}% rollout)\n"
        
        message += f"\n" + t(lang, 'admin_overall_status', enabled_count=enabled_flags, total_count=total_flags)
        
        keyboard = [
            [InlineKeyboardButton(t(lang, 'admin_back_button'), callback_data="admin_main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, reply_markup=reply_markup)
        return FEATURE_FLAG_ADMIN

    else:
        # Handle other callback data
        message = t(lang, 'admin_additional_functionality', data=data)
        await query.edit_message_text(message)
        keyboard = [
            [InlineKeyboardButton(t(lang, 'admin_back_button'), callback_data="admin_main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(t(lang, 'admin_choose_next_action'), reply_markup=reply_markup)
        return FEATURE_FLAG_ADMIN


async def handle_user_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text input from admin user (e.g., user ID for checking flags)."""
    message_text = update.message.text
    lang = update.effective_user.language_code or 'en'
    
    # Check if we're in the right state for user ID input
    # In a real implementation, we'd need to track state differently
    # For now, let's just handle the user ID check
    
    if message_text.isdigit():
        user_id = int(message_text)
        
        # Check if user exists
        user_data = get_user_data_by_telegram_id(user_id)
        if not user_data:
            message = t(lang, 'admin_user_not_found', user_id=user_id)
            await update.message.reply_text(message)
            return FEATURE_FLAG_ADMIN
        
        # Show all feature flags for this user
        user_name = user_data.get('first_name', 'Unknown')
        message = t(lang, 'admin_user_flags_title', user_id=user_id, user_name=user_name) + "\n\n"
        
        for flag in FeatureFlag:
            is_enabled = feature_flag_manager.is_feature_enabled_for_user(user_id, flag)
            global_enabled = feature_flag_manager.is_feature_enabled(flag, user_id)
            
            status_emoji = t(lang, 'admin_flag_status_enabled') if is_enabled else t(lang, 'admin_flag_status_disabled')
            # Using generic emojis for global status since we don't have specific translations for them
            global_status_emoji = "🌐" if global_enabled else "🚫"
            
            message += f"{status_emoji} {flag.value}: {is_enabled} (Global: {global_enabled})\n"
        
        await update.message.reply_text(message)
    else:
        await update.message.reply_text(t(lang, 'admin_invalid_user_id'))
    
    # Return to main admin menu
    keyboard = [
        [InlineKeyboardButton(t(lang, 'admin_back_to_menu_button'), callback_data="admin_main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(t(lang, 'admin_choose_next_action'), reply_markup=reply_markup)
    return FEATURE_FLAG_ADMIN


def get_admin_handler():
    """Return the admin conversation handler for feature flag management."""
    from telegram.ext import ConversationHandler, MessageHandler, filters
    
    admin_handler = ConversationHandler(
        entry_points=[CommandHandler('admin', admin_feature_flags_command)],
        states={
            FEATURE_FLAG_ADMIN: [
                CallbackQueryHandler(admin_callback_handler)
            ],
            SELECT_FEATURE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_input)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel_admin)],
        name="feature_flag_admin",
        persistent=False,
    )
    
    return admin_handler


async def cancel_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the admin session."""
    lang = update.effective_user.language_code or 'en'
    await update.message.reply_text(t(lang, 'admin_session_cancelled'))
    return ConversationHandler.END


# Additional helper functions for admin operations

def get_feature_flags_report():
    """Generate a comprehensive report of all feature flags."""
    report = {
        'total_flags': len(list(FeatureFlag)),
        'enabled_flags': 0,
        'flags_status': {}
    }
    
    for flag in FeatureFlag:
        config = feature_flag_manager.get_feature_flag(flag)
        report['flags_status'][flag.value] = config
        if config['is_enabled']:
            report['enabled_flags'] += 1
    
    return report


async def set_feature_rollout_percentage(admin_user_id: int, flag: FeatureFlag, percentage: int):
    """Allow admin to set rollout percentage for a feature."""
    if admin_user_id not in get_config_admin_ids():  # Will need to implement this
        return False, "Access denied"
    
    if not 0 <= percentage <= 100:
        return False, "Percentage must be between 0 and 100"
    
    feature_flag_manager.set_feature_flag(flag, True, percentage)
    return True, f"Rollout percentage for {flag.value} set to {percentage}%"


def get_config_admin_ids():
    """Get admin IDs from config."""
    from .config import ADMIN_IDS
    return ADMIN_IDS