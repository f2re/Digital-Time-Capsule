"""
Privacy-first analytics system for personalization in Digital Time Capsule bot
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import logging
from collections import Counter

from .database import engine
from sqlalchemy import text

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PrivacyFocusedAnalytics:
    """Privacy-first analytics system for personalization"""
    
    # Behavioral pattern analysis (anonymized)
    BEHAVIOR_PATTERNS = {
        'time_patterns': {
            'morning_creator': {'hours': [7, 8, 9, 10], 'weight': 0.8},
            'lunch_creator': {'hours': [12, 13, 14], 'weight': 0.6},  
            'evening_creator': {'hours': [19, 20, 21, 22], 'weight': 0.9},
            'night_owl': {'hours': [23, 0, 1], 'weight': 0.7}
        },
        
        'content_preferences': {
            'brief_writer': {'avg_length': (10, 100), 'frequency': 'high'},
            'detailed_writer': {'avg_length': (200, 1000), 'frequency': 'medium'},
            'multimedia_user': {'prefers': ['photo', 'voice', 'video']},
            'text_focused': {'prefers': ['text'], 'avg_length': (50, 500)}
        },
        
        'emotional_patterns': {
            'reflective': {'keywords': ['чувствую', 'думаю', 'понял', 'осознал']},
            'goal_oriented': {'keywords': ['хочу', 'планирую', 'достигну', 'цель']},
            'nostalgic': {'keywords': ['помню', 'был', 'тогда', 'раньше']},
            'grateful': {'keywords': ['спасибо', 'благодарен', 'ценю', 'рад']}
        }
    }
    
    @staticmethod
    def analyze_user_behavior(user_id: int) -> Dict:
        """Analyze user behavior patterns (privacy-safe)"""
        
        with engine.connect() as conn:
            # Get anonymized behavioral data
            # We only collect aggregated and anonymized data
            result = conn.execute(text("""
                SELECT 
                    EXTRACT(HOUR FROM created_at) as hour,
                    LENGTH(content_text) as content_length,
                    content_type,
                    DATE(created_at) as creation_date
                FROM capsules 
                WHERE user_id = :user_id 
                AND created_at > DATE('now', '-30 days')
                ORDER BY created_at DESC
            """), {"user_id": user_id}).fetchall()
        
        if not result:
            return {'profile': 'new_user', 'confidence': 0.0}
        
        analysis = {
            'time_profile': PrivacyFocusedAnalytics._analyze_time_patterns(result),
            'content_profile': PrivacyFocusedAnalytics._analyze_content_patterns(result),
            'frequency_profile': PrivacyFocusedAnalytics._analyze_frequency_patterns(result),
            'engagement_score': PrivacyFocusedAnalytics._calculate_engagement_score(result)
        }
        
        return analysis
    
    @staticmethod
    def _analyze_time_patterns(capsule_data: List) -> Dict:
        """Analyze user's preferred creation times"""
        
        hours = [row[0] for row in capsule_data if row[0] is not None]
        if not hours:
            return {'profile': 'unknown', 'confidence': 0.0}
        
        # Count frequency by time periods
        time_counts = {
            'morning': sum(1 for h in hours if 6 <= h <= 11),
            'afternoon': sum(1 for h in hours if 12 <= h <= 17),
            'evening': sum(1 for h in hours if 18 <= h <= 23),
            'night': sum(1 for h in hours if h >= 0 and h <= 5)
        }
        
        total = len(hours)
        time_percentages = {k: v/total for k, v in time_counts.items()}
        
        # Determine primary pattern
        primary_time = max(time_percentages, key=time_percentages.get)
        confidence = time_percentages[primary_time]
        
        return {
            'profile': f"{primary_time}_creator",
            'confidence': confidence,
            'distribution': time_percentages,
            'optimal_hours': PrivacyFocusedAnalytics._get_optimal_hours(primary_time)
        }
    
    @staticmethod
    def _get_optimal_hours(time_profile: str) -> List[int]:
        """Get optimal notification hours for time profile"""
        
        hour_mapping = {
            'morning_creator': [8, 9, 10],
            'afternoon_creator': [13, 14, 15],  
            'evening_creator': [19, 20, 21],
            'night_creator': [22, 23]
        }
        
        return hour_mapping.get(time_profile, [14, 20])  # Default times
    
    @staticmethod
    def _analyze_content_patterns(capsule_data: List) -> Dict:
        """Analyze content preferences and writing style"""
        
        content_lengths = [row[1] for row in capsule_data if row[1] is not None]
        content_types = [row[2] for row in capsule_data if row[2] is not None]
        
        if not content_lengths:
            return {'profile': 'unknown', 'confidence': 0.0}
        
        avg_length = sum(content_lengths) / len(content_lengths) if content_lengths else 0
        type_counts = Counter(content_types) if content_types else Counter()
        
        # Determine writing style
        if avg_length < 50:
            style_profile = 'brief_writer'
        elif avg_length > 200:
            style_profile = 'detailed_writer'
        else:
            style_profile = 'balanced_writer'
        
        # Determine content preference
        if len(type_counts) > 2 and type_counts.get('text', 0) < len(content_types) * 0.7:
            content_profile = 'multimedia_user'
        else:
            content_profile = 'text_focused'
        
        return {
            'style_profile': style_profile,
            'content_profile': content_profile,
            'avg_length': avg_length,
            'preferred_types': [item[0] for item in type_counts.most_common()]
        }
    
    @staticmethod
    def _analyze_frequency_patterns(capsule_data: List) -> Dict:
        """Analyze capsule creation frequency patterns"""
        
        if not capsule_data:
            return {'pattern': 'inactive', 'frequency': 0}
        
        # Group by date to count capsules per day
        dates = [row[3] for row in capsule_data if row[3] is not None]
        date_counts = Counter(dates)
        
        # Calculate daily average
        if dates:
            unique_days = len(date_counts)
            total_capsules = len(capsule_data)
            daily_avg = total_capsules / unique_days
        else:
            daily_avg = 0
        
        # Determine frequency pattern
        if daily_avg >= 1:
            pattern = 'daily'
        elif daily_avg >= 0.5:
            pattern = 'frequent'
        elif daily_avg >= 0.2:
            pattern = 'weekly'
        elif daily_avg > 0:
            pattern = 'occasional'
        else:
            pattern = 'inactive'
        
        return {
            'pattern': pattern,
            'daily_average': daily_avg,
            'active_days': len(date_counts),
            'total_count': len(capsule_data)
        }
    
    @staticmethod
    def _calculate_engagement_score(capsule_data: List) -> float:
        """Calculate user engagement score based on multiple factors"""
        
        if not capsule_data:
            return 0.0
        
        # Calculate various engagement factors
        total_capsules = len(capsule_data)
        
        # Time diversity factor (0-1): how many different time periods used
        hours = [row[0] for row in capsule_data if row[0] is not None]
        if hours:
            time_periods = len(set(['morning' if 6 <= h <= 11 else 
                                  'afternoon' if 12 <= h <= 17 else 
                                  'evening' if 18 <= h <= 23 else 'night' 
                                  for h in hours]))
            time_diversity = time_periods / 4.0
        else:
            time_diversity = 0.0
        
        # Content diversity factor (0-1): how many different content types used
        content_types = [row[2] for row in capsule_data if row[2] is not None]
        if content_types:
            content_diversity = len(set(content_types)) / 5.0  # Assuming 5 possible types
        else:
            content_diversity = 0.0
        
        # Consistency factor (0-1): based on creation frequency
        dates = [row[3] for row in capsule_data if row[3] is not None]
        if dates:
            date_set = set(dates)
            consistency = min(len(date_set) / 30.0, 1.0)  # Max score for daily creation
        else:
            consistency = 0.0
        
        # Calculate weighted engagement score
        engagement_score = (
            0.3 * min(total_capsules / 30.0, 1.0) +  # Total volume factor
            0.2 * time_diversity +                    # Time diversity factor
            0.2 * content_diversity +                 # Content diversity factor
            0.3 * consistency                         # Consistency factor
        )
        
        return min(engagement_score, 1.0)  # Cap at 1.0
    
    @staticmethod
    def get_personalized_suggestions(user_id: int) -> Dict:
        """Get personalized suggestions based on user analysis"""
        
        analysis = PrivacyFocusedAnalytics.analyze_user_behavior(user_id)
        from .database import get_user_data
        user_data = get_user_data(user_id)
        
        if not user_data:
            return {}
        
        current_time = datetime.now()
        
        suggestions = {
            'optimal_notification_times': [],
            'content_suggestions': [],
            'timing_suggestions': {},
            'engagement_tips': [],
            'personalization_profile': analysis
        }
        
        # Optimal notification times
        time_profile = analysis.get('time_profile', {})
        if time_profile.get('confidence', 0) > 0.3:
            suggestions['optimal_notification_times'] = time_profile.get('optimal_hours', [14, 20])
        
        # Content suggestions based on profile
        content_profile = analysis.get('content_profile', {})
        style = content_profile.get('style_profile', 'balanced_writer')
        
        if style == 'brief_writer':
            lang = user_data.get('language_code', 'ru')
            if lang == 'ru':
                suggestions['content_suggestions'] = [
                    'Попробуй добавить больше деталей — через время они станут ценными',
                    'Короткие заметки хороши, но иногда стоит углубиться в детали'
                ]
            else:
                suggestions['content_suggestions'] = [
                    'Try adding more details — they\'ll become valuable over time',
                    'Brief notes are great, but sometimes it\'s worth diving deeper into details'
                ]
        elif style == 'detailed_writer':
            lang = user_data.get('language_code', 'ru')
            if lang == 'ru':
                suggestions['content_suggestions'] = [
                    'Твои подробные записи — настоящие сокровища времени',
                    'Попробуй иногда создать короткую капсулу — одну мысль или чувство'
                ]
            else:
                suggestions['content_suggestions'] = [
                    'Your detailed notes are true treasures of time',
                    'Try creating a short capsule sometimes — one thought or feeling'
                ]
        
        # Engagement optimization
        engagement_score = analysis.get('engagement_score', 0.5)
        if engagement_score < 0.3:
            lang = user_data.get('language_code', 'ru')
            if lang == 'ru':
                suggestions['engagement_tips'] = [
                    'Попробуй создавать капсулы в разное время дня',
                    'Экспериментируй с разными типами контента',
                    'Добавь эмоции и личные детали'
                ]
            else:
                suggestions['engagement_tips'] = [
                    'Try creating capsules at different times of day',
                    'Experiment with different content types',
                    'Add emotions and personal details'
                ]
        
        return suggestions

    @staticmethod
    def get_emotional_profile(user_id: int) -> str:
        """Analyze emotional profile from user's capsule content"""
        
        with engine.connect() as conn:
            # Get recent capsule content for emotional analysis
            result = conn.execute(text("""
                SELECT content_text
                FROM capsules 
                WHERE user_id = :user_id 
                AND content_text IS NOT NULL
                AND created_at > DATE('now', '-14 days')
                LIMIT 10
            """), {"user_id": user_id}).fetchall()
        
        if not result:
            return 'unknown'
        
        # Combine all content
        all_content = ' '.join([row[0] for row in result if row[0]]).lower()
        
        # Define emotional keywords in both languages
        emotional_keywords = {
            'reflective': {
                'ru': ['чувствую', 'думаю', 'осознал', 'понял', 'размышляю', 'осознание', 'осознанный'],
                'en': ['feel', 'think', 'realized', 'understand', 'reflect', 'awareness', 'mindful']
            },
            'goal_oriented': {
                'ru': ['хочу', 'планирую', 'достигну', 'цель', 'поставлю', 'добьюсь', 'пойду'],
                'en': ['want', 'plan', 'achieve', 'goal', 'set', 'succeed', 'go']
            },
            'nostalgic': {
                'ru': ['помню', 'был', 'тогда', 'раньше', 'вспоминаю', 'прошлое', 'воспоминание'],
                'en': ['remember', 'was', 'then', 'before', 'recall', 'past', 'memory']
            },
            'grateful': {
                'ru': ['спасибо', 'благодарен', 'ценю', 'рад', 'счастлив', 'благодарность'],
                'en': ['thank', 'grateful', 'appreciate', 'happy', 'blessed', 'gratitude']
            }
        }
        
        # Count occurrences of emotional keywords
        profile_scores = {}
        lang = get_user_data(user_id).get('language_code', 'ru')
        keywords = emotional_keywords
        
        for profile, words in keywords.items():
            word_list = words.get(lang, words.get('ru', []))
            score = sum(all_content.count(word) for word in word_list)
            profile_scores[profile] = score
        
        # Return the profile with the highest score, or 'unknown' if no clear winner
        max_profile = max(profile_scores, key=profile_scores.get)
        if profile_scores[max_profile] > 0:
            return max_profile
        else:
            return 'unknown'


