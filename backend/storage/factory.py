import os

from .base import Storage
from .memory import InMemoryStorage
from .postgres import PostgresStorage


def create_storage() -> Storage:
    database_url = os.getenv("DATABASE_URL")
    retention_days = int(os.getenv("RETENTION_DAYS", "7"))
    if database_url:
        return PostgresStorage(database_url, retention_days=retention_days)
    return InMemoryStorage(retention_days=retention_days)
