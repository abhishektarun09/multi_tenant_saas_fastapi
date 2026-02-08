FROM python:3.12

ENV PYTHONUNBUFFERED=1

# Install system deps required for psycopg2
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency files first
COPY pyproject.toml uv.lock ./

# Install the application dependencies.
RUN uv sync --frozen --no-cache

# Copy the application into the container.
COPY . .

# Run the application.
CMD uv run uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}