"""
Advanced onboarding system for Digital Time Capsule bot with A/B testing, 
time-based personalization, and completion tracking.
"""

from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from typing import Dict, Any
import logging

from ..database import add_user_onboarding, update_user_onboarding_stage, get_user_data_by_telegram_id, get_user_data
from ..translations import t
from .main_menu import get_main_menu_keyboard
from ..image_menu import send_menu_with_image
from ..database import check_and_activate_username_capsules, get_pending_capsules_for_user
from ..feature_config import feature_flag_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Conversation states
ONBOARDING_START, ONBOARDING_GREETING_SENT, ONBOARDING_CAPSULE_TYPE, ONBOARDING_COMPLETE = range(4)

class OnboardingManager:
    """Manages intelligent onboarding flows with A/B testing"""
    
    @staticmethod
    def get_time_of_day() -> str:
        """Get the time of day based on current hour"""
        current_hour = datetime.now().hour
        if 5 <= current_hour < 12:
            return 'morning'
        elif 12 <= current_hour < 18:
            return 'afternoon'
        else:
            return 'evening'
    
    @staticmethod
    def assign_onboarding_variant(user_id: int) -> str:
        """Assign an onboarding variant for A/B testing using feature flag manager"""
        return feature_flag_manager.get_onboarding_variant(user_id)

    @staticmethod
    async def start_onboarding(user_id: int, lang: str = 'ru') -> str:
        """Initialize onboarding for a new user"""
        time_of_day = OnboardingManager.get_time_of_day()
        variant = OnboardingManager.assign_onboarding_variant(user_id)
        
        # Store user's onboarding variant and stage in database
        await add_user_onboarding(user_id, variant, 'start')
        
        # Get personalized greeting based on variant and time of day
        greeting_key = f'onboarding_greeting_{variant.lower()}'
        greeting = t(lang, greeting_key)
        
        # Add time-based greeting if not using variant A (which has its own greeting)
        if variant != 'A':
            time_greeting = t(lang, f'onboarding_good_{time_of_day}')
            greeting = f"{time_greeting}\n\n{greeting}"
            
        return greeting

    @staticmethod
    async def get_first_capsule_prompt(lang: str = 'ru') -> str:
        """Get the prompt for first capsule creation"""
        time_of_day = OnboardingManager.get_time_of_day()
        time_greeting = t(lang, f'onboarding_good_{time_of_day}')
        prompt = t(lang, 'onboarding_reflection_prompt')
        
        return f"{time_greeting}\n\n{prompt}"
        
    @staticmethod
    def get_capsule_creation_wizard(lang: str = 'ru'):
        """Get the capsule creation wizard with contextual prompts"""
        # Return a structured workflow for creating the first capsule
        wizard = {
            'step_1': {
                'title': t(lang, 'onboarding_capsule_type_title'),
                'prompt': t(lang, 'onboarding_capsule_type_prompt'),
                'options': [
                    t(lang, 'onboarding_capsule_type_reflection'),
                    t(lang, 'onboarding_capsule_type_dream'),
                    t(lang, 'onboarding_capsule_type_memory'),
                    t(lang, 'onboarding_capsule_type_future_self')
                ],
                'templates': {
                    t(lang, 'onboarding_capsule_type_reflection'): t(lang, 'onboarding_capsule_template_reflection'),
                    t(lang, 'onboarding_capsule_type_dream'): t(lang, 'onboarding_capsule_template_dream'),
                    t(lang, 'onboarding_capsule_type_memory'): t(lang, 'onboarding_capsule_template_memory'),
                    t(lang, 'onboarding_capsule_type_future_self'): t(lang, 'onboarding_capsule_template_future_self')
                }
            }
        }
        return wizard


