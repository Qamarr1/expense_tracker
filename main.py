"""Main FastAPI application for the Expense Tracker (MoneyFlow)."""
import os
import time
import datetime as dt
from typing import Dict

from utils import compute_summary
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlmodel import SQLModel, create_engine, Session, select

from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy.exc import OperationalError

from models import Category, Transaction, User
from schemas import (
    CategoryCreate,
    CategoryRead,
    CategoryUpdate,
    IncomeCreate,
    ExpenseCreate,
    TransactionUpdate,
    UserCreate,
    UserRead,
    UserLogin,
    Token,
    TokenData,
    UsernameChange,
    PasswordChange,
)
from auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    SECRET_KEY,
    ALGORITHM,
)

#FastAPI is the main framework that handles HTTP requests.
# I’m giving the app a title and version, for documentation purposes.
# It will handle all HTTP requests (GET, POST, DELETE, etc.)
app = FastAPI(title="Expense Tracker ", version="0.1.0")
instrumentator = Instrumentator().instrument(app)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# Serve files from the local "static/" folder (HTML/CSS/JS/images).
# Without this, the browser can’t load the front-end files.
app.mount("/static", StaticFiles(directory="static"), name="static")

#API endpoint for quick health checks
@app.get("/")
def root():
    return {"message": "Expense Tracker API is running. See /health for status."}

@app.get("/health")
def health():
    return {
        "status": "ok",
        "timestamp": dt.datetime.utcnow().isoformat(),
        "app": "expense-tracker",
        "version": "0.1.0",
    }

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./expense.db")
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
else:
    connect_args = {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False,
)
DEFAULT_CATEGORIES = [
    "Food & Dining",
    "Groceries",
    "Transport",
    "Shopping",
    "Bills & Utilities",
    "Entertainment",
    "Health & Medical",
    "Education",
    "Travel",
    "Gifts",
    "Personal Care",
    "Subscriptions",
    "Insurance",
    "Savings",
    "Other",
]

#This function gives me a session (temporary connection) to the database.
# It opens before each request and closes automatically after.
def get_session():
    """Provide a database session per request."""
    with Session(engine) as session:
        yield session      


def get_category_or_400(session: Session, category_id: int) -> Category:
    """Fetch a category or raise a 400 if missing."""
    category = session.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=400, detail="Category not found")
    return category


def get_user_by_username(session: Session, username: str) -> User | None:
    """Fetch a user by username or return None."""
    stmt = select(User).where(User.username == username)
    return session.exec(stmt).first()

