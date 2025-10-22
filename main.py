#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Digital Time Capsule - Telegram Bot
"""
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ConversationHandler, MessageHandler, filters,
    PreCheckoutQueryHandler
)
from src.config import (
    BOT_TOKEN, SELECTING_LANG, SELECTING_ACTION, SELECTING_CONTENT_TYPE,
    RECEIVING_CONTENT, SELECTING_TIME, SELECTING_DATE, SELECTING_RECIPIENT,
    CONFIRMING_CAPSULE, VIEWING_CAPSULES, MANAGING_SUBSCRIPTION, logger
)
from src.database import init_db
from src.scheduler import init_scheduler
from src.handlers.start import start, select_language
from src.handlers.main_menu import main_menu_handler
from src.handlers.create_capsule import (
    select_content_type, receive_content, select_time,
    select_custom_date, select_recipient, confirm_capsule,
    start_create_capsule
)
from src.handlers.subscription import (
    show_subscription, handle_payment, precheckout_callback,
    successful_payment_callback, paysupport_command
)
from src.handlers.view_capsules import show_capsules
from src.handlers.settings import show_settings
from src.handlers.help import help_command
from src.handlers.delete_capsule import delete_capsule_handler

import asyncio
...
async def main():
    """Start the bot"""
    init_db()
    application = Application.builder().token(BOT_TOKEN).build()
    
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
                CallbackQueryHandler(select_content_type, pattern='^type_')
            ],
            RECEIVING_CONTENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_content),
                MessageHandler(filters.PHOTO, receive_content),
                MessageHandler(filters.VIDEO, receive_content),
                MessageHandler(filters.Document.ALL, receive_content),
                MessageHandler(filters.VOICE, receive_content)
            ],
            SELECTING_TIME: [
                CallbackQueryHandler(select_time, pattern='^time_')
            ],
            SELECTING_DATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, select_custom_date)
            ],
            SELECTING_RECIPIENT: [
                CallbackQueryHandler(select_recipient, pattern='^recipient_')
            ],
            CONFIRMING_CAPSULE: [
                CallbackQueryHandler(confirm_capsule, pattern='^confirm_yes$')
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
        },
        fallbacks=[
            CommandHandler('start', start),
            CallbackQueryHandler(main_menu_handler, pattern='^main_menu$')
        ],
        allow_reentry=True
    )
    
    application.add_handler(conv_handler)
    
    # Payment handlers
    application.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    application.add_handler(
        MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback)
    )
    
    # Additional commands
    application.add_handler(CommandHandler('create', start_create_capsule))
    application.add_handler(CommandHandler('capsules', show_capsules))
    application.add_handler(CommandHandler('subscription', show_subscription))
    application.add_handler(CommandHandler('settings', show_settings))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('paysupport', paysupport_command))
    
    logger.info("Bot started!")
    
    async with application:
        await application.initialize()
        scheduler.start()
        await application.start()
        await application.updater.start_polling()
        # Keep the bot running
        while True:
            await asyncio.sleep(3600)

if __name__ == '__main__':
    asyncio.run(main())
