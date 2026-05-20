import pytest
import duckdb


@pytest.fixture
def db_connection():
    connection = duckdb.connect(":memory:")
    yield connection
    connection.close()


@pytest.fixture
def db_with_schema(db_connection):
    from src.infrastructure.persistence.migrations import create_all_tables

    create_all_tables(db_connection)
    return db_connection
