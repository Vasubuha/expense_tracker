
import os
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Database configuration
DB_PATH = Path(
    os.getenv(
        "EXPENSE_DB_PATH",
        str(
            Path(tempfile.gettempdir())
            / "talora"
            / "expense_tracker.db"
        )
    )
)

# Categories configuration
CATEGORIES_PATH = Path(
    os.getenv(
        "CATEGORIES_PATH",
        str(BASE_DIR / "categories.json")
    )
)

# Logging configuration
LOG_DIR = Path(tempfile.gettempdir()) / "talora" / "logs"

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Database configuration
DB_TIMEOUT = int(os.getenv("DB_TIMEOUT", "30"))

# Pagination
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200

# Validation limits
MAX_NOTE_LENGTH = 500
MAX_CATEGORY_LENGTH = 50
MAX_SUBCATEGORY_LENGTH = 50
