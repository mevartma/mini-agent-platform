FROM python:3.12-slim

WORKDIR /app

# Install build deps for asyncpg / bcrypt
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (source is mounted at runtime, not copied)
COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
