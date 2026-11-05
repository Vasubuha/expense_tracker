
import logging
import aiosqlite

from contextlib import asynccontextmanager

from config import DB_PATH, DB_TIMEOUT


logger = logging.getLogger("talora.database")


# --------------------------------------------------
# DATABASE CONNECTION
# --------------------------------------------------

async def get_connection() -> aiosqlite.Connection:
    """
    Create and configure an asynchronous SQLite connection.
    """

    # Ensure the database directory exists
    DB_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    conn = await aiosqlite.connect(
        str(DB_PATH),
        timeout=DB_TIMEOUT
    )

    conn.row_factory = aiosqlite.Row

    await conn.execute("PRAGMA foreign_keys = ON")
    await conn.execute(
        f"PRAGMA busy_timeout = {DB_TIMEOUT * 1000}"
    )

    return conn


# --------------------------------------------------
# DATABASE CONTEXT MANAGER
# --------------------------------------------------

@asynccontextmanager
async def get_db():
    """
    Provide a database connection with automatic
    commit, rollback and connection cleanup.
    """

    conn = await get_connection()

    try:
        yield conn

        await conn.commit()

    except Exception:
        await conn.rollback()
        raise

    finally:
        await conn.close()


# --------------------------------------------------
# DATABASE INITIALIZATION
# --------------------------------------------------

async def init_db() -> bool:
    """
    Initialize database tables, indexes and WAL mode.
    Safe to execute multiple times.
    """

    logger.info("Initializing TALORA database.")

    async with get_db() as conn:

        # Enable Write-Ahead Logging
        cursor = await conn.execute(
            "PRAGMA journal_mode = WAL"
        )
        await cursor.close()

        # Optimize synchronous writes
        await conn.execute(
            "PRAGMA synchronous = NORMAL"
        )

        # Create expenses table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                date TEXT NOT NULL,

                amount_paise INTEGER NOT NULL
                    CHECK (amount_paise > 0),

                category TEXT NOT NULL,

                subcategory TEXT NOT NULL DEFAULT '',

                note TEXT NOT NULL DEFAULT '',

                created_at TEXT NOT NULL DEFAULT
                    (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            )
        """)

        # Index for date-based filtering
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_expenses_date
            ON expenses(date)
        """)

        # Composite index for category and date filtering
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_expenses_category_date
            ON expenses(category, date)
        """)

    logger.info("TALORA database initialized successfully.")

    return True


# --------------------------------------------------
# DATABASE HEALTH CHECK
# --------------------------------------------------

async def check_db_connection() -> bool:
    """
    Check whether the database is accessible.
    """

    try:
        async with get_db() as conn:

            cursor = await conn.execute(
                "SELECT 1"
            )

            result = await cursor.fetchone()

            await cursor.close()

            return result[0] == 1

    except Exception:
        logger.exception("Database health check failed.")
        return False


# --------------------------------------------------
# DATABASE SHUTDOWN
# --------------------------------------------------

async def close_db() -> None:
    """
    Reserved for future shared connection pool cleanup.

    Connections are currently opened and closed
    independently for each operation.
    """

    logger.info("TALORA database connections are closed.")
