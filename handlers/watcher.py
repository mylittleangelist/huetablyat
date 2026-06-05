import logging
from datetime import date, timedelta
from aiogram import Router, F
from aiogram.types import Message
from aiogram.enums import ParseMode

import config as cfg
import database as db
from utils import (
    days_until, format_date, ROLE_LABELS,
    build_family_reminder_text, build_role_reminder_text,
    should_send_today
)

router = Router()
logger = logging.getLogger(__name__)

def em(emoji_id: str, fallback: str = "•") -> str:
    return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'

TELEGRAM_HTML_LIMIT = 3800

def split_html_lines(lines: list[str], limit: int = TELEGRAM_HTML_LIMIT) -> list[str]:
    """Split message into safe chunks by line, respecting Telegram length limits."""
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for line in lines:
        line_len = len(line)
        sep_len = 1 if current else 0

        # Hard split extremely long line (edge case).
        if line_len > limit:
            if current:
                chunks.append("\n".join(current))
                current = []
                current_len = 0
            start = 0
            while start < line_len:
                chunks.append(line[start:start + limit])
                start += limit
            continue

        if current_len + sep_len + line_len > limit:
            chunks.append("\n".join(current))
            current = [line]
            current_len = line_len
        else:
            current.append(line)
            current_len += sep_len + line_len

    if current:
        chunks.append("\n".join(current))

    return chunks

async def send_chunked_html(message: Message, lines: list[str]):
    for chunk in split_html_lines(lines):
        await message.answer(chunk, parse_mode=ParseMode.HTML, disable_web_page_preview=True)


