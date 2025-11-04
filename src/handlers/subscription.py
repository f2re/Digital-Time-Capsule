# src/handlers/subscription.py

import uuid
from datetime import datetime, timedelta, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import ContextTypes
from ..database import (get_user_data, users, payments, transactions, engine,
                        add_capsules_to_balance, record_capsule_transaction)
from ..translations import t
from ..image_menu import send_menu_with_image
from ..config import (
    MANAGING_SUBSCRIPTION, SELECTING_ACTION, PREMIUM_TIER, FREE_TIER,
    PREMIUM_STORAGE_LIMIT, FREE_STORAGE_LIMIT,
    CAPSULE_PRICE_STARS, CAPSULE_PRICE_RUB, CAPSULE_PRICE_USD,
    CAPSULE_PACKS,
    PREMIUM_MONTH_STARS, PREMIUM_MONTH_RUB, PREMIUM_MONTH_USD, PREMIUM_MONTH_CAPSULES,
    PREMIUM_YEAR_STARS, PREMIUM_YEAR_RUB, PREMIUM_YEAR_USD, PREMIUM_YEAR_CAPSULES,
    PAYMENT_PROVIDER_TOKEN,
    SELECTING_PAYMENT_METHOD, SELECTING_CURRENCY,
    logger
)
from sqlalchemy import insert, update


