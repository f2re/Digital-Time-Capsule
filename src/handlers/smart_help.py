"""
Smart help system with contextual assistance and proactive problem detection.
"""

from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from typing import Dict, List, Optional, Any
import logging

from ..database import get_user_data_by_telegram_id, get_user_data
from ..translations import t
from ..feature_config import feature_flag_manager, FeatureFlag
from ..analytics import analytics_engine

logger = logging.getLogger(__name__)

# Help conversation states
SMART_HELP_MENU, PROACTIVE_HELP, CONTEXTUAL_HELP, FEEDBACK_COLLECTION = range(4)


class SmartHelpSystem:
    """Contextual help system with progressive feature disclosure and proactive problem detection."""
    
    def __init__(self):
        # Help sections will be generated dynamically using translations
        pass
        
        self.proactive_triggers = {
            'new_user_confusion': {
                'condition': lambda user_data: user_data.get('onboarding_stage', 'not_started') == 'greeting_sent' and user_data.get('total_capsules_created', 0) == 0,
                'message_key': 'proactive_new_user_help',
                'priority': 10
            },
            'capsule_creation_difficulty': {
                'condition': lambda user_data: user_data.get('total_capsules_created', 0) == 0 and (datetime.now() - user_data.get('created_at', datetime.now())).days >= 3,
                'message_key': 'proactive_creation_help',
                'priority': 8
            },
            'delivery_confusion': {
                'condition': lambda user_data: user_data.get('total_capsules_created', 0) > 0 and user_data.get('capsules_delivered', 0) == 0,
                'message_key': 'proactive_delivery_help',
                'priority': 5
            }
        }
    
    async def get_smart_help_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Provide smart help menu based on user's context and needs."""
        user_id = update.effective_user.id
        user_data = get_user_data_by_telegram_id(user_id)
        
        if not user_data:
            lang = 'en'  # default language
            if update.message:
                await update.message.reply_text(t(lang, 'please_start_bot'))
            else:
                query = update.callback_query
                if query:
                    await query.answer()
                    await query.edit_message_text(t(lang, 'please_start_bot'))
            return ConversationHandler.END
        
        lang = user_data.get('language_code', 'ru')
        
        # Check if smart help feature is enabled
        if not feature_flag_manager.is_feature_enabled_for_user(user_id, FeatureFlag.SMART_HELP):
            # Fall back to regular help
            from .help import help_command
            return await help_command(update, context)
        
        # Show contextual help options
        keyboard = [
            [InlineKeyboardButton(t(lang, 'help_section_create_capsules'), callback_data="help_create")],
            [InlineKeyboardButton(t(lang, 'help_section_delivery_time'), callback_data="help_delivery")],
            [InlineKeyboardButton(t(lang, 'help_section_sharing'), callback_data="help_sharing")],
            [InlineKeyboardButton(t(lang, 'help_section_premium'), callback_data="help_premium")],
            [InlineKeyboardButton(t(lang, 'help_section_find_solution'), callback_data="help_search")],
            [InlineKeyboardButton(t(lang, 'help_section_feedback'), callback_data="help_feedback")],
            [InlineKeyboardButton(t(lang, 'main_menu_button'), callback_data="main_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Personalize the help menu
        help_text = t(lang, 'smart_help_center_title', name=user_data.get('first_name', 'друг' if lang == 'ru' else 'friend')) + "\n\n"
        help_text += t(lang, 'smart_help_select_section')
        
        # Handle both regular messages and callback queries
        if update.message:
            await update.message.reply_text(help_text, reply_markup=reply_markup)
        else:
            query = update.callback_query
            if query:
                await query.answer()
                # Try to edit the message text, fallback to editing caption if the message has only caption
                try:
                    await query.edit_message_text(help_text, reply_markup=reply_markup)
                except:
                    try:
                        # If text editing fails, try editing caption
                        await query.edit_message_caption(caption=help_text, reply_markup=reply_markup)
                    except:
                        # If both fail, send a new message after deleting the old one
                        try:
                            await query.message.delete()
                            await query.message.reply_text(help_text, reply_markup=reply_markup)
                        except:
                            # Last fallback - send message without deleting
                            await query.message.reply_text(help_text, reply_markup=reply_markup)
        
        return SMART_HELP_MENU
    
    async def handle_help_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle help section selection."""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        user_data = get_user_data_by_telegram_id(user_id)
        if not user_data:
            # Try to edit the message text, fallback to editing caption if the message has only caption
            try:
                await query.edit_message_text(t('en', 'please_start_bot'))  # Use default language 'en'
            except:
                try:
                    # If text editing fails, try editing caption
                    await query.edit_message_caption(caption=t('en', 'please_start_bot'))
                except:
                    # If both fail, send a new message after deleting the old one
                    try:
                        await query.message.delete()
                        await query.message.reply_text(t('en', 'please_start_bot'))
                    except:
                        # Last fallback - send message without deleting
                        await query.message.reply_text(t('en', 'please_start_bot'))
            return ConversationHandler.END
        
        lang = user_data.get('language_code', 'ru')
        
        if query.data.startswith('help_'):
            section = query.data.replace('help_', '')
            
            if section == 'search':
                # Show search interface
                # Try to edit the message text, fallback to editing caption if the message has only caption
                try:
                    await query.edit_message_text(t(lang, 'help_search_prompt'))
                except:
                    try:
                        # If text editing fails, try editing caption
                        await query.edit_message_caption(caption=t(lang, 'help_search_prompt'))
                    except:
                        # If both fail, send a new message after deleting the old one
                        try:
                            await query.message.delete()
                            await query.message.reply_text(t(lang, 'help_search_prompt'))
                        except:
                            # Last fallback - send message without deleting
                            await query.message.reply_text(t(lang, 'help_search_prompt'))
                return CONTEXTUAL_HELP
            elif section == 'feedback':
                # Collect feedback
                # Try to edit the message text, fallback to editing caption if the message has only caption
                try:
                    await query.edit_message_text(t(lang, 'help_feedback_prompt'))
                except:
                    try:
                        # If text editing fails, try editing caption
                        await query.edit_message_caption(caption=t(lang, 'help_feedback_prompt'))
                    except:
                        # If both fail, send a new message after deleting the old one
                        try:
                            await query.message.delete()
                            await query.message.reply_text(t(lang, 'help_feedback_prompt'))
                        except:
                            # Last fallback - send message without deleting
                            await query.message.reply_text(t(lang, 'help_feedback_prompt'))
                return FEEDBACK_COLLECTION
            else:
                # Show specific help section
                help_content = self._get_help_section_content(section, lang)
                if help_content:
                    # Try to edit the message text, fallback to editing caption if the message has only caption
                    try:
                        await query.edit_message_text(help_content, parse_mode='HTML')
                    except:
                        try:
                            # If text editing fails, try editing caption
                            await query.edit_message_caption(caption=help_content, parse_mode='HTML')
                        except:
                            # If both fail, send a new message after deleting the old one
                            try:
                                await query.message.delete()
                                await query.message.reply_text(help_content, parse_mode='HTML')
                            except:
                                # Last fallback - send message without deleting
                                await query.message.reply_text(help_content, parse_mode='HTML')
                else:
                    # Try to edit the message text, fallback to editing caption if the message has only caption
                    try:
                        await query.edit_message_text(t(lang, 'help_section_not_found'))
                    except:
                        try:
                            # If text editing fails, try editing caption
                            await query.edit_message_caption(caption=t(lang, 'help_section_not_found'))
                        except:
                            # If both fail, send a new message after deleting the old one
                            try:
                                await query.message.delete()
                                await query.message.reply_text(t(lang, 'help_section_not_found'))
                            except:
                                # Last fallback - send message without deleting
                                await query.message.reply_text(t(lang, 'help_section_not_found'))
                
                # Show back button
                keyboard = [[InlineKeyboardButton(t(lang, 'back_to_menu_button'), callback_data="help_menu")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.message.reply_text(t(lang, 'next_action_prompt'), reply_markup=reply_markup)
                return SMART_HELP_MENU
        
        elif query.data == 'help_menu':
            # Return to help menu
            await self.get_smart_help_menu(query, context)
            return SMART_HELP_MENU
        
        elif query.data == 'main_menu':
            # Go to main menu
            from .main_menu import main_menu_handler
            return await main_menu_handler(update, context)
        
        return SMART_HELP_MENU
    
    def _get_help_section_content(self, section: str, lang: str) -> Optional[str]:
        """Get content for a specific help section."""
        content_mapping = {
            'create': {
                'title': t(lang, 'capsule_creation_guide_title'),
                'content': [
                    t(lang, 'capsule_creation_guide_step1'),
                    t(lang, 'capsule_creation_guide_step2'),
                    t(lang, 'capsule_creation_guide_step3'),
                    t(lang, 'capsule_creation_guide_step4')
                ]
            },
            'delivery': {
                'title': t(lang, 'delivery_guide_title'),
                'content': [
                    t(lang, 'delivery_guide_step1'),
                    t(lang, 'delivery_guide_step2'),
                    t(lang, 'delivery_guide_step3')
                ]
            },
            'sharing': {
                'title': t(lang, 'sharing_guide_title'),
                'content': [
                    t(lang, 'sharing_guide_step1'),
                    t(lang, 'sharing_guide_step2'),
                    t(lang, 'sharing_guide_step3')
                ]
            },
            'premium': {
                'title': t(lang, 'premium_guide_title'),
                'content': [
                    t(lang, 'premium_guide_step1'),
                    t(lang, 'premium_guide_step2'),
                    t(lang, 'premium_guide_step3')
                ]
            }
        }
        
        if section in content_mapping:
            section_data = content_mapping[section]
            content = f"<b>{section_data['title']}</b>\n\n"
            for i, item in enumerate(section_data['content'], 1):
                content += f"{i}. {item}\n"
            return content
        return None
    
    async def get_contextual_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Provide help based on user's current context or issues."""
        user_id = update.effective_user.id
        user_data = get_user_data_by_telegram_id(user_id)
        
        if not user_data:
            await update.message.reply_text(t(lang, 'please_start_bot'))
            return
        
        lang = user_data.get('language_code', 'ru')
        current_state = context.user_data.get('current_state', 'unknown')
        
        # Determine contextual help based on user state, behavior, and needs
        help_message = self._determine_contextual_help(user_data, current_state, lang)
        
        await update.message.reply_text(help_message, parse_mode='HTML')
    
    def _determine_contextual_help(self, user_data: Dict, current_state: str, lang: str) -> str:
        """Determine the most appropriate help based on user data."""
        # Check for proactive help triggers
        for trigger_name, trigger in self.proactive_triggers.items():
            if trigger['condition'](user_data):
                # Return proactive help message
                message = self._get_proactive_help_message(trigger_name, lang)
                if message:
                    return message
        
        # Based on user's stage in the app, provide appropriate help
        total_capsules = user_data.get('total_capsules_created', 0)
        onboarding_stage = user_data.get('onboarding_stage', 'not_started')
        
        if onboarding_stage in ['not_started', 'greeting_sent'] and total_capsules == 0:
            return t(lang, 'contextual_help_new_user', 
                    user_id=user_data.get('telegram_id'),
                    name=user_data.get('first_name', 'друг'))
        elif total_capsules > 0 and user_data.get('capsules_delivered', 0) == 0:
            return t(lang, 'contextual_help_first_delivery',
                    user_id=user_data.get('telegram_id'),
                    time_remaining="несколько часов")
        elif user_data.get('streak_count', 0) > 5:
            return t(lang, 'contextual_help_active_user',
                    user_id=user_data.get('telegram_id'),
                    streak=user_data.get('streak_count', 0))
        else:
            # General help
            return t(lang, 'contextual_help_general',
                    user_id=user_data.get('telegram_id'),
                    name=user_data.get('first_name', 'друг'))
    
    def _get_proactive_help_message(self, trigger_name: str, lang: str) -> str:
        """Get proactive help message for a specific trigger."""
        messages = {
            'new_user_confusion': t(lang, 'proactive_help_new_user'),
            'capsule_creation_difficulty': t(lang, 'proactive_help_first_capsule'),
            'delivery_confusion': t(lang, 'proactive_help_delivery_info')
        }
        
        return messages.get(trigger_name, messages['new_user_confusion'])
    
    async def detect_proactive_help_needed(self, user_id: int) -> Optional[str]:
        """Detect if user needs proactive help based on their behavior."""
        user_data = get_user_data_by_telegram_id(user_id)
        if not user_data:
            return None
        
        # Check each proactive trigger
        triggered_help = None
        highest_priority = -1
        
        for trigger_name, trigger in self.proactive_triggers.items():
            if trigger['condition'](user_data):
                if trigger['priority'] > highest_priority:
                    triggered_help = trigger_name
                    highest_priority = trigger['priority']
        
        if triggered_help:
            lang = user_data.get('language_code', 'ru')
            return self._get_proactive_help_message(triggered_help, lang)
        
        return None
    
    async def collect_feedback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Collect feedback from user about help system."""
        user_id = update.effective_user.id
        # Get feedback text from the update - this should always be from message.text 
        # since this method is only called by MessageHandler for text input
        feedback = update.message.text
        
        # Log the feedback (in a real system, you might store this in a database)
        logger.info(f"📝 Help feedback from user {user_id}: {feedback}")
        
        # Respond to user
        user_data = get_user_data_by_telegram_id(user_id)
        lang = user_data.get('language_code', 'ru') if user_data else 'ru'
        
        response = t(lang, 'help_feedback_thanks', user_id=user_id)
        
        # Since this is called by MessageHandler (for text input), update.message should exist
        await update.message.reply_text(response)
        
        # Return to help menu
        await self.get_smart_help_menu(update, context)
        return SMART_HELP_MENU
    
    def get_smart_help_handler(self):
        """Get conversation handler for smart help system."""
        from telegram.ext import CallbackQueryHandler, MessageHandler, filters, ConversationHandler
        
        smart_help_handler = ConversationHandler(
            entry_points=[],
            states={
                SMART_HELP_MENU: [
                    CallbackQueryHandler(self.handle_help_selection)
                ],
                CONTEXTUAL_HELP: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.collect_feedback)
                ],
                FEEDBACK_COLLECTION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.collect_feedback)
                ]
            },
            fallbacks=[],
            name="smart_help",
            persistent=False,
        )
        
        return smart_help_handler
    
    async def get_guided_tutorial(self, user_id: int, tutorial_type: str, lang: str = 'ru') -> List[Dict[str, str]]:
        """Provide step-by-step tutorial for specific features."""
        if tutorial_type == 'first_capsule':
            return [
                {
                    'step': 1,
                    'title': t(lang, 'guided_tutorial_title_1'),
                    'message': t(lang, 'guided_tutorial_msg_1'),
                    'action_hint': t(lang, 'guided_tutorial_action_1')
                },
                {
                    'step': 2,
                    'title': t(lang, 'guided_tutorial_title_2'),
                    'message': t(lang, 'guided_tutorial_msg_2'),
                    'action_hint': t(lang, 'guided_tutorial_action_2')
                },
                {
                    'step': 3,
                    'title': t(lang, 'guided_tutorial_title_3'),
                    'message': t(lang, 'guided_tutorial_msg_3'),
                    'action_hint': t(lang, 'guided_tutorial_action_3')
                },
                {
                    'step': 4,
                    'title': t(lang, 'guided_tutorial_title_4'),
                    'message': t(lang, 'guided_tutorial_msg_4'),
                    'action_hint': t(lang, 'guided_tutorial_action_4')
                },
                {
                    'step': 5,
                    'title': t(lang, 'guided_tutorial_title_5'),
                    'message': t(lang, 'guided_tutorial_msg_5'),
                    'action_hint': t(lang, 'guided_tutorial_action_5')
                }
            ]
        return []


# Global instance
smart_help_system = SmartHelpSystem()