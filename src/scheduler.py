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

async def deliver_capsule(bot, capsule_id: int):
    """Deliver a time capsule"""
    try:
        with engine.connect() as conn:
            # Get capsule data
            capsule_row = conn.execute(
                select(capsules, users)
                .join(users, capsules.c.user_id == users.c.id)
                .where(capsules.c.id == capsule_id)
            ).first()

            if not capsule_row:
                logger.error(f"Capsule {capsule_id} not found")
                return

            capsule_data = dict(capsule_row._mapping)
            sender_name = capsule_data['first_name'] or capsule_data['username'] or 'Anonymous'

            # Get recipient
            recipient_id = capsule_data['recipient_id']
            lang = capsule_data['language_code']

            # Prepare message
            delivery_text = t(lang, 'delivery_text',
                            created=capsule_data['created_at'].strftime('%d.%m.%Y %H:%M'),
                            sender=sender_name)

            # Send content based on type
            if capsule_data['content_type'] == 'text':
                await bot.send_message(
                    chat_id=recipient_id,
                    text=f"{t(lang, 'delivery_title')}\n\n{delivery_text}\n\n{capsule_data['content_text']}"
                )
            else:
                # Download and decrypt file
                file_bytes = download_and_decrypt_file(
                    capsule_data['s3_key'],
                    capsule_data['file_key']
                )

                if file_bytes:
                    file_obj = BytesIO(file_bytes)

                    if capsule_data['content_type'] == 'photo':
                        await bot.send_photo(
                            chat_id=recipient_id,
                            photo=file_obj,
                            caption=delivery_text
                        )
                    elif capsule_data['content_type'] == 'video':
                        await bot.send_video(
                            chat_id=recipient_id,
                            video=file_obj,
                            caption=delivery_text
                        )
                    elif capsule_data['content_type'] == 'document':
                        await bot.send_document(
                            chat_id=recipient_id,
                            document=file_obj,
                            caption=delivery_text
                        )
                    elif capsule_data['content_type'] == 'voice':
                        await bot.send_voice(
                            chat_id=recipient_id,
                            voice=file_obj,
                            caption=delivery_text
                        )

            # Delete from S3 if applicable
            if capsule_data['s3_key']:
                delete_file_from_s3(capsule_data['s3_key'])

            # Delete from database
            delete_capsule(capsule_id)

            logger.info(f"Capsule {capsule_id} delivered and deleted successfully")

    except Exception as e:
        logger.error(f"Error delivering capsule {capsule_id}: {e}")

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
