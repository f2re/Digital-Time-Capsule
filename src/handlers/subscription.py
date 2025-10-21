# src/handlers/subscription.py
import uuid
from datetime import datetime, timedelta, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import ContextTypes
from ..database import get_user_data, users, payments, engine
from ..translations import t
from ..config import (
    MANAGING_SUBSCRIPTION, PREMIUM_TIER, FREE_TIER, PREMIUM_STORAGE_LIMIT,
    FREE_STORAGE_LIMIT, FREE_CAPSULE_LIMIT, PREMIUM_SINGLE_PRICE,
    PREMIUM_YEAR_PRICE, PREMIUM_SINGLE_STARS, PREMIUM_YEAR_STARS, logger
)
from sqlalchemy import insert, update

async def show_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show subscription information"""
    # Handle both callback queries and commands
    query = update.callback_query
    if query:
        await query.answer()
    
    user = update.effective_user
    userdata = get_user_data(user.id)
    lang = userdata['language_code']
    
    is_premium = userdata['subscription_status'] == PREMIUM_TIER
    
    if is_premium:
        used_mb = userdata['total_storage_used'] / 1024 / 1024
        total_mb = PREMIUM_STORAGE_LIMIT / 1024 / 1024
        expires = userdata['subscription_expires'].strftime("%d.%m.%Y") if userdata['subscription_expires'] else "Never"
        details = t(lang, "premium_tier_details",
                   count=userdata['capsule_count'],
                   used=f"{used_mb:.1f} MB",
                   total=f"{total_mb:.0f} MB",
                   years=25,
                   expires=expires)
    else:
        used_mb = userdata['total_storage_used'] / 1024 / 1024
        total_mb = FREE_STORAGE_LIMIT / 1024 / 1024
        details = t(lang, "free_tier_details",
                   count=userdata['capsule_count'],
                   limit=FREE_CAPSULE_LIMIT,
                   used=f"{used_mb:.1f} MB",
                   total=f"{total_mb:.0f} MB",
                   days=365)
    
    info_text = t(lang, "subscription_info",
                 tier="PREMIUM" if is_premium else "FREE",
                 details=details)
    
    # Build keyboard
    keyboard = []
    if not is_premium:
        keyboard = [
            [InlineKeyboardButton(
                t(lang, "buy_premium_single", price=PREMIUM_SINGLE_PRICE),
                callback_data="buy_single_rub"
            )],
            [InlineKeyboardButton(
                t(lang, "buy_premium_year", price=PREMIUM_YEAR_PRICE),
                callback_data="buy_year_rub"
            )],
            [InlineKeyboardButton(
                t(lang, "buy_stars_single", stars=PREMIUM_SINGLE_STARS),
                callback_data="buy_single_stars"
            )],
            [InlineKeyboardButton(
                t(lang, "buy_stars_year", stars=PREMIUM_YEAR_STARS),
                callback_data="buy_year_stars"
            )]
        ]
    
    keyboard.append([InlineKeyboardButton(t(lang, "back"), callback_data="main_menu")])
    
    # Send message based on context
    if query and query.message:
        # Called from button click
        await query.edit_message_text(
            info_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        # Called from command
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
    lang = user_data['language_code']
    
    payment_type = query.data  # e.g., 'buy_single_stars', 'buy_year_stars'
    
    # Determine payment details
    if payment_type == 'buy_single_stars':
        title = t(lang, 'buy_stars_single', stars=PREMIUM_SINGLE_STARS)
        description = "Unlock one premium capsule with extended time limits and storage"
        amount = PREMIUM_SINGLE_STARS
        subscription_type = 'single'
    elif payment_type == 'buy_year_stars':
        title = t(lang, 'buy_stars_year', stars=PREMIUM_YEAR_STARS)
        description = "Get 1 year of unlimited premium capsules and storage"
        amount = PREMIUM_YEAR_STARS
        subscription_type = 'yearly'
    else:
        # Placeholder for traditional payment provider (not Stars)
        await query.edit_message_text(
            "Traditional payment integration coming soon!\n\nFor now, use Telegram Stars payment.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(t(lang, 'back'), callback_data='subscription')
            ]])
        )
        return MANAGING_SUBSCRIPTION
    
    # Store subscription type in context for later processing
    context.user_data['pending_subscription'] = subscription_type
    
    # Create invoice with Stars (XTR currency)
    prices = [LabeledPrice(label="XTR", amount=amount)]
    
    try:
        await context.bot.send_invoice(
            chat_id=query.message.chat_id,
            title=title,
            description=description,
            payload=f"{user.id}_{subscription_type}_{uuid.uuid4()}",  # Unique payload
            provider_token="",  # Empty for Stars payments
            currency="XTR",
            prices=prices,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(text=f"Pay {amount} ⭐", pay=True)
            ]])
        )
        
        # Delete the previous message to keep chat clean
        await query.message.delete()
        
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
    """Answer pre-checkout query - verify order before payment"""
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
        
        # Parse payload to verify subscription type
        payload_parts = query.invoice_payload.split('_')
        if len(payload_parts) < 2:
            await query.answer(
                ok=False,
                error_message="Invalid payment request. Please try again."
            )
            return
        
        subscription_type = payload_parts[1]
        
        # Verify the payment amount matches subscription type
        expected_amount = PREMIUM_SINGLE_STARS if subscription_type == 'single' else PREMIUM_YEAR_STARS
        
        if query.total_amount != expected_amount:
            await query.answer(
                ok=False,
                error_message=f"Payment amount mismatch. Expected {expected_amount} stars."
            )
            return
        
        # All checks passed
        await query.answer(ok=True)
        logger.info(f"Pre-checkout approved for user {user.id}, subscription: {subscription_type}")
        
    except Exception as e:
        logger.error(f"Error in pre-checkout: {e}")
        await query.answer(
            ok=False,
            error_message="An error occurred. Please try again later."
        )

async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle successful payment - activate subscription"""
    message = update.message
    user = update.effective_user
    payment = message.successful_payment
    
    try:
        user_data = get_user_data(user.id)
        lang = user_data['language_code']
        
        # Parse payload
        payload_parts = payment.invoice_payload.split('_')
        subscription_type = payload_parts[1]
        
        # Calculate subscription expiry
        if subscription_type == 'single':
            # Single capsule - just add premium for 30 days or until one capsule is used
            expires = datetime.now(timezone.utc) + timedelta(days=30)
            success_message = "🎉 Payment successful!\n\nYou can now create one premium capsule with extended limits!"
        else:  # yearly
            # Full year of premium
            expires = datetime.now(timezone.utc) + timedelta(days=365)
            success_message = "🎉 Payment successful!\n\nPremium subscription activated for 1 year!"
        
        # Update user subscription in database
        with engine.connect() as conn:
            conn.execute(
                update(users)
                .where(users.c.id == user_data['id'])
                .values(
                    subscription_status=PREMIUM_TIER,
                    subscription_expires=expires
                )
            )
            
            # Record payment in payments table
            conn.execute(
                insert(payments).values(
                    user_id=user_data['id'],
                    payment_type='stars',
                    amount=payment.total_amount,
                    currency=payment.currency,
                    subscription_type=subscription_type,
                    payment_id=payment.telegram_payment_charge_id,
                    successful=True,
                    created_at=datetime.now(timezone.utc)
                )
            )
            
            conn.commit()
        
        # Send confirmation
        await message.reply_text(
            success_message,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(t(lang, 'create_capsule'), callback_data='create'),
                InlineKeyboardButton(t(lang, 'main_menu'), callback_data='main_menu')
            ]])
        )
        
        logger.info(f"Payment successful for user {user.id}: {subscription_type}, {payment.total_amount} stars")
        
    except Exception as e:
        logger.error(f"Error processing successful payment: {e}")
        await message.reply_text(
            "Payment received but there was an error activating your subscription. "
            "Please contact support with payment ID: " + payment.telegram_payment_charge_id
        )

