"""SQLite engine and sessions (owner: Core app).

Updated specs: the app uses SQLite. SQLite has no database users or GRANTs,
so access control is enforced in the API by `require_role()` (app/security/rbac.py).
"""
from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


@lru_cache
def get_engine() -> Engine:
    url = get_settings().database_url
    if url.startswith("sqlite:///"):
        # make sure the folder for the .db file exists (e.g. ./data)
        Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    # check_same_thread=False: FastAPI may use the connection from another thread
    return create_engine(url, connect_args={"check_same_thread": False})


def new_session() -> Session:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)()


def get_session() -> Iterator[Session]:
    """FastAPI dependency: one session per request, always closed."""
    db = new_session()
    try:
        yield db
    finally:
        db.close()
