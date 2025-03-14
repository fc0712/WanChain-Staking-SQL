# Builder stage: Use uv to install dependencies and build the application
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
ENV UV_PYTHON_DOWNLOADS=0
WORKDIR /app

# Copy only dependency files first for better layer caching
COPY pyproject.toml uv.lock ./

# Create virtual environment and install dependencies using uv sync
RUN --mount=type=cache,target=/root/.cache/uv \
    uv venv .venv && \
    uv sync --frozen --no-dev --python .venv/bin/python

# Copy application code
COPY . .

# Final stage: Use a lightweight Python image
FROM python:3.13-slim-bookworm

# Create a non-root user for security
RUN useradd -m app
WORKDIR /app

# Copy the virtual environment and application code
COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --from=builder --chown=app:app /app /app

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

# Switch to the non-root user
USER app

# Run the application
CMD ["python", "app.py"]