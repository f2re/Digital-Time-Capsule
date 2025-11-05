# src/handlers/ideas.py
"""Ideas feature handlers: categories -> templates -> preview/edit -> handoff to create flow.

This module follows the project's handler patterns and uses translations via t().
"""
import re
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest

from ..translations import t
from ..config import (
    SELECTING_IDEAS_CATEGORY,
    SELECTING_IDEA_TEMPLATE,
    EDITING_IDEA_CONTENT,
    EDITING_IDEA_DATE,
    SELECTING_ACTION,
    FREE_TIME_LIMIT_DAYS,
    PREMIUM_TIME_LIMIT_DAYS,
    PREMIUM_TIER,
    logger
)
from ..ideas_templates import IDEAS_CATEGORIES, IDEAS_TEMPLATES, dt_in_days, next_new_year
from ..database import get_user_data, get_or_create_user

# Keys in context.user_data used in this flow
CTX_IDEA_KEY = "idea_key"
CTX_IDEA_TEXT = "idea_text"
CTX_IDEA_TITLE = "idea_title"
CTX_IDEA_PRESET_DELIVERY = "idea_preset_delivery"  # datetime
CTX_IDEA_CONTENT_TYPE = "idea_content_type"
CTX_IDEA_RECIPIENT = "idea_recipient"


def _compute_delivery(preset):
    """Compute delivery datetime from a preset descriptor.
    preset can be a dict like {'days': 30} or string 'next_new_year'.
    """
    if isinstance(preset, dict) and 'days' in preset:
        return dt_in_days(int(preset['days']))
    if preset == 'next_new_year':
        return next_new_year()
    # default fallback: 30 days
    return dt_in_days(30)


def _category_keyboard(lang: str) -> InlineKeyboardMarkup:
    rows = []
    for cat_key, meta in IDEAS_CATEGORIES.items():
        icon = meta.get('icon', '💡')
        label = f"{icon} {t(lang, f'ideas_category_{cat_key}')}"
        rows.append([InlineKeyboardButton(label, callback_data=f'ideas_cat:{cat_key}')])
    rows.append([InlineKeyboardButton(t(lang, 'back'), callback_data='main_menu')])
    return InlineKeyboardMarkup(rows)


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


def _preview_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t(lang, 'ideas_use_template'), callback_data='ideas_use')],
        [InlineKeyboardButton(t(lang, 'ideas_edit_text'), callback_data='ideas_edit')],
        [InlineKeyboardButton(t(lang, 'ideas_edit_date'), callback_data='ideas_edit_date')],
        [InlineKeyboardButton(t(lang, 'back'), callback_data='ideas_back')],
    ])


def _date_edit_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Keyboard for date editing with helpful buttons"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t(lang, 'date_quick_1week'), callback_data='ideas_quick_date:7')],
        [InlineKeyboardButton(t(lang, 'date_quick_1month'), callback_data='ideas_quick_date:30')],
        [InlineKeyboardButton(t(lang, 'date_quick_3months'), callback_data='ideas_quick_date:90')],
        [InlineKeyboardButton(t(lang, 'date_quick_1year'), callback_data='ideas_quick_date:365')],
        [InlineKeyboardButton(t(lang, 'back'), callback_data='ideas_back_to_preview')],
    ])


