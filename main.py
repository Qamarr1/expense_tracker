#Creating a minimal FastAPI app with a health endpoint
from fastapi import FastAPI
from sqlmodel import SQLModel, create_engine, Session, Field, select 
from typing import Optional, List, Dict
from datetime import date
from decimal import Decimal

#FastAPI is the main framework that handles HTTP requests.
# I’m giving the app a title and version, for documentation purposes.
# It will handle all HTTP requests (GET, POST, DELETE, etc.)
app = FastAPI(title="Expense Tracker ", version="0.1.0")

#API endpoint for quick health checks
@app.get("/")
def health():
    return {"status": "healthy", "message": "Expense Tracker API is running"}

# Get database engine for  SQLite
# It creates a file called 'expense.db' in the project folder automatically.
DATABASE_URL = "sqlite:///./expense.db"
# Create connection arguments for SQLite, to allow multiple connections safely as it has has a small limitation with multithreading
connect_args = {"check_same_thread": False} 
# Create database engine, this is the actual connection (my Python code with the actual SQLite database.)
# echo=True will print SQL statements in the terminal, helpful for debugging
engine = create_engine(DATABASE_URL, connect_args=connect_args, echo=True)

#This function gives me a session (temporary connection) to the database.
# It opens before each request and closes automatically after.
def get_session():
    with Session(engine) as session:
        yield session      


# These classes describe what data will be stored in the database.
# Each class = one table.
# Each variable inside becomes a column in that table.

class Category(SQLModel, table=True):
    """Table for expense categories.
    Stores expense categories like ('Food', 'Transport', or 'Bills').
    Each category has a unique name."""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True, min_length=1, max_length=50)


class Transaction(SQLModel, table=True):
    """Main table that stores all transactions.
    It records both income and expenses.
    - 'type' = either 'income' or 'expense'
    - 'category_id' = only for expenses (so it can be left empty for income). """

    id: Optional[int] = Field(default=None, primary_key=True) # unique ID
    name: str # name of the transaction (e.g., 'Groceries' or 'Salary')
    amount: Decimal = Field(gt=0) # must be a positive number
    date: date # when the transaction happened
    note: Optional[str] = None # an optional text note from the user
    type: str = Field(regex="^(income|expense)$") # makes sure it’s only 'income' or 'expense'
    category_id: Optional[int] = Field(default=None, foreign_key="category.id") # connect to category if expense

# Schemas (for API requests)
# These are models used by FastAPI when sending or receiving data.
# They describe what information the user can send to the API when adding or editing things.

class CategoryCreate(SQLModel):
    """"Used when creating a new category (e.g., 'Food')."""
    name: str

class IncomeCreate(SQLModel):
    """ Data Used when creating a new income.
    The 'type' is set automatically by the backend, so the user doesn’t have to write it.
    Example: adding 'Salary' or 'Freelance Work' as income."
    """
    name: str
    amount: Decimal = Field(gt=0)
    date: date
    note: Optional[str] = None

class ExpenseCreate(SQLModel):
    """ Data used when creating an expense.
    Every expense must have a category (like Food).
    """
    name: str
    amount: Decimal = Field(gt=0)
    date: date
    note: Optional[str] = None
    category_id: int


class TransactionUpdate(SQLModel):
    """ Data used when updating an income or expense.
    All fields are optional so the user can update only one field.
    """
    name: Optional[str] = None
    amount: Optional[Decimal] = Field(default=None, gt=0)
    date: Optional[date] = None
    note: Optional[str] = None
    category_id: Optional[int] = None

 # Create all database tables (Category, Transaction)
@app.on_event("startup")
def on_startup():
    """Initialize database when app starts"""
    
    # Create all tables (Category, Transaction)
    SQLModel.metadata.create_all(engine)
    print(" Database tables created")
    
    # Add default categories if database is empty
    with Session(engine) as session:
        # Check if we already have categories
        existing_category = session.exec(select(Category)).first()
        
        if not existing_category:
            # Add 5 default expense categories
            session.add(Category(name="Food"))
            session.add(Category(name="Transport"))
            session.add(Category(name="Shopping"))
            session.add(Category(name="Bills"))
            session.add(Category(name="Entertainment"))
            session.commit()
            print("Added 5 default categories")
        else:
            print("Categories already exist, skipping seed")



