# Ideas Flow Fixes - Complete Implementation

## Issues Identified & Solutions

### 1. Remove Duplicate Emojis in Ideas Buttons ❌

**Problem**: Templates display emojis from both the template title and potentially duplicate category icons.

**Fix**: Update `_templates_keyboard` function to remove emoji duplication.

```python
# File: src/handlers/ideas.py

def _templates_keyboard(lang: str, cat_key: str) -> InlineKeyboardMarkup:
    rows = []
    meta = IDEAS_CATEGORIES.get(cat_key, {})
    for idea_key in meta.get('ideas', []):
        # Get template title without emoji prefix from category
        title = t(lang, f"{IDEAS_TEMPLATES[idea_key]['title_key']}")
        # Don't add category icon - template titles already have their own emojis
        rows.append([InlineKeyboardButton(title, callback_data=f'ideas_tpl:{idea_key}')])
    rows.append([
        InlineKeyboardButton(t(lang, 'back'), callback_data='ideas_menu'),
        InlineKeyboardButton(t(lang, 'back_to_menu'), callback_data='main_menu')
    ])
    return InlineKeyboardMarkup(rows)
```

### 2. Add Edit Date in Ideas Preview ✅

**Problem**: Users can only edit text but not the delivery date in Ideas preview.

**Fix**: Add "Edit Date" button to preview keyboard and handle date editing flow.

```python
# File: src/handlers/ideas.py

# Add new conversation state
# File: src/config.py - Add this state:
EDITING_IDEA_DATE = 19  # Add after EDITING_IDEA_CONTENT

# Update _preview_keyboard function:
def _preview_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t(lang, 'ideas_use_template'), callback_data='ideas_use')],
        [InlineKeyboardButton(t(lang, 'ideas_edit_text'), callback_data='ideas_edit')],
        [InlineKeyboardButton(t(lang, 'ideas_edit_date'), callback_data='ideas_edit_date')],  # NEW
        [InlineKeyboardButton(t(lang, 'back'), callback_data='ideas_back')],
    ])

# Add new handler in ideas_router:
elif data == 'ideas_edit_date':
    try:
        await query.message.edit_text(t(lang, 'ideas_enter_date'))
    except BadRequest:
        await query.message.reply_text(t(lang, 'ideas_enter_date'))
    return EDITING_IDEA_DATE

# Add new function for date input:
async def ideas_date_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle custom date input in Ideas flow."""
    user = update.effective_user
    user_data = get_user_data(user.id)
    lang = user_data.get('language_code', 'en')
    message = update.message
    
    if message and message.text:
        date_str = message.text.strip()
        try:
            import re
            from datetime import datetime
            
            # Parse DD.MM.YYYY HH:MM format
            date_pattern = r'^(\d{2})\.(\d{2})\.(\d{4})\s+(\d{2}):(\d{2})$'
            match = re.match(date_pattern, date_str)
            
            if not match:
                await message.reply_text(t(lang, 'invalid_date'))
                return EDITING_IDEA_DATE
                
            day, month, year, hour, minute = map(int, match.groups())
            new_delivery_time = datetime(year, month, day, hour, minute)
            
            # Validate future date
            if new_delivery_time <= datetime.now():
                await message.reply_text(t(lang, 'date_must_be_future'))
                return EDITING_IDEA_DATE
                
            # Update context with new delivery time
            context.user_data[CTX_IDEA_PRESET_DELIVERY] = new_delivery_time
            
            # Re-render preview with updated date
            title = context.user_data.get(CTX_IDEA_TITLE, '')
            text_content = context.user_data.get(CTX_IDEA_TEXT, '')
            when = new_delivery_time.strftime('%d.%m.%Y %H:%M')
            
            # Get hints
            idea_key = context.user_data.get(CTX_IDEA_KEY)
            hints_key = IDEAS_TEMPLATES.get(idea_key, {}).get('hints_key')
            hints = t(lang, hints_key) if hints_key else ''
            
            preview = (
                f"<b>{title}</b>\n\n"
                f"{text_content}\n\n"
                f"<b>{t(lang, 'ideas_preset_time')}</b>: {when}\n\n"
                f"<b>{t(lang, 'ideas_hints')}</b>\n{hints}"
            )
            
            await message.reply_text(
                preview, 
                reply_markup=_preview_keyboard(lang), 
                parse_mode='HTML'
            )
            return EDITING_IDEA_CONTENT
            
        except Exception as e:
            logger.error(f"Error parsing date in ideas flow: {e}")
            await message.reply_text(t(lang, 'invalid_date'))
            return EDITING_IDEA_DATE
    
    await message.reply_text(t(lang, 'ideas_enter_date'))
    return EDITING_IDEA_DATE
```

