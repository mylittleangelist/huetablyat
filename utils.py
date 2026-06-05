from datetime import date, datetime
from typing import Optional
import config as cfg

ROLE_LABELS = {
    "gs":      "ГС Маркета",
    "zgs":     "ЗГС Маркета",
    "rm":      "Руководство Модерации",
    "watcher": "Следящий Маркета",
}

ROLE_EMOJI = {
    "gs":      ("👑", "5870994129244131212"),
    "zgs":     ("⭐", "5870994129244131212"),
    "rm":      ("🛡", "5891207662678317861"),
    "watcher": ("👤", "5870994129244131212"),
}

def can_use_owner_panel(role: str) -> bool:
    return role in ("gs", "zgs", "rm")

def can_assign_gs(role: str) -> bool:
    return role == "gs"

def can_assign_zgs(role: str) -> bool:
    return role == "gs"

def can_assign_rm(role: str) -> bool:
    return role in ("gs", "zgs", "rm")

def can_assign_watcher(role: str) -> bool:
    return role in ("gs", "zgs", "rm")

def days_until(date_str: str) -> int:
    d = datetime.strptime(date_str, "%Y-%m-%d").date()
    return (d - date.today()).days

def format_date(date_str: str) -> str:
    d = datetime.strptime(date_str, "%Y-%m-%d").date()
    return d.strftime("%d.%m.%Y")

def parse_date_input(text: str) -> Optional[str]:
    """Parse dd.mm.yyyy → yyyy-mm-dd. Returns None if invalid."""
    try:
        d = datetime.strptime(text.strip(), "%d.%m.%Y").date()
        return d.isoformat()
    except ValueError:
        return None

def mention_user(username: str, telegram_id: int) -> str:
    """Return HTML hyperlink mention."""
    name = f"@{username}" if username else f"#{telegram_id}"
    return f'<a href="tg://user?id={telegram_id}">{name}</a>'

def build_family_reminder_text(families: list[dict]) -> str:
    if not families:
        return ""
    middle = "\n".join(
        f'&lt;@{f["owner_discord_id"]}&gt; оплатите свою семейную роль "{f["name"]}" до {format_date(f["valid_until"])}'
        for f in families
    )
    return (
        "Приветствую уважаемый пользователь нашего Discord Market!\n"
        "Пришло время для продления ваших семейных ролей.\n\n"
        f"{middle}\n\n"
        "Если вы не заполните заявку до указанной даты - ваша семья будет удалена.\n"
        f"Если вы хотите отказаться от оплаты, напишите в личные сообщения - &lt;@{cfg.DISCORD_CONTACT_ID}&gt;\n\n"
        "Стоимость продления роли на данный момент составляет - 3.000.000$\n"
        "Максимально роль можно продлить до 3-ех месяцев!"
    )

def build_role_reminder_text(roles: list[dict]) -> str:
    if not roles:
        return ""
    middle = "\n".join(
        f'&lt;@{r["owner_discord_id"]}&gt; оплатите свою персональную роль "{r["name"]}" до {format_date(r["valid_until"])}'
        for r in roles
    )
    return (
        "Приветствую уважаемый пользователь нашего Discord Market!\n"
        "Пришло время для продления ваших персональных ролей.\n\n"
        f"{middle}\n\n"
        "Если вы не заполните заявку до указанной даты - ваша роль будет удалена.\n"
        f"Если вы хотите отказаться от оплаты, напишите в личные сообщения - &lt;@{cfg.DISCORD_CONTACT_ID}&gt;\n\n"
        "Стоимость продления роли на данный момент составляет - 3.000.000$\n"
        "Максимально роль можно продлить до 3-ех месяцев!"
    )
def should_send_today(last_send_date_str: Optional[str]) -> bool:
    """True if ≥ SEND_INTERVAL_DAYS since last send, or never sent."""
    if not last_send_date_str:
        return True
    last = datetime.strptime(last_send_date_str, "%Y-%m-%d").date()
    return (date.today() - last).days >= cfg.SEND_INTERVAL_DAYS
