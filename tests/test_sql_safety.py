from sqlalchemy.sql.elements import TextClause

from app.db import crud
from app.db.session import _normalize_db_url


class DummyResult:
    def mappings(self):
        return self

    def first(self):
        return {"ok": True}


class DummyDB:
    def __init__(self):
        self.sql = None
        self.params = None

    def execute(self, sql, params=None):
        self.sql = sql
        self.params = params
        return DummyResult()


def test_fetch_client_snapshot_uses_text():
    db = DummyDB()
    crud.fetch_client_snapshot(db, "551199999999")
    assert isinstance(db.sql, TextClause)
    assert "CAST(:tel AS text)" in str(db.sql)


def test_normalize_db_url():
    assert _normalize_db_url("postgresql+psycopg2://user:pass@host/db").startswith("postgresql+psycopg://")
    assert _normalize_db_url("postgresql+asyncpg://user:pass@host/db").startswith("postgresql+psycopg://")
    assert _normalize_db_url("postgres://user:pass@host/db").startswith("postgresql+psycopg://")
