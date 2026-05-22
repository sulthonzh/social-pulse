import duckdb
import pytest


@pytest.fixture
def db_connection():
    connection = duckdb.connect(":memory:")
    yield connection
    connection.close()


@pytest.fixture
def db_with_schema(db_connection):
    from src.infrastructure.persistence.migrations import create_all_tables  # noqa: PLC0415

    create_all_tables(db_connection)
    return db_connection
