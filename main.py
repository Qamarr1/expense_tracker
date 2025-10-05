#Creating a minimal FastAPI app with a health endpoint
from fastapi import FastAPI
app = FastAPI(title="Expense Tracker ", version="0.1.0")

@app.get("/")
def health():
    """API endpoint for quick health checks """
    return {"status": "healthy", "message": "Expense Tracker API is running"}