def save_and_refresh(session: Session, instance):
    """Persist and refresh an instance in the current session."""
    session.add(instance)
    session.commit()
    session.refresh(instance)
    return instance


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session),
) -> User:
    """Resolve the current user from a bearer token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = get_user_by_username(session, username=username)
    if user is None:
        raise credentials_exception
    return user


def seed_default_categories(session: Session) -> None:
    """Seed default categories if none exist."""
    existing_category = session.exec(select(Category)).first()
    if existing_category:
        print("Categories already exist, skipping seed")
        return

    session.add_all([Category(name=name) for name in DEFAULT_CATEGORIES])
    session.commit()
    print(f"Added {len(DEFAULT_CATEGORIES)} default categories")

@app.on_event("startup")
def on_startup() -> None:
    """
    Run once when the app starts:
    - Wait for Postgres to be ready
    - Create tables
    - Seed default categories
    - Expose Prometheus /metrics
    """
    retries = 10
    delay = 2  # seconds
    last_exc: Exception | None = None

    for attempt in range(1, retries + 1):
        try:
            # Try to talk to the DB (create all tables)
            SQLModel.metadata.create_all(engine)

            # Seed categories
            with Session(engine) as session:
                seed_default_categories(session)

            # Expose Prometheus metrics at /metrics when app start
            instrumentator.expose(app)

            # Ensure database tables exist at startup.

            print(" Database ready, tables created, categories seeded.")
            return
        except OperationalError as exc:
            last_exc = exc
            print(
                f" DB not ready yet (attempt {attempt}/{retries}); "
                f"waiting {delay}s..."
            )
            time.sleep(delay)

    # If we get here, DB never became ready
    print(" Giving up connecting to the database.")
    if last_exc:
        raise last_exc
    raise RuntimeError("Database not reachable on startup.")


# AUTH ENDPOINTS
@app.post("/auth/register", response_model=UserRead, status_code=201)
def register_user(
    user_in: UserCreate,
    session: Session = Depends(get_session),
):
    """Register a new user if the username is free."""
    existing = get_user_by_username(session, user_in.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    hashed = get_password_hash(user_in.password)
    user = User(username=user_in.username, hashed_password=hashed)
    return save_and_refresh(session, user)


@app.post("/auth/login", response_model=Token)
def login(
    user_in: UserLogin,
    session: Session = Depends(get_session),
):
    """Authenticate a user and return a bearer token."""
    user = get_user_by_username(session, user_in.username)
    if not user or not verify_password(user_in.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect username or password",
        )

    access_token = create_access_token({"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/auth/me")
def read_current_user(current_user: User = Depends(get_current_user)):
    """Return the current authenticated user."""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "created_at": getattr(current_user, "created_at", None),
    }


@app.post("/auth/change-username")
def change_username(
    payload: UsernameChange,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Change the current user's username and return a fresh token."""
    existing = session.exec(
        select(User).where(User.username == payload.new_username)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already in use.")

    current_user.username = payload.new_username
    save_and_refresh(session, current_user)

    new_token = create_access_token(
        {"sub": current_user.username, "user_id": current_user.id}
    )

    return {
        "message": "username-updated",
        "access_token": new_token,
        "token_type": "bearer",
    }


@app.post("/auth/change-password")
def change_password(
    payload: PasswordChange,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Change the current user's password."""
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")

    current_user.hashed_password = get_password_hash(payload.new_password)
    save_and_refresh(session, current_user)

    return {"message": "password-updated"}

# CATEGORY ENDPOINTS

# List all categories so the UI can fill a dropdown (sorted by name).
@app.get("/api/categories", response_model=list[CategoryRead])
def list_categories(session: Session = Depends(get_session)):
    """List all categories ordered by name."""
    return session.exec(select(Category).order_by(Category.name)).all()

# Create a new category (e.g., "Food"). I prevent duplicates by checking the name first.
@app.post("/api/categories", response_model=CategoryRead, status_code=201)
def create_category(payload: CategoryCreate, session: Session = Depends(get_session)):
    """Create a new category."""
    existing = session.exec(select(Category).where(Category.name == payload.name)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Category already exists")
    row = Category(name=payload.name)
    return save_and_refresh(session, row)

@app.patch("/api/categories/{category_id}", response_model=CategoryRead)
def update_category(
    category_id: int,
    payload: CategoryUpdate,
    session: Session = Depends(get_session),
):
    """Rename a category, enforcing uniqueness."""
    category = session.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    existing = session.exec(
        select(Category).where(
            Category.name == payload.name,
            Category.id != category_id,
        )
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Category with this name already exists")

    category.name = payload.name
    return save_and_refresh(session, category)


@app.delete("/api/categories/{category_id}", status_code=204)
def delete_category(category_id: int, session: Session = Depends(get_session)):
    """Delete a category if not referenced by transactions."""
    category = session.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    in_use = session.exec(
        select(Transaction).where(Transaction.category_id == category_id)
    ).first()

    if in_use:
        raise HTTPException(
            status_code=400,
            detail="Category is in use and cannot be deleted",
        )

    session.delete(category)
    session.commit()
    return

# INCOME ENDPOINTS
# Create income. The client does NOT send "type"; the server sets type='income'.
@app.post("/api/income", response_model=Transaction, status_code=201)
def create_income(payload: IncomeCreate, session: Session = Depends(get_session)):
    """Create an income transaction."""
    row = Transaction(
        name=payload.name,
        amount=payload.amount,
        date=payload.date,
        note=payload.note,
        type="income",
        category_id=None,  # income does not use a category
    )
    return save_and_refresh(session, row)

# Return all income transactions, newest first (for tables/charts on the dashboard).
@app.get("/api/income", response_model=list[Transaction])
def list_income(session: Session = Depends(get_session)):
    """List income transactions ordered by date descending."""
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
    """Patch an income transaction."""
    transaction = session.get(Transaction, income_id)
    if not transaction or transaction.type != "income":
        raise HTTPException(status_code=404, detail="Income not found")

    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(transaction, field, value)

    return save_and_refresh(session, transaction)

# Delete an income by id.
@app.delete("/api/income/{income_id}", status_code=204)
def delete_income(income_id: int, session: Session = Depends(get_session)):
    """Delete an income transaction."""
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
    """Create an expense transaction with a valid category."""
    get_category_or_400(session, payload.category_id)

    row = Transaction(
        name=payload.name,
        amount=payload.amount,
        date=payload.date,
        note=payload.note,
        type="expense",
        category_id=payload.category_id,
    )
    return save_and_refresh(session, row)

# Return all expenses, newest first (for tables/charts on the dashboard).
@app.get("/api/expenses", response_model=list[Transaction])
def list_expenses(session: Session = Depends(get_session)):
    """List expense transactions ordered by date descending."""
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
    """Patch an expense transaction, validating category changes."""
    transaction = session.get(Transaction, expense_id)
    if not transaction or transaction.type != "expense":
        raise HTTPException(status_code=404, detail="Expense not found")

    data = payload.model_dump(exclude_unset=True)

    if "category_id" in data and data["category_id"] is not None:
        get_category_or_400(session, data["category_id"])

    for field, value in data.items():
        setattr(transaction, field, value)

    return save_and_refresh(session, transaction)

# Delete an expense by id.
@app.delete("/api/expenses/{expense_id}", status_code=204)
def delete_expense(expense_id: int, session: Session = Depends(get_session)):
    """Delete an expense transaction."""
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
    """Compute income/expense totals and balance."""
    incomes = session.exec(
        select(Transaction).where(Transaction.type == "income")
    ).all()
    expenses = session.exec(
        select(Transaction).where(Transaction.type == "expense")
    ).all()

    return compute_summary(
        [t.amount for t in incomes],
        [t.amount for t in expenses],
    )

# Show the dashboard page (simple static HTML file).
# Hitting /dashboard returns static/dashboard.html
@app.get("/dashboard")
def dashboard_page():
    """Serve the dashboard HTML."""
    return FileResponse("static/dashboard.html")

# Show the Income page (lists income using a bit of JS that calls our API).
# Hitting /income-ui returns static/income.html
@app.get("/income-ui")
def income_page():
    """Serve the income HTML."""
    return FileResponse("static/income.html")

# Show the Expenses page (lists expenses using a bit of JS that calls our API).
# Hitting /expenses-ui returns static/expenses.html
@app.get("/expenses-ui")
def expenses_page():
    """Serve the expenses HTML."""
    return FileResponse("static/expenses.html")


@app.get("/settings-ui")
def settings_ui():
    """Serve the settings HTML."""
    return FileResponse("static/settings.html")

@app.get("/login", response_class=HTMLResponse)
def login_ui():
    """Serve the login HTML."""
    return FileResponse("static/login.html")