async def start_onboarding_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the onboarding process"""
    user = update.effective_user

    # Check for deep link parameters (capsule activation)
    args = context.args
    if args and len(args) > 0:
        param = args[0]
        if param.startswith('c_'):
            # If it's a capsule activation link, defer to capsule activation logic
            # (This should be handled in the main start handler)
            pass

    # Get user data, create user if needed
    from ..database import get_or_create_user, get_user_data
    get_or_create_user(user)
    user_data = get_user_data(user.id)

    if not user_data:
        logger.error(f"Failed to create user {user.id}")
        lang = 'en'
        await update.message.reply_text(t(lang, 'error_creating_user'))
        return ConversationHandler.END

    lang = user_data['language_code']

    # Check if user has already completed onboarding
    onboarding_stage = user_data.get('onboarding_stage', 'not_started')
    if onboarding_stage == 'completed':
        # User has already completed onboarding, send to main menu
        caption_text = t(lang, 'start_welcome_full')
        keyboard = get_main_menu_keyboard(lang)

        await send_menu_with_image(
            update=update,
            context=context,
            image_key='welcome',
            caption=caption_text,
            keyboard=keyboard,
            parse_mode='HTML'
        )
        return ConversationHandler.END

    # Check for pending capsules by username
    if user.username:
        activated_count = check_and_activate_username_capsules(user.id, user.username)

        if activated_count > 0:
            await update.message.reply_text(
                t(lang, 'capsules_activated_for_you', count=activated_count),
                parse_mode='HTML'
            )

    # Check for pending capsules
    pending_capsules = get_pending_capsules_for_user(user.id)
    pending_count = len(pending_capsules)

    if pending_count > 0:
        await update.message.reply_text(
            t(lang, 'pending_capsules', count=pending_count)
        )

    try:
        # Initialize onboarding for the user if not already started
        if onboarding_stage == 'not_started':
            greeting = await OnboardingManager.start_onboarding(user.id, lang)
            # Send the personalized greeting
            await update.message.reply_text(greeting)
            
            logger.info(f"Started onboarding for user {user.id} with username {user.username}")
        else:
            # User is somewhere in the onboarding process, send appropriate message
            greeting_key = f'onboarding_greeting_{user_data.get("onboarding_variant", "A").lower()}'
            greeting = t(lang, greeting_key)
            time_of_day = OnboardingManager.get_time_of_day()
            time_greeting = t(lang, f'onboarding_good_{time_of_day}')
            greeting = f"{time_greeting}\n\n{greeting}"
            
            await update.message.reply_text(greeting)

        # Update onboarding stage to greeting_sent if not already
        if onboarding_stage == 'not_started':
            await update_user_onboarding_stage(user.id, 'greeting_sent')
            # Also update the started_at timestamp
            from ..database import update_onboarding_started_time
            await update_onboarding_started_time(user.id)

        # Move to next onboarding step
        return ONBOARDING_GREETING_SENT

    except Exception as e:
        logger.error(f"Error in start_onboarding_command: {e}")
        await update.message.reply_text(t(lang, 'error_occurred'))
        return ConversationHandler.END


async def handle_first_capsule_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the first capsule creation prompt"""
    user_id = update.effective_user.id
    user_data = await get_user_data_by_telegram_id(user_id)
    lang = user_data.get('language_code', 'ru') if user_data else 'ru'
    
    try:
        # Get first capsule prompt
        prompt = await OnboardingManager.get_first_capsule_prompt(lang)
        
        # Send the prompt
        await update.message.reply_text(prompt)
        
        # Update onboarding stage
        await update_user_onboarding_stage(user_id, 'first_capsule_prompt_sent')
        
        logger.info(f"Sent first capsule prompt to user {user_id}")
        
        # Move to capsule type selection
        return ONBOARDING_CAPSULE_TYPE
        
    except Exception as e:
        logger.error(f"Error in handle_first_capsule_prompt: {e}")
        await update.message.reply_text(t(lang, 'error_occurred'))
        return ConversationHandler.END