async def show_ideas_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point: show categories of ideas."""
    query = update.callback_query
    if query:
        await query.answer()
        message = query.message
    else:
        message = update.effective_message

    user = update.effective_user
    user_data = get_user_data(user.id)
    
    if not user_data:
        # User might not be registered, try to create user first
        try:
            get_or_create_user(user)
            user_data = get_user_data(user.id)
        except Exception as e:
            logger.error(f"Failed to create user {user.id}: {e}")
        
        if not user_data:
            logger.error(f"Failed to create/get user data for user {user.id}")
            # Fallback to main menu
            from .start import show_main_menu_with_image
            basic_user_data = {'id': user.id, 'language_code': 'en'}
            return await show_main_menu_with_image(update, context, basic_user_data)

    lang = user_data.get('language_code', 'en')

    try:
        text = t(lang, 'ideas_menu_title')
        keyboard = _category_keyboard(lang)
        
        if query:
            try:
                await query.message.edit_text(text, reply_markup=keyboard)
            except BadRequest:
                # Message might be too old or identical, send a new one
                await query.message.reply_text(text, reply_markup=keyboard)
        else:
            await message.reply_text(text, reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error showing ideas menu to user {user.id}: {e}")
        from .start import show_main_menu_with_image
        return await show_main_menu_with_image(update, context, user_data)
    
    return SELECTING_IDEAS_CATEGORY


async def ideas_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Route callbacks inside Ideas flow based on callback_data."""
    query = update.callback_query
    if query:
        await query.answer()
    else:
        logger.warning("ideas_router called without callback query")
        return SELECTING_ACTION
        
    data = query.data if query else ''
    user = update.effective_user
    user_data = get_user_data(user.id)
    
    if not user_data:
        logger.error(f"User data not found for user {user.id} in ideas_router")
        from .start import show_main_menu_with_image
        basic_user_data = {'id': user.id, 'language_code': 'en'}
        return await show_main_menu_with_image(update, context, basic_user_data)
    
    lang = user_data.get('language_code', 'en')

    try:
        # Handle return to categories
        if data == 'ideas_menu':
            try:
                await query.message.edit_text(
                    t(lang, 'ideas_menu_title'), 
                    reply_markup=_category_keyboard(lang)
                )
            except BadRequest:
                await query.message.reply_text(
                    t(lang, 'ideas_menu_title'), 
                    reply_markup=_category_keyboard(lang)
                )
            return SELECTING_IDEAS_CATEGORY

        # Handle category selection
        elif data.startswith('ideas_cat:'):
            cat_key = data.split(':', 1)[1]
            if cat_key not in IDEAS_CATEGORIES:
                logger.warning(f"Invalid category key: {cat_key}")
                return await show_ideas_menu(update, context)
                
            title = t(lang, f'ideas_category_{cat_key}')
            text = f"{t(lang, 'ideas_select_template_from')} {title}"
            keyboard = _templates_keyboard(lang, cat_key)
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard)
            except BadRequest:
                await query.message.reply_text(text, reply_markup=keyboard)
            
            # Store current category for navigation
            context.user_data['ideas_current_category'] = cat_key
            return SELECTING_IDEA_TEMPLATE

        # Handle template selection
        elif data.startswith('ideas_tpl:'):
            idea_key = data.split(':', 1)[1]
            tpl = IDEAS_TEMPLATES.get(idea_key)
            if not tpl:
                logger.warning(f"Idea template not found: {idea_key} for user {user.id}")
                return await show_ideas_menu(update, context)
                
            # Fill context presets
            context.user_data[CTX_IDEA_KEY] = idea_key
            context.user_data[CTX_IDEA_TITLE] = t(lang, tpl['title_key'])
            context.user_data[CTX_IDEA_TEXT] = t(lang, tpl['text_key'])
            context.user_data[CTX_IDEA_CONTENT_TYPE] = tpl.get('content_type', 'text')
            context.user_data[CTX_IDEA_RECIPIENT] = tpl.get('recipient_preset', 'self')
            
            delivery_preset = tpl.get('delivery_preset')
            context.user_data[CTX_IDEA_PRESET_DELIVERY] = _compute_delivery(delivery_preset)

            return await _show_idea_preview(update, context, lang)

        # Handle edit text request
        elif data == 'ideas_edit':
            try:
                await query.message.edit_text(t(lang, 'ideas_enter_text'))
            except BadRequest:
                await query.message.reply_text(t(lang, 'ideas_enter_text'))
            return EDITING_IDEA_CONTENT

        # Handle edit date request - FIXED: Show better date selection menu
        elif data == 'ideas_edit_date':
            text = f"{t(lang, 'ideas_enter_date')}\n\n{t(lang, 'date_format_example')}"
            keyboard = _date_edit_keyboard(lang)
            try:
                await query.message.edit_text(text, reply_markup=keyboard)
            except BadRequest:
                await query.message.reply_text(text, reply_markup=keyboard)
            return EDITING_IDEA_DATE

        # Handle quick date selection - NEW FEATURE
        elif data.startswith('ideas_quick_date:'):
            days = int(data.split(':', 1)[1])
            
            # Validate time limits based on subscription
            max_days = PREMIUM_TIME_LIMIT_DAYS if user_data['subscription_status'] == PREMIUM_TIER else FREE_TIME_LIMIT_DAYS
            
            if days > max_days:
                await query.answer(t(lang, 'date_exceeds_limit'), show_alert=True)
                return EDITING_IDEA_DATE
            
            new_delivery_time = datetime.now() + timedelta(days=days)
            context.user_data[CTX_IDEA_PRESET_DELIVERY] = new_delivery_time
            
            await query.answer(t(lang, 'date_updated'))
            return await _show_idea_preview(update, context, lang)

        # Handle back to preview from date editing
        elif data == 'ideas_back_to_preview':
            return await _show_idea_preview(update, context, lang)

        # Handle back to templates
        elif data == 'ideas_back':
            cat_key = context.user_data.get('ideas_current_category')
            if not cat_key:
                return await show_ideas_menu(update, context)
                
            title = t(lang, f'ideas_category_{cat_key}')
            text = f"{t(lang, 'ideas_select_template_from')} {title}"
            keyboard = _templates_keyboard(lang, cat_key)
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard)
            except BadRequest:
                await query.message.reply_text(text, reply_markup=keyboard)
            return SELECTING_IDEA_TEMPLATE

        # Handle use template - transition to create flow
        elif data == 'ideas_use':
            # Prepare context for create flow
            context.user_data['prefill_text'] = context.user_data.get(CTX_IDEA_TEXT)
            context.user_data['prefill_content_type'] = context.user_data.get(CTX_IDEA_CONTENT_TYPE, 'text')
            context.user_data['prefill_recipient'] = context.user_data.get(CTX_IDEA_RECIPIENT, 'self')
            
            # Store delivery datetime as ISO string for create flow
            dt = context.user_data.get(CTX_IDEA_PRESET_DELIVERY)
            if dt:
                context.user_data['prefill_delivery_iso'] = dt.isoformat()
            
            # Clear ideas context
            for key in [CTX_IDEA_KEY, CTX_IDEA_TEXT, CTX_IDEA_TITLE, CTX_IDEA_PRESET_DELIVERY, CTX_IDEA_CONTENT_TYPE, CTX_IDEA_RECIPIENT]:
                context.user_data.pop(key, None)
            context.user_data.pop('ideas_current_category', None)
            
            # Jump to create flow
            from .create_capsule import start_create_capsule
            return await start_create_capsule(update, context)

        # Handle fallback cases
        elif data in ('main_menu', 'cancel'):
            # Clean up ideas context before going to main menu
            for key in [CTX_IDEA_KEY, CTX_IDEA_TEXT, CTX_IDEA_TITLE, CTX_IDEA_PRESET_DELIVERY, CTX_IDEA_CONTENT_TYPE, CTX_IDEA_RECIPIENT]:
                context.user_data.pop(key, None)
            context.user_data.pop('ideas_current_category', None)
            
            from .start import show_main_menu_with_image
            return await show_main_menu_with_image(update, context, user_data)
        
        # Unknown callback data
        else:
            logger.warning(f"Unknown callback data in ideas_router: {data}")
            return await show_ideas_menu(update, context)
    
    except Exception as e:
        logger.error(f"Error in ideas_router for user {user.id}, data: {data}, error: {e}")
        # In case of any error, return to main menu
        from .start import show_main_menu_with_image
        return await show_main_menu_with_image(update, context, user_data)


