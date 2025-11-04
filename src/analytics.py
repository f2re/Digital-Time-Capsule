"""
Privacy-focused analytics engine with behavioral pattern analysis and personalization.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import logging
from sqlalchemy import text
from .database import engine, get_user_data_by_telegram_id, get_user_data
from .config import logger as config_logger

logger = logging.getLogger(__name__)


class PrivacyFocusedAnalytics:
    """Analytics engine focused on privacy with anonymized behavioral analysis."""
    
    def __init__(self):
        self._initialize_analytics_tables()
        self.personalization_engine = None  # Initialize later to avoid circular import
    
    def _initialize_analytics_tables(self):
        """Initialize analytics-related tables if they don't exist."""
        try:
            with engine.connect() as conn:
                # Create user_behavior table
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS user_behavior (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        action_type VARCHAR(50) NOT NULL,
                        action_data JSON,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        session_id VARCHAR(100),
                        FOREIGN KEY (user_id) REFERENCES users(id)
                    )
                """))
                
                # Create behavioral_patterns table
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS behavioral_patterns (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        pattern_type VARCHAR(50) NOT NULL,
                        pattern_data JSON,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(id)
                    )
                """))
                
                # Create analytics_summary table
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS analytics_summary (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        metric_name VARCHAR(100) NOT NULL,
                        metric_value FLOAT,
                        date_recorded DATE NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                
                # Create indexes
                try:
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_behavior_user ON user_behavior(user_id)"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_behavior_action ON user_behavior(action_type)"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_behavior_timestamp ON user_behavior(timestamp)"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_patterns_user ON behavioral_patterns(user_id)"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_patterns_type ON behavioral_patterns(pattern_type)"))
                except Exception:
                    # Indexes may already exist, which is fine
                    pass
                
                conn.commit()
                logger.info("✅ Analytics tables initialized")
        except Exception as e:
            logger.error(f"❌ Error initializing analytics tables: {e}")
            raise
    
    def log_user_action(self, user_id: int, action_type: str, action_data: Dict = None, session_id: str = None):
        """Log user action for behavioral analysis."""
        try:
            with engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO user_behavior (user_id, action_type, action_data, session_id)
                    VALUES (:user_id, :action_type, :action_data, :session_id)
                """), {
                    'user_id': user_id,
                    'action_type': action_type,
                    'action_data': action_data,
                    'session_id': session_id
                })
                conn.commit()
                
                logger.info(f"📊 Action logged: {action_type} for user {user_id}")
        except Exception as e:
            logger.error(f"Error logging user action: {e}")
    
    def update_behavioral_patterns(self, user_id: int):
        """Update behavioral patterns for a user based on their actions."""
        try:
            # Get user's recent actions
            with engine.connect() as conn:
                # Get actions from the last 30 days
                since_date = datetime.now() - timedelta(days=30)
                result = conn.execute(text("""
                    SELECT action_type, action_data, timestamp
                    FROM user_behavior
                    WHERE user_id = :user_id AND timestamp > :since_date
                    ORDER BY timestamp DESC
                """), {
                    'user_id': user_id,
                    'since_date': since_date
                }).fetchall()
                
                if not result:
                    return  # No actions to analyze
                
                # Analyze patterns
                patterns = self._analyze_user_patterns(result)
                
                # Update or insert patterns
                for pattern_type, pattern_data in patterns.items():
                    conn.execute(text("""
                        INSERT INTO behavioral_patterns (user_id, pattern_type, pattern_data, last_updated)
                        VALUES (:user_id, :pattern_type, :pattern_data, CURRENT_TIMESTAMP)
                        ON CONFLICT(user_id, pattern_type) DO UPDATE SET
                            pattern_data = :pattern_data,
                            last_updated = CURRENT_TIMESTAMP
                    """), {
                        'user_id': user_id,
                        'pattern_type': pattern_type,
                        'pattern_data': pattern_data
                    })
                
                conn.commit()
                logger.info(f"📈 Behavioral patterns updated for user {user_id}")
        except Exception as e:
            logger.error(f"Error updating behavioral patterns for user {user_id}: {e}")
    
    def _analyze_user_patterns(self, actions: List[Tuple]) -> Dict[str, Dict]:
        """Analyze user actions to identify patterns."""
        patterns = {}
        
        # Time-based patterns
        creation_hours = []
        action_types = {}
        
        for action_type, action_data, timestamp in actions:
            # Count action types
            action_types[action_type] = action_types.get(action_type, 0) + 1
            
            # Record creation hours
            if action_type in ['create_capsule', 'open_capsule', 'edit_profile']:
                creation_hours.append(timestamp.hour)
        
        # Determine time preferences
        if creation_hours:
            hour_counts = {}
            for hour in creation_hours:
                hour_counts[hour] = hour_counts.get(hour, 0) + 1
            
            # Calculate morning vs evening preference
            morning_hours = sum(hour_counts.get(h, 0) for h in range(5, 12))  # 5-11 AM
            evening_hours = sum(hour_counts.get(h, 0) for h in range(18, 24))  # 6 PM+ 
            late_evening_hours = sum(hour_counts.get(h, 0) for h in range(0, 5))  # 12-4 AM
            
            if morning_hours > max(evening_hours, late_evening_hours):
                time_preference = 'morning'
            elif evening_hours > max(morning_hours, late_evening_hours):
                time_preference = 'evening'
            else:
                time_preference = 'anytime'
            
            patterns['time_preference'] = {
                'preference': time_preference,
                'peak_hours': sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            }
        
        # Content preference patterns
        content_actions = [a for a in actions if a[0] == 'create_capsule']
        if content_actions:
            content_types = {}
            for _, action_data, _ in content_actions:
                if action_data and isinstance(action_data, dict):
                    content_type = action_data.get('content_type', 'text')
                    content_types[content_type] = content_types.get(content_type, 0) + 1
            
            if content_types:
                patterns['content_preference'] = {
                    'favorite_types': sorted(content_types.items(), key=lambda x: x[1], reverse=True)
                }
        
        # Activity frequency patterns
        if actions:
            total_actions = len(actions)
            days_active = len(set(a[2].date() for a in actions))  # Count unique days
            
            patterns['activity_frequency'] = {
                'total_actions': total_actions,
                'days_active': days_active,
                'actions_per_day': total_actions / max(days_active, 1)
            }
        
        return patterns
    
    def get_user_pattern(self, user_id: int, pattern_type: str) -> Optional[Dict]:
        """Get specific behavioral pattern for a user."""
        try:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT pattern_data
                    FROM behavioral_patterns
                    WHERE user_id = :user_id AND pattern_type = :pattern_type
                """), {
                    'user_id': user_id,
                    'pattern_type': pattern_type
                }).first()
                
                return result[0] if result else None
        except Exception as e:
            logger.error(f"Error getting user pattern: {e}")
            return None
    
    def get_anonymized_user_insights(self, user_id: int) -> Dict:
        """Get anonymized insights about user behavior."""
        user_data = get_user_data_by_telegram_id(user_id)
        if not user_data:
            return {}
        
        insights = {
            'engagement_level': self._calculate_engagement_level(user_data),
            'preferred_content_types': self._get_preferred_content_types(user_id),
            'optimal_interaction_times': self._get_optimal_interaction_times(user_id),
            'personalization_score': user_data.get('engagement_score', 0.0)
        }
        
        return insights
    
    def _calculate_engagement_level(self, user_data: Dict) -> str:
        """Calculate engagement level based on user metrics."""
        total_capsules = user_data.get('total_capsules_created', 0)
        streak_count = user_data.get('streak_count', 0)
        days_since_registration = (datetime.now() - user_data.get('created_at', datetime.now())).days
        
        if days_since_registration <= 0:
            days_since_registration = 1
        
        # Calculate engagement index
        engagement_index = (total_capsules / max(days_since_registration, 1)) * 10 + streak_count
        
        if engagement_index >= 20:
            return 'high'
        elif engagement_index >= 10:
            return 'medium'
        else:
            return 'low'
    
    def _get_preferred_content_types(self, user_id: int) -> List[str]:
        """Get preferred content types for a user."""
        pattern = self.get_user_pattern(user_id, 'content_preference')
        if pattern and pattern.get('favorite_types'):
            return [item[0] for item in pattern['favorite_types'][:3]]
        return ['text']  # default
    
    def _get_optimal_interaction_times(self, user_id: int) -> List[int]:
        """Get optimal hours for interacting with user."""
        pattern = self.get_user_pattern(user_id, 'time_preference')
        if pattern and pattern.get('peak_hours'):
            return [hour for hour, count in pattern['peak_hours'][:3]]
        return [9, 12, 18, 20]  # default

    def get_anonymized_aggregated_stats(self) -> Dict:
        """Get aggregated, anonymized statistics for all users."""
        try:
            with engine.connect() as conn:
                # Get total registered users
                users_count = conn.execute(text("SELECT COUNT(*) FROM users")).first()[0]
                
                # Get total capsules created
                capsules_count = conn.execute(text("SELECT COUNT(*) FROM capsules")).first()[0]
                
                # Get active users in last 7 days
                week_ago = datetime.now() - timedelta(days=7)
                active_users = conn.execute(text("""
                    SELECT COUNT(DISTINCT user_id) 
                    FROM user_behavior 
                    WHERE timestamp > :week_ago
                """), {'week_ago': week_ago}).first()[0]
                
                # Get most popular content types
                popular_types = conn.execute(text("""
                    SELECT content_type, COUNT(*) as count
                    FROM capsules 
                    GROUP BY content_type 
                    ORDER BY count DESC 
                    LIMIT 5
                """)).fetchall()
                
                stats = {
                    'total_users': users_count,
                    'total_capsules': capsules_count,
                    'active_users_7days': active_users,
                    'user_activity_rate': round((active_users / max(users_count, 1)) * 100, 2),
                    'popular_content_types': [{'type': row[0], 'count': row[1]} for row in popular_types]
                }
                
                return stats
        except Exception as e:
            logger.error(f"Error getting aggregated stats: {e}")
            return {}
    
    def update_user_engagement_score(self, user_id: int) -> float:
        """Update user's engagement score based on behavior."""
        try:
            with engine.connect() as conn:
                # Get user behavior metrics
                result = conn.execute(text("""
                    SELECT 
                        COUNT(*) as total_actions,
                        COUNT(CASE WHEN action_type = 'create_capsule' THEN 1 END) as create_actions,
                        COUNT(CASE WHEN action_type = 'open_capsule' THEN 1 END) as open_actions
                    FROM user_behavior 
                    WHERE user_id = :user_id AND timestamp > :week_ago
                """), {
                    'user_id': user_id,
                    'week_ago': datetime.now() - timedelta(days=7)
                }).first()
                
                if result:
                    total_actions, create_actions, open_actions = result
                    
                    # Calculate weighted score
                    score = (create_actions * 3) + (open_actions * 2) + (total_actions * 0.1)
                    
                    # Normalize to 0-10 scale
                    normalized_score = min(score / 10.0, 10.0)  # Cap at 10
                    
                    # Update user's engagement score
                    conn.execute(text("""
                        UPDATE users 
                        SET engagement_score = :score
                        WHERE telegram_id = :user_id
                    """), {
                        'score': normalized_score,
                        'user_id': user_id
                    })
                    conn.commit()
                    
                    return normalized_score
                
                return 0.0
        except Exception as e:
            logger.error(f"Error updating engagement score for user {user_id}: {e}")
            return 0.0


