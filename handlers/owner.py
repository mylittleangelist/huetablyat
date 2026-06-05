import logging
from datetime import date, timedelta
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode

import database as db
import config as cfg
from utils import (
    can_use_owner_panel, can_assign_gs, can_assign_zgs,
    can_assign_rm, can_assign_watcher,
    days_until, format_date, parse_date_input, ROLE_LABELS
)
from keyboards.owner_kb import (
    get_owner_panel, get_owner_panel_owner, get_owner_panel_no_gs,
    get_cancel_kb, get_main_menu_owner, get_main_menu_watcher,
    get_extend_3m_type_kb
)

router = Router()
logger = logging.getLogger(__name__)

def em(emoji_id: str, fallback: str = "•") -> str:
    return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'

class FamilyCreate(StatesGroup):
    name = State()
    color_id = State()
    discord_role_id = State()
    owner_discord_id = State()
    valid_until = State()

class RoleCreate(StatesGroup):
    name = State()
    color_id = State()
    discord_role_id = State()
    owner_discord_id = State()
    valid_until = State()

class FamilyDelete(StatesGroup):
    number = State()

class RoleDelete(StatesGroup):
    number = State()

class FamilyExtend(StatesGroup):
    number = State()
    new_date = State()

class RoleExtend(StatesGroup):
    number = State()
    new_date = State()

class AssignUser(StatesGroup):
    target_role = State()
    username = State()
    user_id = State()

class FindChat(StatesGroup):
    chat_id = State()
    thread_id = State()
    label = State()

class RemoveWatcher(StatesGroup):
    number = State()

class RenameUser(StatesGroup):
    number = State()
    new_name = State()


class ExtendThreeMonths(StatesGroup):
    number = State()

async def check_owner_access(uid: int) -> tuple[bool, str | None]:
    user = await db.get_user(uid)
    if not user:
        return False, None
    if not can_use_owner_panel(user["role"]):
        return False, None
    return True, user["role"]

async def send_deny(message: Message):
    await message.answer(
        f'{em("5870657884844462243","❌")} <b>У вас нет доступа к этой функции.</b>',
        parse_mode=ParseMode.HTML
    )


def build_compact_item_lines(title_emoji_id: str, title: str, items: list[dict]) -> list[str]:
    lines = [f'{em(title_emoji_id, "•")} <b>{title}</b>\n']
    for item in items:
        d = days_until(item["valid_until"])
        lines.append(f'<b>#{item["id"]}</b> - {item["name"]} | до {format_date(item["valid_until"])} ({d} дн.)')
    return lines


def plus_ninety_days(valid_until: str) -> str | None:
    if valid_until == "9999-12-31":
        return None
    base_date = max(date.today(), date.fromisoformat(valid_until))
    return (base_date + timedelta(days=90)).isoformat()


@router.callback_query(F.data == "op_extend_3m")
async def op_extend_3m(callback: CallbackQuery, state: FSMContext):
    ok, _ = await check_owner_access(callback.from_user.id)
    if not ok:
        await callback.answer("Нет доступа", show_alert=True)
        return

    await state.clear()
    await callback.message.edit_text(
        f'{em("5890937706803894250","📅")} <b>Продление на 3 месяца</b>\n\n'
        f'{em("6028435952299413210","ℹ")} Выберите, что нужно продлить на <b>90 дней</b>:',
        parse_mode=ParseMode.HTML,
        reply_markup=get_extend_3m_type_kb()
    )
    await callback.answer()


@router.callback_query(F.data == "op_extend_3m_family")
async def op_extend_3m_family(callback: CallbackQuery, state: FSMContext):
    ok, _ = await check_owner_access(callback.from_user.id)
    if not ok:
        await callback.answer("Нет доступа", show_alert=True)
        return

    families = await db.get_all_families()
    if not families:
        await callback.message.edit_text(
            f'{em("6028435952299413210","ℹ")} <b>Семей нет.</b>',
            parse_mode=ParseMode.HTML
        )
        await callback.answer()
        return

    lines = build_compact_item_lines("5870772616305839506", "Список семей", families)
    lines.append(f'\n{em("5890937706803894250","📅")} Введите <b>номер</b> семьи для продления на <b>90 дней</b>:')
    await state.update_data(extend_3m_type="family")
    await state.set_state(ExtendThreeMonths.number)
    await callback.message.edit_text(
        "\n".join(lines),
        parse_mode=ParseMode.HTML,
        reply_markup=get_cancel_kb()
    )
    await callback.answer()


@router.callback_query(F.data == "op_extend_3m_role")
async def op_extend_3m_role(callback: CallbackQuery, state: FSMContext):
    ok, _ = await check_owner_access(callback.from_user.id)
    if not ok:
        await callback.answer("Нет доступа", show_alert=True)
        return

    roles = await db.get_all_roles()
    if not roles:
        await callback.message.edit_text(
            f'{em("6028435952299413210","ℹ")} <b>Ролей нет.</b>',
            parse_mode=ParseMode.HTML
        )
        await callback.answer()
        return

    lines = build_compact_item_lines("5870994129244131212", "Список ролей", roles)
    lines.append(f'\n{em("5890937706803894250","📅")} Введите <b>номер</b> роли для продления на <b>90 дней</b>:')
    await state.update_data(extend_3m_type="role")
    await state.set_state(ExtendThreeMonths.number)
    await callback.message.edit_text(
        "\n".join(lines),
        parse_mode=ParseMode.HTML,
        reply_markup=get_cancel_kb()
    )
    await callback.answer()


