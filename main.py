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
from src.handlers.start import start, select_language, show_main_menu_with_image
from src.handlers.main_menu import main_menu_handler
from src.handlers.create_capsule import (
    select_content_type, receive_content, select_time,
    select_custom_date, select_recipient, confirm_capsule,
    start_create_capsule, show_user_list
)
from src.handlers.subscription import (
    show_subscription, handle_payment, precheckout_callback,
    successful_payment_callback, paysupport_command
)
from src.handlers.view_capsules import show_capsules
from src.handlers.settings import show_settings, language_callback_handler
from src.handlers.help import help_command
from src.handlers.delete_capsule import delete_capsule_handler
import asyncio

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors gracefully"""
    logger.error("Exception while handling an update:", exc_info=context.error)
    try:
        if update and hasattr(update, 'effective_message') and update.effective_message:
            await update.effective_message.reply_text(
                "❌ Произошла ошибка. Попробуйте ещё раз или используйте /start"
            )
    except Exception:
        pass

async def main():
    """Start the bot"""
    init_db()

    # Run migrations
    from src.migrations import run_migrations
    migration_success = run_migrations()

    if not migration_success:
        logger.error("❌ Database migrations failed! Bot cannot start safely.")
        return

    logger.info("✅ Database is up to date")

    persistence = PicklePersistence(filepath="conversation_data.pickle")
    application = Application.builder().token(BOT_TOKEN).persistence(persistence).build()

    scheduler = init_scheduler(application)
    application.bot_data['scheduler'] = scheduler

    # Conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            SELECTING_LANG: [
                CallbackQueryHandler(select_language, pattern='^set_lang_')
            ],
            SELECTING_ACTION: [
                CallbackQueryHandler(main_menu_handler),
                CallbackQueryHandler(select_language, pattern='^set_lang_')
            ],
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
            MANAGING_SUBSCRIPTION: [
                CallbackQueryHandler(handle_payment, pattern="^buy_"),
                CallbackQueryHandler(show_subscription, pattern="^subscription$"),
                CallbackQueryHandler(main_menu_handler, pattern="^main_menu$"),
            ],
            VIEWING_CAPSULES: [
                CallbackQueryHandler(show_capsules, pattern="^capsules$"),
                CallbackQueryHandler(delete_capsule_handler, pattern="^delete_"),
                CallbackQueryHandler(main_menu_handler, pattern="^main_menu$"),
            ],
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

    application.add_handler(conv_handler)

    # Payment handlers
    application.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    application.add_handler(
        MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback)
    )

    # Additional commands outside conversation - all show big menu or specific screens
    async def cmd_create(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = get_user_data(update.effective_user.id)
        if user_data:
            return await start_create_capsule(update, context)
        await update.message.reply_text("Please /start the bot first")

    application.add_handler(CommandHandler('create', cmd_create))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('paysupport', paysupport_command))

    logger.info("✅ Bot started!")

    application.add_error_handler(error_handler)

    async with application:
        await application.initialize()
        scheduler.start()
        await application.start()
        await application.updater.start_polling()

        try:
            while True:
                await asyncio.sleep(3600)
        except (KeyboardInterrupt, SystemExit):
            logger.info("Bot stopped by user.")
        finally:
            await application.updater.stop()
            await application.stop()
            scheduler.shutdown()
            logger.info("Bot shutdown gracefully.")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Application terminated.")
