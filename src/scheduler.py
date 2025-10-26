# src/scheduler.py
from datetime import datetime, timezone
from io import BytesIO
from sqlalchemy import select, and_, update as sqlalchemy_update
from telegram.ext import Application
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from .config import logger
from .database import engine, capsules, users, delete_capsule
from .s3_utils import download_and_decrypt_file, delete_file_from_s3
from .translations import t

async def deliver_capsule(application, capsule_id: int):
    """Deliver capsule to recipient at scheduled time"""
    from telegram.error import TelegramError, Forbidden, ChatNotFound

    try:
        # Get capsule data
        with engine.connect() as conn:
            result = conn.execute(
                select(capsules).where(capsules.c.id == capsule_id)
            ).first()

            if not result:
                logger.error(f"Capsule {capsule_id} not found")
                return

            capsule_data = dict(result._mapping)

        # Check if already delivered
        if capsule_data['delivered']:
            logger.info(f"Capsule {capsule_id} already delivered")
            return

        # Get sender info
        sender_data = get_user_by_internal_id(capsule_data['user_id'])
        sender_name = sender_data.get('first_name', 'Anonymous') if sender_data else 'Anonymous'

        # Prepare delivery message
        created_at = capsule_data['created_at'].strftime("%d.%m.%Y")
        content = capsule_data['content_text'] or "[Media content]"

        recipient_type = capsule_data['recipient_type']

        # GROUP DELIVERY
        if recipient_type == 'group':
            try:
                chat_id = int(capsule_data['recipient_id'])

                delivery_message = f"📦 **Time Capsule Delivered!**\n\n"
                delivery_message += f"💌 From: {sender_name}\n"
                delivery_message += f"⏰ Created: {created_at}\n\n"
                delivery_message += f"{content}"

                await application.bot.send_message(
                    chat_id=chat_id,
                    text=delivery_message,
                    parse_mode='Markdown'
                )

                logger.info(f"✅ Capsule {capsule_id} delivered to group {chat_id}")
                mark_capsule_delivered(capsule_id)
                return

            except Forbidden:
                logger.error(f"❌ Bot blocked in group {chat_id}")
            except ChatNotFound:
                logger.error(f"❌ Group {chat_id} not found or bot not member")
            except Exception as e:
                logger.error(f"❌ Error delivering to group: {e}")

            # Notify sender of failed group delivery
            await application.bot.send_message(
                chat_id=sender_data['telegram_id'],
                text=f"❌ Failed to deliver capsule to group.\nMake sure bot is a group member."
            )
            return

        # USER DELIVERY
        elif recipient_type == 'user':
            # Check if activated
            if not capsule_data['is_activated']:
                # Not activated - notify sender
                logger.warning(f"Capsule {capsule_id} not activated yet")

                await application.bot.send_message(
                    chat_id=sender_data['telegram_id'],
                    text=f"⚠️ Capsule awaiting activation!\n\n"
                         f"Recipient hasn't activated the capsule yet.\n"
                         f"Send them this link:\n<code>{capsule_data['activation_link']}</code>",
                    parse_mode='HTML'
                )
                return

            # Activated - deliver
            try:
                user_id = int(capsule_data['recipient_id'])

                delivery_message = f"📦 **Time Capsule Delivered!**\n\n"
                delivery_message += f"💌 From: {sender_name}\n"
                delivery_message += f"⏰ Created: {created_at}\n\n"
                delivery_message += f"{content}"

                await application.bot.send_message(
                    chat_id=user_id,
                    text=delivery_message,
                    parse_mode='Markdown'
                )

                logger.info(f"✅ Capsule {capsule_id} delivered to user {user_id}")
                mark_capsule_delivered(capsule_id)
                return

            except Forbidden:
                logger.error(f"❌ User {user_id} blocked the bot")
                # Notify sender and provide manual forwarding option
                await application.bot.send_message(
                    chat_id=sender_data['telegram_id'],
                    text=f"❌ Recipient blocked the bot.\n\nCapsule content:\n\n{content}"
                )
            except Exception as e:
                logger.error(f"❌ Error delivering to user: {e}")

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
                    # If delivery time is in the past, schedule for immediate delivery
                    scheduler.add_job(
                        deliver_capsule,
                        'date',
                        run_date=datetime.now(timezone.utc),
                        args=[application.bot, cap_dict['id']],
                        id=f"capsule_{cap_dict['id']}",
                        replace_existing=True
                    )
                else:
                    # Otherwise, schedule it for the future
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

    # Add a job to check for due capsules every minute
    scheduler.add_job(
        check_due_capsules,
        'interval',
        minutes=1,
        args=[application.bot]
    )

    return scheduler
