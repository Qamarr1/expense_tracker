#Creating a minimal FastAPI app with a health endpoint
from fastapi import FastAPI
from sqlmodel import SQLModel, create_engine, Session

app = FastAPI(title="Expense Tracker ", version="0.1.0")

@app.get("/")
def health():
    """API endpoint for quick health checks """
    return {"status": "healthy", "message": "Expense Tracker API is running"}

# Get database engine for  SQLite
DATABASE_URL = "sqlite:///./expense.db"
# Create connection arguments for SQLite
connect_args = {"check_same_thread": False} 
# Create database engine, this is the actual connection 
engine = create_engine(DATABASE_URL, connect_args=connect_args, echo=True)

#open a DB session per request and close it automatically.
def get_session():
    with Session(engine) as session:
        yield session

