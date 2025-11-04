"""
Timezone utilities for Digital Time Capsule
Handles timezone conversion between UTC and user's local time
"""

from datetime import datetime
import pytz
from typing import Optional


def convert_utc_to_local(utc_time: datetime, timezone_str: str) -> datetime:
    """
    Convert UTC time to user's local timezone
    
    Args:
        utc_time: Time in UTC
        timezone_str: User's timezone string (e.g., 'Europe/Moscow')
    
    Returns:
        Time converted to user's local timezone
    """
    if utc_time.tzinfo is None:
        # Assume UTC if no timezone info
        utc_time = utc_time.replace(tzinfo=pytz.UTC)
    
    user_tz = pytz.timezone(timezone_str)
    return utc_time.astimezone(user_tz)


def convert_local_to_utc(local_time: datetime, timezone_str: str) -> datetime:
    """
    Convert user's local time to UTC
    
    Args:
        local_time: Time in user's local timezone
        timezone_str: User's timezone string (e.g., 'Europe/Moscow')
    
    Returns:
        Time converted to UTC
    """
    user_tz = pytz.timezone(timezone_str)
    local_time = user_tz.localize(local_time)
    return local_time.astimezone(pytz.UTC)


def format_time_for_user(utc_time: datetime, user_timezone: str, lang: str = 'en') -> str:
    """
    Format UTC time for display to user in their local timezone
    
    Args:
        utc_time: Time in UTC from database
        user_timezone: User's timezone string
        lang: User's language for format preference
    
    Returns:
        Formatted time string in user's local timezone
    """
    local_time = convert_utc_to_local(utc_time, user_timezone)
    
    # Use format based on language preference
    if lang == 'ru':
        # Russian format: DD.MM.YYYY HH:MM
        return local_time.strftime("%d.%m.%Y %H:%M")
    else:
        # English format: DD.MM.YYYY HH:MM (same as Russian in this case)
        return local_time.strftime("%d.%m.%Y %H:%M")


def get_timezone_for_language(lang: str) -> str:
    """
    Get a default timezone based on user's language (fallback for new users)
    
    Args:
        lang: User's language code
    
    Returns:
        Default timezone string for the language
    """
    timezone_map = {
        'ru': 'Europe/Moscow',
        'en': 'UTC'
    }
    return timezone_map.get(lang, 'UTC')