async def show_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show subscription information with payment options using subscription.png"""
    query = update.callback_query
    if query:
        await query.answer()

    user = update.effective_user
    user_data = get_user_data(user.id)

    if not user_data:
        logger.error(f"User data not found for {user.id}")
        lang = 'en'

        # Use send_menu_with_image even for error
        await send_menu_with_image(
            update=update,
            context=context,
            image_key='subscription',
            caption=t(lang, 'user_not_found_payment'),
            keyboard=InlineKeyboardMarkup([[
                InlineKeyboardButton(t(lang, 'back'), callback_data='main_menu')
            ]]),
            parse_mode='HTML'
        )
        return SELECTING_ACTION

    lang = user_data['language_code']
    is_premium = user_data['subscription_status'] == PREMIUM_TIER
    capsule_balance = user_data.get('capsule_balance', 0)

    # Build subscription info
    if is_premium:
        used_mb = user_data['total_storage_used'] / 1024 / 1024
        total_mb = PREMIUM_STORAGE_LIMIT / 1024 / 1024
        expires = user_data['subscription_expires'].strftime("%d.%m.%Y") if user_data['subscription_expires'] else "Never"
        subscription_type_display = "💎 PREMIUM"

        details = t(lang, "premium_subscription_details",
                   capsules=capsule_balance,
                   used=f"{used_mb:.1f} MB",
                   total=f"{total_mb:.0f} MB",
                   expires=expires)
    else:
        used_mb = user_data['total_storage_used'] / 1024 / 1024
        total_mb = FREE_STORAGE_LIMIT / 1024 / 1024
        subscription_type_display = "🆓 FREE"

        details = t(lang, "free_subscription_details",
                   capsules=capsule_balance,
                   used=f"{used_mb:.1f} MB",
                   total=f"{total_mb:.0f} MB")

    info_text = t(lang, "subscription_info",
                  tier=subscription_type_display,
                  details=details)

    # Add starter bonus info
    if user_data['capsule_balance'] <= 3 and user_data.get('capsule_count', 0) == 0:
        info_text += "\n\n" + t(lang, "starter_bonus_info", count=user_data['capsule_balance'])

    # Build keyboard
    keyboard = []

    # Single capsule
    if lang == 'ru':
        button_text = t(lang, "buy_single_capsule",
                       stars=CAPSULE_PRICE_STARS,
                       rub_price=CAPSULE_PRICE_RUB)
    else:
        button_text = t(lang, "buy_single_capsule",
                       stars=CAPSULE_PRICE_STARS,
                       usd_price=CAPSULE_PRICE_USD)

    keyboard.append([InlineKeyboardButton(
        button_text,
        callback_data="select_subscription:single"
    )])

    # Capsule packs (2 per row)
    pack_row = []
    for pack_key, pack_data in CAPSULE_PACKS.items():
        if len(pack_row) == 2:
            keyboard.append(pack_row)
            pack_row = []

        if lang == 'ru':
            button_text = t(lang, f"buy_{pack_key}",
                           stars=pack_data['price_stars'],
                           discount=pack_data['discount'],
                           rub_price=pack_data['price_rub'])
        else:
            button_text = t(lang, f"buy_{pack_key}",
                           stars=pack_data['price_stars'],
                           discount=pack_data['discount'],
                           usd_price=pack_data['price_usd'])

        pack_row.append(InlineKeyboardButton(
            button_text,
            callback_data=f"select_subscription:{pack_key}"
        ))

    if pack_row:
        keyboard.append(pack_row)

    # Premium subscriptions
    if not is_premium:
        if lang == 'ru':
            month_button_text = t(lang, "buy_premium_month",
                                 stars=PREMIUM_MONTH_STARS,
                                 rub_price=PREMIUM_MONTH_RUB,
                                 capsules=PREMIUM_MONTH_CAPSULES)
            year_button_text = t(lang, "buy_premium_year",
                                stars=PREMIUM_YEAR_STARS,
                                rub_price=PREMIUM_YEAR_RUB,
                                capsules=PREMIUM_YEAR_CAPSULES)
        else:
            month_button_text = t(lang, "buy_premium_month",
                                 stars=PREMIUM_MONTH_STARS,
                                 usd_price=PREMIUM_MONTH_USD,
                                 capsules=PREMIUM_MONTH_CAPSULES)
            year_button_text = t(lang, "buy_premium_year",
                                stars=PREMIUM_YEAR_STARS,
                                usd_price=PREMIUM_YEAR_USD,
                                capsules=PREMIUM_YEAR_CAPSULES)

        keyboard.append([InlineKeyboardButton(
            month_button_text,
            callback_data="select_subscription:premium_month"
        )])

        keyboard.append([InlineKeyboardButton(
            year_button_text,
            callback_data="select_subscription:premium_year"
        )])

    keyboard.append([InlineKeyboardButton(t(lang, "back"), callback_data="main_menu")])

    # ⭐ Use send_menu_with_image with subscription.png
    await send_menu_with_image(
        update=update,
        context=context,
        image_key='subscription',
        caption=info_text,
        keyboard=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

    return MANAGING_SUBSCRIPTION


async def select_payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """STEP 2: User selects payment method (Stars or Card) with subscription.png"""
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    user_data = get_user_data(user.id)

    if not user_data:
        await send_menu_with_image(
            update=update,
            context=context,
            image_key='subscription',
            caption="Error: User not found.",
            keyboard=InlineKeyboardMarkup([[
                InlineKeyboardButton('Back', callback_data='main_menu')
            ]]),
            parse_mode='HTML'
        )
        return SELECTING_ACTION

    lang = user_data['language_code']

    # Parse and store subscription type
    subscription_type = query.data.split(":")[1]
    context.user_data['selected_subscription'] = subscription_type

    # Build payment method keyboard
    keyboard = [
        [InlineKeyboardButton(
            t(lang, "payment_method_stars"),
            callback_data="payment_method:stars"
        )],
        [InlineKeyboardButton(
            t(lang, "payment_method_card"),
            callback_data="payment_method:card"
        )],
        [InlineKeyboardButton(t(lang, "back"), callback_data="subscription")]
    ]

    # ⭐ Use send_menu_with_image with subscription.png
    await send_menu_with_image(
        update=update,
        context=context,
        image_key='subscription',
        caption=t(lang, "select_payment_method_text"),
        keyboard=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

    return SELECTING_PAYMENT_METHOD


async def select_currency(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """STEP 3: User selects currency (RUB or USD) for card payment with subscription.png"""
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    user_data = get_user_data(user.id)

    if not user_data:
        await send_menu_with_image(
            update=update,
            context=context,
            image_key='subscription',
            caption="Error: User not found.",
            keyboard=InlineKeyboardMarkup([[
                InlineKeyboardButton('Back', callback_data='main_menu')
            ]]),
            parse_mode='HTML'
        )
        return SELECTING_ACTION

    lang = user_data['language_code']
    payment_method = query.data.split(":")[1]

    # If Stars, skip currency selection
    if payment_method == "stars":
        context.user_data['payment_method'] = 'stars'
        context.user_data['payment_currency'] = 'XTR'
        return await process_payment(update, context)

    # For card, show currency selection
    context.user_data['payment_method'] = 'card'

    keyboard = [
        [InlineKeyboardButton(
            t(lang, "currency_rub"),
            callback_data="currency:RUB"
        )],
        [InlineKeyboardButton(
            t(lang, "currency_usd"),
            callback_data="currency:USD"
        )],
        [InlineKeyboardButton(t(lang, "back"), callback_data="subscription")]
    ]

    # ⭐ Use send_menu_with_image with subscription.png
    await send_menu_with_image(
        update=update,
        context=context,
        image_key='subscription',
        caption=t(lang, "select_currency_text"),
        keyboard=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

    return SELECTING_CURRENCY


async def process_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """STEP 4: Process payment with selected method and currency"""
    query = update.callback_query

    # Handle currency selection
    if query and query.data.startswith("currency:"):
        await query.answer()
        currency = query.data.split(":")[1]
        context.user_data['payment_currency'] = currency

    user = update.effective_user
    user_data = get_user_data(user.id)

    if not user_data:
        if query:
            await send_menu_with_image(
                update=update,
                context=context,
                image_key='subscription',
                caption="Error: User not found.",
                keyboard=InlineKeyboardMarkup([[
                    InlineKeyboardButton('Back', callback_data='main_menu')
                ]]),
                parse_mode='HTML'
            )
        return SELECTING_ACTION

    lang = user_data['language_code']

    # Retrieve stored data
    subscription_type = context.user_data.get('selected_subscription')
    payment_method = context.user_data.get('payment_method')
    currency = context.user_data.get('payment_currency')

    if not all([subscription_type, payment_method, currency]):
        await send_menu_with_image(
            update=update,
            context=context,
            image_key='subscription',
            caption=t(lang, 'error_occurred'),
            keyboard=InlineKeyboardMarkup([[
                InlineKeyboardButton(t(lang, 'back'), callback_data='subscription')
            ]]),
            parse_mode='HTML'
        )
        return MANAGING_SUBSCRIPTION

    # Calculate amount based on subscription and currency
    capsules_to_add = 0

    if subscription_type == 'single':
        if currency == 'XTR':
            stars_amount = CAPSULE_PRICE_STARS
            price_amount = CAPSULE_PRICE_RUB if lang == 'ru' else CAPSULE_PRICE_USD
        else:
            stars_amount = CAPSULE_PRICE_STARS
            price_amount = CAPSULE_PRICE_RUB if currency == 'RUB' else CAPSULE_PRICE_USD

        title = t(lang, "invoice_title_single", stars=stars_amount)
        description = t(lang, "invoice_desc_single", price=price_amount)
        capsules_to_add = 1
        amount = CAPSULE_PRICE_STARS if currency == 'XTR' else int(price_amount * 100)

    elif subscription_type in CAPSULE_PACKS:
        pack_data = CAPSULE_PACKS[subscription_type]

        if currency == 'XTR':
            stars_amount = pack_data['price_stars']
            price_amount = pack_data['price_rub'] if lang == 'ru' else pack_data['price_usd']
        else:
            stars_amount = pack_data['price_stars']
            price_amount = pack_data['price_rub'] if currency == 'RUB' else pack_data['price_usd']

        title = t(lang, "invoice_title_pack", count=pack_data['count'], stars=stars_amount)
        description = t(lang, "invoice_desc_pack", count=pack_data['count'], discount=pack_data['discount'], price=price_amount)
        capsules_to_add = pack_data['count']

        if currency == 'XTR':
            amount = pack_data['price_stars']
        else:
            amount = int(price_amount * 100)

    elif subscription_type == 'premium_month':
        if currency == 'XTR':
            stars_amount = PREMIUM_MONTH_STARS
            price_amount = PREMIUM_MONTH_RUB if lang == 'ru' else PREMIUM_MONTH_USD
        else:
            stars_amount = PREMIUM_MONTH_STARS
            price_amount = PREMIUM_MONTH_RUB if currency == 'RUB' else PREMIUM_MONTH_USD

        title = t(lang, "invoice_title_premium_month", stars=stars_amount)
        description = t(lang, "invoice_desc_premium_month", capsules=PREMIUM_MONTH_CAPSULES, price=price_amount)
        capsules_to_add = PREMIUM_MONTH_CAPSULES

        if currency == 'XTR':
            amount = PREMIUM_MONTH_STARS
        else:
            amount = int(price_amount * 100)

    elif subscription_type == 'premium_year':
        if currency == 'XTR':
            stars_amount = PREMIUM_YEAR_STARS
            price_amount = PREMIUM_YEAR_RUB if lang == 'ru' else PREMIUM_YEAR_USD
        else:
            stars_amount = PREMIUM_YEAR_STARS
            price_amount = PREMIUM_YEAR_RUB if currency == 'RUB' else PREMIUM_YEAR_USD

        title = t(lang, "invoice_title_premium_year", stars=stars_amount)
        description = t(lang, "invoice_desc_premium_year", capsules=PREMIUM_YEAR_CAPSULES, price=price_amount)
        capsules_to_add = PREMIUM_YEAR_CAPSULES

        if currency == 'XTR':
            amount = PREMIUM_YEAR_STARS
        else:
            amount = int(price_amount * 100)

    else:
        await send_menu_with_image(
            update=update,
            context=context,
            image_key='subscription',
            caption=t(lang, 'error_occurred'),
            keyboard=InlineKeyboardMarkup([[
                InlineKeyboardButton(t(lang, 'back'), callback_data='subscription')
            ]]),
            parse_mode='HTML'
        )
        return MANAGING_SUBSCRIPTION

    # Store for validation
    context.user_data['pending_payment'] = {
        'type': subscription_type,
        'amount': amount,
        'capsules': capsules_to_add,
        'currency': currency
    }

    # Create invoice
    prices = [LabeledPrice(label=title, amount=amount)]

    try:
        provider_token = "" if currency == 'XTR' else PAYMENT_PROVIDER_TOKEN

        # Format amount for button display
        if currency == 'XTR':
            amount_display = f"{amount} ⭐"
        else:
            symbol = "₽" if currency == 'RUB' else "$"
            amount_display = f"{symbol}{amount/100:.2f}"

        await context.bot.send_invoice(
            chat_id=query.message.chat_id if query else user.id,
            title=title,
            description=description,
            payload=f"{user.id}:{subscription_type}:{uuid.uuid4()}",
            provider_token=provider_token,
            currency=currency,
            prices=prices,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    text=t(lang, "pay_button", amount=amount_display),
                    pay=True
                )
            ]])
        )

        if query:
            try:
                await query.message.delete()
            except:
                pass

        logger.info(f"Invoice sent: user {user.id}, {subscription_type}, {amount} {currency}")

    except Exception as e:
        logger.error(f"Error sending invoice: {e}")

        # Show error with subscription.png
        await send_menu_with_image(
            update=update,
            context=context,
            image_key='subscription',
            caption=t(lang, 'payment_error'),
            keyboard=InlineKeyboardMarkup([[
                InlineKeyboardButton(t(lang, 'back'), callback_data='subscription')
            ]]),
            parse_mode='HTML'
        )

    return MANAGING_SUBSCRIPTION


async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Validate payment before processing"""
    query = update.pre_checkout_query
    user = update.effective_user

    try:
        user_data = get_user_data(user.id)

        if not user_data:
            await query.answer(ok=False, error_message="User not found. Please /start the bot.")
            return

        payload_parts = query.invoice_payload.split(':')
        if len(payload_parts) < 2:
            await query.answer(ok=False, error_message="Invalid payment.")
            return

        payment_type = payload_parts[1]
        currency = query.currency

        # Calculate expected amount
        if payment_type == 'single':
            expected = CAPSULE_PRICE_STARS if currency == 'XTR' else int((CAPSULE_PRICE_RUB if currency == 'RUB' else CAPSULE_PRICE_USD) * 100)
        elif payment_type in CAPSULE_PACKS:
            pack = CAPSULE_PACKS[payment_type]
            expected = pack['price_stars'] if currency == 'XTR' else int((pack['price_rub'] if currency == 'RUB' else pack['price_usd']) * 100)
        elif payment_type == 'premium_month':
            expected = PREMIUM_MONTH_STARS if currency == 'XTR' else int((PREMIUM_MONTH_RUB if currency == 'RUB' else PREMIUM_MONTH_USD) * 100)
        elif payment_type == 'premium_year':
            expected = PREMIUM_YEAR_STARS if currency == 'XTR' else int((PREMIUM_YEAR_RUB if currency == 'RUB' else PREMIUM_YEAR_USD) * 100)
        else:
            await query.answer(ok=False, error_message="Unknown payment type.")
            return

        if query.total_amount != expected:
            await query.answer(ok=False, error_message="Amount mismatch.")
            return

        await query.answer(ok=True)
        logger.info(f"Pre-checkout OK: user {user.id}, {payment_type}, {currency}")

    except Exception as e:
        logger.error(f"Pre-checkout error: {e}")
        await query.answer(ok=False, error_message="Error occurred.")


