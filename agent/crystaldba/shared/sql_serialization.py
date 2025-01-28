import ast
import base64
from datetime import date
from datetime import datetime
from datetime import time as datetime_time
from datetime import timedelta
from decimal import Decimal
from decimal import InvalidOperation
from typing import Any
from uuid import UUID

from pydantic import JsonValue

from crystaldba.shared.api import SQLToolExecuteResponse
from crystaldba.shared.base_sql_driver import BaseSqlDriver


def to_json_serializable_value(value: Any) -> JsonValue:
    """Convert values to JSON-serializable types."""
    if value is None:
        return None
    if isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, datetime_time):
        return value.strftime("%H:%M:%S.%f")
    if isinstance(value, (timedelta, Decimal, UUID)):
        return str(value)
    if isinstance(value, bytes):
        return base64.b64encode(value).decode("ascii")
    if isinstance(value, (list, tuple)):
        return [to_json_serializable_value(item) for item in value]
    if isinstance(value, dict):
        return {k: to_json_serializable_value(v) for k, v in value.items()}
    return str(value)  # Convert any other types to strings


def to_sql_tool_response(sql_result: list[BaseSqlDriver.RowResult] | None) -> SQLToolExecuteResponse:
    """Convert SQL result to SQLToolExecuteResponse format for transmission."""
    if sql_result is None:
        return SQLToolExecuteResponse(rows=None)

    json_serializable_rows = [{k: to_json_serializable_value(v) for k, v in row.cells.items()} for row in sql_result]

    return SQLToolExecuteResponse(rows=json_serializable_rows)


def from_sql_tool_response(response: SQLToolExecuteResponse) -> list[BaseSqlDriver.RowResult]:
    """Convert a SQLToolExecuteResponse back to a list of RowResults."""
    if response.rows is None:
        return []

    # Convert each row's values back from JSON-serialized format
    deserialized_rows = [{k: from_json_serializable_value(v) for k, v in row.items()} for row in response.rows]

    return [BaseSqlDriver.RowResult(cells=row) for row in deserialized_rows]


def from_json_serializable_value(value: Any) -> Any:
    """Convert JSON-serialized values back to Python objects."""
    if value is None:
        return None
    if isinstance(value, (bool, int)):
        return value
    if isinstance(value, dict):
        return {k: from_json_serializable_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [from_json_serializable_value(item) for item in value]
    if isinstance(value, str):
        try:
            if value.startswith("{") or value.startswith("["):
                parsed = ast.literal_eval(value)
                if isinstance(parsed, dict):
                    return {k: from_json_serializable_value(v) for k, v in parsed.items()}
                if isinstance(parsed, list):
                    return [from_json_serializable_value(v) for v in parsed]
                return parsed
            if "T" in value and value.endswith(("Z", "+00:00")):
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            if "." in value or value.isdigit():
                try:
                    return Decimal(value)
                except (ValueError, InvalidOperation):
                    pass
        except (ValueError, SyntaxError):
            pass
        return value
    return value
