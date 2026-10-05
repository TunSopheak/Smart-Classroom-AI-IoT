from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


def normalize_database_url(url: str) -> str:
    """Use the psycopg 3 driver for PostgreSQL URLs.

    Render and most hosts hand out postgres:// or postgresql:// URLs, which
    SQLAlchemy would otherwise map to the psycopg2 driver.
    """
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


DATABASE_URL = normalize_database_url(settings.DATABASE_URL)
IS_SQLITE = DATABASE_URL.startswith("sqlite")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if IS_SQLITE else {},
    # Hosted Postgres drops idle connections; check them before use.
    pool_pre_ping=not IS_SQLITE,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
