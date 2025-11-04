# src/scheduler.py
from datetime import datetime, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from telegram import Bot
from telegram.ext import Application
from sqlalchemy import select, and_
from .database import capsules, engine, mark_capsule_delivered, get_user_by_internal_id
from .s3_utils import download_and_decrypt_file
from .config import logger
from .translations import t

# Track notified capsules to avoid spam
_notified_pending_capsules = set()

async def deliver_capsule(bot: Bot, capsule_id: int):
    """Deliver a time capsule to recipient"""
    try:
        from telegram.error import TelegramError, Forbidden, BadRequest

        with engine.connect() as conn:
            capsule = conn.execute(
                select(capsules).where(capsules.c.id == capsule_id)
            ).first()

            if not capsule:
                logger.error(f"Capsule {capsule_id} not found")
                return

            capsule_data = dict(capsule._mapping)

            # Get sender info
            sender_data = get_user_by_internal_id(capsule_data['user_id'])
            if not sender_data:
                logger.error(f"Sender not found for capsule {capsule_id}")
                return

            sender_name = sender_data.get('first_name', 'Anonymous')
            sender_lang = sender_data.get('language_code', 'en')

            # Format content
            content = ""
            if capsule_data['content_text']:
                content = capsule_data['content_text']
            elif capsule_data['content_type'] in ('photo', 'video', 'document', 'voice'):
                content = t(sender_lang, 'capsule_has_media')

            if capsule_data.get('message'):
                content += f"\n\n💬 {capsule_data['message']}"

            # Format the created_at time using sender's timezone
            from .timezone_utils import format_time_for_user
            sender_timezone = sender_data.get('timezone', 'UTC')
            created_at = format_time_for_user(capsule_data['created_at'], sender_timezone, sender_lang)

            # Check recipient type
            recipient_type = capsule_data['recipient_type']

            # GROUP DELIVERY
            if recipient_type == 'group':
                try:
                    group_id = capsule_data['recipient_id']

                    # Build message using translation
                    delivery_text = (
                        f"📦 <b>{t(sender_lang, 'capsule_delivered_title')}</b>\n\n"
                        f"💌 {t(sender_lang, 'from')}: {sender_name}\n"
                        f"⏰ {t(sender_lang, 'created')}: {created_at}\n\n"
                        f"{content}"
                    )

                    await bot.send_message(
                        chat_id=group_id,
                        text=delivery_text,
                        parse_mode='HTML'
                    )

                    logger.info(f"✅ Capsule {capsule_id} delivered to group {group_id}")
                    mark_capsule_delivered(capsule_id)
                    return

                except Forbidden:
                    logger.error(f"❌ Bot not a member of group {group_id}")
                    await bot.send_message(
                        chat_id=sender_data['telegram_id'],
                        text=t(sender_lang, 'group_not_member'),
                        parse_mode='HTML'
                    )
                    mark_capsule_delivered(capsule_id)  # ⭐ Mark as delivered to stop retrying
                except BadRequest as e:
                    logger.error(f"❌ Group {group_id} not found or invalid: {e}")
                    await bot.send_message(
                        chat_id=sender_data['telegram_id'],
                        text=t(sender_lang, 'delivery_failed_invalid_chat'),
                        parse_mode='HTML'
                    )
                    mark_capsule_delivered(capsule_id)  # ⭐ Mark as delivered to stop retrying
                return

            # USER DELIVERY
            # ⭐ CRITICAL FIX: Check if capsule needs activation (username-based)
            if not capsule_data.get('recipient_id') and capsule_data.get('recipient_username'):
                # Not yet activated - notify sender ONCE
                username = capsule_data['recipient_username']

                # Check if we already notified about this capsule
                if capsule_id not in _notified_pending_capsules:
                    # Generate invite link
                    import base64
                    encoded_uuid = base64.urlsafe_b64encode(
                        capsule_data['capsule_uuid'].encode()
                    ).decode().rstrip('=')

                    bot_username = (await bot.get_me()).username
                    invite_link = f"https://t.me/{bot_username}?start=c_{encoded_uuid}"

                    notification_text = t(
                        sender_lang,
                        'delivery_pending_notification',
                        username=f"@{username}",
                        invite_link=invite_link
                    )

                    await bot.send_message(
                        chat_id=sender_data['telegram_id'],
                        text=notification_text,
                        parse_mode='HTML'
                    )

                    # Mark as notified
                    _notified_pending_capsules.add(capsule_id)
                    logger.info(f"Notified sender about pending capsule {capsule_id} for @{username}")

                # DON'T mark as delivered - keep waiting for activation
                return

            # Activated - deliver to user
            try:
                user_id = int(capsule_data['recipient_id'])

                # Get recipient language
                recipient_lang = 'en'
                try:
                    from .database import get_user_data_by_telegram_id
                    recipient_user_data = get_user_data_by_telegram_id(user_id)
                    if recipient_user_data:
                        recipient_lang = recipient_user_data.get('language_code', 'en')
                except:
                    pass

                # Build message with HTML using translations
                delivery_message = (
                    f"📦 <b>{t(recipient_lang, 'capsule_delivered_title')}</b>\n\n"
                    f"💌 {t(recipient_lang, 'from')}: {sender_name}\n"
                    f"⏰ {t(recipient_lang, 'created')}: {created_at}\n\n"
                    f"{content}"
                )

                # Send media if present
                if capsule_data['content_type'] in ('photo', 'video', 'document', 'voice'):
                    try:
                        file_data = download_and_decrypt_file(
                            capsule_data['s3_key'],
                            capsule_data['file_key']
                        )

                        if capsule_data['content_type'] == 'photo':
                            await bot.send_photo(
                                chat_id=user_id,
                                photo=file_data,
                                caption=delivery_message,
                                parse_mode='HTML'
                            )
                        elif capsule_data['content_type'] == 'video':
                            await bot.send_video(
                                chat_id=user_id,
                                video=file_data,
                                caption=delivery_message,
                                parse_mode='HTML'
                            )
                        elif capsule_data['content_type'] == 'document':
                            await bot.send_document(
                                chat_id=user_id,
                                document=file_data,
                                caption=delivery_message,
                                parse_mode='HTML'
                            )
                        elif capsule_data['content_type'] == 'voice':
                            await bot.send_voice(
                                chat_id=user_id,
                                voice=file_data,
                                caption=delivery_message
                            )
                    except Exception as e:
                        logger.error(f"Error sending media: {e}")
                        await bot.send_message(
                            chat_id=user_id,
                            text=delivery_message,
                            parse_mode='HTML'
                        )
                else:
                    # Text only
                    await bot.send_message(
                        chat_id=user_id,
                        text=delivery_message,
                        parse_mode='HTML'
                    )

                logger.info(f"✅ Capsule {capsule_id} delivered to user {user_id}")
                mark_capsule_delivered(capsule_id)
                return

            except Forbidden:
                logger.error(f"❌ User {user_id} blocked the bot")
                await bot.send_message(
                    chat_id=sender_data['telegram_id'],
                    text=t(sender_lang, 'delivery_failed_blocked'),
                    parse_mode='HTML'
                )
                mark_capsule_delivered(capsule_id)  # ⭐ Mark as delivered to stop retrying

            except BadRequest as e:
                logger.error(f"❌ Invalid chat {user_id}: {e}")
                await bot.send_message(
                    chat_id=sender_data['telegram_id'],
                    text=t(sender_lang, 'delivery_failed_invalid_chat'),
                    parse_mode='HTML'
                )
                mark_capsule_delivered(capsule_id)  # ⭐ Mark as delivered to stop retrying

            except Exception as e:
                logger.error(f"❌ Error delivering to user: {e}")
                await bot.send_message(
                    chat_id=sender_data['telegram_id'],
                    text=t(sender_lang, 'delivery_failed_error'),
                    parse_mode='HTML'
                )

    except Exception as e:
        logger.error(f"Error in deliver_capsule: {e}")


