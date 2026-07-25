from datetime import datetime, timezone
import dateutil.parser

def parse_date(date_val) -> datetime:
    """
    Normalizes input date_val into a canonical UTC datetime object.
    Supports:
    - ISO 8601 string format (e.g. "2026-06-03T20:11:00Z")
    - DD/MM/YYYY string format (e.g. "31/10/2025")
    - Unix epoch seconds as integer, float, or numeric string (e.g. 1781382480)
    
    Raises ValueError for unparseable input.
    """
    if date_val is None:
        raise ValueError("Date value cannot be None")

    if isinstance(date_val, datetime):
        if date_val.tzinfo is None:
            return date_val.replace(tzinfo=timezone.utc)
        return date_val.astimezone(timezone.utc)

    # Integer or float epoch seconds
    if isinstance(date_val, (int, float)):
        try:
            return datetime.fromtimestamp(date_val, tz=timezone.utc)
        except (OverflowError, OSError, ValueError) as e:
            raise ValueError(f"Invalid numeric epoch timestamp: {date_val}") from e

    if isinstance(date_val, str):
        date_str = date_val.strip()
        if not date_str:
            raise ValueError("Empty date string")

        # Check if numeric epoch string
        if date_str.isdigit():
            return datetime.fromtimestamp(int(date_str), tz=timezone.utc)

        # Check float numeric string
        try:
            val_float = float(date_str)
            return datetime.fromtimestamp(val_float, tz=timezone.utc)
        except ValueError:
            pass

        # Check DD/MM/YYYY format explicitly
        try:
            dt = datetime.strptime(date_str, "%d/%m/%Y")
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            pass

        # Check ISO 8601 parsing
        try:
            dt = dateutil.parser.isoparse(date_str)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            pass

        # Generic dateutil fallback
        try:
            dt = dateutil.parser.parse(date_str)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception as e:
            raise ValueError(f"Unable to parse date string: {date_val}") from e

    raise ValueError(f"Unsupported date format type: {type(date_val).__name__}")