### 3. Make Ideas More Responsible with Smart Timing ⏰

**Problem**: Ideas don't consider optimal delivery times (morning motivation should be sent in the morning, etc.).

**Fix**: Update `ideas_templates.py` with smart timing logic.

```python
# File: src/ideas_templates.py

from datetime import datetime, timedelta, time
import calendar

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

# Update _compute_delivery function in src/handlers/ideas.py
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

# Update IDEAS_TEMPLATES with smart timing:
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
    
    # Evening reflection - Smart evening delivery
    'evening_summary': {
        'title_key': 'idea_evening_summary_title',
        'text_key': 'idea_evening_summary_text',
        'content_type': 'text',
        'recipient_preset': 'self',
        'delivery_preset': {'smart_time': 'next_evening'},  # 8:00 PM today/tomorrow
        'hints_key': 'idea_evening_summary_hints',
    },
    
    # Weekend reflection - Saturday morning
    'day_highlights': {
        'title_key': 'idea_day_highlights_title',
        'text_key': 'idea_day_highlights_text',
        'content_type': 'text',
        'recipient_preset': 'self',
        'delivery_preset': {'smart_time': 'weekend_morning'},  # Next Saturday 9:00 AM
        'hints_key': 'idea_day_highlights_hints',
    },
    
    # Career goals - Monday morning motivation
    'career_goals': {
        'title_key': 'idea_career_goals_title',
        'text_key': 'idea_career_goals_text',
        'content_type': 'text',
        'recipient_preset': 'self',
        'delivery_preset': {'smart_time': 'monday_morning'},  # Next Monday 8:00 AM
        'hints_key': 'idea_career_goals_hints',
    },
    
    # Birthday reminders - Next month
    'birthday_future': {
        'title_key': 'idea_birthday_future_title',
        'text_key': 'idea_birthday_future_text',
        'content_type': 'text',
        'recipient_preset': 'self',
        'delivery_preset': {'smart_time': 'birthday_month'},  # Next month
        'hints_key': 'idea_birthday_future_hints',
    },
    
    # Keep other templates with regular timing or update as needed...
    # [Rest of templates remain the same or get smart timing updates]
}
```

### 4. Fix Successful Capsule Creation from Ideas Flow 🔧

**Problem**: Capsule creation fails when transitioning from Ideas flow due to timezone issues and missing imports.

**Fix**: Update create_capsule handler and add missing imports.

