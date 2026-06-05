from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton


def get_main_menu_owner() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Панель владельца", icon_custom_emoji_id="5870982283724328568")],
            [
                KeyboardButton(text="Статистика", icon_custom_emoji_id="5870921681735781843"),
                KeyboardButton(text="Состав", icon_custom_emoji_id="5870772616305839506"),
            ],
            [
                KeyboardButton(text="Текст для продления", icon_custom_emoji_id="5870676941614354370"),
                KeyboardButton(text="Когда отправить", icon_custom_emoji_id="5890937706803894250"),
            ],
        ],
        resize_keyboard=True
    )


def get_main_menu_watcher() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Статистика", icon_custom_emoji_id="5870921681735781843"),
                KeyboardButton(text="Состав", icon_custom_emoji_id="5870772616305839506"),
            ],
            [
                KeyboardButton(text="Текст для продления", icon_custom_emoji_id="5870676941614354370"),
                KeyboardButton(text="Когда отправить", icon_custom_emoji_id="5890937706803894250"),
            ],
        ],
        resize_keyboard=True
    )


def get_owner_panel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Создать семью", callback_data="op_create_family",
                                 icon_custom_emoji_id="5870772616305839506"),
            InlineKeyboardButton(text="Создать роль", callback_data="op_create_role",
                                 icon_custom_emoji_id="5870994129244131212"),
        ],
        [
            InlineKeyboardButton(text="Удалить семью", callback_data="op_delete_family",
                                 icon_custom_emoji_id="5870875489362513438"),
            InlineKeyboardButton(text="Удалить роль", callback_data="op_delete_role",
                                 icon_custom_emoji_id="5870875489362513438"),
        ],
        [
            InlineKeyboardButton(text="Продлить семью", callback_data="op_extend_family",
                                 icon_custom_emoji_id="5890937706803894250"),
            InlineKeyboardButton(text="Продлить роль", callback_data="op_extend_role",
                                 icon_custom_emoji_id="5890937706803894250"),
        ],
        [
            InlineKeyboardButton(text="Продлить на 3 месяца", callback_data="op_extend_3m",
                                 icon_custom_emoji_id="5890937706803894250"),
        ],
        [
            InlineKeyboardButton(text="Назначить ЗГС", callback_data="op_assign_zgs",
                                 icon_custom_emoji_id="5891207662678317861"),
            InlineKeyboardButton(text="Назначить Рук. Мод.", callback_data="op_assign_rm",
                                 icon_custom_emoji_id="5891207662678317861"),
        ],
        [
            InlineKeyboardButton(text="Назначить Следящего", callback_data="op_assign_watcher",
                                 icon_custom_emoji_id="5870994129244131212"),
        ],
        [
            InlineKeyboardButton(text="Снять Следящего", callback_data="op_remove_watcher",
                                 icon_custom_emoji_id="5893192487324880883"),
            InlineKeyboardButton(text="Сменить ник", callback_data="op_rename_user",
                                 icon_custom_emoji_id="5870676941614354370"),
        ],
        [
            InlineKeyboardButton(text="Найти чат", callback_data="op_find_chat",
                                 icon_custom_emoji_id="5769289093221454192"),
        ],
    ])


def get_owner_panel_owner() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        *get_owner_panel().inline_keyboard,
        [
            InlineKeyboardButton(text="Скачать бекап", callback_data="op_download_backup",
                                 icon_custom_emoji_id="6039802767931871481"),
        ],
    ])


def get_owner_panel_no_gs() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Создать семью", callback_data="op_create_family",
                                 icon_custom_emoji_id="5870772616305839506"),
            InlineKeyboardButton(text="Создать роль", callback_data="op_create_role",
                                 icon_custom_emoji_id="5870994129244131212"),
        ],
        [
            InlineKeyboardButton(text="Удалить семью", callback_data="op_delete_family",
                                 icon_custom_emoji_id="5870875489362513438"),
            InlineKeyboardButton(text="Удалить роль", callback_data="op_delete_role",
                                 icon_custom_emoji_id="5870875489362513438"),
        ],
        [
            InlineKeyboardButton(text="Продлить семью", callback_data="op_extend_family",
                                 icon_custom_emoji_id="5890937706803894250"),
            InlineKeyboardButton(text="Продлить роль", callback_data="op_extend_role",
                                 icon_custom_emoji_id="5890937706803894250"),
        ],
        [
            InlineKeyboardButton(text="Продлить на 3 месяца", callback_data="op_extend_3m",
                                 icon_custom_emoji_id="5890937706803894250"),
        ],
        [
            InlineKeyboardButton(text="Назначить Рук. Мод.", callback_data="op_assign_rm",
                                 icon_custom_emoji_id="5891207662678317861"),
            InlineKeyboardButton(text="Назначить Следящего", callback_data="op_assign_watcher",
                                 icon_custom_emoji_id="5870994129244131212"),
        ],
        [
            InlineKeyboardButton(text="Найти чат", callback_data="op_find_chat",
                                 icon_custom_emoji_id="5769289093221454192"),
        ],
    ])


def get_cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Отмена", callback_data="op_cancel",
                              icon_custom_emoji_id="5870657884844462243")]
    ])


def get_extend_3m_type_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Семья", callback_data="op_extend_3m_family",
                                 icon_custom_emoji_id="5870772616305839506"),
            InlineKeyboardButton(text="Роль", callback_data="op_extend_3m_role",
                                 icon_custom_emoji_id="5870994129244131212"),
        ],
        [
            InlineKeyboardButton(text="Отмена", callback_data="op_cancel",
                                 icon_custom_emoji_id="5870657884844462243"),
        ]
    ])


def get_confirmation_kb(conf_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Подтвердить", callback_data=f"confirm_{conf_id}",
                                 icon_custom_emoji_id="5870633910337015697"),
            InlineKeyboardButton(text="Отклонить", callback_data=f"reject_{conf_id}",
                                 icon_custom_emoji_id="5870657884844462243"),
        ]
    ])


def get_reminder_chat_select_kb(chats: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for c in chats:
        label = c.get("label") or f"Chat {c['chat_id']}"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"sel_chat_{c['id']}",
                                          icon_custom_emoji_id="5769289093221454192")])
    rows.append([InlineKeyboardButton(text="Добавить новый чат", callback_data="op_find_chat",
                                      icon_custom_emoji_id="5870676941614354370")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
