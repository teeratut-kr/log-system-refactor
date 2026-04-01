import os

from .base import Storage
from .memory import InMemoryStorage


def create_storage() -> Storage:
    database_url = os.getenv("DATABASE_URL")
    retention_days = int(os.getenv("RETENTION_DAYS", "7"))
    if database_url:
        from .postgres import PostgresStorage

        return PostgresStorage(database_url, retention_days=retention_days)
    return InMemoryStorage(retention_days=retention_days)
