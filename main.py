#Creating a minimal FastAPI app with a health endpoint
from fastapi import FastAPI,HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlmodel import SQLModel, create_engine, Session, Field, select 
from typing import Optional, List, Dict
from datetime import date
from decimal import Decimal

#FastAPI is the main framework that handles HTTP requests.
# I’m giving the app a title and version, for documentation purposes.
# It will handle all HTTP requests (GET, POST, DELETE, etc.)
app = FastAPI(title="Expense Tracker ", version="0.1.0")

# Serve files from the local "static/" folder (HTML/CSS/JS/images).
# Without this, the browser can’t load the front-end files.
app.mount("/static", StaticFiles(directory="static"), name="static")

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
            session.add(Category(name="Food & Dining"))
            session.add(Category(name="Groceries"))
            session.add(Category(name="Transport"))
            session.add(Category(name="Shopping"))
            session.add(Category(name="Bills & Utilities"))
            session.add(Category(name="Entertainment"))
            session.add(Category(name="Health & Medical"))
            session.add(Category(name="Education"))
            session.add(Category(name="Travel"))
            session.add(Category(name="Gifts"))
            session.add(Category(name="Personal Care"))
            session.add(Category(name="Subscriptions"))
            session.add(Category(name="Insurance"))
            session.add(Category(name="Savings"))
            session.add(Category(name="Other"))
            session.commit()
            print("Added 15 default categories")
        else:
            print("Categories already exist, skipping seed")

# CATEGORY ENDPOINTS

# List all categories so the UI can fill a dropdown (sorted by name).
@app.get("/api/categories", response_model=list[Category])
def list_categories(session: Session = Depends(get_session)):
    return session.exec(select(Category).order_by(Category.name)).all()

# Create a new category (e.g., "Food"). I prevent duplicates by checking the name first.
@app.post("/api/categories", response_model=Category, status_code=201)
def create_category(payload: CategoryCreate, session: Session = Depends(get_session)):
    existing = session.exec(select(Category).where(Category.name == payload.name)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Category already exists")
    row = Category(name=payload.name)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row

# INCOME ENDPOINTS
# Create income. The client does NOT send "type"; the server sets type='income'.
@app.post("/api/income", response_model=Transaction, status_code=201)
def create_income(payload: IncomeCreate, session: Session = Depends(get_session)):
    row = Transaction(
        name=payload.name,
        amount=payload.amount,
        date=payload.date,
        note=payload.note,
        type="income",
        category_id=None,  # income does not use a category
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row

# Return all income transactions, newest first (for tables/charts on the dashboard).
@app.get("/api/income", response_model=list[Transaction])
def list_income(session: Session = Depends(get_session)):
    stmt = (
        select(Transaction)
        .where(Transaction.type == "income")
        .order_by(Transaction.date.desc())
    )
    return session.exec(stmt).all()

# Partially update an income by id. Only the fields provided in the request are changed.
@app.patch("/api/income/{income_id}", response_model=Transaction)
def update_income(
    income_id: int,
    payload: TransactionUpdate,
    session: Session = Depends(get_session),
):
    transaction = session.get(Transaction, income_id)
    if not transaction or transaction.type != "income":
        raise HTTPException(status_code=404, detail="Income not found")

    if payload.name is not None:
        transaction.name = payload.name
    if payload.amount is not None:
        transaction.amount = payload.amount
    if payload.date is not None:
        transaction.date = payload.date
    if payload.note is not None:
        transaction.note = payload.note

    session.add(transaction)
    session.commit()
    session.refresh(transaction)
    return transaction

# Delete an income by id.
@app.delete("/api/income/{income_id}", status_code=204)
def delete_income(income_id: int, session: Session = Depends(get_session)):
    transaction = session.get(Transaction, income_id)
    if not transaction or transaction.type != "income":
        raise HTTPException(status_code=404, detail="Income not found")
    session.delete(transaction)
    session.commit()
    return None

# EXPENSE ENDPOINTS
# Create expense. Must reference a valid category (I validate the category_id exists).
@app.post("/api/expenses", response_model=Transaction, status_code=201)
def create_expense(payload: ExpenseCreate, session: Session = Depends(get_session)):
    if not session.get(Category, payload.category_id):
        raise HTTPException(status_code=400, detail="Category does not exist")

    row = Transaction(
        name=payload.name,
        amount=payload.amount,
        date=payload.date,
        note=payload.note,
        type="expense",
        category_id=payload.category_id,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row

# Return all expenses, newest first (for tables/charts on the dashboard).
@app.get("/api/expenses", response_model=list[Transaction])
def list_expenses(session: Session = Depends(get_session)):
    stmt = (
        select(Transaction)
        .where(Transaction.type == "expense")
        .order_by(Transaction.date.desc())
    )
    return session.exec(stmt).all()

# Partially update an expense by id. If category_id is provided, we validate it exists.
@app.patch("/api/expenses/{expense_id}", response_model=Transaction)
def update_expense(
    expense_id: int,
    payload: TransactionUpdate,
    session: Session = Depends(get_session),
):
    transaction = session.get(Transaction, expense_id)
    if not transaction or transaction.type != "expense":
        raise HTTPException(status_code=404, detail="Expense not found")

    if payload.name is not None:
        transaction.name = payload.name
    if payload.amount is not None:
        transaction.amount = payload.amount
    if payload.date is not None:
        transaction.date = payload.date
    if payload.note is not None:
        transaction.note = payload.note
    if payload.category_id is not None:
        if not session.get(Category, payload.category_id):
            raise HTTPException(status_code=400, detail="Category does not exist")
        transaction.category_id = payload.category_id

    session.add(transaction)
    session.commit()
    session.refresh(transaction)
    return transaction

# Delete an expense by id.
@app.delete("/api/expenses/{expense_id}", status_code=204)
def delete_expense(expense_id: int, session: Session = Depends(get_session)):
    transaction = session.get(Transaction, expense_id)
    if not transaction or transaction.type != "expense":
        raise HTTPException(status_code=404, detail="Expense not found")
    session.delete(transaction)
    session.commit()
    return None

# SUMMARY / STATS
# Compute totals for income and expenses, and the balance (income - expenses).
# We convert Decimal to float for JSON responses.
@app.get("/api/stats/summary")
def get_summary(session: Session = Depends(get_session)) -> Dict[str, float]:
    incomes = session.exec(
        select(Transaction).where(Transaction.type == "income")
    ).all()
    expenses = session.exec(
        select(Transaction).where(Transaction.type == "expense")
    ).all()

    income_total = float(sum(t.amount for t in incomes))
    expense_total = float(sum(t.amount for t in expenses))
    balance = income_total - expense_total

    return {
        "income_total": round(income_total, 2),
        "expense_total": round(expense_total, 2),
        "balance": round(balance, 2),
    }

# Show the dashboard page (simple static HTML file).
# Hitting /dashboard returns static/dashboard.html
@app.get("/dashboard")
def dashboard_page():
    return FileResponse("static/dashboard.html")

# Show the Income page (lists income using a bit of JS that calls our API).
# Hitting /income-ui returns static/income.html
@app.get("/income-ui")
def income_page():
    return FileResponse("static/income.html")

# Show the Expenses page (lists expenses using a bit of JS that calls our API).
# Hitting /expenses-ui returns static/expenses.html
@app.get("/expenses-ui")
def expenses_page():
    return FileResponse("static/expenses.html")



