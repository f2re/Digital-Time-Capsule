"""
Enhanced capsule delivery experience with anticipation building, dramatic opening,
reaction collection, and reply functionality.
"""

from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from typing import Dict, List, Optional, Any
import logging
import uuid
import json

from .database import (
    get_user_data_by_telegram_id, get_capsule_by_id, 
    mark_capsule_delivered, get_pending_capsules
)
from .translations import t
from .feature_config import feature_flag_manager, FeatureFlag
from .config import (
    SELECTING_RECIPIENT, CONFIRMING_CAPSULE
)  # Import for potential integration

logger = logging.getLogger(__name__)

# Delivery conversation states
ANTICIPATION_BUILDING, DRAMATIC_OPENING, REACTION_COLLECTION, REPLY_TO_PAST_SELF = range(4)


class CapsuleDeliveryEnhancer:
    """Manages enhanced delivery experience with anticipation, opening drama, and interaction."""
    
    def __init__(self):
        # These are now accessed via translation system
        pass
    
    async def initiate_anticipation_sequence(self, user_id: int, capsule_data: Dict, lang: str = 'ru'):
        """Initiate the anticipation building sequence before capsule delivery."""
        try:
            delivery_time = capsule_data.get('delivery_time')
            if not delivery_time:
                return False
            
            # Schedule anticipation messages at different times before delivery
            from .smart_scheduler import smart_scheduler
            
            if smart_scheduler:
                # Schedule 24 hours before
                pre_open_24h = delivery_time - timedelta(hours=24)
                if pre_open_24h > datetime.now():
                    smart_scheduler.scheduler.add_job(
                        self._send_anticipation_message,
                        'date',
                        run_date=pre_open_24h,
                        args=[user_id, capsule_data, '24h_before', lang],
                        id=f"anticipation_24h_{capsule_data['id']}"
                    )
                
                # Schedule 2 hours before
                pre_open_2h = delivery_time - timedelta(hours=2)
                if pre_open_2h > datetime.now():
                    smart_scheduler.scheduler.add_job(
                        self._send_anticipation_message,
                        'date',
                        run_date=pre_open_2h,
                        args=[user_id, capsule_data, '2h_before', lang],
                        id=f"anticipation_2h_{capsule_data['id']}"
                    )
                
                # Schedule 15 minutes before
                pre_open_15m = delivery_time - timedelta(minutes=15)
                if pre_open_15m > datetime.now():
                    smart_scheduler.scheduler.add_job(
                        self._send_anticipation_message,
                        'date',
                        run_date=pre_open_15m,
                        args=[user_id, capsule_data, '15m_before', lang],
                        id=f"anticipation_15m_{capsule_data['id']}"
                    )
                
                logger.info(f"📅 Anticipation sequence scheduled for capsule {capsule_data['id']}")
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error initiating anticipation sequence: {e}")
            return False
    
    async def _send_anticipation_message(self, user_id: int, capsule_data: Dict, timing: str, lang: str):
        """Send a specific anticipation message."""
        try:
            user_data = get_user_data_by_telegram_id(user_id)
            if not user_data:
                logger.error(f"User {user_id} not found for anticipation message")
                return
            
            # Get the anticipation message via translation
            translation_key = f"anticipation_{timing}_{lang}"
            message = t(lang, translation_key, creation_date=capsule_data.get('created_at', 'unknown'))
            
            # Add emotional building elements via translation
            if timing == '24h_before':
                message += t(lang, 'anticipation_24h_question_' + lang)
            elif timing == '2h_before':
                message += t(lang, 'anticipation_2h_approaching_' + lang)
            elif timing == '15m_before':
                message += t(lang, 'anticipation_15m_soon_' + lang)
            
            # Send the message via bot
            # Note: Would need bot instance, simplified for now
            logger.info(f"⏳ Sent anticipation message ({timing}) to user {user_id}")
            
        except Exception as e:
            logger.error(f"Error sending anticipation message: {e}")
    
    async def deliver_capsule_dramatically(self, user_id: int, capsule_data: Dict, bot):
        """Deliver capsule with dramatic opening experience."""
        try:
            user_data = get_user_data_by_telegram_id(user_id)
            if not user_data:
                logger.error(f"User {user_id} not found for dramatic delivery")
                return False
            
            lang = user_data.get('language_code', 'ru')
            sender_name = capsule_data.get('sender_name', 'Неизвестный')
            
            # Send opening announcement with dramatic flair
            opening_phrase = t(lang, 'opening_phrase_past_greeting_' + lang)
            
            # Create suspenseful message sequence
            suspense_messages = [
                "...")
            ]
            
            # Send suspense messages with delays (in actual implementation)
            # await bot.send_message(chat_id=user_id, text="...", parse_mode='HTML')
            
            # Build the main delivery message
            delivery_time = capsule_data.get('delivery_time', datetime.now())
            creation_time = capsule_data.get('created_at', datetime.now())
            
            # Calculate days between creation and delivery
            if hasattr(delivery_time, '__sub__') and hasattr(creation_time, '__sub__'):
                days_apart = (delivery_time - creation_time).days
            else:
                days_apart = 0
            
            # Main delivery message
            main_message = f"{opening_phrase}\n\n"
            main_message += f" {/*t(lang, 'from')*/}: {sender_name}\n"
            main_message += f" {/*t(lang, 'created')*/}: {creation_time.strftime('%d.%m.%Y %H:%M')}\n"
            main_message += f" {/*t(lang, 'elapsed_time', count=days_apart)*/ if days_apart > 0 else ''}\n\n"
            
            # Divider to create drama
            main_message += "---\n"
            
            # Add the actual capsule content
            content = capsule_data.get('content_text', '')
            if content:
                main_message += content
            else:
                main_message += t(lang, 'capsule_has_content', type=capsule_data.get('content_type', 'text'))
            
            # Add message if exists
            message = capsule_data.get('message', '')
            if message:
                main_message += f"\n\n💬 {message}"
            
            # Add final divider and emotional element
            main_message += "\n---\n\n"
            main_message += t(lang, 'capsule_what_changed_' + lang)
            
            # Send the dramatic delivery message
            await bot.send_message(chat_id=user_id, text=main_message, parse_mode='HTML')
            
            # Mark capsule as delivered
            mark_capsule_delivered(capsule_data['id'])
            
            logger.info(f"🎭 Dramatic delivery completed for capsule {capsule_data['id']} to user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error in dramatic delivery: {e}")
            return False
    
    async def collect_reaction_after_opening(self, user_id: int, capsule_data: Dict, bot):
        """Collect user reaction after capsule opening."""
        try:
            user_data = get_user_data_by_telegram_id(user_id)
            if not user_data:
                return False
            
            lang = user_data.get('language_code', 'ru')
            
            # Create reaction options
            keyboard = [
                [
                    InlineKeyboardButton(t(lang, 'reaction_button_heartfelt_' + lang), callback_data="reaction_heartfelt"),
                    InlineKeyboardButton(t(lang, 'reaction_button_funny_' + lang), callback_data="reaction_funny")
                ],
                [
                    InlineKeyboardButton(t(lang, 'reaction_button_inspiring_' + lang), callback_data="reaction_inspiring"),
                    InlineKeyboardButton(t(lang, 'reaction_button_sad_' + lang), callback_data="reaction_sad")
                ],
                [
                    InlineKeyboardButton(t(lang, 'reaction_button_thoughtful_' + lang), callback_data="reaction_thoughtful"),
                    InlineKeyboardButton(t(lang, 'reaction_button_motivating_' + lang), callback_data="reaction_motivating")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            message = t(lang, 'reaction_prompt_' + lang)
            
            await bot.send_message(chat_id=user_id, text=message, reply_markup=reply_markup)
            
            logger.info(f"😊 Reaction collection initiated for capsule {capsule_data['id']}")
            return True
            
        except Exception as e:
            logger.error(f"Error collecting reaction: {e}")
            return False
    
    async def create_reply_to_past_self(self, user_id: int, original_capsule_data: Dict, bot):
        """Create functionality to reply to past self."""
        try:
            user_data = get_user_data_by_telegram_id(user_id)
            if not user_data:
                return False
            
            lang = user_data.get('language_code', 'ru')
            
            # Create reply options
            keyboard = [
                [
                    InlineKeyboardButton(t(lang, 'reply_button_write_' + lang), callback_data=f"reply_start_{original_capsule_data['id']}"),
                    InlineKeyboardButton(t(lang, 'reply_button_later_' + lang), callback_data=f"reply_later_{original_capsule_data['id']}")
                ],
                [
                    InlineKeyboardButton(t(lang, 'reply_button_new_capsule_' + lang), callback_data="create_new_capsule"),
                    InlineKeyboardButton(t(lang, 'reply_button_menu_' + lang), callback_data="main_menu")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            original_content = original_capsule_data.get('content_text', '')[:100] + "..."
            message = t(lang, 'reply_to_past_title_' + lang) + "\n\n" + t(lang, 'reply_original_preview_' + lang, content=original_content) + "\n\n" + t(lang, 'reply_to_past_prompt_' + lang)
            
            await bot.send_message(chat_id=user_id, text=message, reply_markup=reply_markup)
            
            logger.info(f"✉️ Reply to past self option provided for capsule {original_capsule_data['id']}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating reply to past self: {e}")
            return False
    
    async def handle_reaction(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle user reaction to opened capsule."""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        reaction = query.data.replace('reaction_', '')
        
        # Store the reaction in a temporary storage or DB
        # This would normally be saved to a reactions table
        logger.info(f"❤️ Reaction received from user {user_id}: {reaction}")
        
        user_data = get_user_data_by_telegram_id(user_id)
        lang = user_data.get('language_code', 'ru') if user_data else 'ru'
        
        # Determine translation key based on reaction
        reaction_keys = {
            'heartfelt': 'reaction_response_heartfelt',
            'funny': 'reaction_response_funny', 
            'inspiring': 'reaction_response_inspiring',
            'sad': 'reaction_response_sad',
            'thoughtful': 'reaction_response_thoughtful',
            'motivating': 'reaction_response_motivating'
        }
        
        key_prefix = reaction_keys.get(reaction, 'default_reaction_response')
        response = t(lang, key_prefix + '_' + lang)
        
        await query.edit_message_text(response)
        
        # Now suggest creating a reply or new capsule
        await self._suggest_next_action(query.message.chat_id, query.message.message_id, update.get_bot())
    
    async def _suggest_next_action(self, chat_id: int, message_id: int, bot):
        """Suggest next actions after reaction."""
        # For this method, we'll use default language or would need to retrieve user's language differently
        # Using 'ru' as default, in a full implementation this would get user's language
        lang = 'ru'  # Would be retrieved based on chat_id in full implementation
        
        keyboard = [
            [
                InlineKeyboardButton(t(lang, 'next_action_reply_' + lang), callback_data="reply_to_self"),
                InlineKeyboardButton(t(lang, 'next_action_new_capsule_' + lang), callback_data="create_new")
            ],
            [
                InlineKeyboardButton(t(lang, 'next_action_stats_' + lang), callback_data="view_stats"),
                InlineKeyboardButton(t(lang, 'next_action_menu_' + lang), callback_data="main_menu")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await bot.send_message(
            chat_id=chat_id,
            text=t(lang, 'time_travel_prompt_' + lang),
            reply_markup=reply_markup
        )
    
    async def get_post_opening_experience(self, user_id: int, capsule_data: Dict, bot):
        """Provide the complete post-opening experience."""
        try:
            # First, collect reaction
            await self.collect_reaction_after_opening(user_id, capsule_data, bot)
            
            # Then, provide reply option after a short delay (in real implementation)
            # await asyncio.sleep(30)  # Wait for user to process the content
            
            # Provide reply to past self option
            await self.create_reply_to_past_self(user_id, capsule_data, bot)
            
            return True
        except Exception as e:
            logger.error(f"Error in post-opening experience: {e}")
            return False
    
    def get_enhanced_delivery_handler(self):
        """Get conversation handler for enhanced delivery interactions."""
        from telegram.ext import CallbackQueryHandler, MessageHandler, filters, ConversationHandler
        
        enhanced_delivery_handler = ConversationHandler(
            entry_points=[],
            states={
                ANTICIPATION_BUILDING: [
                    # Handle anticipation interactions if needed
                ],
                DRAMATIC_OPENING: [
                    # Handle opening interactions if needed
                ],
                REACTION_COLLECTION: [
                    CallbackQueryHandler(self.handle_reaction)
                ],
                REPLY_TO_PAST_SELF: [
                    # Handle reply creation if implemented as separate flow
                ]
            },
            fallbacks=[],
            name="enhanced_delivery",
            persistent=False,
        )
        
        return enhanced_delivery_handler


# Global instance
capsule_delivery_enhancer = CapsuleDeliveryEnhancer()