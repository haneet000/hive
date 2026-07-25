import pytest
from datetime import datetime, timezone
from app.normalizers import parse_date

def test_parse_iso8601_dates():
    # UTC with Z
    dt1 = parse_date("2026-06-03T20:11:00Z")
    assert dt1 == datetime(2026, 6, 3, 20, 11, 0, tzinfo=timezone.utc)

    # Offset timestamp
    dt2 = parse_date("2026-02-15T18:02:00+00:00")
    assert dt2 == datetime(2026, 2, 15, 18, 2, 0, tzinfo=timezone.utc)

    # Standard date string YYYY-MM-DD
    dt3 = parse_date("2025-10-09")
    assert dt3 == datetime(2025, 10, 9, 0, 0, 0, tzinfo=timezone.utc)

def test_parse_dd_mm_yyyy_dates():
    dt = parse_date("31/10/2025")
    assert dt == datetime(2025, 10, 31, 0, 0, 0, tzinfo=timezone.utc)

    dt2 = parse_date("05/04/2025")
    assert dt2 == datetime(2025, 4, 5, 0, 0, 0, tzinfo=timezone.utc)

def test_parse_unix_epoch_seconds():
    # Int
    dt1 = parse_date(1781382480)
    assert dt1 == datetime.fromtimestamp(1781382480, tz=timezone.utc)

    # Float
    dt2 = parse_date(1781382480.0)
    assert dt2 == datetime.fromtimestamp(1781382480, tz=timezone.utc)

    # Numeric string
    dt3 = parse_date("1781382480")
    assert dt3 == datetime.fromtimestamp(1781382480, tz=timezone.utc)

def test_parse_invalid_and_garbage_input():
    invalid_inputs = [
        "not-a-date",
        "31-31-2025",
        "",
        "   ",
        None,
        [],
        {"date": "2025-01-01"}
    ]

    for bad in invalid_inputs:
        with pytest.raises(ValueError):
            parse_date(bad)
