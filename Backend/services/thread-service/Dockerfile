# Use official Python slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl && rm -rf /var/lib/apt/lists/*

# Install uv (same as auth service)
RUN pip install uv

# Copy dependency files first (Docker layer caching)
COPY pyproject.toml ./

# Install Python dependencies
RUN uv sync --no-cache

# Copy application code
COPY . .

# Run database migrations then start server
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
