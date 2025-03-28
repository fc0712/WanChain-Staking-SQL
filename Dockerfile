# Builder stage: Use uv to install dependencies and build the application
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
ENV UV_PYTHON_DOWNLOADS=0
WORKDIR /app

# Bind both pyproject.toml and uv.lock for reproducible builds.
# The first uv sync installs only the dependencies without the project.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --frozen --no-install-project --no-dev

# Copy the rest of your project files.
COPY . /app

# Sync again to install the project itself.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Final stage: Use a lightweight Python image.
FROM python:3.13-slim-bookworm

# Add the virtual environment's bin directory to PATH.
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

# Create a non-root user for improved security.
RUN useradd -m app
WORKDIR /app

# Copy the application and virtual environment from the builder.
COPY --from=builder --chown=app:app /app /app

# Change the ownership of the application to the non-root user.    
RUN chown -R app:app /app

# Switch to the non-root user.
USER app


# Force PATH to be used in interactive shells
SHELL ["/bin/sh", "-c"]

# Debug: Print PATH during build
RUN echo "Final PATH: $PATH"

CMD ["python", "app.py"]