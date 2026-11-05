
import aiosqlite
from contextlib import asynccontextmanager

from config import DB_PATH, DB_TIMEOUT


async def get_connection():
    conn = await aiosqlite.connect(
        DB_PATH,
        timeout=DB_TIMEOUT
    )

    conn.row_factory = aiosqlite.Row

    await conn.execute("PRAGMA foreign_keys = ON")
    await conn.execute("PRAGMA busy_timeout = 30000")

    return conn


@asynccontextmanager
async def get_db():
    conn = await get_connection()

    try:
        yield conn
        await conn.commit()

    except Exception:
        await conn.rollback()
        raise

    finally:
        await conn.close()


async def init_db():

    DB_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    async with get_db() as conn:

        await conn.execute("PRAGMA journal_mode = WAL")

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                amount_paise INTEGER NOT NULL
                    CHECK(amount_paise > 0),
                category TEXT NOT NULL,
                subcategory TEXT NOT NULL DEFAULT '',
                note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT
                    (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            )
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_expenses_date
            ON expenses(date)
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_expenses_category_date
            ON expenses(category, date)
        """)

    return True
