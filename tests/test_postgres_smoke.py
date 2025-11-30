import os
import datetime as dt
import pytest

from sqlmodel import SQLModel, create_engine, Session, select
from models import User, Category, Transaction

# We only run this test when POSTGRES_TEST_URL is set.
POSTGRES_URL = os.getenv("POSTGRES_TEST_URL")


@pytest.mark.skipif(
    not POSTGRES_URL,
    reason="POSTGRES_TEST_URL not set, skipping Postgres integration test.",
)
def test_postgres_basic_crud():
    """
    Smoke test to verify the app models work correctly with PostgreSQL.
    
    Creates tables, inserts:
      - User
      - Category
      - Transaction (expense)
    and reads them back.
    """

    # Create engine for the *real* postgres instance
    engine = create_engine(POSTGRES_URL, echo=False)

    # Create all tables
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        # Create user
        u = User(username="pgtester", hashed_password="hashed!")
        session.add(u)
        session.commit()
        session.refresh(u)
        assert u.id is not None

        # Create category
        cat = Category(name="PG Test Category")
        session.add(cat)
        session.commit()
        session.refresh(cat)
        assert cat.id is not None

        # Create transaction (expense)
        tx = Transaction(
            name="PG Expense Test",
            amount=10.50,
            date=dt.date(2025, 1, 10),
            note="works",
            type="expense",
            category_id=cat.id,
        )
        session.add(tx)
        session.commit()
        session.refresh(tx)
        assert tx.id is not None

        # Read back
        result = session.exec(
            select(Transaction).where(Transaction.id == tx.id)
        ).first()

        assert result is not None
        assert result.name == "PG Expense Test"
        assert float(result.amount) == 10.50
        assert result.category_id == cat.id
