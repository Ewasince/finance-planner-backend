# Stage 1: Builder - Install Poetry and export dependencies
FROM python:3.12-slim-bookworm AS builder

# Set environment variables for Poetry
ENV POETRY_VERSION=1.8.2
ENV POETRY_HOME="/opt/poetry"
ENV POETRY_VIRTUALENVS_IN_PROJECT=true
ENV PATH="$POETRY_HOME/bin:$PATH"

# Install Poetry
RUN pip install poetry==$POETRY_VERSION

# Set the working directory
WORKDIR /app

# Copy pyproject.toml and poetry.lock
COPY pyproject.toml poetry.lock ./

# Install dependencies using Poetry
RUN poetry install --no-root --no-interaction --no-ansi

# Stage 2: Production - Copy installed dependencies and application code
FROM python:3.11-slim-bookworm AS production

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=your_project_name.settings

# Set the working directory
WORKDIR /app

# Copy virtual environment from builder stage
COPY --from=builder /app/.venv /app/.venv

# Add poetry's virtual environment to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Copy your Django application code
COPY . .

# Collect static files (if applicable)
RUN python manage.py collectstatic --noinput

# Expose the port your Django app will run on
EXPOSE 8000

# Command to run the Django development server (or Gunicorn in production)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]