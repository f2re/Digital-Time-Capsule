"""
Dynamic translation system with personalization variables and A/B testing framework.
"""

from typing import Dict, Any, Optional
import logging
from .translations import t as original_t
from .database import get_user_data_by_telegram_id
from .feature_config import feature_flag_manager, FeatureFlag

logger = logging.getLogger(__name__)


class DynamicTranslationSystem:
    """Advanced translation system with personalization and A/B testing capabilities."""
    
    def __init__(self):
        # Additional dynamic translations that can be customized per user
        self.dynamic_translations = {
            'personalized_greeting': {
                'ru': {
                    'morning': 'Доброе утро, {name}! ✨',
                    'afternoon': 'Добрый день, {name}! ☀️',
                    'evening': 'Добрый вечер, {name}! 🌙'
                },
                'en': {
                    'morning': 'Good morning, {name}! ✨',
                    'afternoon': 'Good afternoon, {name}! ☀️',
                    'evening': 'Good evening, {name}! 🌙'
                }
            },
            'achievement_unlocked': {
                'ru': '🎉 Поздравляем! Вы получили достижение: <b>{achievement_name}</b> ({points} очков)',
                'en': '🎉 Congratulations! You earned the achievement: <b>{achievement_name}</b> ({points} points)'
            },
            'streak_announcement': {
                'ru': '🔥 Отлично! Ваша серия составляет {streak_count} дней подряд!',
                'en': '🔥 Excellent! Your streak is now {streak_count} days in a row!'
            },
            'capsule_created_personalized': {
                'ru': '📦 Капсула создана, {name}!\n\nОна будет доставлена {time}\n\nСпасибо за сохранение этого момента для будущего! 💫',
                'en': '📦 Capsule created, {name}!\n\nIt will be delivered on {time}\n\nThanks for saving this moment for the future! 💫'
            }
        }
        
        # A/B test variants for messages
        self.ab_test_variants = {
            'motivational_message': {
                'A': {
                    'ru': 'Продолжайте в том же духе, {name}! 💪',
                    'en': 'Keep up the great work, {name}! 💪'
                },
                'B': {
                    'ru': '{name}, вы делаете отличную работу! 🌟',
                    'en': '{name}, you\'re doing an amazing job! 🌟'
                },
                'C': {
                    'ru': 'Каждая капсула - это шаг вперед, {name}! 🚀',
                    'en': 'Every capsule is a step forward, {name}! 🚀'
                }
            },
            'achievement_notification': {
                'A': {
                    'ru': 'Вы получили новое достижение! {achievement_emoji}',
                    'en': 'You earned a new achievement! {achievement_emoji}'
                },
                'B': {
                    'ru': 'Поздравляем с достижением! {achievement_emoji}',
                    'en': 'Congratulations on your achievement! {achievement_emoji}'
                }
            }
        }
    
    def t(self, lang: str, key: str, user_id: Optional[int] = None, **kwargs) -> str:
        """
        Enhanced translation function with personalization variables and user context.
        
        Args:
            lang: Language code
            key: Translation key
            user_id: Optional user ID for personalization
            **kwargs: Additional formatting parameters
        """
        # Get user data if user_id is provided
        user_data = None
        if user_id:
            user_data = get_user_data_by_telegram_id(user_id)
        
        # First, try to get the dynamic translation
        if key in self.dynamic_translations:
            translation = self._get_dynamic_translation(key, lang, user_data)
        else:
            # Fall back to original translation system
            translation = original_t(lang, key, **kwargs)
        
        # Apply personalization variables if user data is available
        if user_data:
            translation = self._apply_personalization_variables(translation, user_data, **kwargs)
        else:
            # Apply any provided kwargs as formatting variables
            try:
                translation = translation.format(**kwargs)
            except KeyError:
                # If formatting fails due to missing keys, return as is
                pass
        
        return translation
    
    def _get_dynamic_translation(self, key: str, lang: str, user_data: Optional[Dict] = None) -> str:
        """Get a dynamic translation based on context."""
        # Check if it's a personalized greeting that needs time context
        if key == 'personalized_greeting' and user_data:
            time_of_day = self._get_time_of_day()
            translation = self.dynamic_translations[key].get(lang, {}).get(time_of_day, 
                self.dynamic_translations[key][lang]['morning'])
            return translation
        else:
            # Get the translation for the specific key and language
            return self.dynamic_translations[key].get(lang, 
                list(self.dynamic_translations[key].values())[0])  # fallback to first language
    
    def _get_time_of_day(self) -> str:
        """Get the current time of day."""
        from datetime import datetime
        current_hour = datetime.now().hour
        if 5 <= current_hour < 12:
            return 'morning'
        elif 12 <= current_hour < 18:
            return 'afternoon'
        else:
            return 'evening'
    
    def _apply_personalization_variables(self, text: str, user_data: Dict, **kwargs) -> str:
        """Apply personalization variables to the text."""
        # Base variables from user data
        variables = {
            'name': user_data.get('first_name', 'друг'),
            'username': user_data.get('username', ''),
            'streak': user_data.get('streak_count', 0),
            'total_capsules': user_data.get('total_capsules_created', 0),
            'best_streak': user_data.get('best_streak', 0),
            'emotional_profile': user_data.get('emotional_profile', 'unknown'),
        }
        
        # Add any additional variables passed in kwargs
        variables.update(kwargs)
        
        # Apply the variables to the text
        try:
            return text.format(**variables)
        except KeyError as e:
            logger.warning(f"Missing variable for personalization: {e}")
            # If there's a missing variable, try to format with available variables only
            import re
            # Find all placeholders in the string
            placeholders = re.findall(r'\{(\w+)\}', text)
            available_vars = {k: v for k, v in variables.items() if k in placeholders}
            try:
                return text.format(**available_vars)
            except KeyError:
                # If still failing, return original text
                return text
    
    def get_ab_test_message(self, user_id: int, message_type: str, lang: str = 'ru', **kwargs) -> str:
        """
        Get an A/B test variant message for a specific user.
        
        Args:
            user_id: User ID for consistent variant assignment
            message_type: Type of message (e.g., 'motivational_message')
            lang: Language code
            **kwargs: Additional formatting parameters
        """
        if message_type not in self.ab_test_variants:
            logger.warning(f"A/B test message type '{message_type}' not found")
            # Fall back to original translation
            return self.t(lang, message_type, user_id, **kwargs)
        
        # Get the user's assigned variant for this message type
        variant = feature_flag_manager.get_ab_test_variant(user_id, f"message_{message_type}", 
                                                          list(self.ab_test_variants[message_type].keys()))
        
        # Get the translation for the assigned variant
        translation = self.ab_test_variants[message_type][variant].get(lang, 
            list(self.ab_test_variants[message_type][variant].values())[0])
        
        # Apply personalization variables
        user_data = get_user_data_by_telegram_id(user_id)
        if user_data:
            translation = self._apply_personalization_variables(translation, user_data, **kwargs)
        else:
            try:
                translation = translation.format(**kwargs)
            except KeyError:
                pass
        
        return translation
    
    def update_message_content(self, key: str, lang: str, new_content: str):
        """Update dynamic message content (admin feature)."""
        if key not in self.dynamic_translations:
            self.dynamic_translations[key] = {}
        
        if lang not in self.dynamic_translations[key]:
            self.dynamic_translations[key][lang] = {}
        
        # If it's a simple translation (not time-based), store as a string
        self.dynamic_translations[key][lang] = new_content
        logger.info(f"Updated dynamic translation for {key} in {lang}")


# Global instance
dynamic_translation_system = DynamicTranslationSystem()


# Wrapper function to use this system instead of the original t function
def t(lang: str, key: str, user_id: Optional[int] = None, **kwargs) -> str:
    """
    Enhanced translation function with personalization.
    
    Args:
        lang: Language code
        key: Translation key
        user_id: Optional user ID for personalization
        **kwargs: Additional formatting parameters
    
    Returns:
        Translated and personalized string
    """
    return dynamic_translation_system.t(lang, key, user_id, **kwargs)


# Also provide the original function for backward compatibility if needed
def t_original(lang: str, key: str, **kwargs) -> str:
    """
    Original translation function without personalization (for backward compatibility).
    """
    from .translations import t_original as original_t
    return original_t(lang, key, **kwargs)