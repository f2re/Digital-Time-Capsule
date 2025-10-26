#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Digital Time Capsule - Telegram Bot
"""

from telegram import Update
from telegram.error import TelegramError
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ConversationHandler, MessageHandler, filters,
    PreCheckoutQueryHandler, ContextTypes, PicklePersistence
)

from src.config import (
    BOT_TOKEN, SELECTING_LANG, SELECTING_ACTION, SELECTING_CONTENT_TYPE,
    RECEIVING_CONTENT, SELECTING_TIME, SELECTING_DATE, SELECTING_RECIPIENT,
    CONFIRMING_CAPSULE, VIEWING_CAPSULES, MANAGING_SUBSCRIPTION, MANAGING_SETTINGS,
    logger
)

from src.database import init_db, get_user_data
from src.scheduler import init_scheduler

# ============================================================================
# IMPORT HANDLERS BY THEME
# ============================================================================

# Start & Menu Handlers
from src.handlers.start import start, select_language, show_main_menu_with_image
from src.handlers.main_menu import main_menu_handler

# Capsule Creation Handlers
from src.handlers.create_capsule import (
    select_content_type, receive_content, select_time,
    select_custom_date, select_recipient, confirm_capsule,
    start_create_capsule, show_user_list
)

# Capsule Management Handlers
from src.handlers.view_capsules import show_capsules
from src.handlers.delete_capsule import delete_capsule_handler

# Payment & Subscription Handlers
from src.handlers.subscription import (
    show_subscription, handle_payment, precheckout_callback,
    successful_payment_callback, paysupport_command
)

# Settings & Help Handlers
from src.handlers.settings import show_settings, language_callback_handler
from src.handlers.help import help_command

import asyncio

# ============================================================================
# ERROR HANDLER
# ============================================================================

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors gracefully"""
    logger.error("Exception while handling an update:", exc_info=context.error)
    try:
        if update and hasattr(update, 'effective_message') and update.effective_message:
            # Get user language
            user_id = update.effective_user.id if update.effective_user else None
            lang = 'en'  # default
            if user_id:
                user_data = get_user_data(user_id)
                if user_data:
                    lang = user_data.get('language_code', 'en')

            await update.effective_message.reply_text(
                t(lang, 'error_occurred')
            )
    except Exception:
        pass


# ============================================================================
# COMMAND WRAPPERS (Entry Points to Conversation)
# ============================================================================

async def cmd_create_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Wrapper for /create command to enter conversation"""
    user_data = get_user_data(update.effective_user.id)
    if not user_data:
        lang = 'en'
        await update.message.reply_text(t(lang, 'please_start_bot'))
        return ConversationHandler.END
    # Call start_create_capsule which returns the proper state
    return await start_create_capsule(update, context)


async def cmd_capsules_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Wrapper for /capsules command to enter conversation"""
    user_data = get_user_data(update.effective_user.id)
    if not user_data:
        await update.message.reply_text("Please /start the bot first")
        return ConversationHandler.END

    return await show_capsules(update, context)


async def cmd_subscription_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Wrapper for /subscription command to enter conversation"""
    user_data = get_user_data(update.effective_user.id)
    if not user_data:
        await update.message.reply_text("Please /start the bot first")
        return ConversationHandler.END

    return await show_subscription(update, context)


async def cmd_settings_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Wrapper for /settings command to enter conversation"""
    user_data = get_user_data(update.effective_user.id)
    if not user_data:
        await update.message.reply_text("Please /start the bot first")
        return ConversationHandler.END

    return await show_settings(update, context)


# ============================================================================
# MAIN APPLICATION
# ============================================================================