```python
# File: src/handlers/create_capsule.py

# Add missing import at the top
from ..timezone_utils import convert_local_to_utc, format_time_for_user

# Fix show_time_selection function
async def show_time_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show time selection menu"""
    user = update.effective_user
    user_data = get_user_data(user.id)
    lang = user_data['language_code']
    
    # Check if prefill delivery time is available (from ideas module)
    prefill_delivery_time = context.user_data.get('capsule', {}).get('prefill_delivery_time')
    
    if prefill_delivery_time:
        # FIXED: Ensure timezone awareness
        from datetime import timezone
        
        # Convert to UTC if not already timezone-aware
        if prefill_delivery_time.tzinfo is None:
            prefill_delivery_time = prefill_delivery_time.replace(tzinfo=timezone.utc)
        
        # Validate time limits based on subscription
        now = datetime.now(timezone.utc)
        max_days = PREMIUM_TIME_LIMIT_DAYS if user_data['subscription_status'] == PREMIUM_TIER else FREE_TIME_LIMIT_DAYS
        
        if (prefill_delivery_time - now).days > max_days:
            keyboard = [
                [InlineKeyboardButton(t(lang, 'upgrade_subscription'), callback_data='subscription')],
                [InlineKeyboardButton(t(lang, 'back'), callback_data='main_menu')]
            ]
            await send_menu_with_image(
                update, context, 'capsules', 
                t(lang, 'date_too_far', days=FREE_TIME_LIMIT_DAYS, years=PREMIUM_TIME_LIMIT_DAYS//365), 
                InlineKeyboardMarkup(keyboard)
            )
            return SELECTING_ACTION

        context.user_data['capsule']['delivery_time'] = prefill_delivery_time
        logger.info(f"Prefill delivery time used: {prefill_delivery_time} for user {user.id}")

        return await ask_for_recipient(update, context)

    # Continue with normal flow...
    keyboard = [
        [InlineKeyboardButton(t(lang, 'time_1hour'), callback_data='time_1h'),
         InlineKeyboardButton(t(lang, 'time_1day'), callback_data='time_1d')],
        [InlineKeyboardButton(t(lang, 'time_1week'), callback_data='time_1w'),
         InlineKeyboardButton(t(lang, 'time_1month'), callback_data='time_1m')],
        [InlineKeyboardButton(t(lang, 'time_3months'), callback_data='time_3m'),
         InlineKeyboardButton(t(lang, 'time_6months'), callback_data='time_6m')],
        [InlineKeyboardButton(t(lang, 'time_1year'), callback_data='time_1y')]
    ]

    keyboard.extend([
        [InlineKeyboardButton(t(lang, 'time_custom'), callback_data='time_custom')],
        [InlineKeyboardButton(t(lang, 'cancel'), callback_data='cancel')]
    ])

    await send_menu_with_image(update, context, 'capsules', t(lang, 'select_time'), InlineKeyboardMarkup(keyboard))
    return SELECTING_TIME

# Fix confirm_capsule function timezone handling
async def show_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show capsule confirmation"""
    user = update.effective_user
    user_data = get_user_data(user.id)
    lang = user_data['language_code']
    capsule = context.user_data.get('capsule', {})

    # Format recipient display
    recipient_text = ""
    recipient_type = capsule.get('recipient_type')

    if recipient_type == "self":
        recipient_text = t(lang, "recipient_self")
    elif recipient_type == "user":
        recipient_text = f"@{capsule.get('recipient_username', 'Unknown')}"
    elif recipient_type in ("group", "channel"):
        recipient_text = f"{capsule.get('recipient_name', 'Unknown')}"

    # FIXED: Format time display using user's timezone with proper error handling
    try:
        user_timezone = user_data.get('timezone', 'UTC')
        delivery_time = capsule['delivery_time']
        
        # Ensure timezone awareness
        if delivery_time.tzinfo is None:
            delivery_time = delivery_time.replace(tzinfo=timezone.utc)
            
        time_text = format_time_for_user(delivery_time, user_timezone, lang)
    except Exception as e:
        logger.error(f"Error formatting time for user {user.id}: {e}")
        # Fallback to simple formatting
        time_text = capsule['delivery_time'].strftime('%d.%m.%Y %H:%M UTC')

    # Format content type
    content_type_display = t(lang, f"content_{capsule.get('content_type', 'unknown')}")

    keyboard = [
        [InlineKeyboardButton(t(lang, "confirm_yes"), callback_data="confirm_yes")],
        [InlineKeyboardButton(t(lang, "confirm_no"), callback_data="cancel")]
    ]

    confirmation_text = t(lang, "confirm_capsule",
                         type=content_type_display,
                         time=time_text,
                         recipient=recipient_text)

    await send_menu_with_image(update, context, 'capsules', confirmation_text, InlineKeyboardMarkup(keyboard))
    return CONFIRMING_CAPSULE
```

### 5. Add Missing Translation Keys 🌐

**Fix**: Add new translation keys to `src/translations.py`.

```python
# File: src/translations.py

# Add these keys to both 'ru' and 'en' dictionaries:

# Russian translations:
'ru': {
    # ... existing translations ...
    
    # New Ideas flow keys
    'ideas_edit_date': '📅 Изменить дату',
    'ideas_enter_date': '📅 Введите новую дату доставки в формате ДД.ММ.ГГГГ ЧЧ:ММ\nНапример: 25.12.2025 09:00',
    'date_must_be_future': '❌ Дата должна быть в будущем',
    'upgrade_subscription': '⬆️ Обновить подписку',
    'insufficient_balance': '❌ Недостаточно капсул для создания. Купите капсулы или подписку.',
    'creation_cancelled': '❌ Создание капсулы отменено',
    'time_limit_exceeded': '❌ Выбранная дата превышает лимиты вашего тарифа.\n\nБесплатно: до {days} дней\nПремиум: до {years} лет',
    
    # Smart timing descriptions for preview
    'smart_morning_time': 'Завтра утром в 8:00',
    'smart_evening_time': 'Сегодня/завтра вечером в 20:00',
    'smart_weekend_time': 'В следующую субботу в 9:00',
    'smart_monday_time': 'В следующий понедельник в 8:00',
    'smart_birthday_time': 'В следующем месяце',
},

# English translations:
'en': {
    # ... existing translations ...
    
    # New Ideas flow keys
    'ideas_edit_date': '📅 Edit Date',
    'ideas_enter_date': '📅 Enter new delivery date in format DD.MM.YYYY HH:MM\nExample: 25.12.2025 09:00',
    'date_must_be_future': '❌ Date must be in the future',
    'upgrade_subscription': '⬆️ Upgrade Subscription',
    'insufficient_balance': '❌ Insufficient capsules to create. Buy capsules or subscription.',
    'creation_cancelled': '❌ Capsule creation cancelled',
    'time_limit_exceeded': '❌ Selected date exceeds your plan limits.\n\nFree: up to {days} days\nPremium: up to {years} years',
    
    # Smart timing descriptions for preview
    'smart_morning_time': 'Tomorrow morning at 8:00 AM',
    'smart_evening_time': 'Tonight/tomorrow evening at 8:00 PM',
    'smart_weekend_time': 'Next Saturday at 9:00 AM',
    'smart_monday_time': 'Next Monday at 8:00 AM',
    'smart_birthday_time': 'Next month',
}
```

