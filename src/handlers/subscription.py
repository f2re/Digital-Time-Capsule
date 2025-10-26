# src/handlers/subscription.py

import uuid
from datetime import datetime, timedelta, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import ContextTypes
from ..database import (get_user_data, users, payments, transactions, engine,
                        add_capsules_to_balance, record_capsule_transaction)
from ..translations import t
from ..config import (
    MANAGING_SUBSCRIPTION, SELECTING_ACTION, PREMIUM_TIER, FREE_TIER,
    PREMIUM_STORAGE_LIMIT, FREE_STORAGE_LIMIT,
    CAPSULE_PRICE_STARS, CAPSULE_PRICE_RUBLES,
    CAPSULE_PACKS,
    PREMIUM_MONTH_STARS, PREMIUM_MONTH_RUBLES, PREMIUM_MONTH_CAPSULES,
    PREMIUM_YEAR_STARS, PREMIUM_YEAR_RUBLES, PREMIUM_YEAR_CAPSULES,
    logger
)
from sqlalchemy import insert, update

async def show_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show subscription information with new payment options"""
    query = update.callback_query
    if query:
        await query.answer()

    user = update.effective_user
    userdata = get_user_data(user.id)

    if not userdata:
        logger.error(f"User data not found for {user.id}")
        return SELECTING_ACTION

    lang = userdata['language_code']
    is_premium = userdata['subscription_status'] == PREMIUM_TIER
    capsule_balance = userdata.get('capsule_balance', 0)

    # Build subscription info
    if is_premium:
        used_mb = userdata['total_storage_used'] / 1024 / 1024
        total_mb = PREMIUM_STORAGE_LIMIT / 1024 / 1024
        expires = userdata['subscription_expires'].strftime("%d.%m.%Y") if userdata['subscription_expires'] else "Never"
        details = t(lang, "premium_subscription_details",
                   capsules=capsule_balance,
                   used=f"{used_mb:.1f} MB",
                   total=f"{total_mb:.0f} MB",
                   expires=expires)
    else:
        used_mb = userdata['total_storage_used'] / 1024 / 1024
        total_mb = FREE_STORAGE_LIMIT / 1024 / 1024
        details = t(lang, "free_subscription_details",
                   capsules=capsule_balance,
                   used=f"{used_mb:.1f} MB",
                   total=f"{total_mb:.0f} MB")

    info_text = t(lang, "subscription_info",
                 tier="PREMIUM ⭐" if is_premium else "FREE",
                 details=details)

    # Build keyboard
    keyboard = []

    # Single capsule purchase
    keyboard.append([InlineKeyboardButton(
        t(lang, "buy_single_capsule", stars=CAPSULE_PRICE_STARS),
        callback_data="buy_capsule_single"
    )])

    # Capsule packs
    pack_row = []
    for pack_key, pack_data in CAPSULE_PACKS.items():
        if len(pack_row) == 2:
            keyboard.append(pack_row)
            pack_row = []
        pack_row.append(InlineKeyboardButton(
            t(lang, f"buy_{pack_key}", count=pack_data['count'],
              stars=pack_data['price_stars'], discount=pack_data['discount']),
            callback_data=f"buy_capsule_{pack_key}"
        ))
    if pack_row:
        keyboard.append(pack_row)

    # Premium subscriptions
    if not is_premium:
        keyboard.append([InlineKeyboardButton(
            t(lang, "buy_premium_month", stars=PREMIUM_MONTH_STARS,
              capsules=PREMIUM_MONTH_CAPSULES),
            callback_data="buy_premium_month"
        )])
        keyboard.append([InlineKeyboardButton(
            t(lang, "buy_premium_year", stars=PREMIUM_YEAR_STARS,
              capsules=PREMIUM_YEAR_CAPSULES),
            callback_data="buy_premium_year"
        )])

    keyboard.append([InlineKeyboardButton(t(lang, "back"), callback_data="main_menu")])

    # Send message
    if query and query.message:
        try:
            await query.edit_message_text(
                info_text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except:
            try:
                await query.edit_message_caption(
                    caption=info_text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except:
                await query.message.reply_text(
                    info_text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
    else:
        message = update.message or update.effective_message
        if message:
            await message.reply_text(
                info_text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    return MANAGING_SUBSCRIPTION

async def handle_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle payment button clicks and send invoice"""
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    user_data = get_user_data(user.id)

    if not user_data:
        await query.edit_message_text("Error: User not found. Please /start again.")
        return SELECTING_ACTION

    lang = user_data['language_code']
    payment_type = query.data  # e.g., 'buy_capsule_single', 'buy_capsule_pack_3', etc.

    # Determine payment details
    if payment_type == 'buy_capsule_single':
        title = t(lang, "invoice_title_single")
        description = t(lang, "invoice_desc_single")
        amount = CAPSULE_PRICE_STARS
        payload_type = 'single'
        capsules_to_add = 1

    elif payment_type.startswith('buy_capsule_pack_'):
        pack_key = payment_type.replace('buy_capsule_', '')
        pack_data = CAPSULE_PACKS.get(pack_key)

        if not pack_data:
            await query.edit_message_text(t(lang, 'error_occurred'))
            return MANAGING_SUBSCRIPTION

        title = t(lang, "invoice_title_pack", count=pack_data['count'])
        description = t(lang, "invoice_desc_pack",
                       count=pack_data['count'],
                       discount=pack_data['discount'])
        amount = pack_data['price_stars']
        payload_type = pack_key
        capsules_to_add = pack_data['count']

    elif payment_type == 'buy_premium_month':
        title = t(lang, "invoice_title_premium_month")
        description = t(lang, "invoice_desc_premium_month",
                       capsules=PREMIUM_MONTH_CAPSULES)
        amount = PREMIUM_MONTH_STARS
        payload_type = 'premium_month'
        capsules_to_add = PREMIUM_MONTH_CAPSULES

    elif payment_type == 'buy_premium_year':
        title = t(lang, "invoice_title_premium_year")
        description = t(lang, "invoice_desc_premium_year",
                       capsules=PREMIUM_YEAR_CAPSULES)
        amount = PREMIUM_YEAR_STARS
        payload_type = 'premium_year'
        capsules_to_add = PREMIUM_YEAR_CAPSULES

    else:
        await query.edit_message_text(
            t(lang, 'error_occurred'),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(t(lang, 'back'), callback_data='subscription')
            ]])
        )
        return MANAGING_SUBSCRIPTION

    # Store payment info in context
    context.user_data['pending_payment'] = {
        'type': payload_type,
        'amount': amount,
        'capsules': capsules_to_add
    }

    # Create invoice with Stars (XTR currency)
    prices = [LabeledPrice(label="XTR", amount=amount)]

    try:
        await context.bot.send_invoice(
            chat_id=query.message.chat_id,
            title=title,
            description=description,
            payload=f"{user.id}_{payload_type}_{uuid.uuid4()}",
            provider_token="",  # Empty for Stars
            currency="XTR",
            prices=prices,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(text=t(lang, "pay_button", stars=amount), pay=True)
            ]])
        )

        # Delete previous message
        try:
            await query.message.delete()
        except:
            pass

        logger.info(f"Invoice sent to user {user.id} for {payload_type}: {amount} stars")

    except Exception as e:
        logger.error(f"Error sending invoice: {e}")
        await query.edit_message_text(
            t(lang, 'error_occurred'),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(t(lang, 'back'), callback_data='subscription')
            ]])
        )

    return MANAGING_SUBSCRIPTION

