import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
OWNER_ID: int = int(os.getenv("OWNER_ID", "0"))
GROUP_IDS: list[int] = [
    int(x.strip()) for x in os.getenv("GROUP_IDS", "").split(",") if x.strip()
]

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(
    os.getenv("DATA_DIR")
    or os.getenv("RAILWAY_VOLUME_MOUNT_PATH")
    or BASE_DIR
)
DB_PATH = Path(os.getenv("DB_PATH") or (DATA_DIR / "marketa.db"))

# ид того с кем должны связаться если проблемы
DISCORD_CONTACT_ID = "835166731223302204" 
DAYS_THRESHOLD = 15  # со скольки дней должен создать упоминание
SEND_INTERVAL_DAYS = 2  # кд дней между отправкой
