from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Category


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record) -> None:
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    test_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with test_session() as session:
        session.add_all(
            [
                Category(
                    slug="milk",
                    name="Milk",
                    is_active=True,
                    source_url="https://www.s-kaupat.fi/tuotteet/maito-munat-ja-rasvat/maidot-ja-piimat",
                ),
                Category(
                    slug="minced-meat",
                    name="Minced meat",
                    is_active=True,
                    source_url="https://www.s-kaupat.fi/tuotteet/liha-ja-kasviproteiinit/jauheliha",
                ),
                Category(
                    slug="softdrinks",
                    name="Softdrinks",
                    is_active=True,
                    source_url="https://www.s-kaupat.fi/tuotteet/alkoholi-ja-virvoitusjuomat/virvoitusjuomat",
                ),
                Category(
                    slug="snack-bars-biscuits",
                    name="Snack bars and biscuits",
                    is_active=True,
                    source_url="https://www.s-kaupat.fi/tuotteet/karkit-suklaat-ja-keksit/valipalapatukat-ja-keksit",
                ),
                Category(slug="cheese", name="Cheese", is_active=True),
                Category(slug="empty", name="Empty category", is_active=True),
            ]
        )
        session.commit()
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