@router.message(ExtendThreeMonths.number)
async def extend_three_months_apply(message: Message, state: FSMContext):
    data = await state.get_data()
    target_type = data.get("extend_3m_type")

    try:
        item_id = int(message.text.strip())
    except ValueError:
        await message.answer(
            f'{em("5870657884844462243","❌")} Введите число.',
            parse_mode=ParseMode.HTML
        )
        return

    if target_type == "family":
        item = await db.get_family(item_id)
        if not item:
            await message.answer(
                f'{em("5870657884844462243","❌")} Семья #{item_id} не найдена.',
                parse_mode=ParseMode.HTML
            )
            return

        new_date = plus_ninety_days(item["valid_until"])
        if not new_date:
            await message.answer(
                f'{em("6028435952299413210","ℹ")} Семья <b>«{item["name"]}»</b> уже бессрочная.',
                parse_mode=ParseMode.HTML
            )
            return

        await db.extend_family(item_id, new_date)
        await state.clear()
        await message.answer(
            f'{em("5870633910337015697","✅")} Семья <b>«{item["name"]}»</b> продлена на <b>90 дней</b>.\n\n'
            f'{em("5890937706803894250","📅")} Новая дата: <b>{format_date(new_date)}</b>',
            parse_mode=ParseMode.HTML
        )
        return

    if target_type == "role":
        item = await db.get_role(item_id)
        if not item:
            await message.answer(
                f'{em("5870657884844462243","❌")} Роль #{item_id} не найдена.',
                parse_mode=ParseMode.HTML
            )
            return

        new_date = plus_ninety_days(item["valid_until"])
        if not new_date:
            await message.answer(
                f'{em("6028435952299413210","ℹ")} Роль <b>«{item["name"]}»</b> уже бессрочная.',
                parse_mode=ParseMode.HTML
            )
            return

        await db.extend_role(item_id, new_date)
        await state.clear()
        await message.answer(
            f'{em("5870633910337015697","✅")} Роль <b>«{item["name"]}»</b> продлена на <b>90 дней</b>.\n\n'
            f'{em("5890937706803894250","📅")} Новая дата: <b>{format_date(new_date)}</b>',
            parse_mode=ParseMode.HTML
        )
        return

    await state.clear()
    await message.answer(
        f'{em("5870657884844462243","❌")} <b>Не удалось определить тип продления.</b>',
        parse_mode=ParseMode.HTML
    )

@router.message(F.text == "Панель владельца")
async def open_owner_panel(message: Message):
    ok, role = await check_owner_access(message.from_user.id)
    if not ok:
        await send_deny(message)
        return

    if message.from_user.id == cfg.OWNER_ID:
        kb = get_owner_panel_owner()
    else:
        kb = get_owner_panel() if can_assign_gs(role) else get_owner_panel_no_gs()
    await message.answer(
        f'{em("5870982283724328568","⚙")} <b>Панель владельца</b>\n\nВыберите действие:',
        parse_mode=ParseMode.HTML,
        reply_markup=kb
    )

