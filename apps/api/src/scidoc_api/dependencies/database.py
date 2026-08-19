from __future__ import annotations

from collections.abc import Iterator

from scidoc_database.session import new_session
from sqlalchemy.orm import Session


def get_db() -> Iterator[Session]:
    session = new_session()
    try:
        yield session
    finally:
        session.close()
