# expense_tracker
 Expense tracker, built with FastAPI and SQLite
Setup Instructions

Follow these steps to run the Expense Tracker locally.

1️Prerequisites

Make sure you have:

Python 3.9+

pip (comes with Python)

Git

(Optional) Docker (for containerized setup)

 Clone the Repository

Open a terminal and run:

git clone https://github.com/Qamarr1/expense_tracker.git
cd expense_tracker

 Create and Activate a Virtual Environment
On macOS / Linux:
python3 -m venv venv
source venv/bin/activate

On Windows (PowerShell):
python -m venv venv
venv\Scripts\activate


Once activated, you should see (venv) at the start of your terminal prompt.

 Install Dependencies

Install the required packages from requirements.txt:

pip install -r requirements.txt


 Main frameworks used:

fastapi → Web framework

uvicorn → App runner

sqlmodel → ORM for SQLite

jinja2 → HTML templating

python-multipart → Handles HTML forms

Additional libraries (Pydantic, Starlette, SQLAlchemy, etc.) are automatically installed as dependencies.

 Initialize the Database

No manual SQL setup is needed!
When you first run the app, it automatically creates the database file expense.db and adds default categories like “Food”, “Transport”, etc.

If you delete expense.db, the app will recreate it on startup.

You can verify by checking that a file named expense.db appears in your project directory after the first run.

 Run the Application

Start the FastAPI server:

uvicorn main:app --reload


If your code is in a folder (e.g. /app/main.py), then:

uvicorn app.main:app --reload


When it starts successfully, you’ll see:

Application startup complete.


Then visit these URLs:

Page	URL
Health Check (API root)	http://127.0.0.1:8000

Dashboard	http://127.0.0.1:8000/dashboard

Income Page	http://127.0.0.1:8000/income-ui

Expenses Page	http://127.0.0.1:8000/expenses-ui

Interactive API Docs	http://127.0.0.1:8000/docs
 Stop and Deactivate

To stop the server, press:

CTRL + C


To deactivate your virtual environment:

deactivate
