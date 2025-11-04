"""
Intelligent notification system with behavioral triggers and user engagement optimization.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
import logging
from telegram import Bot
from sqlalchemy import text
from .database import engine, get_user_data_by_telegram_id, get_user_data
from .translations import t
from .feature_config import feature_flag_manager, FeatureFlag

logger = logging.getLogger(__name__)


class NotificationType(Enum):
    """Types of notifications that can be sent to users."""
    ONBOARDING_DAY_1 = "onboarding_day_1"
    ONBOARDING_DAY_2 = "onboarding_day_2"
    ONBOARDING_DAY_3 = "onboarding_day_3"
    STREAK_REMINDER = "streak_reminder"
    MILESTONE_CELEBRATION = "milestone_celebration"
    CONTENT_SUGGESTION = "content_suggestion"
    CAPSULE_OPENING_SOON = "capsule_opening_soon"
    ANTI_FORGET_REMINDER = "anti_forget_reminder"


class NotificationManager:
    """Manages intelligent, contextual notifications with behavioral triggers."""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.anti_spam_cache = {}  # In-memory cache to prevent spam
        
    async def should_send_notification(self, user_id: int, notification_type: NotificationType, 
                                     current_time: datetime = None) -> bool:
        """Determine if notification should be sent based on user behavior and anti-spam rules."""
        if current_time is None:
            current_time = datetime.now()
            
        # Check if feature is enabled for user
        if not feature_flag_manager.is_feature_enabled_for_user(user_id, FeatureFlag.SMART_NOTIFICATIONS):
            return False
            
        user_data = get_user_data_by_telegram_id(user_id)
        if not user_data:
            logger.warning(f"User {user_id} not found in database")
            return False
        
        # Anti-spam protection - minimum 6 hours between notifications
        last_notification = user_data.get('last_notification_time')
        if last_notification:
            try:
                # Convert to datetime if it's a string
                if isinstance(last_notification, str):
                    last_notification = datetime.fromisoformat(last_notification.replace('Z', '+00:00'))
                    
                hours_since_last = (current_time - last_notification).total_seconds() / 3600
                if hours_since_last < 6:  # Minimum 6 hours between notifications
                    return False
            except Exception as e:
                logger.error(f"Error parsing last notification time for user {user_id}: {e}")
        
        # Check specific conditions for different notification types
        if notification_type in [NotificationType.ONBOARDING_DAY_1, 
                                NotificationType.ONBOARDING_DAY_2, 
                                NotificationType.ONBOARDING_DAY_3]:
            # Check if user is in onboarding phase
            onboarding_stage = user_data.get('onboarding_stage', 'not_started')
            if onboarding_stage in ['completed', 'skipped']:
                return False
                
            # Check timing requirements
            if notification_type == NotificationType.ONBOARDING_DAY_1:
                onboarding_start = user_data.get('onboarding_started_at')
                if onboarding_start:
                    time_since_start = (current_time - onboarding_start).days
                    return time_since_start == 0  # Same day
            elif notification_type == NotificationType.ONBOARDING_DAY_2:
                onboarding_start = user_data.get('onboarding_started_at')
                if onboarding_start:
                    time_since_start = (current_time - onboarding_start).days
                    return time_since_start == 1  # Second day
            elif notification_type == NotificationType.ONBOARDING_DAY_3:
                onboarding_start = user_data.get('onboarding_started_at')
                if onboarding_start:
                    time_since_start = (current_time - onboarding_start).days
                    return time_since_start == 2  # Third day
                    
        elif notification_type == NotificationType.STREAK_REMINDER:
            # Only send if user has a streak and hasn't created a capsule today
            streak_count = user_data.get('streak_count', 0)
            if streak_count < 2:  # Only remind for streaks of 2+
                return False
                
            # Check if user has created a capsule today
            last_activity = user_data.get('last_activity_time')
            if last_activity:
                last_activity_date = last_activity.date() if hasattr(last_activity, 'date') else last_activity
                today = current_time.date()
                if last_activity_date == today:
                    # User was active today, no need to remind
                    return False
                    
        elif notification_type == NotificationType.MILESTONE_CELEBRATION:
            # Check for milestone achievements
            total_capsules = user_data.get('total_capsules_created', 0)
            if total_capsules not in [10, 25, 50, 100]:  # Specific milestone targets
                return False
                
        return True
    
    async def send_notification(self, user_id: int, notification_type: NotificationType, 
                               custom_data: Dict = None, current_time: datetime = None) -> bool:
        """Send a notification to a user if conditions are met."""
        if current_time is None:
            current_time = datetime.now()
            
        # Check if we should send the notification
        if not await self.should_send_notification(user_id, notification_type, current_time):
            return False
            
        try:
            # Get user data to customize message
            user_data = get_user_data_by_telegram_id(user_id)
            if not user_data:
                logger.error(f"User {user_id} not found when sending notification")
                return False
                
            lang = user_data.get('language_code', 'ru')
            first_name = user_data.get('first_name', 'друг')
            
            # Generate appropriate message based on notification type
            message = await self._get_notification_message(notification_type, user_data, lang, custom_data)
            
            if not message:
                logger.warning(f"No message generated for notification type {notification_type}")
                return False
            
            # Send the message
            await self.bot.send_message(chat_id=user_id, text=message, parse_mode='HTML')
            
            # Update last notification time in database
            with engine.connect() as conn:
                conn.execute(text("""
                    UPDATE users 
                    SET last_notification_time = :notification_time 
                    WHERE telegram_id = :user_id
                """), {
                    'notification_time': current_time,
                    'user_id': user_id
                })
                conn.commit()
                
            logger.info(f"✅ Notification {notification_type.value} sent to user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending notification {notification_type.value} to user {user_id}: {e}")
            return False
    
    async def _get_notification_message(self, notification_type: NotificationType, 
                                      user_data: Dict, lang: str, custom_data: Dict = None) -> str:
        """Generate appropriate message content based on notification type."""
        first_name = user_data.get('first_name', 'друг')
        streak_count = user_data.get('streak_count', 0)
        total_capsules = user_data.get('total_capsules_created', 0)
        
        if notification_type == NotificationType.ONBOARDING_DAY_1:
            # Evening reminder on day 1 if user hasn't created second capsule
            if total_capsules == 1:  # User created only one capsule
                greeting = self._get_time_greeting(lang)
                return (f"{greeting} {first_name} 🌙\n\n"
                        f"У тебя уже есть одна капсула в пути\n"
                        f"Многие создают вторую — для другого настроения\n\n"
                        f"[Создать вечернюю капсулу]")
        
        elif notification_type == NotificationType.ONBOARDING_DAY_2:
            # Morning notification on day 2
            greeting = self._get_time_greeting(lang, 'morning')
            return (f"{greeting} {first_name}!\n\n"
                    f"Вчера ты создал капсулу\n"
                    f"Сегодня ты уже немного другой\n\n"
                    f"Записать эту разницу? ☕️\n"
                    f"[Новая мысль]")
        
        elif notification_type == NotificationType.ONBOARDING_DAY_3:
            # Critical moment on day 3 if no activity
            last_activity = user_data.get('last_activity_time')
            if last_activity:
                from datetime import datetime
                last_activity_dt = last_activity if isinstance(last_activity, datetime) else datetime.fromisoformat(str(last_activity))
                days_since_activity = (datetime.now() - last_activity_dt).days
                if days_since_activity >= 2:  # No activity in 2+ days
                    return (f"Твоя первая капсула откроется [дата]\n\n"
                            f"Пока она в пути, можешь создать ещё:\n"
                            f"• Голосовое сообщение себе 🎤\n"
                            f"• Фото этого момента 📸\n"
                            f"• Просто пару строк 📝\n\n"
                            f"Каждая капсула — это точка на карте твоей жизни")
        
        elif notification_type == NotificationType.STREAK_REMINDER:
            if streak_count >= 2:
                greeting = self._get_time_greeting(lang)
                return (f"Привет, {first_name}! {greeting}\n\n"
                        f"Ты на {streak_count}-дневной серии! 🔥\n"
                        f"Не пропусти сегодняшний день - создай капсулу и сохрани серию\n\n"
                        f"[Создать капсулу сегодня] ✨")
        
        elif notification_type == NotificationType.MILESTONE_CELEBRATION:
            if total_capsules in [10, 25, 50, 100]:
                milestone_messages = {
                    10: "10 капсул — это целая коллекция! 💎",
                    25: "25 капсул — ты настоящий архивист времени! 🏆",
                    50: "50 капсул — в твоём архиве уже целая история! 📚",
                    100: "100 капсул — ты создал целый музей! 🏛️"
                }
                
                message = milestone_messages.get(total_capsules, f"{total_capsules} капсул — отличный результат! 🎉")
                return (f"Поздравляем, {first_name}! 🎉\n\n"
                        f"{message}\n"
                        f"Ты в топ-20% активных пользователей\n"
                        f"Спасибо, что доверяешь нам своё время\n\n"
                        f"Небольшой подарок:\n"
                        f"[+3 премиум капсулы бесплатно]")
        
        elif notification_type == NotificationType.CONTENT_SUGGESTION:
            # Suggest content based on user's emotional profile
            emotional_profile = user_data.get('emotional_profile', 'unknown')
            suggestions = {
                'reflective': "В настроении для рефлексии? 🤔 Запиши, что занимает твои мысли",
                'goal_oriented': "Какие цели ты хочешь достичь? 🎯 Создай капсулу с мечтой",
                'grateful': "За что ты благодарен сегодня? 💛 Поделись своей благодарностью",
                'nostalgic': "Хочется вспомнить? 🌅 Запиши воспоминание в капсулу"
            }
            
            suggestion = suggestions.get(emotional_profile, "Что хочешь сохранить в капсуле времени? ✨")
            return f"Привет, {first_name}! \n\n{suggestion}\n\n[Создать капсулу]"
        
        elif notification_type == NotificationType.ANTI_FORGET_REMINDER:
            # Gentle reminder for inactive users
            days_inactive = custom_data.get('days_inactive', 7) if custom_data else 7
            return (f"Привет, {first_name}! 👋\n\n"
                    f"Мы заметили, что ты не заходил к нам {days_inactive} дней\n"
                    f"Твои капсулы ждут, чтобы продолжить твою историю\n\n"
                    f"Не хочешь добавить что-то новое? 📝\n\n"
                    f"[Вернуться к капсулам]")
        
        return None  # No message for this type or condition
    
    def _get_time_greeting(self, lang: str, time_period: str = None) -> str:
        """Get appropriate time-based greeting."""
        if not time_period:
            current_hour = datetime.now().hour
            if 5 <= current_hour < 12:
                time_period = 'morning'
            elif 12 <= current_hour < 18:
                time_period = 'afternoon'
            else:
                time_period = 'evening'
        
        greetings = {
            'ru': {
                'morning': 'Доброе утро!',
                'afternoon': 'Добрый день!',
                'evening': 'Добрый вечер!'
            },
            'en': {
                'morning': 'Good morning!',
                'afternoon': 'Good afternoon!',
                'evening': 'Good evening!'
            }
        }
        
        return greetings.get(lang, greetings['en']).get(time_period, greetings[lang]['morning'])
    
    async def check_and_send_behavioral_triggers(self):
        """Check for users who should receive behavioral trigger notifications."""
        try:
            with engine.connect() as conn:
                # Find users who might need notifications
                # This would typically run as a scheduled task
                result = conn.execute(text("""
                    SELECT id, telegram_id, onboarding_stage, 
                           onboarding_started_at, last_activity_time,
                           streak_count, total_capsules_created,
                           emotional_profile, language_code
                    FROM users
                    WHERE onboarding_stage != 'completed'
                    AND onboarding_stage != 'skipped'
                """)).fetchall()
                
                current_time = datetime.now()
                
                for row in result:
                    user_id = row.telegram_id
                    user_data = dict(row._mapping)
                    
                    # Check for onboarding day notifications
                    if user_data.get('onboarding_started_at'):
                        start_date = user_data['onboarding_started_at']
                        if isinstance(start_date, str):
                            start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                        
                        days_since_start = (current_time - start_date).days
                        
                        # Send notifications for days 1, 2, 3 if appropriate
                        if days_since_start == 0:  # Day 1
                            await self.send_notification(user_id, NotificationType.ONBOARDING_DAY_1, current_time=current_time)
                        elif days_since_start == 1:  # Day 2
                            await self.send_notification(user_id, NotificationType.ONBOARDING_DAY_2, current_time=current_time)
                        elif days_since_start == 2:  # Day 3
                            await self.send_notification(user_id, NotificationType.ONBOARDING_DAY_3, current_time=current_time)
                    
                    # Check for streak reminders (evening time, ideally)
                    if user_data.get('streak_count', 0) >= 2:
                        current_hour = current_time.hour
                        # Send in the evening if user hasn't been active today
                        if 18 <= current_hour <= 22:  # Evening hours
                            last_activity = user_data.get('last_activity_time')
                            if last_activity:
                                last_activity_dt = last_activity if isinstance(last_activity, datetime) else datetime.fromisoformat(str(last_activity))
                                if last_activity_dt.date() != current_time.date():
                                    await self.send_notification(user_id, NotificationType.STREAK_REMINDER, current_time=current_time)
                
        except Exception as e:
            logger.error(f"Error in check_and_send_behavioral_triggers: {e}")
    
    async def send_capsule_opening_reminder(self, user_id: int, capsule_data: Dict):
        """Send reminder about upcoming capsule opening."""
        try:
            user_data = get_user_data_by_telegram_id(user_id)
            if not user_data:
                return False
                
            lang = user_data.get('language_code', 'ru')
            first_name = user_data.get('first_name', 'друг')
            
            # Create personalized message based on capsule details
            message = (f"Привет, {first_name}! 👋\n\n"
                      f"Через 24 часа откроется твоя капсула\n"
                      f"Созданная {capsule_data.get('created_at', 'недавно')}\n\n"
                      f"Приготовься к встрече с прошлым собой 💫\n\n"
                      f"Хочешь подготовиться к открытию?")
            
            await self.bot.send_message(chat_id=user_id, text=message, parse_mode='HTML')
            return True
            
        except Exception as e:
            logger.error(f"Error sending capsule opening reminder to {user_id}: {e}")
            return False


# Global function to access notification manager
# This would be initialized when the bot starts
notification_manager = None

def init_notification_manager(bot: Bot):
    """Initialize the notification manager with the bot instance."""
    global notification_manager
    notification_manager = NotificationManager(bot)
    return notification_manager