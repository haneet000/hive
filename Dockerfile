FROM python:3.12-slim

WORKDIR /app

# Install system dependencies required for psycopg2 build
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

EXPOSE 8000

# Run migrations, run data ingestion, then launch FastAPI backend
CMD ["sh", "-c", "alembic upgrade head && python -m scripts.ingest && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