async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Answer pre-checkout query"""
    query = update.pre_checkout_query
    user = update.effective_user

    try:
        user_data = get_user_data(user.id)
        if not user_data:
            await query.answer(
                ok=False,
                error_message="User not found. Please start the bot with /start first."
            )
            return

        # Parse payload
        payload_parts = query.invoice_payload.split('_')
        if len(payload_parts) < 2:
            await query.answer(
                ok=False,
                error_message="Invalid payment request."
            )
            return

        payment_type = payload_parts[1]

        # Verify amount based on payment type
        if payment_type == 'single':
            expected_amount = CAPSULE_PRICE_STARS
        elif payment_type in CAPSULE_PACKS:
            expected_amount = CAPSULE_PACKS[payment_type]['price_stars']
        elif payment_type == 'premium_month':
            expected_amount = PREMIUM_MONTH_STARS
        elif payment_type == 'premium_year':
            expected_amount = PREMIUM_YEAR_STARS
        else:
            await query.answer(
                ok=False,
                error_message="Unknown payment type."
            )
            return

        if query.total_amount != expected_amount:
            await query.answer(
                ok=False,
                error_message=f"Payment amount mismatch."
            )
            return

        await query.answer(ok=True)
        logger.info(f"Pre-checkout approved for user {user.id}, type: {payment_type}")

    except Exception as e:
        logger.error(f"Error in pre-checkout: {e}")
        await query.answer(
            ok=False,
            error_message="An error occurred. Please try again."
        )

async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle successful payment"""
    message = update.message
    user = update.effective_user
    payment = message.successful_payment

    try:
        user_data = get_user_data(user.id)
        if not user_data:
            logger.error(f"User data not found after payment for user {user.id}")
            await message.reply_text("Error: User not found. Please contact support.")
            return

        lang = user_data['language_code']

        # Parse payload
        payload_parts = payment.invoice_payload.split('_')
        payment_type = payload_parts[1] if len(payload_parts) > 1 else 'single'

        # Determine capsules and subscription changes
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
        with engine.connect() as conn:
            # Add capsules to balance
            if capsules_to_add > 0:
                add_capsules_to_balance(user_data['id'], capsules_to_add)

            # Update subscription if premium
            if subscription_change:
                conn.execute(
                    update(users)
                    .where(users.c.id == user_data['id'])
                    .values(
                        subscription_status=subscription_change['status'],
                        subscription_expires=subscription_change['expires']
                    )
                )

            # Record transaction
            record_capsule_transaction(
                user_data['id'],
                payment_type,
                payment.total_amount,
                capsules_to_add,
                payment.telegram_payment_charge_id
            )

            conn.commit()

        # Success message
        success_message = t(lang, "payment_success",
                          capsules=capsules_to_add,
                          type=payment_type)

        await message.reply_text(
            success_message + f"\n\n💳 Transaction ID: `{payment.telegram_payment_charge_id}`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(t(lang, 'create_capsule'), callback_data='create'),
                InlineKeyboardButton(t(lang, 'main_menu'), callback_data='main_menu')
            ]])
        )

        logger.info(f"Payment successful: user {user.id}, type {payment_type}, "
                   f"capsules +{capsules_to_add}, charge_id: {payment.telegram_payment_charge_id}")

    except Exception as e:
        logger.error(f"Error processing successful payment: {e}")
        await message.reply_text(
            "Payment received but there was an error. Please contact support with payment ID: " +
            payment.telegram_payment_charge_id
        )

async def paysupport_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /paysupport command"""
    user = update.effective_user
    user_data = get_user_data(user.id)
    lang = user_data['language_code'] if user_data else 'en'

    support_text = t(lang, "paysupport_text")

    await update.message.reply_text(
        support_text,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(t(lang, 'main_menu'), callback_data='main_menu')
        ]])
    )

async def refund_payment(telegram_payment_charge_id: str, user_id: int, bot) -> bool:
    """Refund a Stars payment"""
    try:
        result = await bot.refund_star_payment(
            user_id=user_id,
            telegram_payment_charge_id=telegram_payment_charge_id
        )
        logger.info(f"Refund successful for payment {telegram_payment_charge_id}, user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Refund failed for payment {telegram_payment_charge_id}: {e}")
        return False
