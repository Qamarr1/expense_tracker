# tests/test_postgres_smoke.py

import os
from datetime import date

import pytest
from sqlalchemy import text
from sqlmodel import SQLModel, Session, create_engine, select

from models import User, Category, Transaction
from auth import get_password_hash

# URL for real Postgres instance; test is skipped if this is not set
POSTGRES_URL = os.getenv("POSTGRES_TEST_URL")


@pytest.mark.integration
@pytest.mark.skipif(
    not POSTGRES_URL,
    reason="POSTGRES_TEST_URL not set, skipping Postgres smoke test.",
)
def test_postgres_basic_crud():
    """
    Postgres smoke test that is SAFE to run multiple times.

    It checks:
      - We can connect to Postgres
      - We can create the schema if needed
      - We can insert-or-get a user, category, and transaction via SQLModel
      - We can read them back via SQLModel
    """

    engine = create_engine(POSTGRES_URL, echo=False, pool_pre_ping=True)

    # Make sure tables exist (no-op if they already exist)
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        # 1) Connectivity check (simple SELECT 1)
        row = session.exec(text("SELECT 1")).first()
        assert row[0] == 1

        # 2) "Upsert" user using ORM (no NOT NULL issues, uses defaults)
        username = "pg_smoke_user"
        hashed_pw = get_password_hash("SmokePass123!")

        user = session.exec(
            select(User).where(User.username == username)
        ).first()
        if user is None:
            user = User(username=username, hashed_password=hashed_pw)
            session.add(user)
            session.commit()
            session.refresh(user)

        assert user.id is not None

        # 3) "Upsert" category using ORM (avoid unique violations)
        cat_name = "PG_Smoke_Category_V3"

        category = session.exec(
            select(Category).where(Category.name == cat_name)
        ).first()
        if category is None:
            category = Category(name=cat_name)
            session.add(category)
            session.commit()
            session.refresh(category)

        assert category.id is not None

        # 4) "Upsert" a transaction using ORM
        tx_name = "PG Smoke Expense V3"

        tx = session.exec(
            select(Transaction).where(
                Transaction.name == tx_name,
                Transaction.category_id == category.id,
            )
        ).first()

        if tx is None:
            tx = Transaction(
                name=tx_name,
                amount=42.50,
                date=date(2025, 1, 1),
                note="postgres-smoke",
                type="expense",
                category_id=category.id,
            )
            session.add(tx)
            session.commit()
            session.refresh(tx)

        assert tx.id is not None
        assert tx.type == "expense"
        assert tx.category_id == category.id