class PersonalizationEngine:
    """Engine for user personalization based on behavioral analysis."""
    
    def __init__(self):
        # Initialize analytics reference in methods that use it to avoid circular import
        self.analytics = None
    
    def get_personalized_content_suggestions(self, user_id: int) -> List[Dict]:
        """Get personalized content suggestions for a user."""
        # Import analytics here to avoid circular import
        from .analytics import analytics_engine
        insights = analytics_engine.get_anonymized_user_insights(user_id)
        
        suggestions = []
        
        if insights.get('engagement_level') == 'low':
            # For low engagement, suggest simple, engaging content types
            suggestions = [
                {'type': 'moment_capture', 'priority': 10, 'reason': 'easy to start with'},
                {'type': 'gratitude', 'priority': 9, 'reason': 'positive reinforcement'},
                {'type': 'reflection', 'priority': 8, 'reason': 'simple introspection'}
            ]
        else:
            # For higher engagement, suggest based on preferences
            preferred_types = insights.get('preferred_content_types', ['reflection'])
            
            for i, content_type in enumerate(preferred_types[:3]):
                suggestions.append({
                    'type': content_type,
                    'priority': 10 - i,
                    'reason': f'user preference based on behavior'
                })
        
        return suggestions
    
    def get_personalized_timing(self, user_id: int) -> List[int]:
        """Get personalized timing suggestions for interactions."""
        # Import analytics here to avoid circular import
        from .analytics import analytics_engine
        insights = analytics_engine.get_anonymized_user_insights(user_id)
        return insights.get('optimal_interaction_times', [9, 12, 18, 20])
    
    def get_user_emotional_profile(self, user_id: int) -> str:
        """Determine user's emotional profile based on content and behavior."""
        try:
            with engine.connect() as conn:
                # Look at recent capsule content and user behavior
                recent_capsules = conn.execute(text("""
                    SELECT content_text, content_type, created_at
                    FROM capsules 
                    WHERE user_id = (
                        SELECT id FROM users WHERE telegram_id = :user_id
                    )
                    ORDER BY created_at DESC
                    LIMIT 10
                """), {'user_id': user_id}).fetchall()
                
                if not recent_capsules:
                    return 'unknown'
                
                # Simple keyword analysis for emotional profile
                positive_keywords = ['хорошо', 'рад', 'счастье', 'любовь', 'прекрасно', 
                                   'good', 'happy', 'love', 'wonderful', 'amazing']
                negative_keywords = ['плохо', 'грустно', 'страх', 'печаль', 'один',
                                   'bad', 'sad', 'fear', 'alone', 'worry']
                reflective_keywords = ['думать', 'мысль', 'думать', 'философи', 'осозна',
                                     'think', 'thought', 'philosophy', 'aware']
                
                positive_count = 0
                negative_count = 0
                reflective_count = 0
                
                for capsule in recent_capsules:
                    content = (capsule[0] or '').lower()
                    for word in positive_keywords:
                        positive_count += content.count(word)
                    for word in negative_keywords:
                        negative_count += content.count(word)
                    for word in reflective_keywords:
                        reflective_count += content.count(word)
                
                # Determine profile based on counts
                if reflective_count >= positive_count and reflective_count >= negative_count:
                    return 'reflective'
                elif positive_count > negative_count:
                    return 'positive'
                elif negative_count > positive_count:
                    return 'emotional'
                else:
                    return 'balanced'
                    
        except Exception as e:
            logger.error(f"Error getting emotional profile: {e}")
            return 'unknown'
    
    def update_user_personalization_data(self, user_id: int):
        """Update all personalization data for a user."""
        # Import analytics here to avoid circular import
        from .analytics import analytics_engine
        
        # Update behavioral patterns
        analytics_engine.update_behavioral_patterns(user_id)
        
        # Update engagement score
        engagement_score = analytics_engine.update_user_engagement_score(user_id)
        
        # Determine emotional profile
        emotional_profile = self.get_user_emotional_profile(user_id)
        
        # Update user profile in database
        try:
            with engine.connect() as conn:
                conn.execute(text("""
                    UPDATE users 
                    SET engagement_score = :engagement_score,
                        emotional_profile = :emotional_profile
                    WHERE telegram_id = :user_id
                """), {
                    'engagement_score': engagement_score,
                    'emotional_profile': emotional_profile,
                    'user_id': user_id
                })
                conn.commit()
                
                logger.info(f"👤 Personalization data updated for user {user_id}")
        except Exception as e:
            logger.error(f"Error updating personalization data for user {user_id}: {e}")


# Global instances - avoid circular instantiation
analytics_engine = None  # Will be initialized after module is loaded
personalization_engine = None  # Will be initialized after module is loaded

def _init_analytics_module():
    """Initialize analytics module after it's fully loaded to avoid circular references."""
    global analytics_engine, personalization_engine
    if analytics_engine is None:
        analytics_engine = PrivacyFocusedAnalytics()
    if personalization_engine is None:
        personalization_engine = PersonalizationEngine()

# Initialize the modules now
_init_analytics_module()