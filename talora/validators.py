import re
from datetime import date
from decimal import Decimal, InvalidOperation

from config import (
    MAX_NOTE_LENGTH,
    MAX_CATEGORY_LENGTH,
    MAX_SUBCATEGORY_LENGTH
)


def validate_date(value: str) -> str:

    try:
        parsed = date.fromisoformat(value)

        if parsed.isoformat() != value:
            raise ValueError

        return value

    except (ValueError, TypeError):
        raise ValueError(
            "Date must use YYYY-MM-DD format."
        )


def validate_date_range(start_date, end_date):

    start = validate_date(start_date)
    end = validate_date(end_date)

    if start > end:
        raise ValueError(
            "Start date cannot be after end date."
        )

    return start, end


def validate_amount(amount: str) -> int:

    if not isinstance(amount, str):
        raise ValueError(
            "Amount must be supplied as a decimal string."
        )

    if not re.fullmatch(r"\d{1,10}(?:\.\d{1,2})?", amount):
        raise ValueError(
            "Invalid amount. Use a positive value "
            "with at most two decimal places."
        )

    try:
        value = Decimal(amount)

    except InvalidOperation:
        raise ValueError("Invalid monetary amount.")

    if not value.is_finite() or value <= 0:
        raise ValueError(
            "Amount must be greater than zero."
        )

    return int(value * 100)


def validate_text(
    value: str,
    field_name: str,
    max_length: int
) -> str:

    if not isinstance(value, str):
        raise ValueError(
            f"{field_name} must be a string."
        )

    value = value.strip()

    if len(value) > max_length:
        raise ValueError(
            f"{field_name} exceeds {max_length} characters."
        )

    if "\x00" in value:
        raise ValueError(
            f"{field_name} contains invalid characters."
        )

    return value


def validate_category(category: str) -> str:

    return validate_text(
        category,
        "Category",
        MAX_CATEGORY_LENGTH
    )


def validate_subcategory(subcategory: str) -> str:

    return validate_text(
        subcategory,
        "Subcategory",
        MAX_SUBCATEGORY_LENGTH
    )


def validate_note(note: str) -> str:

    return validate_text(
        note,
        "Note",
        MAX_NOTE_LENGTH
    )