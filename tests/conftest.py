import pytest
from datetime import date, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app
from app.models.stock import Item
from app.models.consumption import ConsumptionTransaction

# Dedicated SQLite test database
TEST_DATABASE_URL = "sqlite:///./test_inventory.db"

engine_test = create_engine(
    TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.drop_all(bind=engine_test)
    Base.metadata.create_all(bind=engine_test)
    yield
    Base.metadata.drop_all(bind=engine_test)


@pytest.fixture
def db_session():
    connection = engine_test.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_item(db_session):
    item = Item(
        sku="TEST-SKU-1",
        name="Test Item 1",
        category="Testing",
        current_stock=20,
        min_stock_level=15,
        max_stock_level=200,
        lead_time_days=5,
        unit_cost=25.0,
        ordering_cost=50.0,
        holding_cost_rate=0.20
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    return item


@pytest.fixture
def sample_item_with_history(db_session, sample_item):
    today = date.today()
    # Add 30 days of sales history (avg ~10 units/day)
    for i in range(30, 0, -1):
        trans = ConsumptionTransaction(
            item_id=sample_item.id,
            transaction_date=today - timedelta(days=i),
            quantity=10 + (i % 3),
            channel="Test Channel",
            unit_price=35.0
        )
        db_session.add(trans)
    db_session.commit()
    return sample_item
