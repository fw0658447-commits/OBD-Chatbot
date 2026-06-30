from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from app.config import settings

try:
    import psycopg
    from psycopg.rows import dict_row
except ModuleNotFoundError:  # Allows local mock-mode smoke tests without installing optional DB deps first.
    psycopg = None
    dict_row = None


def is_database_configured() -> bool:
    return bool(settings.database_url.strip()) and psycopg is not None


@contextmanager
def get_connection() -> Iterator['psycopg.Connection']:
    if not settings.database_url.strip():
        raise RuntimeError('DATABASE_URL is not configured')
    if psycopg is None or dict_row is None:
        raise RuntimeError('psycopg is not installed. Run pip install -r requirements.txt')

    with psycopg.connect(settings.database_url, row_factory=dict_row) as connection:
        yield connection
