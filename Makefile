# Variables
PYTHON = uv run python
MANAGE = $(PYTHON) finance_planner/manage.py

# Install dependencies
.PHONY: install
install:
	@uv sync
	@uv run pre-commit install

# Run database migrations
.PHONY: migrate
migrate:
	$(MANAGE) migrate

# Run database migrations
.PHONY: bootstrap
bootstrap:
	$(MANAGE) bootstrap_dev_data

# Run development server
.PHONY: run
run:
	$(MANAGE) runserver

# Run development server on specific port
.PHONY: run.8001
run.8001:
	$(MANAGE) runserver 8001

# Open Django shell
.PHONY: shell
shell:
	$(MANAGE) shell

# Run tests
.PHONY: test.pytest
test.pytest:
	@uv run pytest

# Run tests with coverage
.PHONY: test.coverage
test.coverage:
	@coverage run manage.py test
	@coverage report
	@coverage html

# Clean pycache files
.PHONY: clean
clean:
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete

# Create superuser
.PHONY: superuser
superuser:
	$(MANAGE) createsuperuser

# Collect static files
.PHONY: collectstatic
collectstatic:
	$(MANAGE) collectstatic --noinput

# Database operations
.PHONY: makemigrations
makemigrations:
	$(MANAGE) makemigrations

.PHONY: resetdb
resetdb:  # Warning: destructive operation!
	$(MANAGE) reset_db --noinput
	$(MANAGE) migrate
	$(MANAGE) loaddata initial_data.json


# Production
.PHONY: gunicorn
gunicorn:
	gunicorn myproject.wsgi:application --bind 0.0.0.0:8000


# Code Quality
.PHONY: lint.mypy
lint.mypy:
	@uv run mypy

.PHONY: lint.ruff
lint.ruff:
	@uv run ruff check . --fix

.PHONY: pre-commit-all
pre-commit-all:
	@uv run pre-commit run --all-files

.PHONY: align_code
align_code:
	uv run ruff format .
