import json
from datetime import date
from datetime import datetime
from datetime import time
from decimal import Decimal
from uuid import UUID

import pytest
import sqlalchemy.exc
from sqlalchemy import text

from crystaldba.cli.sql_tool import LocalSqlDriver
from crystaldba.shared.sql_serialization import from_json_serializable_value
from crystaldba.shared.sql_serialization import from_sql_tool_response
from crystaldba.shared.sql_serialization import to_json_serializable_value
from crystaldba.shared.sql_serialization import to_sql_tool_response


@pytest.fixture
def local_sql_driver(test_postgres_connection_string):
    connection_string, _ = test_postgres_connection_string
    return LocalSqlDriver(engine_url=connection_string)


def setup_test_tables(sql_driver):
    with sql_driver.engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS test_orders"))
        conn.execute(text("DROP TABLE IF EXISTS test_customers"))

        conn.execute(
            text("""
            CREATE TABLE test_orders (
                id SERIAL PRIMARY KEY,
                total DECIMAL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """)
        )

        conn.execute(
            text("""
            CREATE TABLE test_customers (
                id SERIAL PRIMARY KEY,
                name TEXT
            )
        """)
        )

        # Insert minimal test data
        conn.execute(
            text("""
            INSERT INTO test_customers (name) VALUES ('Alice'), ('Bob')
            """)
        )

        conn.execute(
            text("""
            INSERT INTO test_orders (total) VALUES (100.50), (200.75)
            """)
        )


def cleanup_test_tables(sql_driver):
    with sql_driver.engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS test_orders"))
        conn.execute(text("DROP TABLE IF EXISTS test_customers"))


def test_value_serialization():
    """Test serialization of individual values."""
    test_cases = [
        (None, None),
        (True, True),
        (42, 42),
        (3.14, 3.14),
        ("hello", "hello"),
        (datetime(2023, 1, 1, 12, 30), "2023-01-01T12:30:00"),
        (date(2023, 1, 1), "2023-01-01"),
        (time(12, 30), "12:30:00.000000"),
        (Decimal("123.45"), "123.45"),
        (UUID("550e8400-e29b-41d4-a716-446655440000"), "550e8400-e29b-41d4-a716-446655440000"),
        (b"binary data", "YmluYXJ5IGRhdGE="),  # base64 encoded
        ([1, "two", 3.0], [1, "two", 3.0]),
    ]

    # TODO use from_json_serializable_value to convert back to orginal value and assert that they are the same
    for input_value, expected_output in test_cases:
        serialized = to_json_serializable_value(input_value)
        assert serialized == expected_output
        # Verify it can be JSON serialized
        json.dumps(serialized)


def test_value_deserialization():
    """Test deserialization of values."""
    test_cases = [
        (None, None),
        (True, True),
        (42, 42),
        ("123.45", Decimal("123.45")),
        ("[1, 2, 3]", [1, 2, 3]),
        ('{"a": 1, "b": 2}', {"a": 1, "b": 2}),
    ]

    for input_value, expected_output in test_cases:
        deserialized = from_json_serializable_value(input_value)
        assert deserialized == expected_output


@pytest.mark.postgres
def test_sql_result_serialization(local_sql_driver):
    """Test that SQL results can be serialized and deserialized correctly."""
    setup_test_tables(local_sql_driver)
    try:
        queries = [
            "SELECT 1 as num",
            """
            SELECT id, total, created_at
            FROM test_orders
            WHERE total > 150
            """,
            """
            SELECT o.id, o.total, c.name
            FROM test_orders o
            JOIN test_customers c ON o.id = c.id
            """,
        ]

        for query in queries:
            result = local_sql_driver.execute_query(query)
            if result is None:
                continue

            response = to_sql_tool_response(result)
            deserialized = from_sql_tool_response(response)

            assert deserialized is not None
            assert len(deserialized) == len(result)
            for orig, des in zip(result, deserialized):
                assert des.cells.keys() == orig.cells.keys()
                for key in orig.cells:
                    if isinstance(orig.cells[key], (datetime, Decimal)):
                        assert str(des.cells[key]) == str(orig.cells[key])
                    else:
                        assert des.cells[key] == orig.cells[key]

        explain_queries = [
            "EXPLAIN (FORMAT JSON) SELECT * FROM test_orders WHERE total > 150",
            "EXPLAIN (FORMAT JSON) SELECT o.*, c.name FROM test_orders o JOIN test_customers c ON o.id = c.id",
            "EXPLAIN (ANALYZE, FORMAT JSON) SELECT * FROM test_orders WHERE total > 150",
        ]

        for query in explain_queries:
            result = local_sql_driver.execute_query(query)
            if result is None:
                continue

            response = to_sql_tool_response(result)
            deserialized = from_sql_tool_response(response)

            assert deserialized is not None
            assert len(deserialized) == len(result)
            for orig, des in zip(result, deserialized):
                assert des.cells.keys() == orig.cells.keys()
                assert "QUERY PLAN" in des.cells
                assert isinstance(des.cells["QUERY PLAN"], list)

                orig_plan = des.cells["QUERY PLAN"]
                des_plan = des.cells["QUERY PLAN"]
                assert len(des_plan) == len(orig_plan)

                for orig_item, des_item in zip(orig_plan, des_plan):
                    assert orig_item.keys() == des_item.keys()
                    for key in orig_item:
                        assert orig_item[key] == des_item[key]
    finally:
        cleanup_test_tables(local_sql_driver)


@pytest.mark.postgres
def test_nonexistent_table_error(local_sql_driver):
    """Test error when querying nonexistent table."""
    setup_test_tables(local_sql_driver)
    with pytest.raises(sqlalchemy.exc.ProgrammingError) as exc_info:
        local_sql_driver.execute_query("SELECT * FROM nonexistent_table")
    assert 'relation "nonexistent_table" does not exist' in str(exc_info.value)


@pytest.mark.postgres
def test_division_by_zero_error(local_sql_driver):
    """Test division by zero error."""
    setup_test_tables(local_sql_driver)
    with pytest.raises(sqlalchemy.exc.DataError) as exc_info:
        local_sql_driver.execute_query("SELECT total / 0 FROM test_orders")
    assert "division by zero" in str(exc_info.value)
