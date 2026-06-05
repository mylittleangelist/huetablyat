import aiosqlite
import logging
import random
import shutil
from datetime import date, datetime, timedelta
from typing import Optional
import config as cfg

DB_PATH = str(cfg.DB_PATH)
logger = logging.getLogger(__name__)


def _table_count_sql(table: str) -> str:
    return f"SELECT COUNT(*) FROM {table}"


def _db_has_business_data(path: str) -> bool:
    try:
        import sqlite3

        with sqlite3.connect(path) as conn:
            cur = conn.cursor()
            total = 0
            for table in ("families", "personal_roles"):
                cur.execute(_table_count_sql(table))
                total += int(cur.fetchone()[0])
            return total > 0
    except Exception:
        return False


def _ensure_seed_database():
    source = cfg.BASE_DIR / "marketa.db"
    target = cfg.DB_PATH

    if source.resolve() == target.resolve():
        return
    if not source.exists():
        return

    source_has_data = _db_has_business_data(str(source))
    if not source_has_data:
        return

    if not target.exists():
        shutil.copy2(source, target)
        logger.warning("Seeded database from %s to %s", source, target)
        return

    target_has_data = _db_has_business_data(str(target))
    if not target_has_data:
        shutil.copy2(source, target)
        logger.warning("Replaced empty database at %s using seed %s", target, source)

CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS users (
    telegram_id   INTEGER PRIMARY KEY,
    username      TEXT,
    full_name     TEXT,
    role          TEXT CHECK(role IN ('gs','zgs','rm','watcher')),
    added_by      INTEGER,
    added_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS families (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    name              TEXT    NOT NULL,
    color_id          TEXT,
    discord_role_id   TEXT,
    owner_discord_id  TEXT,
    valid_until       DATE    NOT NULL,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS personal_roles (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    name              TEXT    NOT NULL,
    color_id          TEXT,
    discord_role_id   TEXT,
    owner_discord_id  TEXT,
    valid_until       DATE    NOT NULL,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reminder_chats (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id   INTEGER NOT NULL,
    thread_id INTEGER,
    label     TEXT
);

CREATE TABLE IF NOT EXISTS watcher_queue (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    watcher_telegram_id  INTEGER NOT NULL,
    position             INTEGER NOT NULL,
    cycle_id             INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS queue_state (
    id               INTEGER PRIMARY KEY CHECK(id=1),
    current_position INTEGER DEFAULT 0,
    current_cycle_id INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS daily_confirmations (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    conf_date            DATE    NOT NULL,
    watcher_telegram_id  INTEGER NOT NULL,
    remind_msg_id        INTEGER,
    remind_chat_id       INTEGER,
    remind_thread_id     INTEGER,
    confirm_msg_id       INTEGER,
    confirm_chat_id      INTEGER,
    confirm_thread_id    INTEGER,
    status               TEXT    DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""

async def init():
    cfg.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    _ensure_seed_database()
    async with aiosqlite.connect(DB_PATH) as db:
        for stmt in CREATE_TABLES.strip().split(";"):
            s = stmt.strip()
            if s:
                await db.execute(s)
        await db.execute(
            "INSERT OR IGNORE INTO queue_state(id, current_position, current_cycle_id) VALUES(1,0,0)"
        )
        await db.commit()
    logger.info("Database initialized at %s", DB_PATH)

async def get_user(telegram_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE telegram_id=?", (telegram_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

async def add_user(telegram_id: int, username: str, full_name: str, role: str, added_by: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO users(telegram_id,username,full_name,role,added_by) VALUES(?,?,?,?,?)",
            (telegram_id, username, full_name, role, added_by)
        )
        await db.commit()

async def remove_user(telegram_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM users WHERE telegram_id=?", (telegram_id,))
        await db.commit()

async def get_users_by_role(role: str) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE role=? ORDER BY added_at", (role,)) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

async def get_all_staff() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users ORDER BY CASE role WHEN 'gs' THEN 1 WHEN 'zgs' THEN 2 WHEN 'rm' THEN 3 WHEN 'watcher' THEN 4 END, added_at"
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

async def get_all_watchers() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE role IN ('gs', 'zgs', 'watcher')"
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

async def update_user_chat_id(telegram_id: int, chat_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET telegram_id=? WHERE telegram_id=?", (chat_id, telegram_id))
        await db.commit()

async def add_family(name: str, color_id: str, discord_role_id: str, owner_discord_id: str, valid_until: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO families(name,color_id,discord_role_id,owner_discord_id,valid_until) VALUES(?,?,?,?,?)",
            (name, color_id, discord_role_id, owner_discord_id, valid_until)
        )
        await db.commit()
        return cur.lastrowid

async def get_family(family_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM families WHERE id=?", (family_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

async def get_all_families() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM families ORDER BY id") as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

async def delete_family(family_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM families WHERE id=?", (family_id,))
        await db.commit()

async def extend_family(family_id: int, new_date: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE families SET valid_until=? WHERE id=?", (new_date, family_id))
        await db.commit()

async def get_expiring_families(days: int = 15) -> list[dict]:
    threshold = (date.today() + timedelta(days=days)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM families WHERE valid_until <= ? ORDER BY valid_until", (threshold,)
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

async def add_role(name: str, color_id: str, discord_role_id: str, owner_discord_id: str, valid_until: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO personal_roles(name,color_id,discord_role_id,owner_discord_id,valid_until) VALUES(?,?,?,?,?)",
            (name, color_id, discord_role_id, owner_discord_id, valid_until)
        )
        await db.commit()
        return cur.lastrowid

async def get_role(role_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM personal_roles WHERE id=?", (role_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

async def get_all_roles() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM personal_roles ORDER BY id") as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

async def delete_role(role_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM personal_roles WHERE id=?", (role_id,))
        await db.commit()

async def extend_role(role_id: int, new_date: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE personal_roles SET valid_until=? WHERE id=?", (new_date, role_id))
        await db.commit()

async def get_expiring_roles(days: int = 15) -> list[dict]:
    threshold = (date.today() + timedelta(days=days)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM personal_roles WHERE valid_until <= ? ORDER BY valid_until", (threshold,)
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

async def add_reminder_chat(chat_id: int, thread_id: Optional[int], label: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO reminder_chats(chat_id,thread_id,label) VALUES(?,?,?)",
            (chat_id, thread_id, label)
        )
        await db.commit()
        return cur.lastrowid

async def get_reminder_chats() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM reminder_chats") as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

async def delete_reminder_chat(rc_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM reminder_chats WHERE id=?", (rc_id,))
        await db.commit()

async def get_queue_state() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM queue_state WHERE id=1") as cur:
            row = await cur.fetchone()
            return dict(row) if row else {"current_position": 0, "current_cycle_id": 0}

async def set_queue_state(position: int, cycle_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE queue_state SET current_position=?, current_cycle_id=? WHERE id=1",
            (position, cycle_id)
        )
        await db.commit()

async def rebuild_queue(watchers: list[dict], cycle_id: int, last_watcher_id: int = None):
    """Shuffle watchers and store as new cycle.
    Если задан last_watcher_id — гарантирует, что он НЕ окажется первым.
    """
    ids = [w["telegram_id"] for w in watchers]
    random.shuffle(ids)
 
    if last_watcher_id and len(ids) > 1 and ids[0] == last_watcher_id:
        swap_idx = random.randint(1, len(ids) - 1)
        ids[0], ids[swap_idx] = ids[swap_idx], ids[0]
 
    async with aiosqlite.connect(DB_PATH) as db:
        # Queue is stored for the active cycle only.
        await db.execute("DELETE FROM watcher_queue")
        for pos, tid in enumerate(ids):
            await db.execute(
                "INSERT INTO watcher_queue(watcher_telegram_id,position,cycle_id) VALUES(?,?,?)",
                (tid, pos, cycle_id)
            )
        await db.commit()

async def ensure_queue_consistency() -> bool:
    """Ensure active queue matches current watcher list.
    Returns True if queue was rebuilt.
    """
    watchers = await get_all_watchers()
    state = await get_queue_state()
    cycle = state["current_cycle_id"]
    current_pos = state["current_position"]

    if not watchers:
        await set_queue_state(0, cycle)
        return False

    watcher_ids = [w["telegram_id"] for w in watchers]

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT watcher_telegram_id, position FROM watcher_queue WHERE cycle_id=? ORDER BY position",
            (cycle,)
        ) as cur:
            queue_rows = await cur.fetchall()

    queue_ids = [r["watcher_telegram_id"] for r in queue_rows]
    same_members = len(queue_ids) == len(watcher_ids) and set(queue_ids) == set(watcher_ids)

    if same_members:
        if queue_ids and current_pos >= len(queue_ids):
            await set_queue_state(0, cycle)
        return False

    last_watcher_id = None
    if queue_rows and current_pos > 0:
        prev_idx = min(current_pos - 1, len(queue_rows) - 1)
        last_watcher_id = queue_rows[prev_idx]["watcher_telegram_id"]

    new_cycle = cycle + 1
    await rebuild_queue(watchers, new_cycle, last_watcher_id=last_watcher_id)
    await set_queue_state(0, new_cycle)
    logger.warning(
        "Watcher queue rebuilt: members changed (%s -> %s), new cycle=%s",
        len(queue_ids), len(watcher_ids), new_cycle
    )
    return True

async def get_next_watcher() -> Optional[dict]:
    """Get next watcher in queue, rebuilding if needed."""
    state = await get_queue_state()
    pos = state["current_position"]
    cycle = state["current_cycle_id"]
 
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM watcher_queue WHERE cycle_id=? AND position=?", (cycle, pos)
        ) as cur:
            row = await cur.fetchone()
 
        if row is None:
            last_watcher_id = None
            if pos > 0:
                async with db.execute(
                    "SELECT watcher_telegram_id FROM watcher_queue WHERE cycle_id=? AND position=?",
                    (cycle, pos - 1)
                ) as cur:
                    last_row = await cur.fetchone()
                    if last_row:
                        last_watcher_id = last_row["watcher_telegram_id"]
 
            watchers = await get_all_watchers()
            if not watchers:
                return None
 
            new_cycle = cycle + 1
            await rebuild_queue(watchers, new_cycle, last_watcher_id=last_watcher_id)
            await set_queue_state(0, new_cycle)
            cycle = new_cycle
            pos = 0
 
            async with db.execute(
                "SELECT * FROM watcher_queue WHERE cycle_id=? AND position=?", (cycle, pos)
            ) as cur:
                row = await cur.fetchone()
 
            if not row:
                return None
 
        watcher_id = row["watcher_telegram_id"]
        await set_queue_state(pos + 1, cycle)
        return await get_user(watcher_id)

async def get_watcher_queue_position(telegram_id: int) -> Optional[int]:
    """Return how many slots until this watcher is next."""
    state = await get_queue_state()
    pos = state["current_position"]
    cycle = state["current_cycle_id"]
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT position FROM watcher_queue WHERE cycle_id=? AND watcher_telegram_id=?",
            (cycle, telegram_id)
        ) as cur:
            row = await cur.fetchone()
        if not row:
            return None
        watcher_pos = row["position"]
        if watcher_pos >= pos:
            return watcher_pos - pos
        # Already used in this cycle, next cycle
        async with db.execute(
            "SELECT COUNT(*) as cnt FROM watcher_queue WHERE cycle_id=?", (cycle,)
        ) as cur:
            total = (await cur.fetchone())["cnt"]
        return total - pos + watcher_pos

async def get_setting(key: str) -> Optional[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT value FROM settings WHERE key=?", (key,)) as cur:
            row = await cur.fetchone()
            return row["value"] if row else None

async def set_setting(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (key, value))
        await db.commit()

async def add_confirmation(conf_date: str, watcher_id: int,
                           remind_msg_id: int, remind_chat_id: int, remind_thread_id: Optional[int]) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """INSERT INTO daily_confirmations
               (conf_date,watcher_telegram_id,remind_msg_id,remind_chat_id,remind_thread_id)
               VALUES(?,?,?,?,?)""",
            (conf_date, watcher_id, remind_msg_id, remind_chat_id, remind_thread_id)
        )
        await db.commit()
        return cur.lastrowid

async def set_confirm_message(conf_id: int, msg_id: int, chat_id: int, thread_id: Optional[int]):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE daily_confirmations SET confirm_msg_id=?,confirm_chat_id=?,confirm_thread_id=? WHERE id=?",
            (msg_id, chat_id, thread_id, conf_id)
        )
        await db.commit()

async def update_confirmation_status(conf_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE daily_confirmations SET status=? WHERE id=?", (status, conf_id))
        await db.commit()

async def get_todays_confirmations() -> list[dict]:
    today = date.today().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM daily_confirmations WHERE conf_date=?", (today,)
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

async def get_confirmation(conf_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM daily_confirmations WHERE id=?", (conf_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None
        
async def update_user_nickname(telegram_id: int, new_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET full_name=? WHERE telegram_id=?",
            (new_name, telegram_id)
        )
        await db.commit()
