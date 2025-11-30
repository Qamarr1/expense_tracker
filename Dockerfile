# Use a slim official Python image
FROM python:3.11-slim

# Create working directory
WORKDIR /app

# (Optional but nice) - avoid .pyc, force unbuffered logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Copy requirements first (for build cache)
COPY requirements.txt .

# Install Python dependencies (psycopg[binary] brings its own compiled bits)
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app
COPY . .

# Expose app port
EXPOSE 8000

# Start the API
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

