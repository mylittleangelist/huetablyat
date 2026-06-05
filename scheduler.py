import logging
from datetime import date
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from aiogram.enums import ParseMode

import database as db
import config as cfg
from utils import (
    build_family_reminder_text, build_role_reminder_text,
    should_send_today, format_date, days_until
)
from keyboards.owner_kb import get_confirmation_kb

logger = logging.getLogger(__name__)

def em(emoji_id: str, fallback: str = "•") -> str:
    return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'

# отправляет модерам сообщение в 12:00 мск

async def job_morning_reminder(bot: Bot):
    """Send renewal reminders to next watcher in queue at 12:00 MSK."""
    logger.info("Running morning reminder job...")

    exp_families = await db.get_expiring_families(cfg.DAYS_THRESHOLD)
    exp_roles = await db.get_expiring_roles(cfg.DAYS_THRESHOLD)

    if not exp_families and not exp_roles:
        logger.info("No expiring items — skipping reminder.")
        return

    last_send = await db.get_setting("last_send_date")
    if not should_send_today(last_send):
        logger.info("Not a send day yet — skipping.")
        return

    watchers = await db.get_all_watchers()
    if not watchers:
        logger.warning("No watchers in system — skipping reminder.")
        return

    await db.ensure_queue_consistency()

    watcher = await db.get_next_watcher()
    if not watcher:
        logger.warning("Could not get next watcher.")
        return

    await db.set_setting("last_send_date", date.today().isoformat())

    watcher_name = f'@{watcher["username"]}' if watcher.get("username") else f'Следящий'
    watcher_mention = f'<a href="tg://user?id={watcher["telegram_id"]}">{watcher_name}</a>'

    # создает сообщение о напоминании
    today_str = date.today().isoformat()

    reminder_intro = (
        f'{em("6039486778597970865","🔔")} {watcher_mention}, пришел день отправки для продлении,\n'
        f'нажми на текст чтобы скопировать:\n\n'
    )

    sections = []
    if exp_families:
        family_text = build_family_reminder_text(exp_families)
        sections.append(
            f'{em("5870772616305839506","👥")} <b>Семья:</b>\n\n<code>{family_text}</code>'
        )
    if exp_roles:
        role_text = build_role_reminder_text(exp_roles)
        sections.append(
            f'{em("5870994129244131212","👤")} <b>Роль:</b>\n\n<code>{role_text}</code>'
        )

    full_reminder = reminder_intro + "\n\n".join(sections)

    # находит чат куда отправлять
    reminder_chats = await db.get_reminder_chats()

    sent_chat_id = None
    sent_thread_id = None
    sent_msg_id = None

    # отправка
    for rc in reminder_chats:
        try:
            kwargs = dict(
                chat_id=rc["chat_id"],
                text=full_reminder,
                parse_mode=ParseMode.HTML
            )
            if rc.get("thread_id"):
                kwargs["message_thread_id"] = rc["thread_id"]
            msg = await bot.send_message(**kwargs)
            sent_chat_id = rc["chat_id"]
            sent_thread_id = rc.get("thread_id")
            sent_msg_id = msg.message_id
        except Exception as e:
            logger.error(f"Failed to send to reminder chat {rc['chat_id']}: {e}")

    # отправка в лс
    watcher_chat_id = await db.get_setting(f"chat_id_{watcher['telegram_id']}")
    dm_msg_id = None
    dm_chat_id = None
    if watcher_chat_id:
        try:
            dm_msg = await bot.send_message(
                int(watcher_chat_id),
                full_reminder,
                parse_mode=ParseMode.HTML
            )
            dm_msg_id = dm_msg.message_id
            dm_chat_id = int(watcher_chat_id)
        except Exception as e:
            logger.error(f"Failed to send DM to watcher {watcher['telegram_id']}: {e}")
    else:
        logger.warning(f"Watcher {watcher['telegram_id']} has no saved chat_id")

    if sent_chat_id or dm_chat_id:
        await db.add_confirmation(
            conf_date=today_str,
            watcher_id=watcher["telegram_id"],
            remind_msg_id=sent_msg_id or dm_msg_id or 0,
            remind_chat_id=sent_chat_id or dm_chat_id or 0,
            remind_thread_id=sent_thread_id
        )

    logger.info(f"Morning reminder sent to watcher {watcher['telegram_id']}")

# в 20:00 мск аоыторное сообщение с вопросом типо отправил или нет

async def job_evening_check(bot: Bot):
    """At 20:00 MSK, ask if watcher sent the renewal message."""
    logger.info("Running evening check job...")

    confirmations = await db.get_todays_confirmations()
    if not confirmations:
        logger.info("No confirmations for today.")
        return

    reminder_chats = await db.get_reminder_chats()

    for conf in confirmations:
        if conf["status"] != "pending":
            continue

        watcher = await db.get_user(conf["watcher_telegram_id"])
        watcher_name = f'@{watcher["username"]}' if watcher and watcher.get("username") else "Следящий"
        watcher_mention = (
            f'<a href="tg://user?id={watcher["telegram_id"]}">{watcher_name}</a>'
            if watcher else watcher_name
        )

        check_text = (
            f'{em("6028435952299413210","ℹ")} Проверка отправки напоминания\n\n'
            f'{em("5870994129244131212","👤")} {watcher_mention} написал(а) о продлении?'
        )

        for rc in reminder_chats:
            try:
                kwargs = dict(
                    chat_id=rc["chat_id"],
                    text=check_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=get_confirmation_kb(conf["id"])
                )
                if rc.get("thread_id"):
                    kwargs["message_thread_id"] = rc["thread_id"]
                msg = await bot.send_message(**kwargs)
                await db.set_confirm_message(conf["id"], msg.message_id, rc["chat_id"], rc.get("thread_id"))
            except Exception as e:
                logger.error(f"Failed to send evening check to {rc['chat_id']}: {e}")

    logger.info("Evening check messages sent.")

def setup_scheduler(scheduler: AsyncIOScheduler, bot: Bot):
    scheduler.add_job(
        job_morning_reminder,
        trigger="cron",
        hour=12, minute=0,
        timezone="Europe/Moscow",
        args=[bot],
        id="morning_reminder",
        replace_existing=True
    )
    scheduler.add_job(
        job_evening_check,
        trigger="cron",
        hour=20, minute=0,
        timezone="Europe/Moscow",
        args=[bot],
        id="evening_check",
        replace_existing=True
    )
    logger.info("Scheduler configured: 12:00 and 20:00 MSK jobs.")
