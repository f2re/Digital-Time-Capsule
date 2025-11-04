"""
Gamification system with achievements, streak tracking and reward mechanisms.
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
import logging
from sqlalchemy import text
from .database import engine, get_user_data_by_telegram_id, get_user_data

logger = logging.getLogger(__name__)


class AchievementType(Enum):
    """Types of achievements that users can earn."""
    FIRST_CAPSULE = "first_capsule"
    WEEK_STREAK = "week_streak"
    MONTH_CREATOR = "month_creator"
    MEMORY_KEEPER = "memory_keeper"
    DREAM_ACHIEVER = "dream_achiever"
    STORYTELLER = "storyteller"

    @classmethod
    def get_all_types(cls):
        """Get all achievement types as a list."""
        return [item for item in cls]


class Achievement:
    """Represents a single achievement."""
    
    def __init__(self, achievement_type: AchievementType, name: str, description: str, 
                 tier: str = "bronze", points: int = 10):
        self.type = achievement_type
        self.name = name
        self.description = description
        self.tier = tier  # bronze, silver, gold, platinum
        self.points = points
        self.created_at = datetime.now()
        
    def to_dict(self) -> Dict:
        """Convert achievement to dictionary."""
        return {
            'type': self.type.value,
            'name': self.name,
            'description': self.description,
            'tier': self.tier,
            'points': self.points,
            'created_at': self.created_at.isoformat()
        }


class GamificationEngine:
    """Manages achievements, streaks, and gamification elements."""
    
    def __init__(self):
        self._initialize_achievements_table()
        self.achievement_definitions = self._get_achievement_definitions()
    
    def _initialize_achievements_table(self):
        """Initialize the achievements table if it doesn't exist."""
        try:
            with engine.connect() as conn:
                # Create achievements table
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS achievements (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        achievement_type VARCHAR(50) NOT NULL,
                        name VARCHAR(255) NOT NULL,
                        description TEXT,
                        tier VARCHAR(20) DEFAULT 'bronze',
                        points INTEGER DEFAULT 10,
                        earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(id)
                    )
                """))
                
                # Create user_achievements junction table if needed
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS user_achievements (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        achievement_id INTEGER NOT NULL,
                        unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(id),
                        FOREIGN KEY (achievement_id) REFERENCES achievements(id)
                    )
                """))
                
                # Create indexes
                try:
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_achievements_user ON achievements(user_id)"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_achievements_type ON achievements(achievement_type)"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_user_achievements_user ON user_achievements(user_id)"))
                except Exception:
                    # Indexes may already exist, which is fine
                    pass
                
                conn.commit()
                logger.info("✅ Achievements tables initialized")
        except Exception as e:
            logger.error(f"❌ Error initializing achievements tables: {e}")
            raise
    
    def _get_achievement_definitions(self) -> Dict[AchievementType, Dict[str, Any]]:
        """Get definitions for all achievements."""
        return {
            AchievementType.FIRST_CAPSULE: {
                'name': {
                    'ru': 'Первая капсула',
                    'en': 'First Capsule'
                },
                'description': {
                    'ru': 'Создай свою первую капсулу времени',
                    'en': 'Create your first time capsule'
                },
                'tier': 'bronze',
                'points': 10,
                'condition': lambda user_data: user_data.get('total_capsules_created', 0) >= 1
            },
            AchievementType.WEEK_STREAK: {
                'name': {
                    'ru': 'Недельный марафон',
                    'en': 'Week Marathon'
                },
                'description': {
                    'ru': 'Создай капсулы 7 дней подряд',
                    'en': 'Create capsules for 7 consecutive days'
                },
                'tier': 'silver',
                'points': 25,
                'condition': lambda user_data: user_data.get('streak_count', 0) >= 7
            },
            AchievementType.MONTH_CREATOR: {
                'name': {
                    'ru': 'Месяц творца',
                    'en': 'Creator Month'
                },
                'description': {
                    'ru': 'Создай 30 капсул за месяц',
                    'en': 'Create 30 capsules in a month'
                },
                'tier': 'gold',
                'points': 50,
                'condition': lambda user_data: user_data.get('total_capsules_created', 0) >= 30
            },
            AchievementType.MEMORY_KEEPER: {
                'name': {
                    'ru': 'Хранитель воспоминаний',
                    'en': 'Memory Keeper'
                },
                'description': {
                    'ru': 'Открой 10 своих прошлых капсул',
                    'en': 'Open 10 of your past capsules'
                },
                'tier': 'silver',
                'points': 30,
                'condition': lambda user_data: user_data.get('capsules_opened', 0) >= 10
            },
            AchievementType.DREAM_ACHIEVER: {
                'name': {
                    'ru': 'Мечтатель',
                    'en': 'Dream Achiever'
                },
                'description': {
                    'ru': 'Создай 5 капсул с мечтами/целями',
                    'en': 'Create 5 capsules with dreams/goals'
                },
                'tier': 'bronze',
                'points': 15,
                'condition': lambda user_data: user_data.get('dream_capsules_created', 0) >= 5
            },
            AchievementType.STORYTELLER: {
                'name': {
                    'ru': 'Рассказчик',
                    'en': 'Storyteller'
                },
                'description': {
                    'ru': 'Создай 20 капсул с длинным контентом (>100 слов)',
                    'en': 'Create 20 capsules with long content (>100 words)'
                },
                'tier': 'gold',
                'points': 40,
                'condition': lambda user_data: user_data.get('long_capsules_created', 0) >= 20
            }
        }
    
    def check_and_award_achievements(self, user_id: int) -> List[Achievement]:
        """Check if user earned any new achievements and award them."""
        user_data = get_user_data_by_telegram_id(user_id)
        if not user_data:
            return []
        
        earned_achievements = []
        
        # Get already earned achievements to avoid duplicates
        earned_types = self.get_user_achievement_types(user_id)
        
        # Check each achievement type
        for achievement_type in AchievementType.get_all_types():
            if achievement_type.value in earned_types:
                continue  # Already earned
            
            definition = self.achievement_definitions[achievement_type]
            if definition['condition'](user_data):
                # Award the achievement
                achievement = self.award_achievement(user_id, achievement_type, user_data.get('language_code', 'ru'))
                if achievement:
                    earned_achievements.append(achievement)
        
        return earned_achievements
    
    def award_achievement(self, user_id: int, achievement_type: AchievementType, lang: str = 'ru') -> Optional[Achievement]:
        """Award a specific achievement to a user."""
        try:
            definition = self.achievement_definitions[achievement_type]
            
            achievement = Achievement(
                achievement_type=achievement_type,
                name=definition['name'][lang],
                description=definition['description'][lang],
                tier=definition['tier'],
                points=definition['points']
            )
            
            # Save to database
            with engine.connect() as conn:
                # Insert the achievement
                result = conn.execute(text("""
                    INSERT INTO achievements (user_id, achievement_type, name, description, tier, points)
                    VALUES (:user_id, :type, :name, :description, :tier, :points)
                """), {
                    'user_id': user_id,
                    'type': achievement_type.value,
                    'name': achievement.name,
                    'description': achievement.description,
                    'tier': achievement.tier,
                    'points': achievement.points
                })
                
                achievement_id = result.lastrowid
                conn.commit()
                
                logger.info(f"🏆 Achievement {achievement_type.value} awarded to user {user_id}")
                return achievement
                
        except Exception as e:
            logger.error(f"Error awarding achievement {achievement_type.value} to user {user_id}: {e}")
            return None
    
    def get_user_achievement_types(self, user_id: int) -> List[str]:
        """Get list of achievement types already earned by user."""
        try:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT DISTINCT achievement_type 
                    FROM achievements 
                    WHERE user_id = :user_id
                """), {'user_id': user_id}).fetchall()
                
                return [row[0] for row in result]
        except Exception as e:
            logger.error(f"Error getting user achievements for user {user_id}: {e}")
            return []
    
    def get_user_achievements(self, user_id: int) -> List[Dict]:
        """Get all achievements earned by a user."""
        try:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT achievement_type, name, description, tier, points, earned_at
                    FROM achievements
                    WHERE user_id = :user_id
                    ORDER BY earned_at DESC
                """), {'user_id': user_id}).fetchall()
                
                achievements = []
                for row in result:
                    achievements.append({
                        'type': row[0],
                        'name': row[1],
                        'description': row[2],
                        'tier': row[3],
                        'points': row[4],
                        'earned_at': row[5]
                    })
                
                return achievements
        except Exception as e:
            logger.error(f"Error getting user achievements for user {user_id}: {e}")
            return []
    
    def get_user_total_points(self, user_id: int) -> int:
        """Calculate total points earned by user."""
        try:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT SUM(points) as total_points
                    FROM achievements
                    WHERE user_id = :user_id
                """), {'user_id': user_id}).first()
                
                return result[0] if result and result[0] else 0
        except Exception as e:
            logger.error(f"Error calculating user points for user {user_id}: {e}")
            return 0
    
    def update_streak(self, user_id: int, current_date: datetime = None) -> int:
        """Update user's streak count based on activity."""
        if current_date is None:
            current_date = datetime.now().date()
        else:
            current_date = current_date.date()
        
        user_data = get_user_data_by_telegram_id(user_id)
        if not user_data:
            return 0
        
        # Get last activity date
        last_activity = user_data.get('last_activity_time')
        if last_activity:
            if isinstance(last_activity, str):
                from datetime import datetime
                last_activity = datetime.fromisoformat(last_activity.replace('Z', '+00:00'))
            last_activity_date = last_activity.date()
        else:
            last_activity_date = current_date  # First time user
        
        current_streak = user_data.get('streak_count', 0)
        best_streak = user_data.get('best_streak', 0)
        
        # Calculate if we should increment or reset streak
        day_difference = (current_date - last_activity_date).days
        
        if day_difference == 0:
            # Same day activity, don't change streak
            new_streak = current_streak
        elif day_difference == 1:
            # Consecutive day, increment streak
            new_streak = current_streak + 1
        elif day_difference > 1:
            # Break in streak, reset to 1
            new_streak = 1
        else:
            # Shouldn't happen, but just in case
            new_streak = current_streak
        
        # Update best streak if needed
        if new_streak > best_streak:
            best_streak = new_streak
        
        # Update user data in database
        try:
            with engine.connect() as conn:
                conn.execute(text("""
                    UPDATE users 
                    SET streak_count = :streak_count, 
                        best_streak = :best_streak,
                        last_activity_time = :activity_time
                    WHERE telegram_id = :user_id
                """), {
                    'streak_count': new_streak,
                    'best_streak': best_streak,
                    'activity_time': datetime.now(),
                    'user_id': user_id
                })
                conn.commit()
                
                logger.info(f"📈 Streak updated for user {user_id}: {current_streak} -> {new_streak}")
                return new_streak
        except Exception as e:
            logger.error(f"Error updating streak for user {user_id}: {e}")
            return current_streak
    
    def get_leaderboard(self, limit: int = 10) -> List[Dict]:
        """Get top users by achievement points."""
        try:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT u.telegram_id, u.first_name, u.username, 
                           COALESCE(SUM(a.points), 0) as total_points,
                           COUNT(a.id) as achievements_count
                    FROM users u
                    LEFT JOIN achievements a ON u.id = a.user_id
                    GROUP BY u.id, u.telegram_id, u.first_name, u.username
                    ORDER BY total_points DESC, achievements_count DESC
                    LIMIT :limit
                """), {'limit': limit}).fetchall()
                
                leaderboard = []
                for i, row in enumerate(result, 1):
                    leaderboard.append({
                        'rank': i,
                        'user_id': row[0],
                        'name': row[1],
                        'username': row[2],
                        'points': row[3] or 0,
                        'achievements_count': row[4] or 0
                    })
                
                return leaderboard
        except Exception as e:
            logger.error(f"Error getting leaderboard: {e}")
            return []
    
    def increment_user_capsule_counters(self, user_id: int, content_type: str = None, word_count: int = 0):
        """Increment appropriate counters when user creates a capsule."""
        try:
            with engine.connect() as conn:
                # Update basic counters
                conn.execute(text("""
                    UPDATE users 
                    SET total_capsules_created = total_capsules_created + 1
                    WHERE telegram_id = :user_id
                """), {'user_id': user_id})
                
                # Update specific counters based on content
                updates = []
                values = {'user_id': user_id}
                
                if content_type in ['goals', 'dreams']:
                    updates.append("dream_capsules_created = COALESCE(dream_capsules_created, 0) + 1")
                
                if word_count > 100:
                    updates.append("long_capsules_created = COALESCE(long_capsules_created, 0) + 1")
                
                if updates:
                    update_query = f"UPDATE users SET {', '.join(updates)} WHERE telegram_id = :user_id"
                    conn.execute(text(update_query), values)
                
                conn.commit()
                
                # Check for any new achievements after incrementing
                self.check_and_award_achievements(user_id)
                
                logger.info(f"📈 Counters updated for user {user_id}")
        except Exception as e:
            logger.error(f"Error incrementing counters for user {user_id}: {e}")


# Global instance
gamification_engine = GamificationEngine()