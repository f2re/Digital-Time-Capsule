# src/handlers/ideas.py
"""Ideas feature handlers: categories -> templates -> preview/edit -> handoff to create flow.

This module follows the project's handler patterns and uses translations via t().
"""
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from ..translations import t
from ..config import (
    SELECTING_IDEAS_CATEGORY,
    SELECTING_IDEA_TEMPLATE,
    EDITING_IDEA_CONTENT,
    SELECTING_ACTION,
)
from ..ideas_templates import IDEAS_CATEGORIES, IDEAS_TEMPLATES, dt_in_days, next_new_year
from ..database import get_user_data

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
        title = t(lang, f"{IDEAS_TEMPLATES[idea_key]['title_key']}")
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
        [InlineKeyboardButton(t(lang, 'back'), callback_data='ideas_back')],
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
    lang = user_data.get('language_code', 'en') if user_data else 'en'

    text = t(lang, 'ideas_menu_title')
    await message.reply_text(text, reply_markup=_category_keyboard(lang))
    return SELECTING_IDEAS_CATEGORY


async def ideas_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Route callbacks inside Ideas flow based on callback_data."""
    query = update.callback_query
    if query:
        await query.answer()
    data = query.data if query else ''

    user = update.effective_user
    user_data = get_user_data(user.id)
    lang = user_data.get('language_code', 'en') if user_data else 'en'

    if data == 'ideas_menu':
        # Back to categories
        await query.message.edit_text(t(lang, 'ideas_menu_title'), reply_markup=_category_keyboard(lang))
        return SELECTING_IDEAS_CATEGORY

    if data.startswith('ideas_cat:'):
        cat_key = data.split(':', 1)[1]
        # Render templates list for category
        title = t(lang, f'ideas_category_{cat_key}')
        await query.message.edit_text(
            f"{t(lang, 'ideas_select_template_from')} {title}",
            reply_markup=_templates_keyboard(lang, cat_key)
        )
        # Store current category if needed later
        context.user_data['ideas_current_category'] = cat_key
        return SELECTING_IDEA_TEMPLATE

    if data.startswith('ideas_tpl:'):
        idea_key = data.split(':', 1)[1]
        tpl = IDEAS_TEMPLATES.get(idea_key)
        if not tpl:
            return SELECTING_IDEA_TEMPLATE
        # Fill context presets
        context.user_data[CTX_IDEA_KEY] = idea_key
        context.user_data[CTX_IDEA_TITLE] = t(lang, tpl['title_key'])
        context.user_data[CTX_IDEA_TEXT] = t(lang, tpl['text_key'])
        context.user_data[CTX_IDEA_CONTENT_TYPE] = tpl.get('content_type', 'text')
        context.user_data[CTX_IDEA_RECIPIENT] = tpl.get('recipient_preset', 'self')
        delivery_preset = tpl.get('delivery_preset')
        context.user_data[CTX_IDEA_PRESET_DELIVERY] = _compute_delivery(delivery_preset)

        # Compose preview text
        hints = t(lang, tpl['hints_key'])
        dt = context.user_data[CTX_IDEA_PRESET_DELIVERY]
        when = dt.strftime('%d.%m.%Y %H:%M')
        preview = (
            f"{context.user_data[CTX_IDEA_TITLE]}\n\n"
            f"{context.user_data[CTX_IDEA_TEXT]}\n\n"
            f"{t(lang, 'ideas_preset_time')}: {when}\n"
            f"{t(lang, 'ideas_hints')}\n{hints}"
        )
        await query.message.edit_text(preview, reply_markup=_preview_keyboard(lang), parse_mode='HTML')
        return EDITING_IDEA_CONTENT

    if data == 'ideas_edit':
        await query.message.edit_text(t(lang, 'ideas_enter_text'))
        return EDITING_IDEA_CONTENT

    if data == 'ideas_back':
        # Return to templates in current category
        cat_key = context.user_data.get('ideas_current_category')
        if not cat_key:
            await query.message.edit_text(t(lang, 'ideas_menu_title'), reply_markup=_category_keyboard(lang))
            return SELECTING_IDEAS_CATEGORY
        await query.message.edit_text(
            f"{t(lang, 'ideas_select_template_from')} {t(lang, f'ideas_category_{cat_key}')}",
            reply_markup=_templates_keyboard(lang, cat_key)
        )
        return SELECTING_IDEA_TEMPLATE

    if data == 'ideas_use':
        # Hand off to standard create flow with presets in context.user_data
        # We will set flags expected by create flow to prefill
        context.user_data['prefill_text'] = context.user_data.get(CTX_IDEA_TEXT)
        context.user_data['prefill_content_type'] = context.user_data.get(CTX_IDEA_CONTENT_TYPE, 'text')
        context.user_data['prefill_recipient'] = context.user_data.get(CTX_IDEA_RECIPIENT, 'self')
        # Store delivery dt as ISO string if later needed in select_time
        dt = context.user_data.get(CTX_IDEA_PRESET_DELIVERY)
        if dt:
            context.user_data['prefill_delivery_iso'] = dt.isoformat()
        # Jump to existing create flow entry point
        from .create_capsule import start_create_capsule
        return await start_create_capsule(update, context)

    return SELECTING_ACTION


async def ideas_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Capture edited text from user during Ideas flow and return to preview."""
    user = update.effective_user
    user_data = get_user_data(user.id)
    lang = user_data.get('language_code', 'en') if user_data else 'en'

    text = (update.message.text or '').strip()
    if text:
        context.user_data[CTX_IDEA_TEXT] = text
    # Re-render preview
    title = context.user_data.get(CTX_IDEA_TITLE, '')
    dt = context.user_data.get(CTX_IDEA_PRESET_DELIVERY, datetime.now() + timedelta(days=30))
    when = dt.strftime('%d.%m.%Y %H:%M')

    # Retrieve original hints
    idea_key = context.user_data.get(CTX_IDEA_KEY)
    hints_key = IDEAS_TEMPLATES.get(idea_key, {}).get('hints_key')
    hints = t(lang, hints_key) if hints_key else ''

    preview = (
        f"{title}\n\n{context.user_data.get(CTX_IDEA_TEXT, '')}\n\n"
        f"{t(lang, 'ideas_preset_time')}: {when}\n"
        f"{t(lang, 'ideas_hints')}\n{hints}"
    )
    await update.message.reply_text(preview, reply_markup=_preview_keyboard(lang), parse_mode='HTML')
    return EDITING_IDEA_CONTENT