async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle successful payment"""
    message = update.message
    user = update.effective_user
    payment = message.successful_payment

    try:
        user_data = get_user_data(user.id)

        if not user_data:
            logger.error(f"User not found after payment: {user.id}")
            await message.reply_text("Error: User not found. Contact support.")
            return

        lang = user_data['language_code']
        payload_parts = payment.invoice_payload.split(':')
        payment_type = payload_parts[1] if len(payload_parts) > 1 else 'single'

        # Calculate capsules and subscription changes
        capsules_to_add = 0
        subscription_change = None

        if payment_type == 'single':
            capsules_to_add = 1
        elif payment_type in CAPSULE_PACKS:
            capsules_to_add = CAPSULE_PACKS[payment_type]['count']
        elif payment_type == 'premium_month':
            capsules_to_add = PREMIUM_MONTH_CAPSULES
            subscription_change = {
                'status': PREMIUM_TIER,
                'expires': datetime.now(timezone.utc) + timedelta(days=30)
            }
        elif payment_type == 'premium_year':
            capsules_to_add = PREMIUM_YEAR_CAPSULES
            subscription_change = {
                'status': PREMIUM_TIER,
                'expires': datetime.now(timezone.utc) + timedelta(days=365)
            }

        # Update database
        from sqlalchemy import update as sqlalchemy_update
        
        if capsules_to_add > 0:
            add_capsules_to_balance(user_data['id'], capsules_to_add)

        if subscription_change:
            from ..database import update_user_subscription
            update_user_subscription(
                user_data['id'],
                subscription_change['status'],
                subscription_change['expires']
            )

        charge_id = getattr(payment, 'telegram_payment_charge_id', None) or getattr(payment, 'provider_payment_charge_id', 'unknown')

        record_capsule_transaction(
            user_data['id'],
            payment_type,
            payment.total_amount,
            capsules_to_add,
            charge_id
        )

        success_msg = t(lang, "payment_success", capsules=capsules_to_add, type=payment_type)

        # Use HTML parse mode to avoid markdown parsing issues with charge_id
        await message.reply_text(
            success_msg + f"\n\n💳 {t(lang, 'transaction_id')}: <code>{charge_id}</code>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(t(lang, 'create_capsule'), callback_data='create'),
                InlineKeyboardButton(t(lang, 'main_menu'), callback_data='main_menu')
            ]])
        )

        logger.info(f"Payment success: user {user.id}, {payment_type}, +{capsules_to_add} capsules")

    except Exception as e:
        logger.error(f"Payment processing error: {e}")
        await message.reply_text(t(lang, "payment_error_contact_support"))


async def paysupport_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /paysupport command"""
    user = update.effective_user
    user_data = get_user_data(user.id)
    lang = user_data['language_code'] if user_data else 'en'

    await update.message.reply_text(
        t(lang, "paysupport_text"),
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(t(lang, 'main_menu'), callback_data='main_menu')
        ]])
    )


async def refund_payment(telegram_payment_charge_id: str, user_id: int, bot) -> bool:
    """Refund Stars payment"""
    try:
        await bot.refund_star_payment(
            user_id=user_id,
            telegram_payment_charge_id=telegram_payment_charge_id
        )
        logger.info(f"Refund successful: {telegram_payment_charge_id}")
        return True
    except Exception as e:
        logger.error(f"Refund failed: {e}")
        return False