async def paysupport_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /paysupport command - required for Stars payments"""
    user = update.effective_user
    user_data = get_user_data(user.id)
    lang = user_data['language_code'] if user_data else 'en'
    
    support_text = (
        "💬 Payment Support\n\n"
        "If you have any issues with your payment or subscription:\n\n"
        "1. Check your subscription status with /subscription\n"
        "2. For refunds, contact: your_support_email@example.com\n"
        "3. Include your Telegram username and payment details\n\n"
        "⚠️ Refund Policy:\n"
        "- Digital goods are generally non-refundable\n"
        "- Technical issues: Full refund within 24 hours\n"
        "- Unused subscriptions: Prorated refund available\n\n"
        "Response time: Usually within 24 hours"
    )
    
    await update.message.reply_text(
        support_text,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(t(lang, 'main_menu'), callback_data='main_menu')
        ]])
    )

async def refund_payment(telegram_payment_charge_id: str, bot) -> bool:
    """
    Refund a Stars payment
    Returns True if successful, False otherwise
    """
    try:
        result = await bot.refund_star_payment(
            user_id=None,  # Will be extracted from payment_charge_id
            telegram_payment_charge_id=telegram_payment_charge_id
        )
        logger.info(f"Refund successful for payment {telegram_payment_charge_id}")
        return True
    except Exception as e:
        logger.error(f"Refund failed for payment {telegram_payment_charge_id}: {e}")
        return False
