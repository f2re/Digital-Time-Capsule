"""
Comprehensive achievement and streak management system for Digital Time Capsule bot
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional
import logging

from .database import get_user_data, add_capsules_to_balance, update_user_onboarding_stage
from .translations import t

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AchievementType(Enum):
    STREAK_3 = 'streak_3'
    STREAK_7 = 'streak_7'
    STREAK_30 = 'streak_30'
    CAPSULES_10 = 'capsules_10'
    TIME_TRAVELER = 'time_traveler'
    VARIETY_MASTER = 'variety_master'


class AchievementSystem:
    """Comprehensive achievement and streak management"""
    
    pass  # All achievement data will be accessed via the translation system
    
    pass  # Streak recovery messages will be accessed via translation system
    
    @staticmethod
    def check_achievements(user_id: int, user_data: dict) -> List[str]:
        """Check and award new achievements"""
        
        awarded_achievements = []
        current_achievements = set(user_data.get('achievements', []))
        lang = user_data.get('language_code', 'ru')
        
        # Define achievement conditions and rewards
        ACHIEVEMENTS = {
            AchievementType.STREAK_3.value: {
                'condition': lambda user_data: user_data.get('streak_count', 0) >= 3,
                'reward': {'capsules': 1}
            },
            
            AchievementType.STREAK_7.value: {
                'condition': lambda user_data: user_data.get('streak_count', 0) >= 7,
                'reward': {'capsules': 3, 'premium_days': 3}
            },
            
            AchievementType.STREAK_30.value: {
                'condition': lambda user_data: user_data.get('streak_count', 0) >= 30,
                'reward': {'premium_month': 1, 'badge': 'month_master'}
            },
            
            AchievementType.CAPSULES_10.value: {
                'condition': lambda user_data: user_data.get('total_capsules_created', 0) >= 10,
                'reward': {'capsules': 3, 'storage_mb': 50}
            },
            
            AchievementType.TIME_TRAVELER.value: {
                'condition': lambda user_data: user_data.get('longest_capsule_days', 0) >= 365,
                'reward': {'badge': 'time_traveler'}
            },
            
            AchievementType.VARIETY_MASTER.value: {
                'condition': lambda user_data: len(user_data.get('used_content_types', [])) >= 5,
                'reward': {'capsules': 5}
            }
        }
        
        for achievement_id, achievement in ACHIEVEMENTS.items():
            if achievement_id not in current_achievements:
                if achievement['condition'](user_data):
                    # Award achievement
                    awarded_achievements.append(achievement_id)
                    
                    # Apply rewards
                    rewards = achievement.get('reward', {})
                    if 'capsules' in rewards:
                        add_capsules_to_balance(user_id, rewards['capsules'])
                    
                    # Add achievement to user's list
                    new_achievements = user_data.get('achievements', [])
                    new_achievements.append(achievement_id)
                    user_data['achievements'] = new_achievements
        
        return awarded_achievements
    
    @staticmethod
    def update_streak(user_id: int, user_data: dict) -> dict:
        """Update user streak and check for achievements"""
        
        today = datetime.now().date()
        
        # Get the last capsule creation date
        last_capsule_date_str = user_data.get('last_capsule_date')
        if last_capsule_date_str:
            try:
                # Try to parse the date string
                if isinstance(last_capsule_date_str, str):
                    last_date = datetime.fromisoformat(last_capsule_date_str.split('T')[0]).date()
                else:
                    last_date = last_capsule_date_str
            except ValueError:
                # If parsing fails, assume it's in YYYY-MM-DD format
                last_date = datetime.strptime(last_capsule_date_str.split(' ')[0], '%Y-%m-%d').date()
        else:
            last_date = None
        
        if last_date:
            days_diff = (today - last_date).days
            
            if days_diff == 0:
                # Already created today - no streak change
                pass
            elif days_diff == 1:
                # Consecutive day - extend streak
                user_data['streak_count'] = user_data.get('streak_count', 0) + 1
                user_data['best_streak'] = max(user_data.get('best_streak', 0), user_data['streak_count'])
            elif days_diff > 1:
                # Streak broken
                old_streak = user_data.get('streak_count', 0)
                user_data['streak_count'] = 1  # Reset to 1 (today's capsule)
                
                # Store broken streak info for recovery message
                if old_streak > 3:
                    user_data['last_broken_streak'] = old_streak
        else:
            # First capsule ever
            user_data['streak_count'] = 1
        
        user_data['last_capsule_date'] = today.isoformat()
        user_data['last_activity_time'] = datetime.utcnow()
        return user_data


class StreakMotivation:
    """Streak-based motivation system"""
    
    pass  # Motivation messages will be accessed via translation system
    
    @staticmethod
    def get_motivation_message(streak_count: int, lang: str, user_data: dict = None) -> Optional[str]:
        """Get appropriate motivation message for streak"""
        
        if streak_count == 2:
            return t(lang, 'motivation_streak_2')
        elif streak_count == 5:
            return t(lang, 'motivation_streak_5')
        elif streak_count == 1 and user_data and user_data.get('best_streak', 0) > 3:
            # Comeback after broken streak
            message = t(lang, 'motivation_streak_comeback')
            return message.format(best_streak=user_data['best_streak'])
        
        return None


class PersonalizationEngine:
    """Personalization engine for enhanced user experience"""
    
    @staticmethod
    def get_personalized_greeting(user_data: dict, current_time: datetime) -> str:
        """Get personalized greeting based on user behavior"""
        
        lang = user_data.get('language_code', 'ru')
        hour = current_time.hour
        streak = user_data.get('streak_count', 0)
        total_capsules = user_data.get('total_capsules_created', 0)
        
        # Time-based greeting
        if 6 <= hour <= 11:
            time_greeting = t(lang, 'onboarding_good_morning')
        elif 12 <= hour <= 17:
            time_greeting = t(lang, 'onboarding_good_afternoon')
        elif 18 <= hour <= 22:
            time_greeting = t(lang, 'onboarding_good_evening')
        else:
            time_greeting = t(lang, 'hello_default')
        
        # Personalization based on history
        if total_capsules == 0:
            # First time user
            greeting = t(lang, 'personalization_greeting_first_time')
        
        elif streak > 0:
            # Active streak user
            greeting = t(lang, 'personalization_greeting_active_streak', streak_count=streak)
        
        elif total_capsules > 0:
            # Returning user
            from .database import get_pending_capsules_for_user
            pending_count = len(get_pending_capsules_for_user(user_data['telegram_id']))
            if pending_count > 0:
                greeting = t(lang, 'personalization_greeting_returning', pending_count=pending_count)
            else:
                greeting = t(lang, 'personalization_greeting_general', total_capsules=total_capsules)
        
        return f"{time_greeting}! {greeting}"


class SmartCapsuleCreator:
    """Enhanced capsule creation with contextual guidance"""
    
    pass  # Date suggestions will be accessed via translation system
    
    # Content enhancement prompts
    ENHANCEMENT_PROMPTS = {
        'too_short': {
            'ru': 'Всего {count} символов — маловато для будущего\n\nДобавь немного:\n• Почему это важно?\n• Что чувствуешь?\n• Контекст момента?\n\n[Дописать] [Оставить так]',
            'en': 'Only {count} characters — not enough for the future\n\nAdd a bit:\n• Why is this important?\n• What do you feel?\n• Context of the moment?\n\n[Add more] [Leave as is]'
        },
        'encourage_details': {
            'ru': 'Стоп ⏸\n\nПеречитай. Добавь деталей, если хочется\n\nЭти слова будут важны через время',
            'en': 'Stop ⏸\n\nReread it. Add details if you want\n\nThese words will be important later'
        }
    }
    
    # Writing assistance templates
    WRITING_TEMPLATES = {
        'reflection_starter': {
            'ru': [
                'Сегодня я понял, что...',
                'Прямо сейчас чувствую...',
                'Хочу запомнить этот момент, потому что...',
                'Через год я буду смеяться над тем, что...'
            ],
            'en': [
                'Today I realized that...',
                'Right now I feel...',
                'I want to remember this moment because...',
                'In a year I\'ll laugh at what...'
            ]
        },
        'goal_framework': {
            'ru': [
                'Через [срок] я уже...',
                'Моя цель — это не просто..., это...',
                'Я знаю, что смогу, потому что...',
                'Первый шаг который сделаю завтра...'
            ],
            'en': [
                'In [timeframe] I already...',
                'My goal is not just... but...',
                'I know I can because...',
                'The first step I\'ll take tomorrow...'
            ]
        },
        'gratitude_prompts': {
            'ru': [
                'Сегодня благодарен [кому/чему] за то, что...',
                'Этот человек изменил мой день тем, что...',
                'Простая вещь, которая сделала меня счастливым...',
                'Без чего я не представляю свою жизнь...'
            ],
            'en': [
                'Today grateful to [whom] for the fact that...',
                'This person changed my day by...',
                'Simple thing that made me happy...',
                'Without which I can\'t imagine my life...'
            ]
        }
    }