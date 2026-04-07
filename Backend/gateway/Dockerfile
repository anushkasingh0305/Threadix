FROM python:3.11-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml ./

RUN uv sync --no-cache

COPY app/ ./app/

EXPOSE 8080

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