@router.message(F.text == "Статистика")
async def cmd_statistics(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user:
        return

    families = await db.get_all_families()
    roles = await db.get_all_roles()

    summary_lines = [
        f'{em("5870921681735781843","📊")} <b>Статистика Маркета</b>',
        "",
        f'{em("5870772616305839506","👥")} Семьи: <b>{len(families)}</b>',
        f'{em("5870994129244131212","👤")} Персональные роли: <b>{len(roles)}</b>',
    ]
    await send_chunked_html(message, summary_lines)

    families_lines = [f'{em("5870772616305839506","👥")} <b>Статистика семей ({len(families)})</b>', ""]
    if families:
        for f in families:
            d = days_until(f["valid_until"])
            warn = f' {em("5983150113483134607","⏰")}' if d <= 15 else ""
            families_lines.extend([
                f'{em("5870528606328852614","📁")} <b>#{f["id"]}</b> <b>{f["name"]}</b>{warn}',
                f'{em("5886285355279193209","🏷")} Цвет ID: {f["color_id"]}',
                f'{em("5940433880585605708","🔨")} Discord роль: {f["discord_role_id"]}',
                f'{em("5870994129244131212","👤")} Владелец: {f["owner_discord_id"]}',
                f'{em("5890937706803894250","📅")} До: {format_date(f["valid_until"])} — осталось <b>{d} дн.</b>',
                ""
            ])
    else:
        families_lines.append(f'{em("6028435952299413210","ℹ")} <i>Семей нет</i>')
    await send_chunked_html(message, families_lines)

    roles_lines = [f'{em("5870994129244131212","👤")} <b>Статистика ролей ({len(roles)})</b>', ""]
    if roles:
        for r in roles:
            d = days_until(r["valid_until"])
            warn = f' {em("5983150113483134607","⏰")}' if d <= 15 else ""
            roles_lines.extend([
                f'{em("5870528606328852614","📁")} <b>#{r["id"]}</b> <b>{r["name"]}</b>{warn}',
                f'{em("5886285355279193209","🏷")} Цвет ID: {r["color_id"]}',
                f'{em("5940433880585605708","🔨")} Discord роль: {r["discord_role_id"]}',
                f'{em("5870994129244131212","👤")} Владелец: {r["owner_discord_id"]}',
                f'{em("5890937706803894250","📅")} До: {format_date(r["valid_until"])} — осталось <b>{d} дн.</b>',
                ""
            ])
    else:
        roles_lines.append(f'{em("6028435952299413210","ℹ")} <i>Ролей нет</i>')
    await send_chunked_html(message, roles_lines)



@router.message(F.text == "Текст для продления")
async def cmd_renewal_text(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user:
        return

    exp_families = await db.get_expiring_families(15)
    exp_roles = await db.get_expiring_roles(15)

    if not exp_families and not exp_roles:
        await message.answer(
            f'{em("5870633910337015697","✅")} <b>Нет истекающих записей</b>\n\n'
            f'Все семьи и роли действительны более 15 дней.',
            parse_mode=ParseMode.HTML
        )
        return

    msgs = []

    if exp_families:
        text = build_family_reminder_text(exp_families)
        msgs.append(
            f'{em("5870772616305839506","👥")} <b>Текст для семей</b> (нажми чтобы скопировать):\n\n'
            f'<code>{text}</code>'
        )

    if exp_roles:
        text = build_role_reminder_text(exp_roles)
        msgs.append(
            f'{em("5870994129244131212","👤")} <b>Текст для ролей</b> (нажми чтобы скопировать):\n\n'
            f'<code>{text}</code>'
        )

    for msg in msgs:
        await message.answer(msg, parse_mode=ParseMode.HTML)



@router.message(F.text == "Когда отправить")
async def cmd_when_to_send(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user:
        return

    exp_families = await db.get_expiring_families(15)
    exp_roles = await db.get_expiring_roles(15)

    if not exp_families and not exp_roles:
        await message.answer(
            f'{em("5890937706803894250","📅")} <b>Напоминание не требуется</b>\n\n'
            f'Нет записей с истечением в течение 15 дней.',
            parse_mode=ParseMode.HTML
        )
        return

    last_send = await db.get_setting("last_send_date")
    await db.ensure_queue_consistency()
    state = await db.get_queue_state()
    watchers = await db.get_all_watchers()

    lines = [f'{em("5890937706803894250","📅")} <b>Информация об очереди</b>\n']

    if should_send_today(last_send):
        lines.append(f'{em("6039486778597970865","🔔")} Сегодня — <b>день отправки</b> (12:00 МСК)')
    else:
        last_d = date.fromisoformat(last_send) if last_send else date.today()
        next_d = last_d + timedelta(days=2)
        lines.append(f'{em("5983150113483134607","⏰")} Следующая отправка: <b>{next_d.strftime("%d.%m.%Y")}</b>')


    if user["role"] == "watcher" and watchers:
        pos = await db.get_watcher_queue_position(message.from_user.id)
        if pos is not None:
            lines.append(f'\n{em("5870994129244131212","👤")} Ваша позиция в очереди: <b>#{pos + 1}</b>')
            if pos == 0:
                lines.append(f'{em("5870633910337015697","✅")} Вы <b>следующий</b> на отправку!')
        else:
            lines.append(f'\n{em("6028435952299413210","ℹ")} Вы будете добавлены в очередь при следующем цикле отправки.')


    if exp_families:
        lines.append(f'\n{em("5870772616305839506","👥")} <b>Истекающие семьи ({len(exp_families)}):</b>')
        for f in exp_families:
            d = days_until(f["valid_until"])
            lines.append(f'  • {f["name"]} — <b>{d} дн.</b>')

    if exp_roles:
        lines.append(f'\n{em("5870994129244131212","👤")} <b>Истекающие роли ({len(exp_roles)}):</b>')
        for r in exp_roles:
            d = days_until(r["valid_until"])
            lines.append(f'  • {r["name"]} - до оплаты <b>{d} дн.</b>')


    all_watchers = await db.get_all_watchers()
    if all_watchers:
        lines.append(f'\n{em("5890937706803894250","📅")} <b>Расписание очереди:</b>')


        if last_send:
            base_date = date.fromisoformat(last_send) + timedelta(days=cfg.SEND_INTERVAL_DAYS)
        else:
            base_date = date.today()


        queue_state = await db.get_queue_state()
        cycle_id = queue_state["current_cycle_id"]
        current_pos = queue_state["current_position"]


        import aiosqlite
        async with aiosqlite.connect(db.DB_PATH) as dbc:
            dbc.row_factory = aiosqlite.Row
            async with dbc.execute(
                "SELECT * FROM watcher_queue WHERE cycle_id=? ORDER BY position",
                (cycle_id,)
            ) as cur:
                queue_rows = await cur.fetchall()
                queue_rows = [dict(r) for r in queue_rows]

        if queue_rows:

            remaining = [r for r in queue_rows if r["position"] >= current_pos]
            already_done = [r for r in queue_rows if r["position"] < current_pos]

            ordered = remaining + already_done

            for i, row in enumerate(ordered):
                w = await db.get_user(row["watcher_telegram_id"])
                if not w:
                    continue
                send_date = base_date + timedelta(days=i * cfg.SEND_INTERVAL_DAYS)
                name = w.get("full_name") or w.get("username") or str(w["telegram_id"])
                username = w.get("username")


                if send_date == date.today():
                    mark = '  <b>сегодня</b>'
                elif i == 0:
                    mark = '  <b>следующий</b>'
                else:
                    mark = ''

                if username:
                    mention = f'<a href="https://t.me/{username}">{name}</a>'
                else:
                    mention = f'<a href="tg://user?id={w["telegram_id"]}">{name}</a>'

                lines.append(
                    f'  <b>{send_date.strftime("%d.%m.%Y")}</b> - {mention}{mark}'
                )
        else:
            lines.append('  <i>Очереди еще нету</i>')

    await message.bot.send_message(
        chat_id=message.chat.id,
        text="\n".join(lines),
        parse_mode="HTML",
        disable_web_page_preview=True
    )



@router.message(F.text == "Состав")
async def cmd_staff(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user:
        return

    staff = await db.get_all_staff()

    role_sections = {
        "gs":      (f'{em("5870994129244131212","👤")} ГС Маркета',       []),
        "zgs":     (f'{em("5891207662678317861","👤")} ЗГС Маркета',      []),
        "rm":      (f'{em("5891207662678317861","🛡")} Руководство Мод.', []),
        "watcher": (f'{em("5870994129244131212","👥")} Следящие Маркета', []),
    }

    for s in staff:
        role = s["role"]
        if role in role_sections:
            display = s.get("full_name") or s.get("username") or str(s["telegram_id"])
            username = s.get("username")
            if username:
                mention = f'<a href="https://t.me/{username}">{display}</a>'
            else:
                mention = display
            role_sections[role][1].append(mention)

    lines = [f'{em("5870772616305839506","👥")} <b>Состав Следящих Маркета</b>\n']
    for role_key in ("gs", "zgs", "rm", "watcher"):
        label, members = role_sections[role_key]
        lines.append(f'<b>{label}</b>')
        if members:
            for m in members:
                lines.append(f'  • {m}')
        else:
            lines.append('  <i>Нет следящих</i>')
        lines.append("")

    await message.bot.send_message(
        chat_id=message.chat.id,
        text="\n".join(lines),
        parse_mode="HTML",
        disable_web_page_preview=True
    )
