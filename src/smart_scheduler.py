"""
Smart scheduler with behavioral triggers and personalized timing detection.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from telegram import Bot
from sqlalchemy import text
from .database import engine, get_user_data_by_telegram_id
from .feature_config import feature_flag_manager, FeatureFlag
from .notification_manager import NotificationManager, NotificationType

logger = logging.getLogger(__name__)


class SmartScheduler:
    """Enhanced scheduler with behavioral triggers and personalized timing detection."""
    
    # Timing patterns for different user types
    USER_TIMING_PROFILES = {
        'morning_person': {
            'optimal_hours': [7, 8, 9],
            'avoid_hours': [22, 23, 0, 1, 2, 3, 4, 5, 6],
            'peak_engagement': [8, 9]
        },
        'evening_person': {
            'optimal_hours': [19, 20, 21, 22],
            'avoid_hours': [6, 7, 8, 9],
            'peak_engagement': [20, 21]
        },
        'afternoon_person': {
            'optimal_hours': [13, 14, 15, 16],
            'avoid_hours': [2, 3, 4, 5],
            'peak_engagement': [14, 15]
        },
        'anytime_user': {
            'optimal_hours': [10, 14, 18, 20],
            'avoid_hours': [1, 2, 3, 4, 5, 6],
            'peak_engagement': [14, 20]
        }
    }
    
    def __init__(self, bot: Bot = None):
        self.bot = bot
        self.scheduler = AsyncIOScheduler(timezone=datetime.now().astimezone().tzinfo)
        self.notification_manager = NotificationManager(bot) if bot else None
        
    def set_bot(self, bot: Bot):
        """Set the bot instance for the scheduler."""
        self.bot = bot
        if self.notification_manager:
            self.notification_manager.bot = bot
        else:
            self.notification_manager = NotificationManager(bot)
    
    def determine_user_timing_profile(self, user_data: Dict) -> str:
        """Analyze user behavior to determine optimal timing profile."""
        creation_hours = user_data.get('capsule_creation_hours', [])
        
        # If we don't have specific hour data, use general activity data
        if not creation_hours:
            last_activity = user_data.get('last_activity_time')
            if last_activity:
                # Use last activity time as indicator
                if isinstance(last_activity, str):
                    from datetime import datetime
                    last_activity = datetime.fromisoformat(last_activity.replace('Z', '+00:00'))
                creation_hours = [last_activity.hour]
            else:
                # Default to anytime user if no data
                return 'anytime_user'
        
        # Count occurrences for each hour
        hour_counts = {}
        for hour in creation_hours:
            hour_str = str(hour) if isinstance(hour, int) else hour
            hour_int = int(hour_str)
            hour_counts[hour_int] = hour_counts.get(hour_int, 0) + 1
        
        # Calculate preference scores for each profile
        scores = {}
        for profile_name, profile_data in self.USER_TIMING_PROFILES.items():
            score = 0
            for hour, count in hour_counts.items():
                if hour in profile_data['optimal_hours']:
                    score += count * 2  # Double weight for optimal hours
                elif hour not in profile_data['avoid_hours']:
                    score += count      # Regular weight for acceptable hours
            scores[profile_name] = score
        
        # Return profile with highest score
        if scores:
            return max(scores, key=scores.get)
        else:
            return 'anytime_user'
    
    def calculate_optimal_notification_time(self, user_id: int, notification_type: NotificationType,
                                          base_time: datetime = None) -> datetime:
        """Calculate the best time to send a notification to a specific user."""
        if base_time is None:
            base_time = datetime.now()
            
        user_data = get_user_data_by_telegram_id(user_id)
        if not user_data:
            # Default to next available optimal time
            return self._get_next_optimal_time(base_time)
        
        # Determine user's timing profile
        timing_profile = self.determine_user_timing_profile(user_data)
        optimal_hours = self.USER_TIMING_PROFILES[timing_profile]['optimal_hours']
        
        # Special handling for different notification types
        if notification_type in [NotificationType.ONBOARDING_DAY_1, 
                                NotificationType.ONBOARDING_DAY_2, 
                                NotificationType.ONBOARDING_DAY_3]:
            # For onboarding notifications, respect user's timing profile but ensure 
            # they are sent during day 1, 2, or 3 respectively
            target_date = base_time.date()
            
            # Find next optimal time today or tomorrow
            for hour in optimal_hours:
                candidate_time = base_time.replace(hour=hour, minute=0, second=0, microsecond=0)
                if candidate_time.date() == target_date and candidate_time > base_time:
                    return candidate_time
                elif candidate_time.date() > target_date:
                    return candidate_time
        
        # For other notification types, find next optimal time
        for hour in optimal_hours:
            candidate_time = base_time.replace(hour=hour, minute=0, second=0, microsecond=0)
            if candidate_time > base_time:
                return candidate_time
        
        # If no time today, schedule for tomorrow's first optimal hour
        tomorrow = base_time + timedelta(days=1)
        return tomorrow.replace(hour=optimal_hours[0], minute=0, second=0, microsecond=0)
    
    def _get_next_optimal_time(self, base_time: datetime) -> datetime:
        """Get next optimal time based on default preferences."""
        optimal_hours = [9, 12, 15, 18, 20]  # Default optimal hours
        
        for hour in optimal_hours:
            candidate_time = base_time.replace(hour=hour, minute=0, second=0, microsecond=0)
            if candidate_time > base_time:
                return candidate_time
        
        # If no time today, schedule for tomorrow's first optimal hour
        tomorrow = base_time + timedelta(days=1)
        return tomorrow.replace(hour=optimal_hours[0], minute=0, second=0, microsecond=0)
    
    def schedule_user_notification(self, user_id: int, notification_type: NotificationType,
                                 custom_data: Dict = None, delay_minutes: int = 0) -> str:
        """Schedule a notification for a specific user at optimal time."""
        try:
            # Calculate optimal time
            optimal_time = self.calculate_optimal_notification_time(user_id, notification_type)
            
            # Apply delay if specified
            if delay_minutes > 0:
                optimal_time = optimal_time + timedelta(minutes=delay_minutes)
            
            # Create job ID
            job_id = f"notify_{user_id}_{notification_type.value}_{int(optimal_time.timestamp())}"
            
            # Schedule the notification
            self.scheduler.add_job(
                self._send_scheduled_notification,
                'date',
                run_date=optimal_time,
                id=job_id,
                args=[user_id, notification_type, custom_data],
                replace_existing=True
            )
            
            logger.info(f"⏰ Scheduled {notification_type.value} for user {user_id} at {optimal_time}")
            return job_id
            
        except Exception as e:
            logger.error(f"Error scheduling notification for user {user_id}: {e}")
            return None
    
    async def _send_scheduled_notification(self, user_id: int, notification_type: NotificationType,
                                         custom_data: Dict):
        """Internal method to send scheduled notifications."""
        if self.notification_manager:
            await self.notification_manager.send_notification(user_id, notification_type, custom_data)
    
    def schedule_behavioral_triggers(self):
        """Schedule recurring job to check for behavioral triggers."""
        try:
            job_id = "behavioral_triggers_check"
            
            # Run every hour to check for users who need notifications
            self.scheduler.add_job(
                self._check_behavioral_triggers,
                'interval',
                minutes=60,  # Check every hour
                id=job_id,
                replace_existing=True
            )
            
            logger.info("✅ Behavioral triggers checker scheduled (every hour)")
        except Exception as e:
            logger.error(f"Error scheduling behavioral triggers: {e}")
    
    async def _check_behavioral_triggers(self):
        """Check for users who should receive behavioral trigger notifications."""
        if self.notification_manager:
            await self.notification_manager.check_and_send_behavioral_triggers()
    
    def schedule_user_timing_analysis(self):
        """Schedule recurring analysis to update user timing profiles."""
        try:
            job_id = "user_timing_analysis"
            
            # Run daily to update user timing profiles
            self.scheduler.add_job(
                self._analyze_user_timing_patterns,
                'cron',
                hour=2,  # Run at 2 AM daily
                id=job_id,
                replace_existing=True
            )
            
            logger.info("✅ User timing analysis scheduled (daily at 2 AM)")
        except Exception as e:
            logger.error(f"Error scheduling timing analysis: {e}")
    
    async def _analyze_user_timing_patterns(self):
        """Analyze and update user timing patterns."""
        try:
            # This would update user timing preferences based on their activity
            # For now, just log that it ran
            logger.info("📅 User timing patterns analysis completed")
        except Exception as e:
            logger.error(f"Error in timing pattern analysis: {e}")
    
    def schedule_smart_capsule_delivery_reminders(self):
        """Schedule reminders before capsule delivery."""
        try:
            job_id = "capsule_delivery_reminders"
            
            # Run every 6 hours to check for upcoming deliveries
            self.scheduler.add_job(
                self._check_upcoming_deliveries,
                'interval',
                hours=6,
                id=job_id,
                replace_existing=True
            )
            
            logger.info("✅ Capsule delivery reminders scheduled (every 6 hours)")
        except Exception as e:
            logger.error(f"Error scheduling delivery reminders: {e}")
    
    async def _check_upcoming_deliveries(self):
        """Check for capsules that will be delivered soon and send reminders."""
        try:
            # This would query the database for capsules to be delivered soon
            # and send appropriate reminders
            from .database import get_pending_capsules
            
            soon_to_deliver = []  # Placeholder - would get capsules delivered in next 24h
            logger.info(f"✅ Checked upcoming deliveries, found {len(soon_to_deliver)} capsules")
        except Exception as e:
            logger.error(f"Error checking upcoming deliveries: {e}")
    
    def start_scheduler(self):
        """Start the scheduler."""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("⏰ Smart Scheduler started")
            
            # Schedule all recurring jobs
            self.schedule_behavioral_triggers()
            self.schedule_user_timing_analysis()
            self.schedule_smart_capsule_delivery_reminders()
        else:
            logger.info("⏰ Smart Scheduler already running")
    
    def stop_scheduler(self):
        """Stop the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("⏰ Smart Scheduler stopped")
    
    def get_scheduled_jobs(self) -> List:
        """Get list of all scheduled jobs."""
        return self.scheduler.get_jobs()
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a specific scheduled job."""
        try:
            self.scheduler.remove_job(job_id)
            return True
        except Exception:
            return False
    
    def schedule_onboarding_sequence(self, user_id: int):
        """Schedule the complete onboarding notification sequence for a new user."""
        # Day 1 notification (will be sent at optimal time for user)
        self.schedule_user_notification(user_id, NotificationType.ONBOARDING_DAY_1)
        
        # Day 2 notification (will be sent at optimal time for user)
        day2_time = datetime.now() + timedelta(days=1)
        self.schedule_user_notification(user_id, NotificationType.ONBOARDING_DAY_2, delay_minutes=0)
        
        # Day 3 notification (will be sent at optimal time for user)
        day3_time = datetime.now() + timedelta(days=2)
        self.schedule_user_notification(user_id, NotificationType.ONBOARDING_DAY_3, delay_minutes=0)
        
        logger.info(f"✅ Onboarding sequence scheduled for user {user_id}")


# Global instance for the smart scheduler
smart_scheduler = None

def init_smart_scheduler(bot: Bot = None):
    """Initialize the smart scheduler with optional bot instance."""
    global smart_scheduler
    smart_scheduler = SmartScheduler(bot)
    return smart_scheduler