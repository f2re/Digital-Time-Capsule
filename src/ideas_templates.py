# src/ideas_templates.py
"""
Predefined idea categories and templates for the Ideas feature.
All static content keys reference translations in translations.py.
"""

from datetime import datetime, timedelta, time
import calendar

# Categories metadata: key -> icon and ordered idea keys
IDEAS_CATEGORIES = {
    'self_motivation': {
        'icon': '💪',
        'ideas': [
            'morning_motivation',
            'goal_achievement',
            'overcoming_challenges',
            'dream_reminder',
        ],
    },
    'holidays': {
        'icon': '🎉',
        'ideas': [
            'new_year_wishes',
            'birthday_future',
            'anniversary_message',
            'pro_day',
        ],
    },
    'daily_reflection': {
        'icon': '📝',
        'ideas': [
            'evening_summary',
            'gratitude_note',
            'day_highlights',
            'lesson_learned',
        ],
    },
    'relationships': {
        'icon': '❤️',
        'ideas': [
            'letter_to_loved',
            'thanks_to_parents',
            'message_to_kids',
            'friendly_note',
        ],
    },
    'goals_plans': {
        'icon': '🎯',
        'ideas': [
            'progress_check',
            'plans_reminder',
            'change_motivation',
            'career_goals',
        ],
    },
    'memories': {
        'icon': '🤔',
        'ideas': [
            'save_the_moment',
            'today_mood',
            'important_event',
            'wisdom_note',
        ],
    },
}

# Helper functions to compute default delivery datetimes relative to now

def dt_in_days(days: int) -> datetime:
    return datetime.now() + timedelta(days=days)


def next_new_year() -> datetime:
    now = datetime.now()
    year = now.year + (1 if (now.month, now.day) > (1, 1) or now.month > 1 else 0)
    # Deliver on Dec 31 of current or next year at 23:59 local time
    target_year = now.year if now.month < 12 or (now.month == 12 and now.day < 31) else now.year + 1
    return datetime(target_year, 12, 31, 23, 59)


def _compute_delivery(preset):
    """Compute delivery datetime from a preset descriptor with smart timing."""
    if isinstance(preset, dict):
        if 'days' in preset:
            return dt_in_days(int(preset['days']))
        elif 'smart_time' in preset:
            smart_type = preset['smart_time']
            if smart_type == 'next_morning':
                return next_morning()
            elif smart_type == 'next_evening':
                return next_evening()
            elif smart_type == 'weekend_morning':
                return next_weekend_morning()
            elif smart_type == 'monday_morning':
                return next_monday_morning()
            elif smart_type == 'birthday_month':
                return next_birthday_month()
    elif preset == 'next_new_year':
        return next_new_year()
    
    # Default fallback: 30 days
    return dt_in_days(30)


# Add smart timing functions
def next_morning(target_hour=8, target_minute=0):
    """Get next morning at specified time (default 8:00 AM)."""
    now = datetime.now()
    tomorrow = now + timedelta(days=1)
    return tomorrow.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)


def next_evening(target_hour=20, target_minute=0):
    """Get next evening at specified time (default 8:00 PM)."""
    now = datetime.now()
    if now.hour < target_hour:
        # Today evening
        return now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
    else:
        # Tomorrow evening
        tomorrow = now + timedelta(days=1)
        return tomorrow.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)


def next_weekend_morning():
    """Get next Saturday morning at 9:00 AM."""
    now = datetime.now()
    days_until_saturday = (5 - now.weekday()) % 7  # Saturday is 5
    if days_until_saturday == 0 and now.hour >= 9:
        days_until_saturday = 7  # Next Saturday if it's already Saturday afternoon
    
    saturday = now + timedelta(days=days_until_saturday)
    return saturday.replace(hour=9, minute=0, second=0, microsecond=0)


def next_monday_morning():
    """Get next Monday morning at 8:00 AM."""
    now = datetime.now()
    days_until_monday = (7 - now.weekday()) % 7  # Monday is 0
    if days_until_monday == 0:
        days_until_monday = 7
    
    monday = now + timedelta(days=days_until_monday)
    return monday.replace(hour=8, minute=0, second=0, microsecond=0)


