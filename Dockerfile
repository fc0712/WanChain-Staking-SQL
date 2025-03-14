# Builder stage: Use uv to install dependencies and build the application
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
# Disable Python downloads to use the system interpreter
ENV UV_PYTHON_DOWNLOADS=0
WORKDIR /app

# First install dependencies without the project
# Use cache mounts for efficiency and bind mounts for dependency files
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv venv .venv && \
    uv sync --no-install-project --python .venv/bin/python

# Then add the project files and install the project itself
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --python .venv/bin/python

# Final stage: Use a lightweight Python image
FROM python:3.13-slim-bookworm

# Create a non-root user for security
RUN useradd -m app
WORKDIR /app

# Copy the virtual environment and application code from the builder stage
COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --from=builder --chown=app:app /app /app

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

# Switch to the non-root user
USER app

# Run the application
CMD ["python", "app.py"]