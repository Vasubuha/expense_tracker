
import asyncio
import json
import logging

from decimal import Decimal
from fastmcp import FastMCP

from config import (
    CATEGORIES_PATH,
    LOG_DIR,
    LOG_LEVEL,
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE
)

from database import init_db, get_db

from validators import (
    validate_date,
    validate_date_range,
    validate_amount,
    validate_category,
    validate_subcategory,
    validate_note
)


# --------------------------------------------------
# LOGGING
# --------------------------------------------------

LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(
            LOG_DIR / "app.log",
            encoding="utf-8"
        ),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("expense_tracker")


# --------------------------------------------------
# MCP SERVER
# --------------------------------------------------

mcp = FastMCP(
    name="ExpenseTracker",
    instructions=(
        "An asynchronous expense management MCP server "
        "for recording, retrieving and summarizing "
        "personal expenses in Indian Rupees."
    )
)


# --------------------------------------------------
# COMMON UTILITIES
# --------------------------------------------------

def load_categories():

    with open(
        CATEGORIES_PATH,
        "r",
        encoding="utf-8"
    ) as file:

        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("Invalid categories configuration.")

    return data


def validate_expense_category(category, subcategory):

    categories = load_categories()

    if category not in categories:
        raise ValueError(
            f"Unknown category: {category}"
        )

    if subcategory and subcategory not in categories[category]:
        raise ValueError(
            f"Invalid subcategory for {category}"
        )


def format_amount(amount_paise):

    amount = Decimal(amount_paise) / Decimal(100)

    return f"{amount:.2f}"


async def execute_safely(operation):

    try:
        return await operation()

    except (ValueError, TypeError) as exc:

        logger.warning("Validation error: %s", exc)

        return {
            "status": "error",
            "error": str(exc)
        }

    except Exception:

        logger.exception("Unexpected application error.")

        return {
            "status": "error",
            "error": "An internal error occurred."
        }


# --------------------------------------------------
# TOOL 1: ADD EXPENSE
# --------------------------------------------------

