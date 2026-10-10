from pathlib import Path
import sys
from typing import Generator
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from starlette.testclient import TestClient

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.main import app
from app.database.db import get_db
from app.database.models import Base
from app.rag.embeddings import MockEmbeddingProvider, set_global_embedding_provider


@pytest.fixture(autouse=True, scope="session")
def configure_test_embeddings():
    """Ensure all tests use deterministic offline MockEmbeddingProvider with zero downloads."""
    set_global_embedding_provider(MockEmbeddingProvider())
    yield
    set_global_embedding_provider(None)



@pytest.fixture
def test_engine():
    """Function-scoped isolated SQLite engine for complete test isolation."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def test_db(test_engine) -> Generator[Session, None, None]:
    """Function-scoped clean session bound to the isolated test engine."""
    SessionTest = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = SessionTest()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(test_db: Session) -> Generator[TestClient, None, None]:
    """Test client overriding the get_db dependency with test_db."""
    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