async def handle_first_capsule_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle first capsule type selection"""
    user_id = update.effective_user.id
    user_data = await get_user_data_by_telegram_id(user_id)
    lang = user_data.get('language_code', 'ru') if user_data else 'ru'
    
    try:
        # Get capsule type options
        options = t(lang, 'onboarding_capsule_for')
        
        # Send the options
        await update.message.reply_text(options)
        
        # Update onboarding stage
        await update_user_onboarding_stage(user_id, 'capsule_type_selected')
        
        logger.info(f"Sent capsule type options to user {user_id}")
        
        # Move to completion
        return ONBOARDING_COMPLETE
        
    except Exception as e:
        logger.error(f"Error in handle_first_capsule_type: {e}")
        await update.message.reply_text(t(lang, 'error_occurred'))
        return ConversationHandler.END


async def complete_onboarding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Complete the onboarding process"""
    user_id = update.effective_user.id
    user_data = await get_user_data_by_telegram_id(user_id)
    lang = user_data.get('language_code', 'ru') if user_data else 'ru'
    
    try:
        # Update onboarding stage to completed
        await update_user_onboarding_stage(user_id, 'completed')
        
        # Send completion message
        completion_msg = t(lang, 'onboarding_complete')
        await update.message.reply_text(completion_msg)
        
        logger.info(f"Completed onboarding for user {user_id}")
        
        # Show main menu after completion
        from .main_menu import get_main_menu_keyboard
        from ..image_menu import send_menu_with_image
        
        caption_text = t(lang, 'start_welcome_full')
        keyboard = get_main_menu_keyboard(lang)

        await send_menu_with_image(
            update=update,
            context=context,
            image_key='welcome',
            caption=caption_text,
            keyboard=keyboard,
            parse_mode='HTML'
        )
        
        # End the conversation
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error in complete_onboarding: {e}")
        await update.message.reply_text(t(lang, 'error_occurred'))
        return ConversationHandler.END


async def skip_onboarding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle skipping onboarding"""
    user_id = update.effective_user.id
    
    try:
        # Update onboarding stage to skipped
        await update_user_onboarding_stage(user_id, 'skipped')
        
        # Send skip message
        user_data = await get_user_data_by_telegram_id(user_id)
        lang = user_data.get('language_code', 'ru') if user_data else 'ru'
        await update.message.reply_text(t(lang, 'onboarding_skip'))
        
        logger.info(f"User {user_id} skipped onboarding")
        
        # Show main menu after skipping
        from .main_menu import get_main_menu_keyboard
        from ..image_menu import send_menu_with_image
        
        caption_text = t(lang, 'start_welcome_full')
        keyboard = get_main_menu_keyboard(lang)

        await send_menu_with_image(
            update=update,
            context=context,
            image_key='welcome',
            caption=caption_text,
            keyboard=keyboard,
            parse_mode='HTML'
        )
        
        # End the conversation
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error in skip_onboarding: {e}")
        return ConversationHandler.END


def get_onboarding_handler():
    """Return the onboarding conversation handler"""
    from telegram.ext import CommandHandler, MessageHandler, filters, ConversationHandler
    
    onboarding_handler = ConversationHandler(
        entry_points=[CommandHandler('onboard', start_onboarding_command)],
        states={
            ONBOARDING_GREETING_SENT: [  # After initial greeting
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_first_capsule_prompt)
            ],
            ONBOARDING_CAPSULE_TYPE: [  # After first prompt
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_first_capsule_type)
            ]
        },
        fallbacks=[CommandHandler('skip', skip_onboarding)],
        name="onboarding",
        persistent=True,
    )
    
    return onboarding_handler


# Additional helper functions for metrics and analytics
async def get_onboarding_metrics():
    """Get onboarding completion metrics"""
    # This would typically query the database for onboarding analytics
    # Implementation would depend on the database schema
    pass


async def get_completion_rate_by_variant(variant: str) -> float:
    """Calculate completion rate for a specific onboarding variant"""
    # This would query the database for completion rates by variant
    # Implementation would depend on the database schema
    pass