@mcp.tool()
async def add_expense(
    date: str,
    amount: str,
    category: str,
    subcategory: str = "",
    note: str = ""
) -> dict:
    """
    Add a new expense to the database.

    Args:
        date: Expense date in YYYY-MM-DD format.
        amount: Positive INR amount as a string.
        category: Valid expense category.
        subcategory: Optional subcategory.
        note: Optional expense description.
    """

    async def operation():

        expense_date = validate_date(date)

        amount_paise = validate_amount(amount)

        category_value = validate_category(category)

        subcategory_value = validate_subcategory(
            subcategory
        )

        note_value = validate_note(note)

        validate_expense_category(
            category_value,
            subcategory_value
        )

        async with get_db() as conn:

            cursor = await conn.execute(
                """
                INSERT INTO expenses (
                    date,
                    amount_paise,
                    category,
                    subcategory,
                    note
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    expense_date,
                    amount_paise,
                    category_value,
                    subcategory_value,
                    note_value
                )
            )

            expense_id = cursor.lastrowid

            await cursor.close()

        logger.info("Expense created: ID=%s", expense_id)

        return {
            "status": "success",
            "message": "Expense recorded successfully.",
            "expense": {
                "id": expense_id,
                "date": expense_date,
                "amount_inr": format_amount(amount_paise),
                "category": category_value,
                "subcategory": subcategory_value,
                "note": note_value
            }
        }

    return await execute_safely(operation)


# --------------------------------------------------
# TOOL 2: LIST EXPENSES
# --------------------------------------------------

@mcp.tool()
async def list_expenses(
    start_date: str,
    end_date: str,
    limit: int = DEFAULT_PAGE_SIZE,
    offset: int = 0
) -> dict:
    """
    Retrieve expenses within an inclusive date range.

    Supports pagination.
    """

    async def operation():

        start, end = validate_date_range(
            start_date,
            end_date
        )

        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or not 1 <= limit <= MAX_PAGE_SIZE
        ):
            raise ValueError("Invalid pagination limit.")

        if (
            isinstance(offset, bool)
            or not isinstance(offset, int)
            or offset < 0
        ):
            raise ValueError("Invalid pagination offset.")

        async with get_db() as conn:

            cursor = await conn.execute(
                """
                SELECT
                    id,
                    date,
                    amount_paise,
                    category,
                    subcategory,
                    note,
                    created_at
                FROM expenses
                WHERE date BETWEEN ? AND ?
                ORDER BY date DESC, id DESC
                LIMIT ? OFFSET ?
                """,
                (start, end, limit, offset)
            )

            rows = await cursor.fetchall()

            await cursor.close()

            cursor = await conn.execute(
                """
                SELECT COUNT(*)
                FROM expenses
                WHERE date BETWEEN ? AND ?
                """,
                (start, end)
            )

            total = (await cursor.fetchone())[0]

            await cursor.close()

        expenses = [
            {
                "id": row["id"],
                "date": row["date"],
                "amount_inr": format_amount(
                    row["amount_paise"]
                ),
                "category": row["category"],
                "subcategory": row["subcategory"],
                "note": row["note"],
                "created_at": row["created_at"]
            }
            for row in rows
        ]

        return {
            "status": "success",
            "date_range": {
                "start_date": start,
                "end_date": end
            },
            "total_records": total,
            "returned_records": len(expenses),
            "limit": limit,
            "offset": offset,
            "has_more": offset + len(expenses) < total,
            "expenses": expenses
        }

    return await execute_safely(operation)


# --------------------------------------------------
# TOOL 3: SUMMARIZE EXPENSES
# --------------------------------------------------

@mcp.tool()
async def summarize(
    start_date: str,
    end_date: str,
    category: str | None = None
) -> dict:
    """
    Summarize expenses by category within a date range.
    """

    async def operation():

        start, end = validate_date_range(
            start_date,
            end_date
        )

        category_value = None

        if category is not None:

            category_value = validate_category(category)

            categories = load_categories()

            if category_value not in categories:
                raise ValueError(
                    f"Unknown category: {category_value}"
                )

        query = """
            SELECT
                category,
                SUM(amount_paise) AS total_paise,
                COUNT(*) AS transaction_count
            FROM expenses
            WHERE date BETWEEN ? AND ?
        """

        params = [start, end]

        if category_value:

            query += " AND category = ?"

            params.append(category_value)

        query += """
            GROUP BY category
            ORDER BY total_paise DESC
        """

        async with get_db() as conn:

            cursor = await conn.execute(
                query,
                params
            )

            rows = await cursor.fetchall()

            await cursor.close()

        summaries = [
            {
                "category": row["category"],
                "total_inr": format_amount(
                    row["total_paise"]
                ),
                "transaction_count": row["transaction_count"]
            }
            for row in rows
        ]

        total_paise = sum(
            row["total_paise"] for row in rows
        )

        total_transactions = sum(
            row["transaction_count"] for row in rows
        )

        return {
            "status": "success",
            "date_range": {
                "start_date": start,
                "end_date": end
            },
            "currency": "INR",
            "overall_total_inr": format_amount(
                total_paise
            ),
            "total_transactions": total_transactions,
            "category_summary": summaries
        }

    return await execute_safely(operation)


# --------------------------------------------------
# RESOURCE: EXPENSE CATEGORIES
# --------------------------------------------------

@mcp.resource(
    "expense://categories",
    mime_type="application/json"
)
def get_categories() -> str:
    """
    Return available expense categories.
    """

    return json.dumps(
        load_categories(),
        ensure_ascii=False,
        indent=2
    )


# --------------------------------------------------
# PROMPT: EXPENSE ASSISTANT
# --------------------------------------------------

@mcp.prompt()
def expense_assistant() -> str:
    """
    Instructions for the AI expense management assistant.
    """

    return """
You are a reliable personal Expense Tracker Assistant.

AVAILABLE TOOLS:

1. add_expense:
   Record a new expense.

2. list_expenses:
   Retrieve expenses within a date range.

3. summarize:
   Calculate category-wise spending.

AVAILABLE RESOURCE:

expense://categories

RULES:

1. Never fabricate financial records or totals.
2. Check categories before recording expenses.
3. Use YYYY-MM-DD date format.
4. Use INR as the currency.
5. Ask for missing essential information.
6. Never confirm an expense until the tool succeeds.
7. Use summarize for financial totals.
8. Retrieve additional pages when has_more is true.
9. Distinguish transaction records from summaries.
10. Use the current date provided by the host
    when interpreting today or yesterday.
11. Never expose database internals.

Present expense history in tables and summaries
with category-wise totals and overall spending.
"""


# --------------------------------------------------
# APPLICATION ENTRY POINT
# --------------------------------------------------

if __name__ == "__main__":

    asyncio.run(init_db())

    logger.info("Starting ExpenseTracker MCP server.")

    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=8000
    )