async def _show_idea_preview(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> int:
    """Show the idea preview with current settings"""
    # Compose preview text
    title = context.user_data.get(CTX_IDEA_TITLE, '')
    text_content = context.user_data.get(CTX_IDEA_TEXT, '')
    dt = context.user_data.get(CTX_IDEA_PRESET_DELIVERY, datetime.now() + timedelta(days=30))
    when = dt.strftime('%d.%m.%Y %H:%M')

    # Retrieve original hints
    idea_key = context.user_data.get(CTX_IDEA_KEY)
    hints_key = IDEAS_TEMPLATES.get(idea_key, {}).get('hints_key')
    hints = t(lang, hints_key) if hints_key else ''

    preview = (
        f"<b>{title}</b>\n\n"
        f"{text_content}\n\n"
        f"<b>{t(lang, 'ideas_preset_time')}</b>: {when}\n\n"
        f"<b>{t(lang, 'ideas_hints')}</b>\n{hints}"
    )
    
    try:
        query = update.callback_query
        if query:
            await query.message.edit_text(
                preview, 
                reply_markup=_preview_keyboard(lang), 
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text(
                preview, 
                reply_markup=_preview_keyboard(lang), 
                parse_mode='HTML'
            )
    except BadRequest:
        # If edit fails, send new message
        await update.effective_message.reply_text(
            preview, 
            reply_markup=_preview_keyboard(lang), 
            parse_mode='HTML'
        )
    
    return EDITING_IDEA_CONTENT


async def ideas_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Capture edited text from user during Ideas flow and return to preview."""
    user = update.effective_user
    user_data = get_user_data(user.id)
    
    if not user_data:
        logger.error(f"User data not found for user {user.id} in ideas_text_input")
        from .start import show_main_menu_with_image
        basic_user_data = {'id': user.id, 'language_code': 'en'}
        return await show_main_menu_with_image(update, context, basic_user_data)
    
    lang = user_data.get('language_code', 'en')

    try:
        text = (update.message.text or '').strip()
        if text:
            context.user_data[CTX_IDEA_TEXT] = text
            
        # Show preview with updated text
        return await _show_idea_preview(update, context, lang)
        
    except Exception as e:
        logger.error(f"Error in ideas_text_input for user {user.id}, error: {e}")
        # Return to main menu in case of error
        from .start import show_main_menu_with_image
        return await show_main_menu_with_image(update, context, user_data)


async def ideas_date_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle custom date input in Ideas flow - COMPLETELY FIXED."""
    user = update.effective_user
    user_data = get_user_data(user.id)
    
    if not user_data:
        logger.error(f"User data not found for user {user.id} in ideas_date_input")
        from .start import show_main_menu_with_image
        basic_user_data = {'id': user.id, 'language_code': 'en'}
        return await show_main_menu_with_image(update, context, basic_user_data)
    
    lang = user_data.get('language_code', 'en')
    message = update.message
    
    if message and message.text:
        date_str = message.text.strip()
        try:
            from datetime import datetime, timezone
            
            # Parse DD.MM.YYYY HH:MM format
            date_pattern = r'^(\d{1,2})\.(\d{1,2})\.(\d{4})\s+(\d{1,2}):(\d{2})$'
            match = re.match(date_pattern, date_str)
            
            if not match:
                await message.reply_text(
                    f"{t(lang, 'invalid_date')}\n\n{t(lang, 'date_format_example')}",
                    reply_markup=_date_edit_keyboard(lang)
                )
                return EDITING_IDEA_DATE
                
            day, month, year, hour, minute = map(int, match.groups())
            
            # Validate date components
            if not (1 <= day <= 31 and 1 <= month <= 12 and year >= datetime.now().year and 0 <= hour <= 23 and 0 <= minute <= 59):
                await message.reply_text(
                    f"{t(lang, 'invalid_date')}\n\n{t(lang, 'date_format_example')}",
                    reply_markup=_date_edit_keyboard(lang)
                )
                return EDITING_IDEA_DATE
            
            try:
                new_delivery_time = datetime(year, month, day, hour, minute)
            except ValueError:
                await message.reply_text(
                    f"{t(lang, 'invalid_date')}\n\n{t(lang, 'date_format_example')}",
                    reply_markup=_date_edit_keyboard(lang)
                )
                return EDITING_IDEA_DATE
            
            # Validate future date
            if new_delivery_time <= datetime.now():
                await message.reply_text(
                    f"{t(lang, 'date_must_be_future')}\n\n{t(lang, 'date_format_example')}",
                    reply_markup=_date_edit_keyboard(lang)
                )
                return EDITING_IDEA_DATE
            
            # Check subscription limits
            max_days = PREMIUM_TIME_LIMIT_DAYS if user_data.get('subscription_status') == PREMIUM_TIER else FREE_TIME_LIMIT_DAYS
            days_diff = (new_delivery_time - datetime.now()).days
            
            if days_diff > max_days:
                limit_text = t(lang, 'date_too_far', days=FREE_TIME_LIMIT_DAYS, years=PREMIUM_TIME_LIMIT_DAYS//365)
                await message.reply_text(
                    f"{limit_text}\n\n{t(lang, 'date_format_example')}",
                    reply_markup=_date_edit_keyboard(lang)
                )
                return EDITING_IDEA_DATE
                
            # Update context with new delivery time
            context.user_data[CTX_IDEA_PRESET_DELIVERY] = new_delivery_time
            
            # Show success message and return to preview
            await message.reply_text(t(lang, 'date_updated_success'))
            
            # Show preview with updated date
            return await _show_idea_preview(update, context, lang)
            
        except Exception as e:
            logger.error(f"Error parsing date in ideas flow for user {user.id}: {e}")
            await message.reply_text(
                f"{t(lang, 'invalid_date')}\n\n{t(lang, 'date_format_example')}",
                reply_markup=_date_edit_keyboard(lang)
            )
            return EDITING_IDEA_DATE
    
    # If not a valid text message, show help again
    await message.reply_text(
        f"{t(lang, 'ideas_enter_date')}\n\n{t(lang, 'date_format_example')}",
        reply_markup=_date_edit_keyboard(lang)
    )
    return EDITING_IDEA_DATE