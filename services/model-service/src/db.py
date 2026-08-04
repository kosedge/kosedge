import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.environ["DATABASE_URL"]

# SQLAlchemy wants postgresql+psycopg://
if DATABASE_URL.startswith("postgresql://"):
    SQLALCHEMY_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
else:
    SQLALCHEMY_URL = DATABASE_URL

# Fail fast when Postgres is unreachable (default TCP hang can exceed BFF budgets).
_CONNECT_TIMEOUT_S = int(os.getenv("DB_CONNECT_TIMEOUT_S", "5"))

engine = create_engine(
    SQLALCHEMY_URL,
    pool_pre_ping=True,
    connect_args={"connect_timeout": _CONNECT_TIMEOUT_S},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
