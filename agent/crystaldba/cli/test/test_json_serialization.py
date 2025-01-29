from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta
from decimal import Decimal
from uuid import UUID

from crystaldba.shared.sql_serialization import to_json_serializable_value


def test_none_value():
    assert to_json_serializable_value(None) is None


def test_primitive_types():
    assert to_json_serializable_value(True) is True
    assert to_json_serializable_value(42) == 42
    assert to_json_serializable_value(3.14) == 3.14
    assert to_json_serializable_value("hello") == "hello"


def test_datetime_types():
    # Test datetime
    dt = datetime(2023, 1, 1, 12, 30, 45)
    assert to_json_serializable_value(dt) == "2023-01-01T12:30:45"

    # Test date
    d = date(2023, 1, 1)
    assert to_json_serializable_value(d) == "2023-01-01"

    # Test time
    t = time(12, 30, 45)
    assert to_json_serializable_value(t) == "12:30:45.000000"


def test_special_types():
    # Test timedelta
    td = timedelta(days=1, hours=2)
    assert to_json_serializable_value(td) == "1 day, 2:00:00"

    # Test Decimal
    dec = Decimal("3.14")
    assert to_json_serializable_value(dec) == "3.14"

    # Test UUID
    uuid_str = "550e8400-e29b-41d4-a716-446655440000"
    uuid = UUID(uuid_str)
    assert to_json_serializable_value(uuid) == uuid_str


def test_bytes():
    # Test bytes
    b = bytes([65, 66, 67])  # ABC in bytes
    assert to_json_serializable_value(b) == "QUJD"


def test_lists_and_tuples():
    # Test list with mixed types
    test_list = [1, "two", datetime(2023, 1, 1)]
    expected = [1, "two", "2023-01-01T00:00:00"]
    assert to_json_serializable_value(test_list) == expected

    # Test tuple
    test_tuple = (1, "two", datetime(2023, 1, 1))
    assert to_json_serializable_value(test_tuple) == expected


def test_nested_structures():
    nested = [1, [datetime(2023, 1, 1), Decimal("3.14")], (UUID("550e8400-e29b-41d4-a716-446655440000"), bytes([65]))]
    expected = [1, ["2023-01-01T00:00:00", "3.14"], ["550e8400-e29b-41d4-a716-446655440000", "QQ=="]]
    assert to_json_serializable_value(nested) == expected


def test_unsupported_type():
    # Test that unsupported types are converted to strings
    class CustomClass:
        def __str__(self):
            return "custom_object"

    custom_obj = CustomClass()
    assert to_json_serializable_value(custom_obj) == "custom_object"