def next_birthday_month():
    """Get delivery time for next month (for birthday reminders)."""
    now = datetime.now()
    if now.month == 12:
        next_month = now.replace(year=now.year + 1, month=1, day=1, hour=10, minute=0)
    else:
        next_month = now.replace(month=now.month + 1, day=1, hour=10, minute=0)
    return next_month


# Template definitions
# Each template describes defaults; text/title keys are stored in translations
# content_type can be: 'text' (default), user can change later in the flow
# recipient_preset: 'self' by default
# delivery_preset: callable or dict {'days': int}; computed at runtime by handler
IDEAS_TEMPLATES = {
    # Self Motivation - Smart morning delivery
    'morning_motivation': {
        'title_key': 'idea_morning_motivation_title',
        'text_key': 'idea_morning_motivation_text',
        'content_type': 'text',
        'recipient_preset': 'self',
        'delivery_preset': {'smart_time': 'next_morning'},  # 8:00 AM tomorrow
        'hints_key': 'idea_morning_motivation_hints',
    },
    'goal_achievement': {
        'title_key': 'idea_goal_achievement_title',
        'text_key': 'idea_goal_achievement_text',
        'content_type': 'text',
        'recipient_preset': 'self',
        'delivery_preset': {'days': 90},
        'hints_key': 'idea_goal_achievement_hints',
    },
    'overcoming_challenges': {
        'title_key': 'idea_overcoming_challenges_title',
        'text_key': 'idea_overcoming_challenges_text',
        'content_type': 'text',
        'recipient_preset': 'self',
        'delivery_preset': {'days': 7},
        'hints_key': 'idea_overcoming_challenges_hints',
    },
    'dream_reminder': {
        'title_key': 'idea_dream_reminder_title',
        'text_key': 'idea_dream_reminder_text',
        'content_type': 'text',
        'recipient_preset': 'self',
        'delivery_preset': {'days': 180},
        'hints_key': 'idea_dream_reminder_hints',
    },

    # Holidays
    'new_year_wishes': {
        'title_key': 'idea_new_year_wishes_title',
        'text_key': 'idea_new_year_wishes_text',
        'content_type': 'text',
        'recipient_preset': 'self',
        'delivery_preset': 'next_new_year',  # special
        'hints_key': 'idea_new_year_wishes_hints',
    },
    'birthday_future': {
        'title_key': 'idea_birthday_future_title',
        'text_key': 'idea_birthday_future_text',
        'content_type': 'text',
        'recipient_preset': 'self',
        'delivery_preset': {'smart_time': 'birthday_month'},  # Next month
        'hints_key': 'idea_birthday_future_hints',
    },
    'anniversary_message': {
        'title_key': 'idea_anniversary_message_title',
        'text_key': 'idea_anniversary_message_text',
        'content_type': 'text',
        'recipient_preset': 'self',
        'delivery_preset': {'days': 365},
        'hints_key': 'idea_anniversary_message_hints',
    },
    'pro_day': {
        'title_key': 'idea_pro_day_title',
        'text_key': 'idea_pro_day_text',
        'content_type': 'text',
        'recipient_preset': 'self',
        'delivery_preset': {'days': 365},
        'hints_key': 'idea_pro_day_hints',
    },

    # Daily Reflection
    'evening_summary': {
        'title_key': 'idea_evening_summary_title',
        'text_key': 'idea_evening_summary_text',
        'content_type': 'text',
        'recipient_preset': 'self',
        'delivery_preset': {'smart_time': 'next_evening'},  # 8:00 PM today/tomorrow
        'hints_key': 'idea_evening_summary_hints',
    },
    'gratitude_note': {
        'title_key': 'idea_gratitude_note_title',
        'text_key': 'idea_gratitude_note_text',
        'content_type': 'text',
        'recipient_preset': 'self',
        'delivery_preset': {'days': 7},
        'hints_key': 'idea_gratitude_note_hints',
    },
    'day_highlights': {
        'title_key': 'idea_day_highlights_title',
        'text_key': 'idea_day_highlights_text',
        'content_type': 'text',
        'recipient_preset': 'self',
        'delivery_preset': {'smart_time': 'weekend_morning'},  # Next Saturday 9:00 AM
        'hints_key': 'idea_day_highlights_hints',
    },
    'lesson_learned': {
        'title_key': 'idea_lesson_learned_title',
        'text_key': 'idea_lesson_learned_text',
        'content_type': 'text',
        'recipient_preset': 'self',
        'delivery_preset': {'days': 30},
        'hints_key': 'idea_lesson_learned_hints',
    },

    # Relationships
    'letter_to_loved': {
        'title_key': 'idea_letter_to_loved_title',
        'text_key': 'idea_letter_to_loved_text',
        'content_type': 'text',
        'recipient_preset': 'self',
        'delivery_preset': {'days': 30},
        'hints_key': 'idea_letter_to_loved_hints',
    },
    'thanks_to_parents': {
        'title_key': 'idea_thanks_to_parents_title',
        'text_key': 'idea_thanks_to_parents_text',
        'content_type': 'text',
        'recipient_preset': 'self',
        'delivery_preset': {'days': 180},
        'hints_key': 'idea_thanks_to_parents_hints',
    },
    'message_to_kids': {
        'title_key': 'idea_message_to_kids_title',
        'text_key': 'idea_message_to_kids_text',
        'content_type': 'text',
        'recipient_preset': 'self',
        'delivery_preset': {'days': 365 * 5},
        'hints_key': 'idea_message_to_kids_hints',
    },
    'friendly_note': {
        'title_key': 'idea_friendly_note_title',
        'text_key': 'idea_friendly_note_text',
        'content_type': 'text',
        'recipient_preset': 'self',
        'delivery_preset': {'days': 90},
        'hints_key': 'idea_friendly_note_hints',
    },

    # Goals & Plans
    'progress_check': {
        'title_key': 'idea_progress_check_title',
        'text_key': 'idea_progress_check_text',
        'content_type': 'text',
        'recipient_preset': 'self',
        'delivery_preset': {'days': 90},
        'hints_key': 'idea_progress_check_hints',
    },
    'plans_reminder': {
        'title_key': 'idea_plans_reminder_title',
        'text_key': 'idea_plans_reminder_text',
        'content_type': 'text',
        'recipient_preset': 'self',
        'delivery_preset': {'days': 365},
        'hints_key': 'idea_plans_reminder_hints',
    },
    'change_motivation': {
        'title_key': 'idea_change_motivation_title',
        'text_key': 'idea_change_motivation_text',
        'content_type': 'text',
        'recipient_preset': 'self',
        'delivery_preset': {'days': 30},
        'hints_key': 'idea_change_motivation_hints',
    },
    'career_goals': {
        'title_key': 'idea_career_goals_title',
        'text_key': 'idea_career_goals_text',
        'content_type': 'text',
        'recipient_preset': 'self',
        'delivery_preset': {'smart_time': 'monday_morning'},  # Next Monday 8:00 AM
        'hints_key': 'idea_career_goals_hints',
    },

    # Memories
    'save_the_moment': {
        'title_key': 'idea_save_the_moment_title',
        'text_key': 'idea_save_the_moment_text',
        'content_type': 'text',
        'recipient_preset': 'self',
        'delivery_preset': {'days': 365},
        'hints_key': 'idea_save_the_moment_hints',
    },
    'today_mood': {
        'title_key': 'idea_today_mood_title',
        'text_key': 'idea_today_mood_text',
        'content_type': 'text',
        'recipient_preset': 'self',
        'delivery_preset': {'days': 180},
        'hints_key': 'idea_today_mood_hints',
    },
    'important_event': {
        'title_key': 'idea_important_event_title',
        'text_key': 'idea_important_event_text',
        'content_type': 'text',
        'recipient_preset': 'self',
        'delivery_preset': {'days': 365 * 5},
        'hints_key': 'idea_important_event_hints',
    },
    'wisdom_note': {
        'title_key': 'idea_wisdom_note_title',
        'text_key': 'idea_wisdom_note_text',
        'content_type': 'text',
        'recipient_preset': 'self',
        'delivery_preset': {'days': 30},
        'hints_key': 'idea_wisdom_note_hints',
    },
}
