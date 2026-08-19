from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from scidoc_database.models import Base

_engine: Engine | None = None
_factory: sessionmaker[Session] | None = None


def configure_database(url: str, *, echo: bool = False) -> Engine:
    global _engine, _factory
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    _engine = create_engine(url, echo=echo, pool_pre_ping=True, connect_args=connect_args)
    _factory = sessionmaker(bind=_engine, expire_on_commit=False, autoflush=False)
    return _engine


def engine() -> Engine:
    if _engine is None:
        raise RuntimeError("database has not been configured")
    return _engine


def create_schema() -> None:
    Base.metadata.create_all(engine())


def new_session() -> Session:
    if _factory is None:
        raise RuntimeError("database has not been configured")
    return _factory()


@contextmanager
def session_scope() -> Iterator[Session]:
    session = new_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
