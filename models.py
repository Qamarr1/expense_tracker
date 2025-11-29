from typing import Optional
from decimal import Decimal
import datetime as dt
from datetime import datetime

from sqlmodel import SQLModel, Field
from sqlalchemy import Column, Integer, String, Numeric, Date, ForeignKey
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

# These classes describe what data will be stored in the database.
# Each class = one table.
# Each variable inside becomes a column in that table.
class Category(SQLModel, table=True):
    """Table for expense categories.
    Stores expense categories like ('Food', 'Transport', or 'Bills').
    Each category has a unique name.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True, min_length=1, max_length=50)

class Transaction(SQLModel, table=True):
    """Main table that stores all transactions.
    It records both income and expenses.
    - 'type' = either 'income' or 'expense'
    - 'category_id' = only for expenses (so it can be left empty for income).
    """
    id: Optional[int] = Field(default=None, primary_key=True) # unique ID
    name: str # name of the transaction (e.g., 'Groceries' or 'Salary')
    amount: Decimal = Field(gt=0) # must be a positive number
    date: dt.date # when the transaction happened
    note: Optional[str] = None # an optional text note from the user
    type: str = Field(regex="^(income|expense)$") # makes sure it’s only 'income' or 'expense'
    category_id: Optional[int] = Field(default=None, foreign_key="category.id") # connect to category if expense


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
