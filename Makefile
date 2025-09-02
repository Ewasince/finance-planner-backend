# Variables
PYTHON = poetry run python
PIP = pip
MANAGE = $(PYTHON) finance_planner/manage.py
VENV = venv
REQUIREMENTS = requirements.txt

# Default target
.DEFAULT_GOAL := help

# Help
help:
	@echo "Django Project Makefile"
	@echo ""
	@echo "Available commands:"
	@echo "  make install      - Install dependencies"
	@echo "  make migrate      - Run database migrations"
	@echo "  make run          - Run development server"
	@echo "  make shell        - Open Django shell"
	@echo "  make test         - Run tests"
	@echo "  make clean        - Clean pycache files"
	@echo "  make superuser    - Create superuser"
	@echo "  make collectstatic - Collect static files"
	@echo "  make requirements - Update requirements.txt"

# Install dependencies
install:
	$(PIP) install -r $(REQUIREMENTS)

# Run database migrations
migrate:
	$(MANAGE) migrate

# Run development server
run:
	$(MANAGE) runserver

# Run development server on specific port
run-8001:
	$(MANAGE) runserver 8001

# Open Django shell
shell:
	$(MANAGE) shell

# Run tests
test:
	$(MANAGE) test

# Run tests with coverage
test-coverage:
	coverage run manage.py test
	coverage report
	coverage html

# Clean pycache files
clean:
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete

# Create superuser
superuser:
	$(MANAGE) createsuperuser

# Collect static files
collectstatic:
	$(MANAGE) collectstatic --noinput

# Update requirements
requirements:
	$(PIP) freeze > $(REQUIREMENTS)

# Database operations
makemigrations:
	$(MANAGE) makemigrations

resetdb:  # Warning: destructive operation!
	$(MANAGE) reset_db --noinput
	$(MANAGE) migrate
	$(MANAGE) loaddata initial_data.json

# Code quality
lint:
	flake8 .
	isort --check-only .
	black --check .

format:
	isort .
	black .

# Production
gunicorn:
	gunicorn myproject.wsgi:application --bind 0.0.0.0:8000

.PHONY: help install migrate run shell test clean superuser collectstatic requirements makemigrations resetdb lint format gunicorn