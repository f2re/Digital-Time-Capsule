# File: src/timezone_utils.py

from datetime import datetime, timezone
import pytz
from typing import Optional

def convert_local_to_utc(local_time: datetime, user_timezone: str = 'UTC') -> datetime:
    """Convert local datetime to UTC."""
    try:
        if user_timezone == 'UTC':
            return local_time.replace(tzinfo=timezone.utc)
        
        # Get timezone object
        tz = pytz.timezone(user_timezone)
        
        # Localize the naive datetime
        localized_time = tz.localize(local_time)
        
        # Convert to UTC
        return localized_time.astimezone(timezone.utc)
    except Exception:
        # Fallback to UTC if timezone conversion fails
        return local_time.replace(tzinfo=timezone.utc)

def format_time_for_user(utc_time: datetime, user_timezone: str = 'UTC', lang: str = 'en') -> str:
    """Format UTC datetime for display in user's timezone."""
    try:
        if user_timezone == 'UTC':
            formatted_time = utc_time.strftime('%d.%m.%Y %H:%M')
            return f"{formatted_time} UTC"
        
        # Convert to user's timezone
        tz = pytz.timezone(user_timezone)
        local_time = utc_time.astimezone(tz)
        
        formatted_time = local_time.strftime('%d.%m.%Y %H:%M')
        return f"{formatted_time} ({user_timezone})"
    except Exception:
        # Fallback formatting
        return utc_time.strftime('%d.%m.%Y %H:%M UTC')