@router.callback_query(F.data == "op_cancel")
async def cancel_op(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        f'{em("5870657884844462243","❌")} <b>Действие отменено.</b>',
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

@router.callback_query(F.data == "op_create_family")
async def op_create_family(callback: CallbackQuery, state: FSMContext):
    ok, _ = await check_owner_access(callback.from_user.id)
    if not ok:
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.message.edit_text(
        f'{em("5870772616305839506","👥")} <b>Создание семьи</b>\n\n'
        f'Шаг 1/5 — Введите <b>название</b> семьи:',
        parse_mode=ParseMode.HTML,
        reply_markup=get_cancel_kb()
    )
    await state.set_state(FamilyCreate.name)
    await callback.answer()

@router.message(FamilyCreate.name)
async def fc_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await message.answer(
        f'{em("5886285355279193209","🏷")} Шаг 2/5 — Введите <b>Цвет (ID)</b> роли:',
        parse_mode=ParseMode.HTML,
        reply_markup=get_cancel_kb()
    )
    await state.set_state(FamilyCreate.color_id)

@router.message(FamilyCreate.color_id)
async def fc_color(message: Message, state: FSMContext):
    await state.update_data(color_id=message.text.strip())
    await message.answer(
        f'{em("5940433880585605708","🔨")} Шаг 3/5 — Введите <b>ID роли</b> (Discord):',
        parse_mode=ParseMode.HTML,
        reply_markup=get_cancel_kb()
    )
    await state.set_state(FamilyCreate.discord_role_id)

@router.message(FamilyCreate.discord_role_id)
async def fc_discord_role(message: Message, state: FSMContext):
    await state.update_data(discord_role_id=message.text.strip())
    await message.answer(
        f'{em("5870994129244131212","👤")} Шаг 4/5 — Введите <b>ID владельца</b> (Discord):',
        parse_mode=ParseMode.HTML,
        reply_markup=get_cancel_kb()
    )
    await state.set_state(FamilyCreate.owner_discord_id)

@router.message(FamilyCreate.owner_discord_id)
async def fc_owner(message: Message, state: FSMContext):
    await state.update_data(owner_discord_id=message.text.strip())
    await message.answer(
        f'{em("5890937706803894250","📅")} Шаг 5/5 — Введите <b>дату окончания</b> (дд.мм.гггг):',
        parse_mode=ParseMode.HTML,
        reply_markup=get_cancel_kb()
    )
    await state.set_state(FamilyCreate.valid_until)

@router.message(FamilyCreate.valid_until)
async def fc_date(message: Message, state: FSMContext):
    iso = parse_date_input(message.text)
    if not iso:
        await message.answer(
            f'{em("5870657884844462243","❌")} Неверный формат. Введите дату в формате <b>дд.мм.гггг</b>:',
            parse_mode=ParseMode.HTML
        )
        return
    data = await state.get_data()
    fid = await db.add_family(
        data["name"], data["color_id"], data["discord_role_id"],
        data["owner_discord_id"], iso
    )
    await state.clear()
    d_left = days_until(iso)
    await message.answer(
        f'{em("5870633910337015697","✅")} <b>Семья успешно создана!</b>\n\n'
        f'{em("5886285355279193209","🏷")} <b>Название:</b> {data["name"]}\n'
        f'{em("5940433880585605708","🔨")} <b>ID роли:</b> {data["discord_role_id"]}\n'
        f'{em("5870994129244131212","👤")} <b>Владелец:</b> {data["owner_discord_id"]}\n'
        f'{em("5890937706803894250","📅")} <b>До:</b> {format_date(iso)} ({d_left} дн.)\n'
        f'{em("6028435952299413210","ℹ")} <b>Номер в системе:</b> #{fid}',
        parse_mode=ParseMode.HTML
    )

@router.callback_query(F.data == "op_create_role")
async def op_create_role(callback: CallbackQuery, state: FSMContext):
    ok, _ = await check_owner_access(callback.from_user.id)
    if not ok:
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.message.edit_text(
        f'{em("5870994129244131212","👤")} <b>Создание персональной роли</b>\n\n'
        f'Шаг 1/5 — Введите <b>название</b> роли:',
        parse_mode=ParseMode.HTML,
        reply_markup=get_cancel_kb()
    )
    await state.set_state(RoleCreate.name)
    await callback.answer()

@router.message(RoleCreate.name)
async def rc_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await message.answer(
        f'{em("5886285355279193209","🏷")} Шаг 2/5 — Введите <b>Цвет (ID)</b>:',
        parse_mode=ParseMode.HTML, reply_markup=get_cancel_kb()
    )
    await state.set_state(RoleCreate.color_id)

@router.message(RoleCreate.color_id)
async def rc_color(message: Message, state: FSMContext):
    await state.update_data(color_id=message.text.strip())
    await message.answer(
        f'{em("5940433880585605708","🔨")} Шаг 3/5 — Введите <b>ID роли</b> (Discord):',
        parse_mode=ParseMode.HTML, reply_markup=get_cancel_kb()
    )
    await state.set_state(RoleCreate.discord_role_id)

@router.message(RoleCreate.discord_role_id)
async def rc_discord_role(message: Message, state: FSMContext):
    await state.update_data(discord_role_id=message.text.strip())
    await message.answer(
        f'{em("5870994129244131212","👤")} Шаг 4/5 — Введите <b>ID владельца</b> (Discord):',
        parse_mode=ParseMode.HTML, reply_markup=get_cancel_kb()
    )
    await state.set_state(RoleCreate.owner_discord_id)

@router.message(RoleCreate.owner_discord_id)
async def rc_owner(message: Message, state: FSMContext):
    await state.update_data(owner_discord_id=message.text.strip())
    await message.answer(
        f'{em("5890937706803894250","📅")} Шаг 5/5 — Введите <b>дату окончания</b> (дд.мм.гггг):',
        parse_mode=ParseMode.HTML, reply_markup=get_cancel_kb()
    )
    await state.set_state(RoleCreate.valid_until)

@router.message(RoleCreate.valid_until)
async def rc_date(message: Message, state: FSMContext):
    iso = parse_date_input(message.text)
    if not iso:
        await message.answer(
            f'{em("5870657884844462243","❌")} Неверный формат. Введите дату в формате <b>дд.мм.гггг</b>:',
            parse_mode=ParseMode.HTML
        )
        return
    data = await state.get_data()
    rid = await db.add_role(
        data["name"], data["color_id"], data["discord_role_id"],
        data["owner_discord_id"], iso
    )
    await state.clear()
    d_left = days_until(iso)
    await message.answer(
        f'{em("5870633910337015697","✅")} <b>Роль успешно создана!</b>\n\n'
        f'{em("5886285355279193209","🏷")} <b>Название:</b> {data["name"]}\n'
        f'{em("5940433880585605708","🔨")} <b>ID роли:</b> {data["discord_role_id"]}\n'
        f'{em("5870994129244131212","👤")} <b>Владелец:</b> {data["owner_discord_id"]}\n'
        f'{em("5890937706803894250","📅")} <b>До:</b> {format_date(iso)} ({d_left} дн.)\n'
        f'{em("6028435952299413210","ℹ")} <b>Номер в системе:</b> #{rid}',
        parse_mode=ParseMode.HTML
    )

@router.callback_query(F.data == "op_delete_family")
async def op_delete_family(callback: CallbackQuery, state: FSMContext):
    ok, _ = await check_owner_access(callback.from_user.id)
    if not ok:
        await callback.answer("Нет доступа", show_alert=True)
        return
    families = await db.get_all_families()
    if not families:
        await callback.message.edit_text(
            f'{em("6028435952299413210","ℹ")} <b>Семей нет.</b>', parse_mode=ParseMode.HTML
        )
        await callback.answer()
        return
    lines = [f'{em("5870772616305839506","👥")} <b>Список семей</b>\n']
    for f in families:
        d = days_until(f["valid_until"])
        lines.append(f'<b>#{f["id"]}</b> — {f["name"]} | до {format_date(f["valid_until"])} ({d} дн.)')
    lines.append(f'\n{em("5870875489362513438","🗑")} Введите <b>номер</b> семьи для удаления:')
    await callback.message.edit_text(
        "\n".join(lines), parse_mode=ParseMode.HTML, reply_markup=get_cancel_kb()
    )
    await state.set_state(FamilyDelete.number)
    await callback.answer()

@router.message(FamilyDelete.number)
async def fd_number(message: Message, state: FSMContext):
    try:
        fid = int(message.text.strip())
    except ValueError:
        await message.answer(f'{em("5870657884844462243","❌")} Введите число.', parse_mode=ParseMode.HTML)
        return
    family = await db.get_family(fid)
    if not family:
        await message.answer(f'{em("5870657884844462243","❌")} Семья #{fid} не найдена.', parse_mode=ParseMode.HTML)
        return
    await db.delete_family(fid)
    await state.clear()
    await message.answer(
        f'{em("5870633910337015697","✅")} Семья <b>#{fid} «{family["name"]}»</b> удалена.',
        parse_mode=ParseMode.HTML
    )

@router.callback_query(F.data == "op_delete_role")
async def op_delete_role(callback: CallbackQuery, state: FSMContext):
    ok, _ = await check_owner_access(callback.from_user.id)
    if not ok:
        await callback.answer("Нет доступа", show_alert=True)
        return
    roles = await db.get_all_roles()
    if not roles:
        await callback.message.edit_text(
            f'{em("6028435952299413210","ℹ")} <b>Ролей нет.</b>', parse_mode=ParseMode.HTML
        )
        await callback.answer()
        return
    lines = [f'{em("5870994129244131212","👤")} <b>Список ролей</b>\n']
    for r in roles:
        d = days_until(r["valid_until"])
        lines.append(f'<b>#{r["id"]}</b> — {r["name"]} | до {format_date(r["valid_until"])} ({d} дн.)')
    lines.append(f'\n{em("5870875489362513438","🗑")} Введите <b>номер</b> роли для удаления:')
    await callback.message.edit_text(
        "\n".join(lines), parse_mode=ParseMode.HTML, reply_markup=get_cancel_kb()
    )
    await state.set_state(RoleDelete.number)
    await callback.answer()

@router.message(RoleDelete.number)
async def rd_number(message: Message, state: FSMContext):
    try:
        rid = int(message.text.strip())
    except ValueError:
        await message.answer(f'{em("5870657884844462243","❌")} Введите число.', parse_mode=ParseMode.HTML)
        return
    role = await db.get_role(rid)
    if not role:
        await message.answer(f'{em("5870657884844462243","❌")} Роль #{rid} не найдена.', parse_mode=ParseMode.HTML)
        return
    await db.delete_role(rid)
    await state.clear()
    await message.answer(
        f'{em("5870633910337015697","✅")} Роль <b>#{rid} «{role["name"]}»</b> удалена.',
        parse_mode=ParseMode.HTML
    )

@router.callback_query(F.data == "op_extend_family")
async def op_extend_family(callback: CallbackQuery, state: FSMContext):
    ok, _ = await check_owner_access(callback.from_user.id)
    if not ok:
        await callback.answer("Нет доступа", show_alert=True)
        return
    families = await db.get_all_families()
    if not families:
        await callback.message.edit_text(
            f'{em("6028435952299413210","ℹ")} <b>Семей нет.</b>', parse_mode=ParseMode.HTML
        )
        await callback.answer()
        return
    lines = [f'{em("5890937706803894250","📅")} <b>Продление семьи</b>\n']
    for f in families:
        d = days_until(f["valid_until"])
        lines.append(f'<b>#{f["id"]}</b> — {f["name"]} | до {format_date(f["valid_until"])} ({d} дн.)')
    lines.append(f'\nВведите <b>номер</b> семьи для продления:')
    await callback.message.edit_text(
        "\n".join(lines), parse_mode=ParseMode.HTML, reply_markup=get_cancel_kb()
    )
    await state.set_state(FamilyExtend.number)
    await callback.answer()

@router.message(FamilyExtend.number)
async def fex_number(message: Message, state: FSMContext):
    try:
        fid = int(message.text.strip())
    except ValueError:
        await message.answer(f'{em("5870657884844462243","❌")} Введите число.', parse_mode=ParseMode.HTML)
        return
    family = await db.get_family(fid)
    if not family:
        await message.answer(f'{em("5870657884844462243","❌")} Семья #{fid} не найдена.', parse_mode=ParseMode.HTML)
        return
    await state.update_data(fid=fid, fname=family["name"])
    await message.answer(
        f'{em("5890937706803894250","📅")} Введите <b>новую дату окончания</b> для семьи «{family["name"]}» (дд.мм.гггг):',
        parse_mode=ParseMode.HTML, reply_markup=get_cancel_kb()
    )
    await state.set_state(FamilyExtend.new_date)

@router.message(FamilyExtend.new_date)
async def fex_date(message: Message, state: FSMContext):
    iso = parse_date_input(message.text)
    if not iso:
        await message.answer(
            f'{em("5870657884844462243","❌")} Неверный формат. Введите дату в формате <b>дд.мм.гггг</b>:',
            parse_mode=ParseMode.HTML
        )
        return
    data = await state.get_data()
    await db.extend_family(data["fid"], iso)
    await state.clear()
    await message.answer(
        f'{em("5870633910337015697","✅")} Семья <b>«{data["fname"]}»</b> продлена до <b>{format_date(iso)}</b>.',
        parse_mode=ParseMode.HTML
    )

@router.callback_query(F.data == "op_extend_role")
async def op_extend_role(callback: CallbackQuery, state: FSMContext):
    ok, _ = await check_owner_access(callback.from_user.id)
    if not ok:
        await callback.answer("Нет доступа", show_alert=True)
        return
    roles = await db.get_all_roles()
    if not roles:
        await callback.message.edit_text(
            f'{em("6028435952299413210","ℹ")} <b>Ролей нет.</b>', parse_mode=ParseMode.HTML
        )
        await callback.answer()
        return
    lines = [f'{em("5890937706803894250","📅")} <b>Продление роли</b>\n']
    for r in roles:
        d = days_until(r["valid_until"])
        lines.append(f'<b>#{r["id"]}</b> — {r["name"]} | до {format_date(r["valid_until"])} ({d} дн.)')
    lines.append('\nВведите <b>номер</b> роли для продления:')
    await callback.message.edit_text(
        "\n".join(lines), parse_mode=ParseMode.HTML, reply_markup=get_cancel_kb()
    )
    await state.set_state(RoleExtend.number)
    await callback.answer()

@router.message(RoleExtend.number)
async def rex_number(message: Message, state: FSMContext):
    try:
        rid = int(message.text.strip())
    except ValueError:
        await message.answer(f'{em("5870657884844462243","❌")} Введите число.', parse_mode=ParseMode.HTML)
        return
    role = await db.get_role(rid)
    if not role:
        await message.answer(f'{em("5870657884844462243","❌")} Роль #{rid} не найдена.', parse_mode=ParseMode.HTML)
        return
    await state.update_data(rid=rid, rname=role["name"])
    await message.answer(
        f'{em("5890937706803894250","📅")} Введите <b>новую дату окончания</b> для роли «{role["name"]}» (дд.мм.гггг):',
        parse_mode=ParseMode.HTML, reply_markup=get_cancel_kb()
    )
    await state.set_state(RoleExtend.new_date)

@router.message(RoleExtend.new_date)
async def rex_date(message: Message, state: FSMContext):
    iso = parse_date_input(message.text)
    if not iso:
        await message.answer(
            f'{em("5870657884844462243","❌")} Неверный формат. Введите дату в формате <b>дд.мм.гггг</b>:',
            parse_mode=ParseMode.HTML
        )
        return
    data = await state.get_data()
    await db.extend_role(data["rid"], iso)
    await state.clear()
    await message.answer(
        f'{em("5870633910337015697","✅")} Роль <b>«{data["rname"]}»</b> продлена до <b>{format_date(iso)}</b>.',
        parse_mode=ParseMode.HTML
    )

async def _start_assign(callback: CallbackQuery, state: FSMContext, target_role: str, label: str):
    await callback.message.edit_text(
        f'{em("5891207662678317861","👤")} <b>Назначение: {label}</b>\n\n'
        f'Введите данные в формате:\n<code>username Ник</code>\n\n'
        f'Например: <code>ivan123 Иван</code>',
        parse_mode=ParseMode.HTML,
        reply_markup=get_cancel_kb()
    )
    await state.update_data(target_role=target_role)
    await state.set_state(AssignUser.username)
    await callback.answer()

@router.callback_query(F.data == "op_assign_zgs")
async def op_assign_zgs(callback: CallbackQuery, state: FSMContext):
    user = await db.get_user(callback.from_user.id)
    if not user or not can_assign_zgs(user["role"]):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await _start_assign(callback, state, "zgs", "ЗГС Маркета")

@router.callback_query(F.data == "op_assign_rm")
async def op_assign_rm(callback: CallbackQuery, state: FSMContext):
    user = await db.get_user(callback.from_user.id)
    if not user or not can_assign_rm(user["role"]):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await _start_assign(callback, state, "rm", "Руководство Модерации")

@router.callback_query(F.data == "op_assign_watcher")
async def op_assign_watcher(callback: CallbackQuery, state: FSMContext):
    user = await db.get_user(callback.from_user.id)
    if not user or not can_assign_watcher(user["role"]):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await _start_assign(callback, state, "watcher", "Следящий Маркета")

@router.message(AssignUser.username)
async def assign_username(message: Message, state: FSMContext):
    parts = message.text.strip().split(None, 1)
    if len(parts) < 2:
        await message.answer(
            f'{em("5870657884844462243","❌")} Неверный формат. Введите: <code>username Ник</code>',
            parse_mode=ParseMode.HTML
        )
        return
    username, nick = parts[0].lstrip("@"), parts[1]
    data = await state.get_data()
    target_role = data["target_role"]

    async with __import__("aiosqlite").connect(db.DB_PATH) as db_conn:
        db_conn.row_factory = __import__("aiosqlite").Row
        async with db_conn.execute(
            "SELECT * FROM users WHERE username=?", (username,)
        ) as cur:
            existing = await cur.fetchone()

    if existing:
        existing = dict(existing)
        await db.add_user(existing["telegram_id"], username, nick, target_role, message.from_user.id)
        label = ROLE_LABELS.get(target_role, target_role)
        await state.clear()
        await message.answer(
            f'{em("5870633910337015697","✅")} <b>@{username}</b> назначен(а) как <b>{label}</b>.',
            parse_mode=ParseMode.HTML
        )
    else:
        await state.update_data(username=username, nick=nick)
        await message.answer(
            f'{em("6028435952299413210","ℹ")} На самом деле тут ошибка в коде и мне лень исправлять, введи <b>ID телеграма модера</b>\n\n'
            f'И кстати попроси есу написать /start в боте. by francisco lachowski',
            parse_mode=ParseMode.HTML,
            reply_markup=get_cancel_kb()
        )
        await state.set_state(AssignUser.user_id)

@router.message(AssignUser.user_id)
async def assign_user_id(message: Message, state: FSMContext):
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.answer(f'{em("5870657884844462243","❌")} Введите числовой ID.', parse_mode=ParseMode.HTML)
        return
    data = await state.get_data()
    username = data["username"]
    nick = data["nick"]
    target_role = data["target_role"]
    await db.add_user(uid, username, nick, target_role, message.from_user.id)
    label = ROLE_LABELS.get(target_role, target_role)
    await state.clear()
    await message.answer(
        f'{em("5870633910337015697","✅")} <b>@{username}</b> (ID: {uid}) назначен(а) как <b>{label}</b>.',
        parse_mode=ParseMode.HTML
    )

@router.callback_query(F.data == "op_find_chat")
async def op_find_chat(callback: CallbackQuery, state: FSMContext):
    ok, _ = await check_owner_access(callback.from_user.id)
    if not ok:
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.message.edit_text(
        f'{em("5769289093221454192","🔗")} <b>Настройка чата для напоминаний</b>\n\n'
        f'Введите <b>ID чата</b> (группы/супергруппы).\n'
        f'Чтобы узнать ID, добавьте бота в чат и перешлите любое сообщение из него боту @userinfobot',
        parse_mode=ParseMode.HTML,
        reply_markup=get_cancel_kb()
    )
    await state.set_state(FindChat.chat_id)
    await callback.answer()

@router.message(FindChat.chat_id)
async def fc_chat_id(message: Message, state: FSMContext):
    text = message.text.strip()
    try:
        chat_id = int(text)
    except ValueError:
        await message.answer(f'{em("5870657884844462243","❌")} Введите числовой ID чата.', parse_mode=ParseMode.HTML)
        return
    await state.update_data(chat_id=chat_id)
    await message.answer(
        f'{em("5769289093221454192","🔗")} Введите <b>ID топика</b> (thread_id) для отправки напоминаний.\n'
        f'Если чат без топиков — введите <code>0</code>:',
        parse_mode=ParseMode.HTML,
        reply_markup=get_cancel_kb()
    )
    await state.set_state(FindChat.thread_id)

@router.message(FindChat.thread_id)
async def fc_thread_id(message: Message, state: FSMContext):
    try:
        thread_id = int(message.text.strip())
    except ValueError:
        await message.answer(f'{em("5870657884844462243","❌")} Введите число (0 если без топика).', parse_mode=ParseMode.HTML)
        return
    await state.update_data(thread_id=thread_id if thread_id != 0 else None)
    await message.answer(
        f'{em("5870676941614354370","🖋")} Введите <b>название</b> для этого чата (для вашего удобства):',
        parse_mode=ParseMode.HTML,
        reply_markup=get_cancel_kb()
    )
    await state.set_state(FindChat.label)

@router.message(FindChat.label)
async def fc_label(message: Message, state: FSMContext):
    data = await state.get_data()
    rc_id = await db.add_reminder_chat(data["chat_id"], data.get("thread_id"), message.text.strip())
    await state.clear()
    await message.answer(
        f'{em("5870633910337015697","✅")} <b>Чат для напоминаний сохранён!</b>\n\n'
        f'{em("6028435952299413210","ℹ")} ID: {data["chat_id"]} | Топик: {data.get("thread_id","—")} | '
        f'Название: {message.text.strip()}',
        parse_mode=ParseMode.HTML
    )

@router.callback_query(F.data.startswith("confirm_"))
async def confirm_reminder(callback: CallbackQuery):
    conf_id = int(callback.data.split("_")[1])
    conf = await db.get_confirmation(conf_id)
    if not conf:
        await callback.answer("Запись не найдена.", show_alert=True)
        return

    watcher = await db.get_user(conf["watcher_telegram_id"])
    watcher_name = f'@{watcher["username"]}' if watcher and watcher.get("username") else f'Следящий'
    await db.update_confirmation_status(conf_id, "confirmed")

    await callback.message.edit_text(
        f'{em("5870633910337015697","✅")} <b>Подтверждено</b>\n\n'
        f'{em("5870994129244131212","👤")} {watcher_name} отправил(а) сообщение о продлении.',
        parse_mode=ParseMode.HTML
    )
    await callback.answer("Подтверждено ✅")

@router.callback_query(F.data.startswith("reject_"))
async def reject_reminder(callback: CallbackQuery):
    from aiogram import Bot
    conf_id = int(callback.data.split("_")[1])
    conf = await db.get_confirmation(conf_id)
    if not conf:
        await callback.answer("Запись не найдена.", show_alert=True)
        return

    watcher = await db.get_user(conf["watcher_telegram_id"])
    await db.update_confirmation_status(conf_id, "rejected")

    bot: Bot = callback.bot
    watcher_name = f'@{watcher["username"]}' if watcher and watcher.get("username") else "Следящий"
    watcher_mention = (
        f'<a href="tg://user?id={watcher["telegram_id"]}">{watcher_name}</a>'
        if watcher else watcher_name
    )

    reject_text = (
        f'{em("6039486778597970865","🔔")} {watcher_mention}, твоё сообщение о продлении <b>не было найдено</b>!\n\n'
        f'{em("5870657884844462243","❌")} Пожалуйста, отправь его <b>немедленно</b>.'
    )

    watcher_chat = await db.get_setting(f"chat_id_{conf['watcher_telegram_id']}")
    if watcher_chat:
        try:
            await bot.send_message(int(watcher_chat), reject_text, parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.warning(f"Could not send to watcher: {e}")

    reminder_chats = await db.get_reminder_chats()
    for rc in reminder_chats:
        try:
            kwargs = dict(chat_id=rc["chat_id"], text=reject_text, parse_mode=ParseMode.HTML)
            if rc.get("thread_id"):
                kwargs["message_thread_id"] = rc["thread_id"]
            await bot.send_message(**kwargs)
        except Exception as e:
            logger.warning(f"Could not send to reminder chat: {e}")

    await callback.message.edit_text(
        f'{em("5870657884844462243","❌")} <b>Отклонено</b> — повторное уведомление отправлено {watcher_mention}.',
        parse_mode=ParseMode.HTML
    )
    await callback.answer("Отклонено ❌")

@router.callback_query(F.data == "op_remove_watcher")
async def op_remove_watcher(callback: CallbackQuery, state: FSMContext):
    ok, _ = await check_owner_access(callback.from_user.id)
    if not ok:
        await callback.answer("Нет доступа", show_alert=True)
        return

    watchers = await db.get_users_by_role("watcher")
    if not watchers:
        await callback.message.edit_text(
            f'{em("6028435952299413210","ℹ")} <b>Следящих нет.</b>',
            parse_mode=ParseMode.HTML
        )
        await callback.answer()
        return

    lines = [f'{em("5893192487324880883","👤")} <b>Снятие следящего</b>\n']
    for i, w in enumerate(watchers, start=1):
        name = w.get("username") or w.get("full_name") or str(w["telegram_id"])
        lines.append(f'<b>{i}.</b> @{name} (ID: {w["telegram_id"]})')
    lines.append(f'\n{em("5870875489362513438","🗑")} Введите <b>номер</b> следящего для снятия:')

    await callback.message.edit_text(
        "\n".join(lines),
        parse_mode=ParseMode.HTML,
        reply_markup=get_cancel_kb()
    )
    await state.update_data(watchers_list=[w["telegram_id"] for w in watchers])
    await state.set_state(RemoveWatcher.number)
    await callback.answer()


@router.message(RemoveWatcher.number)
async def remove_watcher_number(message: Message, state: FSMContext):
    data = await state.get_data()
    watchers_list = data.get("watchers_list", [])

    try:
        num = int(message.text.strip())
        if num < 1 or num > len(watchers_list):
            raise ValueError
    except ValueError:
        await message.answer(
            f'{em("5870657884844462243","❌")} Введите число от 1 до {len(watchers_list)}.',
            parse_mode=ParseMode.HTML
        )
        return

    target_id = watchers_list[num - 1]
    target_user = await db.get_user(target_id)
    name = target_user.get("username") or target_user.get("full_name") or str(target_id)

    await db.remove_user(target_id)
    await state.clear()

    await message.answer(
        f'{em("5870633910337015697","✅")} Следящий <b>@{name}</b> снят с должности.',
        parse_mode=ParseMode.HTML
    )


@router.callback_query(F.data == "op_rename_user")
async def op_rename_user(callback: CallbackQuery, state: FSMContext):
    ok, _ = await check_owner_access(callback.from_user.id)
    if not ok:
        await callback.answer("Нет доступа", show_alert=True)
        return

    all_staff = await db.get_all_staff()
    if not all_staff:
        await callback.message.edit_text(
            f'{em("6028435952299413210","ℹ")} <b>Сотрудников нет.</b>',
            parse_mode=ParseMode.HTML
        )
        await callback.answer()
        return

    lines = [f'{em("5870676941614354370","🖋")} <b>Смена ника</b>\n']
    for i, s in enumerate(all_staff, start=1):
        name = s.get("username") or s.get("full_name") or str(s["telegram_id"])
        role_label = ROLE_LABELS.get(s["role"], s["role"])
        lines.append(f'<b>{i}.</b> @{name} — {role_label}')
    lines.append(f'\nВведите <b>номер</b> сотрудника для смены ника:')

    await callback.message.edit_text(
        "\n".join(lines),
        parse_mode=ParseMode.HTML,
        reply_markup=get_cancel_kb()
    )
    await state.update_data(staff_list=[s["telegram_id"] for s in all_staff])
    await state.set_state(RenameUser.number)
    await callback.answer()


@router.message(RenameUser.number)
async def rename_user_number(message: Message, state: FSMContext):
    data = await state.get_data()
    staff_list = data.get("staff_list", [])

    try:
        num = int(message.text.strip())
        if num < 1 or num > len(staff_list):
            raise ValueError
    except ValueError:
        await message.answer(
            f'{em("5870657884844462243","❌")} Введите число от 1 до {len(staff_list)}.',
            parse_mode=ParseMode.HTML
        )
        return

    target_id = staff_list[num - 1]
    target_user = await db.get_user(target_id)
    old_name = target_user.get("username") or target_user.get("full_name") or str(target_id)

    await state.update_data(target_id=target_id, old_name=old_name)
    await message.answer(
        f'{em("5870676941614354370","🖋")} Текущий ник: <b>@{old_name}</b>\n\n'
        f'Введите <b>новый ник</b> (без @):',
        parse_mode=ParseMode.HTML,
        reply_markup=get_cancel_kb()
    )
    await state.set_state(RenameUser.new_name)


@router.message(RenameUser.new_name)
async def rename_user_apply(message: Message, state: FSMContext):
    new_name = message.text.strip().lstrip("@")
    data = await state.get_data()
    target_id = data["target_id"]
    old_name = data["old_name"]

    await db.update_user_nickname(target_id, new_name)
    await state.clear()

    await message.answer(
        f'{em("5870633910337015697","✅")} Ник изменён: <b>@{old_name}</b> → <b>@{new_name}</b>',
        parse_mode=ParseMode.HTML
    )

@router.callback_query(F.data == "op_download_backup")
async def op_download_backup(callback: CallbackQuery):
    if callback.from_user.id != cfg.OWNER_ID:
        await callback.answer("Нет доступа", show_alert=True)
        return

    if not cfg.DB_PATH.exists():
        await callback.answer("Файл базы не найден", show_alert=True)
        return

    import sqlite3
    import tempfile
    from pathlib import Path

    backup_path = Path(tempfile.gettempdir()) / f"marketa-backup-{date.today().isoformat()}-{callback.from_user.id}.db"

    try:
        with sqlite3.connect(str(cfg.DB_PATH)) as source_conn:
            with sqlite3.connect(str(backup_path)) as backup_conn:
                source_conn.backup(backup_conn)

        await callback.message.answer_document(
            document=FSInputFile(
                path=str(backup_path),
                filename=f"marketa-backup-{date.today().isoformat()}.db"
            ),
            caption=(
                f'{em("6039802767931871481","⬇")} <b>Бекап базы данных</b>\n\n'
                f'{em("6028435952299413210","ℹ")} Отправлена актуальная копия базы '
                f'<code>{cfg.DB_PATH.name}</code>.'
            ),
            parse_mode=ParseMode.HTML
        )
        await callback.answer()
    except Exception as exc:
        logger.exception("Failed to create backup")
        await callback.answer(f"Ошибка бекапа: {exc}", show_alert=True)
    finally:
        if backup_path.exists():
            backup_path.unlink()