### 6. Update Main.py Conversation States 🔄

**Fix**: Add new conversation state to `main.py`.

```python
# File: main.py

# Update conversation handler states:
states={
    # ... existing states ...
    
    # Ideas States (UPDATED)
    SELECTING_IDEAS_CATEGORY: [
        CallbackQueryHandler(ideas_router, pattern='^ideas_cat:'),
        CallbackQueryHandler(ideas_router, pattern='^(ideas_menu|main_menu|cancel)$')
    ],
    SELECTING_IDEA_TEMPLATE: [
        CallbackQueryHandler(ideas_router, pattern='^ideas_tpl:'),
        CallbackQueryHandler(ideas_router, pattern='^(ideas_menu|ideas_back|main_menu|cancel)$')
    ],
    EDITING_IDEA_CONTENT: [
        CallbackQueryHandler(ideas_router, pattern='^(ideas_use|ideas_edit|ideas_edit_date|ideas_back|ideas_menu|main_menu|cancel)$'),
        MessageHandler(filters.TEXT & ~filters.COMMAND, ideas_text_input),
    ],
    EDITING_IDEA_DATE: [  # NEW STATE
        CallbackQueryHandler(ideas_router, pattern='^(ideas_back|ideas_menu|main_menu|cancel)$'),
        MessageHandler(filters.TEXT & ~filters.COMMAND, ideas_date_input),
    ],
    
    # ... rest of states ...
}

# Import the new handler
from src.handlers.ideas import show_ideas_menu, ideas_router, ideas_text_input, ideas_date_input
```

### 7. Create Missing Timezone Utils 🌍

**Fix**: Create `src/timezone_utils.py` if it doesn't exist.

```python
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
```

## Testing Instructions

### 1. Update Dependencies

Add to `requirements.txt`:
```
pytz==2023.3
```

### 2. Test Each Fix

1. **Test Emoji Deduplication**:
   - Go to Ideas → Any Category
   - Verify template buttons don't have duplicate emojis

2. **Test Date Editing**:
   - Select any idea template
   - Click "📅 Edit Date"
   - Enter: `25.12.2025 09:00`
   - Verify preview updates with new date

3. **Test Smart Timing**:
   - Select "Morning Motivation" → should show next morning delivery
   - Select "Evening Summary" → should show evening delivery
   - Verify times make contextual sense

4. **Test Complete Flow**:
   - Ideas → Category → Template → Edit text/date → Use Template
   - Verify capsule creation completes successfully
   - Check capsule is created with correct data

## Deployment Checklist

- [ ] Update `src/handlers/ideas.py`
- [ ] Update `src/ideas_templates.py`
- [ ] Update `src/handlers/create_capsule.py`
- [ ] Update `src/translations.py`
- [ ] Update `src/config.py` (add new state)
- [ ] Update `main.py` (conversation handler)
- [ ] Create `src/timezone_utils.py`
- [ ] Update `requirements.txt`
- [ ] Test all functionality
- [ ] Deploy and monitor logs

## Success Metrics

- ✅ No duplicate emojis in template buttons
- ✅ Date editing works in preview
- ✅ Smart timing delivers at appropriate times
- ✅ Complete Ideas → Capsule flow works
- ✅ No timezone-related errors
- ✅ All translations display correctly

---

**Status**: Ready for implementation and testing. All fixes address the core issues while maintaining backward compatibility.