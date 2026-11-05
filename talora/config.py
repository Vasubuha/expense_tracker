import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

DB_PATH = Path(
    os.getenv(
        "EXPENSE_DB_PATH",
        str(Path(tempfile.gettempdir()) / "talora" / "expense_tracker.db")
    )
)

CATEGORIES_PATH = Path(
    os.getenv(
        "CATEGORIES_PATH",
        str(BASE_DIR / "categories.json")
    )
)

import tempfile

LOG_DIR = Path(tempfile.gettempdir()) / "talora" / "logs"

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

DB_TIMEOUT = int(os.getenv("DB_TIMEOUT", "30"))

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200

MAX_NOTE_LENGTH = 500
MAX_CATEGORY_LENGTH = 50
MAX_SUBCATEGORY_LENGTH = 50