class BehavioralTriggers:
    """System to detect and respond to behavioral triggers"""
    
    @staticmethod
    def check_for_triggers(user_id: int):
        """Check if any behavioral triggers apply to this user"""
        
        user_data = PrivacyFocusedAnalytics.get_user_data(user_id)
        analytics = PrivacyFocusedAnalytics.analyze_user_behavior(user_id)
        
        triggers = []
        
        # Check for streak-breaking patterns
        if user_data.get('streak_count', 0) > 5:
            last_activity = user_data.get('last_activity_time')
            if last_activity:
                from datetime import datetime
                last_date = datetime.fromisoformat(str(last_activity).split('.')[0])
                days_since = (datetime.now() - last_date).days
                if days_since > 1:  # Streak broken
                    triggers.append('streak_recovery')
        
        # Check for low engagement
        engagement_score = analytics.get('engagement_score', 0)
        if engagement_score < 0.2:
            triggers.append('low_engagement_boost')
        
        # Check for content type variety
        content_profile = analytics.get('content_profile', {})
        preferred_types = content_profile.get('preferred_types', [])
        if len(set(preferred_types)) < 2:
            triggers.append('content_diversification')
        
        return triggers
    
    @staticmethod
    def get_trigger_response(trigger_type: str, user_id: int) -> Optional[Dict]:
        """Get appropriate response for a behavioral trigger"""
        
        user_data = PrivacyFocusedAnalytics.get_user_data(user_id)
        lang = user_data.get('language_code', 'ru')
        
        responses = {
            'streak_recovery': {
                'ru': 'Пропустил(а) несколько дней? 💪\n\nНе беда — можно начать заново\nТвой рекорд: {} дней\nПопробуешь побить?\n\n[Начать новый streak]'.format(user_data.get('best_streak', 0)),
                'en': 'Missed a few days? 💪\n\nNo problem — you can start over\nYour record: {} days\nTry to beat it?\n\n[Start new streak]'.format(user_data.get('best_streak', 0))
            },
            'low_engagement_boost': {
                'ru': 'Как настроение? 🌟\n\nНапоминаю, что ты можешь создать капсулу с любого устройства\nДаже короткое сообщение станет важным воспоминанием\n\n[Создать капсулу]',
                'en': 'How are you feeling? 🌟\n\nJust a reminder that you can create a capsule from any device\nEven a short message will become an important memory\n\n[Create capsule]'
            },
            'content_diversification': {
                'ru': 'Интересный факт: разнообразие делает капсулы ценнее\n\nПопробуй сегодня:\n• Голосовое сообщение 🎤\n• Фото момента 📸\n• Рисунок или заметку ✍️\n\n[Экспериментировать]',
                'en': 'Interesting fact: variety makes capsules more valuable\n\nTry today:\n• Voice message 🎤\n• Photo of the moment 📸\n• Drawing or note ✍️\n\n[Experiment]'
            }
        }
        
        return responses.get(trigger_type, {}).get(lang)