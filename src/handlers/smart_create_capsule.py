"""
Smart capsule creator with contextual prompts and workflow assistance.
"""

from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from typing import Dict, Any, List, Optional
import logging

from ..database import get_user_data_by_telegram_id, get_user_data, create_capsule
from ..translations import t
from ..capsule_content_suggester import CapsuleContentSuggester, CapsuleType, ContentSuggestionType
from ..feature_config import feature_flag_manager, FeatureFlag
from ..config import (
    SELECTING_CONTENT_TYPE, RECEIVING_CONTENT, SELECTING_TIME,
    SELECTING_DATE, SELECTING_RECIPIENT, CONFIRMING_CAPSULE
)

logger = logging.getLogger(__name__)

# Smart creation conversation states
SMART_SELECTING_CAPSULE_TYPE, SMART_SELECTING_TEMPLATE, SMART_CREATING_CONTENT = range(3)


class SmartCapsuleCreator:
    """Manages intelligent capsule creation with contextual prompts and templates."""
    
    def __init__(self):
        self.content_suggester = CapsuleContentSuggester()
    
    async def start_smart_creation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start the smart capsule creation flow."""
        user_id = update.effective_user.id
        user_data = get_user_data_by_telegram_id(user_id)
        
        if not user_data:
            lang = 'en'
            if update.message:
                await update.message.reply_text(t(lang, 'please_start_bot'))
            else:
                query = update.callback_query
                if query:
                    await query.answer()
                    await query.edit_message_text(t(lang, 'please_start_bot'))
            return ConversationHandler.END
        
        lang = user_data.get('language_code', 'ru')
        
        # Check if smart creation feature is enabled
        if not feature_flag_manager.is_feature_enabled_for_user(user_id, FeatureFlag.CONTENT_SUGGESTIONS):
            # Fall back to regular creation
            from .create_capsule import start_create_capsule
            return await start_create_capsule(update, context)
        
        # Show capsule type selection
        keyboard = self._get_capsule_type_keyboard(lang)
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = t(lang, 'select_content_type') + "\n\n" + t(lang, 'smart_creation_intro')
        
        # Handle both regular messages and callback queries
        if update.message:
            await update.message.reply_text(message, reply_markup=reply_markup)
        else:
            query = update.callback_query
            if query:
                await query.answer()
                # Try to edit the message text, fallback to editing caption if the message has only caption
                try:
                    await query.edit_message_text(message, reply_markup=reply_markup)
                except:
                    try:
                        # If text editing fails, try editing caption
                        await query.edit_message_caption(caption=message, reply_markup=reply_markup)
                    except:
                        # If both fail, send a new message after deleting the old one
                        try:
                            await query.message.delete()
                            await query.message.reply_text(message, reply_markup=reply_markup)
                        except:
                            # Last fallback - send message without deleting
                            await query.message.reply_text(message, reply_markup=reply_markup)
        
        return SMART_SELECTING_CAPSULE_TYPE
    
    def _get_capsule_type_keyboard(self, lang: str) -> List[List[InlineKeyboardButton]]:
        """Get keyboard with smart capsule types."""
        types = CapsuleType.get_all_types()
        keyboard = []
        
        # Group types in pairs
        for i in range(0, len(types), 2):
            row = []
            for j in range(i, min(i+2, len(types))):
                capsule_type = types[j]
                # Get appropriate translation key
                type_key = self._get_type_translation_key(capsule_type)
                text = t(lang, type_key, type=capsule_type.value)
                row.append(InlineKeyboardButton(text, callback_data=f"smart_type_{capsule_type.value}"))
            keyboard.append(row)
        
        # Add back button
        keyboard.append([InlineKeyboardButton(t(lang, 'back'), callback_data='back_to_main')])
        
        return keyboard
    
    def _get_type_translation_key(self, capsule_type: CapsuleType) -> str:
        """Get appropriate translation key for capsule type."""
        # We'll use existing translation keys or create new specific ones
        mapping = {
            CapsuleType.REFLECTION: 'content_type_reflection',
            CapsuleType.DREAM: 'content_type_dream',
            CapsuleType.MEMORY: 'content_type_memory',
            CapsuleType.LETTER_TO_FUTURE: 'content_type_letter_future',
            CapsuleType.GRATITUDE: 'content_type_gratitude',
            CapsuleType.CHALLENGE: 'content_type_challenge'
        }
        return mapping.get(capsule_type, 'select_content_type')
    
    async def get_capsule_workflow(self, capsule_type: CapsuleType, user_data: Dict, lang: str = 'ru') -> Dict:
        """Get specific workflow for each capsule type."""
        workflows = {
            CapsuleType.REFLECTION: {
                'title': t(lang, 'workflow_reflection_title'),
                'steps': [
                    {
                        'prompt': t(lang, 'workflow_reflection_step1'),
                        'input_type': 'text',
                        'required': True
                    },
                    {
                        'prompt': t(lang, 'workflow_reflection_step2'),
                        'input_type': 'text',
                        'required': True
                    },
                    {
                        'prompt': t(lang, 'workflow_reflection_step3'),
                        'input_type': 'text',
                        'required': False
                    }
                ],
                'completion_message': t(lang, 'workflow_reflection_complete'),
                'delivery_suggestions': [7, 30, 60]  # days
            },
            CapsuleType.DREAM: {
                'title': t(lang, 'workflow_dream_title'),
                'steps': [
                    {
                        'prompt': t(lang, 'workflow_dream_step1'),
                        'input_type': 'text',
                        'required': True
                    },
                    {
                        'prompt': t(lang, 'workflow_dream_step2'),
                        'input_type': 'text',
                        'required': True
                    },
                    {
                        'prompt': t(lang, 'workflow_dream_step3'),
                        'input_type': 'text',
                        'required': False
                    }
                ],
                'completion_message': t(lang, 'workflow_dream_complete'),
                'delivery_suggestions': [90, 365, 1095]  # days
            },
            CapsuleType.MEMORY: {
                'title': t(lang, 'workflow_memory_title'),
                'steps': [
                    {
                        'prompt': t(lang, 'workflow_memory_step1'),
                        'input_type': 'text',
                        'required': True
                    },
                    {
                        'prompt': t(lang, 'workflow_memory_step2'),
                        'input_type': 'text',
                        'required': False
                    },
                    {
                        'prompt': t(lang, 'workflow_memory_step3'),
                        'input_type': 'text',
                        'required': True
                    }
                ],
                'completion_message': t(lang, 'workflow_memory_complete'),
                'delivery_suggestions': [365, 1095, 1825]  # days
            },
            CapsuleType.LETTER_TO_FUTURE: {
                'title': t(lang, 'workflow_letter_title'),
                'steps': [
                    {
                        'prompt': t(lang, 'workflow_letter_step1'),
                        'input_type': 'text',
                        'required': True
                    },
                    {
                        'prompt': t(lang, 'workflow_letter_step2'),
                        'input_type': 'text',
                        'required': True
                    },
                    {
                        'prompt': t(lang, 'workflow_letter_step3'),
                        'input_type': 'text',
                        'required': False
                    }
                ],
                'completion_message': t(lang, 'workflow_letter_complete'),
                'delivery_suggestions': [365, 1095, 1825]  # days
            },
            CapsuleType.GRATITUDE: {
                'title': t(lang, 'workflow_gratitude_title'),
                'steps': [
                    {
                        'prompt': t(lang, 'workflow_gratitude_step1'),
                        'input_type': 'text',
                        'required': True
                    },
                    {
                        'prompt': t(lang, 'workflow_gratitude_step2'),
                        'input_type': 'text',
                        'required': False
                    },
                    {
                        'prompt': t(lang, 'workflow_gratitude_step3'),
                        'input_type': 'text',
                        'required': False
                    }
                ],
                'completion_message': t(lang, 'workflow_gratitude_complete'),
                'delivery_suggestions': [365, 730]  # days
            },
            CapsuleType.CHALLENGE: {
                'title': t(lang, 'workflow_challenge_title'),
                'steps': [
                    {
                        'prompt': t(lang, 'workflow_challenge_step1'),
                        'input_type': 'text',
                        'required': True
                    },
                    {
                        'prompt': t(lang, 'workflow_challenge_step2'),
                        'input_type': 'text',
                        'required': True
                    },
                    {
                        'prompt': t(lang, 'workflow_challenge_step3'),
                        'input_type': 'text',
                        'required': True
                    }
                ],
                'completion_message': t(lang, 'workflow_challenge_complete'),
                'delivery_suggestions': [30, 90, 365]  # days
            }
        }
        
        return workflows.get(capsule_type, workflows[CapsuleType.REFLECTION])
    
    async def handle_capsule_type_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle capsule type selection with smart templates."""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        user_data = get_user_data_by_telegram_id(user_id)
        if not user_data:
            # Try to edit the message text, fallback to editing caption if the message has only caption
            try:
                await query.edit_message_text(t('en', 'please_start_bot_smart'))  # Use default language 'en'
            except:
                try:
                    # If text editing fails, try editing caption
                    await query.edit_message_caption(caption=t('en', 'please_start_bot_smart'))
                except:
                    # If both fail, send a new message after deleting the old one
                    try:
                        await query.message.delete()
                        await query.message.reply_text(t('en', 'please_start_bot_smart'))
                    except:
                        # Last fallback - send message without deleting
                        await query.message.reply_text(t('en', 'please_start_bot_smart'))
            return ConversationHandler.END
        
        lang = user_data.get('language_code', 'ru')
        
        if query.data.startswith('smart_type_'):
            capsule_type_value = query.data.replace('smart_type_', '')
            try:
                capsule_type = CapsuleType(capsule_type_value)
                
                # Store the selected type in context
                context.user_data['smart_capsule_type'] = capsule_type_value
                
                # Show appropriate template based on type
                templates = self.content_suggester.get_writing_templates(
                    self._map_capsule_type_to_content_type(capsule_type), lang
                )
                
                # Create template selection keyboard
                keyboard = self._get_template_keyboard(lang, capsule_type)
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                message = f"📝 Выбран тип капсулы: <b>{capsule_type.value}</b>\n\n"
                message += "Выберите шаблон или напишите свой контент:"
                
                # Try to edit the message text, fallback to editing caption if the message has only caption
                try:
                    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='HTML')
                except:
                    try:
                        # If text editing fails, try editing caption
                        await query.edit_message_caption(caption=message, reply_markup=reply_markup, parse_mode='HTML')
                    except:
                        # If both fail, send a new message after deleting the old one
                        try:
                            await query.message.delete()
                            await query.message.reply_text(message, reply_markup=reply_markup, parse_mode='HTML')
                        except:
                            # Last fallback - send message without deleting
                            await query.message.reply_text(message, reply_markup=reply_markup, parse_mode='HTML')
                return SMART_SELECTING_TEMPLATE
                
            except ValueError:
                # Try to edit the message text, fallback to editing caption if the message has only caption
                try:
                    await query.edit_message_text(t(lang, 'error_occurred'))
                except:
                    try:
                        # If text editing fails, try editing caption
                        await query.edit_message_caption(caption=t(lang, 'error_occurred'))
                    except:
                        # If both fail, send a new message after deleting the old one
                        try:
                            await query.message.delete()
                            await query.message.reply_text(t(lang, 'error_occurred'))
                        except:
                            # Last fallback - send message without deleting
                            await query.message.reply_text(t(lang, 'error_occurred'))
                return ConversationHandler.END
        
        elif query.data == 'back_to_main':
            # Go back to main menu
            from .main_menu import main_menu_handler
            return await main_menu_handler(update, context)
        
        return SMART_SELECTING_CAPSULE_TYPE
    
    def _map_capsule_type_to_content_type(self, capsule_type: CapsuleType) -> ContentSuggestionType:
        """Map capsule type to content suggestion type."""
        mapping = {
            CapsuleType.REFLECTION: ContentSuggestionType.REFLECTION,
            CapsuleType.DREAM: ContentSuggestionType.GOALS,
            CapsuleType.MEMORY: ContentSuggestionType.MOMENT_CAPTURE,
            CapsuleType.LETTER_TO_FUTURE: ContentSuggestionType.LETTERS,
            CapsuleType.GRATITUDE: ContentSuggestionType.GRATITUDE,
            CapsuleType.CHALLENGE: ContentSuggestionType.CHALLENGES
        }
        return mapping.get(capsule_type, ContentSuggestionType.REFLECTION)
    
    def _get_template_keyboard(self, lang: str, capsule_type: CapsuleType) -> List[List[InlineKeyboardButton]]:
        """Get keyboard with template options."""
        keyboard = []
        
        # Add template options based on type using translations
        templates = {
            CapsuleType.REFLECTION: [
                (t(lang, 'smart_capsule_template_journal'), "journal_entry"),
                (t(lang, 'smart_capsule_template_daily_reflection'), "daily_reflection"),
                (t(lang, 'smart_capsule_template_deep_meditation'), "deep_meditation")
            ],
            CapsuleType.DREAM: [
                (t(lang, 'smart_capsule_template_big_dream'), "big_dream"),
                (t(lang, 'smart_capsule_template_short_term_goal'), "short_term_goal"),
                (t(lang, 'smart_capsule_template_success_visualization'), "success_visualization")
            ],
            CapsuleType.MEMORY: [
                (t(lang, 'smart_capsule_template_warm_memory'), "warm_memory"),
                (t(lang, 'smart_capsule_template_important_moment'), "important_moment"),
                (t(lang, 'smart_capsule_template_story_with_lesson'), "story_with_lesson")
            ],
            CapsuleType.LETTER_TO_FUTURE: [
                (t(lang, 'smart_capsule_template_letter_1_year'), "letter_1_year"),
                (t(lang, 'smart_capsule_template_letter_5_years'), "letter_5_years"),
                (t(lang, 'smart_capsule_template_advice_from_now'), "advice_from_now")
            ],
            CapsuleType.GRATITUDE: [
                (t(lang, 'smart_capsule_template_gratitude_journal'), "gratitude_journal"),
                (t(lang, 'smart_capsule_template_gratitude_people'), "gratitude_people"),
                (t(lang, 'smart_capsule_template_gratitude_life'), "gratitude_life")
            ],
            CapsuleType.CHALLENGE: [
                (t(lang, 'smart_capsule_template_current_challenge'), "current_challenge"),
                (t(lang, 'smart_capsule_template_learning_from_it'), "learning_from_it"),
                (t(lang, 'smart_capsule_template_overcoming_it'), "overcoming_it")
            ]
        }
        
        type_templates = templates.get(capsule_type, [])
        
        # Group templates in pairs
        for i in range(0, len(type_templates), 2):
            row = []
            for j in range(i, min(i+2, len(type_templates))):
                template_text, template_key = type_templates[j]
                row.append(InlineKeyboardButton(
                    template_text, 
                    callback_data=f"template_{template_key}"
                ))
            keyboard.append(row)
        
        # Add custom content option and back button
        keyboard.append([InlineKeyboardButton(t(lang, 'smart_capsule_custom_content'), callback_data="custom_content")])
        keyboard.append([InlineKeyboardButton(t(lang, 'back'), callback_data="back_to_type_selection")])
        
        return keyboard
    
    def get_content_enhancement_tips(self, content_type: ContentSuggestionType, user_input: str = "", lang: str = 'ru') -> List[str]:
        """Get content enhancement tips based on content type and user input."""
        tips = {
            ContentSuggestionType.REFLECTION: [
                t(lang, 'tip_add_emotions'),
                t(lang, 'tip_describe_impact'),
                t(lang, 'tip_share_experience'),
                t(lang, 'tip_include_sensory_details')
            ],
            ContentSuggestionType.GOALS: [
                t(lang, 'tip_make_goals_specific_measurable'),
                t(lang, 'tip_add_timelines'),
                t(lang, 'tip_describe_importance'),
                t(lang, 'tip_mention_specific_steps')
            ],
            ContentSuggestionType.GRATITUDE: [
                t(lang, 'tip_be_specific_not_general'),
                t(lang, 'tip_explain_gratitude_reason'),
                t(lang, 'tip_describe_impact_on_life'),
                t(lang, 'tip_add_emotional_details')
            ],
            ContentSuggestionType.MOMENT_CAPTURE: [
                t(lang, 'tip_describe_setting_detailed'),
                t(lang, 'tip_include_all_senses'),
                t(lang, 'tip_record_thoughts'),
                t(lang, 'tip_describe_what_makes_moment_important')
            ],
            ContentSuggestionType.LETTERS: [
                t(lang, 'tip_address_recipient_by_name'),
                t(lang, 'tip_be_sincere_open'),
                t(lang, 'tip_add_personal_details'),
                t(lang, 'tip_express_feelings_not_just_facts')
            ],
            ContentSuggestionType.CHALLENGES: [
                t(lang, 'tip_describe_situation_details'),
                t(lang, 'tip_note_what_you_learned'),
                t(lang, 'tip_include_steps_youre_taking'),
                t(lang, 'tip_add_how_it_changes_you')
            ]
        }
        
        # Basic content quality checks based on user input
        quality_tips = []
        if user_input:
            if len(user_input.split()) < 10:
                quality_tips.append(t(lang, 'tip_make_text_longer_for_clarity'))
            if '?' not in user_input and '.' not in user_input[5:]:  # Check for proper punctuation after first few chars
                quality_tips.append(t(lang, 'tip_add_more_structure_punctuation'))
            if user_input.lower().count('и') > 5:  # Check for excessive conjunctions
                quality_tips.append(t(lang, 'tip_diversify_sentence_structure_suggestions'))
        
        all_tips = tips.get(content_type, []) + quality_tips
        # Return a sample of tips to not overwhelm the user
        return all_tips[:4]  # Return first 4 tips
    
    def get_smart_content_evaluation(self, content: str, content_type: ContentSuggestionType) -> Dict[str, Any]:
        """Evaluate content quality and provide suggestions."""
        evaluation = {
            'length_score': 0,
            'quality_score': 0,
            'suggestions': [],
            'positive_feedback': []
        }
        
        word_count = len(content.split())
        
        # Length evaluation
        if 20 <= word_count <= 200:
            evaluation['length_score'] = 90
            evaluation['positive_feedback'].append("✅ Отличная длина текста")
        elif 10 <= word_count < 20:
            evaluation['length_score'] = 70
            evaluation['suggestions'].append("Добавьте немного больше деталей")
        elif word_count > 200:
            evaluation['length_score'] = 80
            evaluation['positive_feedback'].append("✅ Большой объем информации")
            if word_count > 500:
                evaluation['suggestions'].append("Возможно, текст слишком длинный для восприятия")
        else:
            evaluation['length_score'] = 40
            evaluation['suggestions'].append("Текст слишком короткий, добавьте больше информации")
        
        # Type-specific evaluation
        if content_type == ContentSuggestionType.REFLECTION:
            # Look for emotional language
            emotional_words = ['чувствую', 'эмоция', 'волнуюсь', 'рад', 'печалюсь', 'счастлив', 
                              'think', 'feel', 'emotion', 'happy', 'sad', 'excited', 'anxious']
            has_emotions = any(word in content.lower() for word in emotional_words)
            if has_emotions:
                evaluation['quality_score'] += 25
                evaluation['positive_feedback'].append("✅ Хорошо переданы эмоции")
            else:
                evaluation['suggestions'].append("Добавьте больше эмоциональных описаний")
        
        elif content_type == ContentSuggestionType.GOALS:
            future_words = ['буду', 'хотелось бы', 'планирую', 'мечтаю', 'will', 'would like', 'plan']
            has_future_orientation = any(word in content.lower() for word in future_words)
            if has_future_orientation:
                evaluation['quality_score'] += 25
                evaluation['positive_feedback'].append("✅ Хорошая ориентация на будущее")
            else:
                evaluation['suggestions'].append("Сделайте акцент на будущих действиях и целях")
        
        elif content_type == ContentSuggestionType.GRATITUDE:
            gratitude_words = ['благодар', 'спасибо', 'цен', 'признател', 'thank', 'grateful', 'appreciate']
            has_gratitude = any(word in content.lower() for word in gratitude_words)
            if has_gratitude:
                evaluation['quality_score'] += 25
                evaluation['positive_feedback'].append("✅ Хорошо выражена благодарность")
            else:
                evaluation['suggestions'].append("Усильте выражение благодарности")
        
        # Overall quality boost based on variety
        unique_words = len(set(content.lower().split()))
        total_words = len(content.split())
        if total_words > 0 and unique_words / total_words > 0.5:  # More than 50% unique words
            evaluation['quality_score'] += 20
            evaluation['positive_feedback'].append("✅ Хорошое разнообразие слов")
        
        # Calculate final score
        evaluation['overall_score'] = (evaluation['length_score'] + evaluation['quality_score']) // 2
        
        return evaluation
    
    async def handle_template_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle template selection and show writing assistance."""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        user_data = get_user_data_by_telegram_id(user_id)
        if not user_data:
            # Try to edit the message text, fallback to editing caption if the message has only caption
            try:
                await query.edit_message_text(t('en', 'please_start_bot_smart'))  # Use default language 'en'
            except:
                try:
                    # If text editing fails, try editing caption
                    await query.edit_message_caption(caption=t('en', 'please_start_bot_smart'))
                except:
                    # If both fail, send a new message after deleting the old one
                    try:
                        await query.message.delete()
                        await query.message.reply_text(t('en', 'please_start_bot_smart'))
                    except:
                        # Last fallback - send message without deleting
                        await query.message.reply_text(t('en', 'please_start_bot_smart'))
            return ConversationHandler.END
        
        lang = user_data.get('language_code', 'ru')
        
        if query.data.startswith('template_'):
            template_key = query.data.replace('template_', '')
            
            # Get the capsule type from context
            capsule_type_value = context.user_data.get('smart_capsule_type')
            if not capsule_type_value:
                # Try to edit the message text, fallback to editing caption if the message has only caption
                try:
                    await query.edit_message_text(t(lang, 'error_occurred'))
                except:
                    try:
                        # If text editing fails, try editing caption
                        await query.edit_message_caption(caption=t(lang, 'error_occurred'))
                    except:
                        # If both fail, send a new message after deleting the old one
                        try:
                            await query.message.delete()
                            await query.message.reply_text(t(lang, 'error_occurred'))
                        except:
                            # Last fallback - send message without deleting
                            await query.message.reply_text(t(lang, 'error_occurred'))
                return ConversationHandler.END
            
            capsule_type = CapsuleType(capsule_type_value)
            content_type = self._map_capsule_type_to_content_type(capsule_type)
            
            # Get template content
            templates = self.content_suggester.get_writing_templates(content_type, lang)
            
            # Show template with writing prompts
            message = f"📝 Шаблон: <b>{templates.get('title', 'Контент')}</b>\n\n"
            message += f" {templates.get('introduction', '')}\n\n"
            
            # Add prompts
            prompts = templates.get('prompts', [])
            for i, prompt in enumerate(prompts[:3], 1):  # Show first 3 prompts
                message += f"{i}. {prompt}\n"
            
            message += "\n💡 Подсказки по написанию:\n"
            tips = templates.get('writing_tips', [])
            for tip in tips[:3]:  # Show first 3 tips
                message += f"• {tip}\n"
            
            message += "\n" + t(lang, 'send_content', type=t(lang, 'content_text'))
            
            await query.edit_message_text(message, parse_mode='HTML')
            
            # Store template info for later use
            context.user_data['smart_template'] = template_key
            context.user_data['content_type'] = content_type.value
            
            # Next step would be to receive content
            # For now, let's transition to the normal content receiving flow
            # In a full implementation, we'd continue with SMART_CREATING_CONTENT
            return SMART_CREATING_CONTENT
        
        elif query.data == 'custom_content':
            # User wants to write custom content
            capsule_type_value = context.user_data.get('smart_capsule_type')
            if not capsule_type_value:
                # Try to edit the message text, fallback to editing caption if the message has only caption
                try:
                    await query.edit_message_text(t(lang, 'error_occurred'))
                except:
                    try:
                        # If text editing fails, try editing caption
                        await query.edit_message_caption(caption=t(lang, 'error_occurred'))
                    except:
                        # If both fail, send a new message after deleting the old one
                        try:
                            await query.message.delete()
                            await query.message.reply_text(t(lang, 'error_occurred'))
                        except:
                            # Last fallback - send message without deleting
                            await query.message.reply_text(t(lang, 'error_occurred'))
                return ConversationHandler.END
            
            capsule_type = CapsuleType(capsule_type_value)
            content_type = self._map_capsule_type_to_content_type(capsule_type)
            
            # Get general writing assistance for the content type
            templates = self.content_suggester.get_writing_templates(content_type, lang)
            
            message = f"✍️ {t(lang, 'custom_content_creation', type=capsule_type.value)}\n\n"
            message += f" {templates.get('introduction', t(lang, 'send_content', type=t(lang, 'content_text')))}\n\n"
            
            message += f"💡 {t(lang, 'smart_content_enhancement_tips')}:\n"
            tips = templates.get('writing_tips', [])
            for tip in tips[:3]:
                message += f"• {tip}\n"
            
            # Try to edit the message text, fallback to editing caption if the message has only caption
            try:
                await query.edit_message_text(message, parse_mode='HTML')
            except:
                try:
                    # If text editing fails, try editing caption
                    await query.edit_message_caption(caption=message, parse_mode='HTML')
                except:
                    # If both fail, send a new message after deleting the old one
                    try:
                        await query.message.delete()
                        await query.message.reply_text(message, parse_mode='HTML')
                    except:
                        # Last fallback - send message without deleting
                        await query.message.reply_text(message, parse_mode='HTML')
            
            context.user_data['content_type'] = content_type.value
            return SMART_CREATING_CONTENT
        
        elif query.data == 'back_to_type_selection':
            # Show type selection again
            keyboard = self._get_capsule_type_keyboard(lang)
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Try to edit the message text, fallback to editing caption if the message has only caption
            try:
                await query.edit_message_text("📝 Выберите тип капсулы:", reply_markup=reply_markup)
            except:
                try:
                    # If text editing fails, try editing caption
                    await query.edit_message_caption(caption="📝 Выберите тип капсулы:", reply_markup=reply_markup)
                except:
                    # If both fail, send a new message after deleting the old one
                    try:
                        await query.message.delete()
                        await query.message.reply_text("📝 Выберите тип капсулы:", reply_markup=reply_markup)
                    except:
                        # Last fallback - send message without deleting
                        await query.message.reply_text("📝 Выберите тип капсулы:", reply_markup=reply_markup)
            return SMART_SELECTING_CAPSULE_TYPE
        
        return SMART_SELECTING_TEMPLATE
    
    async def receive_smart_content(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Receive and validate smart content."""
        user_id = update.effective_user.id
        user_data = get_user_data_by_telegram_id(user_id)
        if not user_data:
            lang = 'en'  # default language
            if update.message:
                await update.message.reply_text(t(lang, 'please_start_bot_smart'))
            else:
                query = update.callback_query
                if query:
                    await query.answer()
                    # Try to edit the message text, fallback to editing caption if the message has only caption
                    try:
                        await query.edit_message_text(t(lang, 'please_start_bot_smart'))
                    except:
                        try:
                            # If text editing fails, try editing caption
                            await query.edit_message_caption(caption=t(lang, 'please_start_bot_smart'))
                        except:
                            # If both fail, send a new message after deleting the old one
                            try:
                                await query.message.delete()
                                await query.message.reply_text(t(lang, 'please_start_bot_smart'))
                            except:
                                # Last fallback - send message without deleting
                                await query.message.reply_text(t(lang, 'please_start_bot_smart'))
            return ConversationHandler.END
        
        lang = user_data.get('language_code', 'ru')
        
        content = update.message.text if update.message else None
        if not content:
            # If not text, check for other content types (photo, etc.)
            if update.message:
                await update.message.reply_text(t(lang, 'send_content', type=t(lang, 'content_text')))
            else:
                # Handle callback query scenario if needed
                query = update.callback_query
                if query:
                    await query.answer()
                    # Try to edit the message text, fallback to editing caption if the message has only caption
                    try:
                        await query.edit_message_text(t(lang, 'send_content', type=t(lang, 'content_text')))
                    except:
                        try:
                            # If text editing fails, try editing caption
                            await query.edit_message_caption(caption=t(lang, 'send_content', type=t(lang, 'content_text')))
                        except:
                            # If both fail, send a new message after deleting the old one
                            try:
                                await query.message.delete()
                                await query.message.reply_text(t(lang, 'send_content', type=t(lang, 'content_text')))
                            except:
                                # Last fallback - send message without deleting
                                await query.message.reply_text(t(lang, 'send_content', type=t(lang, 'content_text')))
            return SMART_CREATING_CONTENT
        
        # Store the content in context
        context.user_data['content_text'] = content
        
        # Get content type from context
        content_type_value = context.user_data.get('content_type', 'reflection')
        try:
            # Map the value back to ContentSuggestionType enum
            content_type_mapping = {
                'reflection': ContentSuggestionType.REFLECTION,
                'goals': ContentSuggestionType.GOALS,
                'gratitude': ContentSuggestionType.GRATITUDE,
                'moment_capture': ContentSuggestionType.MOMENT_CAPTURE,
                'letters': ContentSuggestionType.LETTERS,
                'challenges': ContentSuggestionType.CHALLENGES
            }
            content_suggestion_type = content_type_mapping.get(content_type_value, ContentSuggestionType.REFLECTION)
        except:
            content_suggestion_type = ContentSuggestionType.REFLECTION
        
        # Evaluate content quality
        evaluation = self.get_smart_content_evaluation(content, content_suggestion_type)
        
        # Build feedback message
        feedback_message = t(lang, 'content_saved') + "\n\n"
        
        # Add positive feedback
        if evaluation['positive_feedback']:
            feedback_message += t(lang, 'smart_content_positive_feedback') + ":\n"
            for feedback in evaluation['positive_feedback'][:2]:  # Show first 2 positive points
                feedback_message += f"• {feedback}\n"
            feedback_message += "\n"
        
        # Add suggestions if any
        if evaluation['suggestions']:
            feedback_message += t(lang, 'smart_content_suggestions') + ":\n"
            for suggestion in evaluation['suggestions'][:2]:  # Show first 2 suggestions
                feedback_message += f"• {suggestion}\n"
            feedback_message += "\n"
        
        # Handle both regular messages and callback queries
        if update.message:
            await update.message.reply_text(feedback_message)
        else:
            query = update.callback_query
            if query:
                await query.answer()
                # Try to edit the message text, fallback to editing caption if the message has only caption
                try:
                    await query.edit_message_text(feedback_message)
                except:
                    try:
                        # If text editing fails, try editing caption
                        await query.edit_message_caption(caption=feedback_message)
                    except:
                        # If both fail, send a new message after deleting the old one
                        try:
                            await query.message.delete()
                            await query.message.reply_text(feedback_message)
                        except:
                            # Last fallback - send message without deleting
                            await query.message.reply_text(feedback_message)
        
        # Get smart time suggestions
        time_suggestions = await self.get_smart_time_suggestions(user_id, content_type_value.replace('_', ''))
        
        if time_suggestions:
            # Show intelligent time suggestions
            time_message = t(lang, 'smart_time_suggestions_title') + "\n\n"
            
            for i, suggestion in enumerate(time_suggestions[:3]):  # Show top 3 suggestions
                date_str = suggestion['date'].strftime("%d.%m.%Y")
                time_message += f"• {date_str} - {suggestion['reason']}\n"
            
            time_message += "\n" + t(lang, 'select_time')
            
            # Create keyboard with smart suggestions
            keyboard = []
            for suggestion in time_suggestions[:3]:
                date_str = suggestion['date'].strftime("%d.%m.%Y")
                keyboard.append([InlineKeyboardButton(
                    f"{date_str} ({suggestion['reason']})", 
                    callback_data=f"smart_time_{suggestion['days']}"
                )])
            
            # Add standard options
            keyboard.append([
                InlineKeyboardButton(t(lang, 'time_1day'), callback_data="time_1day"),
                InlineKeyboardButton(t(lang, 'time_1week'), callback_data="time_1week")
            ])
            keyboard.append([
                InlineKeyboardButton(t(lang, 'time_1month'), callback_data="time_1month"),
                InlineKeyboardButton(t(lang, 'time_1year'), callback_data="time_1year")
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            # Handle both regular messages and callback queries
            if update.message:
                await update.message.reply_text(time_message, reply_markup=reply_markup)
            else:
                query = update.callback_query
                if query:
                    await query.answer()
                    # Try to edit the message text, fallback to editing caption if the message has only caption
                    try:
                        await query.edit_message_text(time_message, reply_markup=reply_markup)
                    except:
                        try:
                            # If text editing fails, try editing caption
                            await query.edit_message_caption(caption=time_message, reply_markup=reply_markup)
                        except:
                            # If both fail, send a new message after deleting the old one
                            try:
                                await query.message.delete()
                                await query.message.reply_text(time_message, reply_markup=reply_markup)
                            except:
                                # Last fallback - send message without deleting
                                await query.message.reply_text(time_message, reply_markup=reply_markup)
            
            # Store evaluation in context for later use
            context.user_data['content_evaluation'] = evaluation
            context.user_data['content_type_enum'] = content_suggestion_type.value
            
            # Stay in smart creation to handle time selection
            return SMART_CREATING_CONTENT
        else:
            # Fallback to regular time selection
            message = t(lang, 'select_time')
            # Handle both regular messages and callback queries
            if update.message:
                await update.message.reply_text(message)
            else:
                query = update.callback_query
                if query:
                    await query.answer()
                    # Try to edit the message text, fallback to editing caption if the message has only caption
                    try:
                        await query.edit_message_text(message)
                    except:
                        try:
                            # If text editing fails, try editing caption
                            await query.edit_message_caption(caption=message)
                        except:
                            # If both fail, send a new message after deleting the old one
                            try:
                                await query.message.delete()
                                await query.message.reply_text(message)
                            except:
                                # Last fallback - send message without deleting
                                await query.message.reply_text(message)
            return SELECTING_TIME
    
    async def get_smart_time_suggestions(self, user_id: int, content_type: str) -> List[Dict]:
        """Get intelligent time suggestions based on content type and user behavior."""
        user_data = get_user_data_by_telegram_id(user_id)
        if not user_data:
            return []
        
        suggestions = []
        
        # Content type-based suggestions
        type_suggestions = {
            'reflection': [
                {'delay_days': 7, 'reason': 'через неделю, чтобы осознать мысли'},
                {'delay_days': 30, 'reason': 'через месяц, для долгосрочной рефлексии'},
            ],
            'dream': [
                {'delay_days': 90, 'reason': 'через 3 месяца, для проверки прогресса'},
                {'delay_days': 365, 'reason': 'через год, для проверки достижения мечты'},
            ],
            'gratitude': [
                {'delay_days': 365, 'reason': 'через год, для напоминания о хорошем'},
                {'delay_days': 30, 'reason': 'через месяц, для улучшения настроения'},
            ],
            'memory': [
                {'delay_days': 365, 'reason': 'через год, для ностальгии'},
                {'delay_days': 180, 'reason': 'через полгода, для воспоминаний'},
            ],
            'letter_to_future': [
                {'delay_days': 365, 'reason': 'через год, для встречи с будущим собой'},
                {'delay_days': 1825, 'reason': 'через 5 лет, для важного жизненного этапа'},
            ],
            'challenge': [
                {'delay_days': 30, 'reason': 'через месяц, для оценки прогресса'},
                {'delay_days': 90, 'reason': 'через 3 месяца, для осознания роста'},
            ]
        }
        
        content_key = content_type.replace('capsule', '').replace('_', '')
        if content_key in type_suggestions:
            for suggestion in type_suggestions[content_key]:
                future_date = datetime.now() + timedelta(days=suggestion['delay_days'])
                suggestions.append({
                    'date': future_date,
                    'reason': suggestion['reason'],
                    'days': suggestion['delay_days']
                })
        
        # Add user behavior-based suggestions
        if user_data.get('streak_count', 0) > 5:
            # For active users, suggest more frequent intervals
            suggestions.append({
                'date': datetime.now() + timedelta(days=14),
                'reason': 'через 2 недели, для активных пользователей',
                'days': 14
            })
        
        return suggestions
    
    async def get_smart_recipient_suggestions(self, user_id: int, content_type: str) -> List[Dict]:
        """Get intelligent recipient suggestions based on content type."""
        user_data = get_user_data_by_telegram_id(user_id)
        if not user_data:
            return []
        
        suggestions = []
        
        # Content type-based recipient suggestions
        if content_type in ['letter_to_future', 'reflection']:
            suggestions.append({
                'type': 'self',
                'reason': 'для личной рефлексии и саморазвития'
            })
        elif content_type in ['gratitude', 'memory']:
            suggestions.append({
                'type': 'loved_ones',
                'reason': 'для близких людей, которые трогают ваше сердце'
            })
        elif content_type == 'dream':
            suggestions.append({
                'type': 'accountability_partner',
                'reason': 'кому вы доверяете свои цели и мечты'
            })
        
        # Add based on user's past behavior
        if user_data.get('total_capsules_created', 0) > 10:
            # Experienced users might want to send to others
            suggestions.append({
                'type': 'friends',
                'reason': 'для друзей, которые оценят вашу историю'
            })
        
        return suggestions
    
    def get_smart_creation_handler(self):
        """Get the conversation handler for smart capsule creation."""
        from telegram.ext import CallbackQueryHandler, MessageHandler, filters, ConversationHandler
        
        smart_creation_handler = ConversationHandler(
            entry_points=[],
            states={
                SMART_SELECTING_CAPSULE_TYPE: [
                    CallbackQueryHandler(self.handle_capsule_type_selection)
                ],
                SMART_SELECTING_TEMPLATE: [
                    CallbackQueryHandler(self.handle_template_selection)
                ],
                SMART_CREATING_CONTENT: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.receive_smart_content)
                ]
            },
            fallbacks=[],
            name="smart_creation",
            persistent=False,
        )
        
        return smart_creation_handler


# Global instance
smart_capsule_creator = SmartCapsuleCreator()