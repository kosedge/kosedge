from __future__ import annotations

import os
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL: Optional[str] = os.environ.get("DATABASE_URL")

engine: Optional[Engine] = None
SessionLocal = None

if DATABASE_URL:
    # SQLAlchemy wants postgresql+psycopg://
    if DATABASE_URL.startswith("postgresql://"):
        SQLALCHEMY_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
    else:
        SQLALCHEMY_URL = DATABASE_URL

    engine = create_engine(SQLALCHEMY_URL, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def require_engine() -> Engine:
    if engine is None:
        raise RuntimeError(
            "DATABASE_URL is not set; configure it on the Railway service to enable DB routes"
        )
    return engine
