FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Change the working directory to the `app` directory
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --no-dev --locked --no-install-project --no-editable

FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=your_project_name.settings

RUN useradd -m -u 1000 app
WORKDIR /app

# Copy the environment, but not the source code
COPY --from=builder --chown=app:app /app/.venv /app/.venv

# Copy the source code separately
ADD ./finance_planner finance_planner

USER app
ENV PATH="/app/.venv/bin:$PATH"

# Collect static files (if applicable)
RUN python manage.py collectstatic --noinput

# Expose the port your Django app will run on
EXPOSE 8000

# Command to run the Django development server (or Gunicorn in production)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]