async def main():
    """Start the bot"""
    # Initialize database
    init_db()

    # Run migrations
    from src.migrations import run_migrations
    migration_success = run_migrations()

    if not migration_success:
        logger.error("❌ Database migrations failed! Bot cannot start safely.")
        return

    logger.info("✅ Database is up to date")

    # Create application with persistence
    persistence = PicklePersistence(filepath="conversation_data.pickle")
    application = Application.builder().token(BOT_TOKEN).persistence(persistence).build()

    # Initialize and store scheduler
    scheduler = init_scheduler(application)
    application.bot_data['scheduler'] = scheduler

    # ========================================================================
    # CONVERSATION HANDLER - Main bot logic
    # ========================================================================

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            CommandHandler('create', cmd_create_wrapper),
            CommandHandler('capsules', cmd_capsules_wrapper),
            CommandHandler('subscription', cmd_subscription_wrapper),
            CommandHandler('settings', cmd_settings_wrapper),
        ],
        states={
            # Language Selection State
            SELECTING_LANG: [
                CallbackQueryHandler(select_language, pattern='^set_lang_')
            ],

            # Main Menu State
            SELECTING_ACTION: [
                CallbackQueryHandler(main_menu_handler),
                CallbackQueryHandler(select_language, pattern='^set_lang_')
            ],

            # Capsule Creation States
            SELECTING_CONTENT_TYPE: [
                CallbackQueryHandler(select_content_type, pattern='^type_'),
                CallbackQueryHandler(main_menu_handler, pattern='^(main_menu|cancel)$')
            ],

            RECEIVING_CONTENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_content),
                MessageHandler(filters.PHOTO, receive_content),
                MessageHandler(filters.VIDEO, receive_content),
                MessageHandler(filters.Document.ALL, receive_content),
                MessageHandler(filters.VOICE, receive_content),
                CallbackQueryHandler(main_menu_handler, pattern='^(main_menu|cancel)$')
            ],

            SELECTING_TIME: [
                CallbackQueryHandler(select_time, pattern='^time_'),
                CallbackQueryHandler(main_menu_handler, pattern='^(main_menu|cancel)$')
            ],

            SELECTING_DATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, select_custom_date),
                CallbackQueryHandler(main_menu_handler, pattern='^(main_menu|cancel)$')
            ],

            SELECTING_RECIPIENT: [
                CallbackQueryHandler(select_recipient, pattern='^recipient_'),
                CallbackQueryHandler(select_recipient, pattern='^select_user_'),
                CallbackQueryHandler(show_user_list, pattern='^recipient_user_list$'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, select_recipient),
                CallbackQueryHandler(main_menu_handler, pattern='^(main_menu|cancel)$')
            ],

            CONFIRMING_CAPSULE: [
                CallbackQueryHandler(confirm_capsule, pattern='^confirm_yes$'),
                CallbackQueryHandler(main_menu_handler, pattern='^(main_menu|cancel|confirm_no)$')
            ],

            # Subscription Management States
            MANAGING_SUBSCRIPTION: [
                CallbackQueryHandler(handle_payment, pattern="^buy_"),
                CallbackQueryHandler(show_subscription, pattern="^subscription$"),
                CallbackQueryHandler(main_menu_handler, pattern="^main_menu$"),
            ],

            # Capsule Viewing States
            VIEWING_CAPSULES: [
                CallbackQueryHandler(show_capsules, pattern="^capsules$"),
                CallbackQueryHandler(delete_capsule_handler, pattern="^delete_"),
                CallbackQueryHandler(main_menu_handler, pattern="^main_menu$"),
            ],

            # Settings States
            MANAGING_SETTINGS: [
                CallbackQueryHandler(language_callback_handler, pattern="^set_lang_"),
                CallbackQueryHandler(main_menu_handler, pattern="^main_menu$"),
            ],
        },
        fallbacks=[
            CommandHandler('start', start),
            CallbackQueryHandler(main_menu_handler, pattern='^(main_menu|cancel)$'),
        ],
        allow_reentry=True,
        name="main_conversation",
        persistent=True,
        per_chat=True,
        per_message=False
    )

    # Add conversation handler
    application.add_handler(conv_handler)

    # ========================================================================
    # PAYMENT HANDLERS (Outside conversation - work independently)
    # ========================================================================

    application.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    application.add_handler(
        MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback)
    )

    # ========================================================================
    # ADDITIONAL COMMANDS (Outside conversation - standalone)
    # ========================================================================

    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('paysupport', paysupport_command))

    # ========================================================================
    # ERROR HANDLER
    # ========================================================================

    application.add_error_handler(error_handler)

    # ========================================================================
    # START BOT
    # ========================================================================

    logger.info("✅ Bot started successfully!")
    logger.info("📋 Registered handlers:")
    logger.info("   - Conversation Handler (main logic)")
    logger.info("   - Payment Handlers (Stars integration)")
    logger.info("   - Command Handlers: /help, /paysupport")
    logger.info("   - Error Handler")

    async with application:
        await application.initialize()
        scheduler.start()
        logger.info("⏰ Scheduler started")

        await application.start()
        await application.updater.start_polling()
        logger.info("🔄 Polling started")

        try:
            while True:
                await asyncio.sleep(3600)
        except (KeyboardInterrupt, SystemExit):
            logger.info("🛑 Bot stopped by user")
        finally:
            await application.updater.stop()
            await application.stop()
            scheduler.shutdown()
            logger.info("✅ Bot shutdown gracefully")


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Application terminated")
