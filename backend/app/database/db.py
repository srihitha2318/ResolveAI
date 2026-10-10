from pathlib import Path
import sys
from typing import Generator
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session

_backend_dir = Path(__file__).resolve().parent.parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from app.core.config import settings
from app.core.logging_config import logger


def get_engine(db_url: str | None = None):
    """Creates a SQLAlchemy engine configured for SQLite with foreign keys enabled."""
    url = db_url or settings.resolved_database_url

    # If it is a file-based SQLite URL, ensure directory exists
    if url.startswith("sqlite:///") and not url.startswith("sqlite:////"):
        file_path_str = url[len("sqlite:///"):]
        if file_path_str != ":memory:":
            file_path = Path(file_path_str)
            file_path.parent.mkdir(parents=True, exist_ok=True)

    connect_args = {}
    if "sqlite" in url:
        connect_args["check_same_thread"] = False

    engine = create_engine(
        url,
        connect_args=connect_args,
        echo=False,
        future=True,
    )

    # Enforce foreign key constraints in SQLite
    if "sqlite" in url:
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


# Default application engine and session factory
engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session and safely closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection(session: Session | None = None) -> bool:
    """Checks whether the database connection is alive and functional."""
    try:
        if session:
            session.execute(text("SELECT 1"))
        else:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error("Database health check failed: %s", e)
        return False
