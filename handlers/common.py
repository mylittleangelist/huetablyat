import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart, Command
from aiogram.enums import ParseMode

import database as db
import config as cfg
from utils import can_use_owner_panel, ROLE_LABELS
from keyboards.owner_kb import get_main_menu_owner, get_main_menu_watcher

router = Router()
logger = logging.getLogger(__name__)

def em(emoji_id: str, fallback: str = "•") -> str:
    return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'

@router.message(CommandStart())
async def cmd_start(message: Message):
    uid = message.from_user.id

    if uid == cfg.OWNER_ID:
        existing = await db.get_user(uid)
        if not existing:
            await db.add_user(
                uid,
                message.from_user.username or "",
                message.from_user.full_name,
                "gs",
                uid
            )

    user = await db.get_user(uid)
    if not user:
        await message.answer(
            f'{em("5870657884844462243","❌")} <b>У вас нет доступа к боту.</b>\n\n'
            f'Обратитесь к руководству для получения роли.',
            parse_mode=ParseMode.HTML
        )
        return

    role = user["role"]
    role_label = ROLE_LABELS.get(role, role)

    # созраняет либо получает ид чата
    await db.set_setting(f"chat_id_{uid}", str(message.chat.id))

    if can_use_owner_panel(role):
        kb = get_main_menu_owner()
    else:
        kb = get_main_menu_watcher()

    await message.answer(
        f'{em("5873147866364514353","🏠")} <b>Добро пожаловать, {message.from_user.first_name}!</b>\n\n'
        f'{em("5870994129244131212","👤")} Ваша роль: <b>{role_label}</b>\n\n'
        f'Выберите действие из меню ниже.',
        parse_mode=ParseMode.HTML,
        reply_markup=kb
    )

@router.message(Command("help"))
async def cmd_help(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user:
        return
    role = user["role"]
    lines = [
        f'{em("6028435952299413210","ℹ")} <b>Справка по боту для следящих маркета</b>\n',
        f'<b>Твоя роль:</b> {ROLE_LABELS.get(role, role)}\n',
    ]
    if can_use_owner_panel(role):
        lines.append(
            '📋 <b>Команды панели гс/згс:</b>\n'
            '• Создать/удалить/продлить семью или роль\n'
            '• Назначать следящиэ\n'
            '• Настроить чат для напоминаний\n'
        )
    lines.append(
        '📊 <b>Функции следящего:</b>\n'
        '• Статистика - показывает роли и семьи\n'
        '• Текст для продления - текст который нужно отправить\n'
        '• Когда отправить - показывает расписание для следящиэ\n'
        '• Состав — список следящих\n'
    )
    await message.answer("\n".join(lines), parse_mode=ParseMode.HTML)

@router.message(F.text == "/checkdb")
async def cmd_checkdb(message: Message):
    if message.from_user.id != cfg.OWNER_ID:
        return
    staff = await db.get_all_staff()
    lines = []
    for s in staff:
        lines.append(f'ID: {s["telegram_id"]} | username: "{s["username"]}" | full_name: "{s["full_name"]}"')
    await message.answer("\n".join(lines) or "Пусто")