async def check_due_capsules(bot):
    """Check for and deliver capsules that are due"""
    try:
        with engine.connect() as conn:
            due_capsules = conn.execute(
                select(capsules)
                .where(and_(
                    capsules.c.delivery_time <= datetime.now(timezone.utc),
                    capsules.c.delivered == False
                ))
            ).fetchall()

            for capsule in due_capsules:
                await deliver_capsule(bot, capsule.id)

    except Exception as e:
        logger.error(f"Error checking for due capsules: {e}")


def init_scheduler(application: Application) -> AsyncIOScheduler:
    """Initialize scheduler and load pending capsules"""
    scheduler = AsyncIOScheduler(timezone=timezone.utc)

    try:
        with engine.connect() as conn:
            pending_capsules = conn.execute(
                select(capsules)
                .where(capsules.c.delivered == False)
            ).fetchall()

            for capsule in pending_capsules:
                cap_dict = dict(capsule._mapping)
                delivery_time = cap_dict['delivery_time'].replace(tzinfo=timezone.utc)

                if delivery_time <= datetime.now(timezone.utc):
                    scheduler.add_job(
                        deliver_capsule,
                        'date',
                        run_date=datetime.now(timezone.utc),
                        args=[application.bot, cap_dict['id']],
                        id=f"capsule_{cap_dict['id']}",
                        replace_existing=True
                    )
                else:
                    scheduler.add_job(
                        deliver_capsule,
                        trigger=DateTrigger(run_date=delivery_time),
                        args=[application.bot, cap_dict['id']],
                        id=f"capsule_{cap_dict['id']}",
                        replace_existing=True
                    )

            logger.info(f"Scheduled {len(pending_capsules)} pending capsules")

    except Exception as e:
        logger.error(f"Error initializing scheduler: {e}")

    scheduler.add_job(
        check_due_capsules,
        'interval',
        minutes=1,
        args=[application.bot]
    )

    return scheduler
