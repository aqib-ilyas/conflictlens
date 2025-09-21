# VIEWS Conflict Forecasting API - Makefile
# Compatible with Windows (using Python commands)

.DEFAULT_GOAL := help
SHELL := cmd.exe

# Python and pip executables
PYTHON := python
PIP := pip

# Project directories
SRC_DIR := .
TEST_DIR := tests
DATA_DIR := data
STATIC_DIR := static

# Virtual environment (Windows)
VENV_DIR := venv
VENV_ACTIVATE := $(VENV_DIR)\Scripts\activate.bat

.PHONY: help install install-dev setup run test lint format clean docker-build docker-run

help: ## Show this help message
	@echo VIEWS Conflict Forecasting API - Available Commands:
	@echo.
	@findstr /R "^[a-zA-Z_-]*:.*##" $(MAKEFILE_LIST) | findstr /V findstr | for /f "delims=: tokens=1,2" %%a in ('more') do @echo   %%a: %%b

install: ## Install production dependencies
	$(PIP) install -r requirements.txt

setup: ## Set up the project (create directories, install deps)
	@if not exist $(DATA_DIR) mkdir $(DATA_DIR)
	@if not exist $(STATIC_DIR) mkdir $(STATIC_DIR)
	@if not exist tests mkdir tests
	@if not exist logs mkdir logs
	$(MAKE) install-dev
	@echo Setup complete! Run 'make run' to start the server.

venv: ## Create virtual environment
	$(PYTHON) -m venv $(VENV_DIR)
	@echo Virtual environment created. Activate with: $(VENV_ACTIVATE)

run: ## Run the development server
	$(PYTHON) -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

run-prod: ## Run the production server
	$(PYTHON) -m uvicorn main:app --host 0.0.0.0 --port 8000

test: ## Run tests with pytest
	$(PYTHON) -m pytest tests/ -v --tb=short

test-coverage: ## Run tests with coverage report
	$(PYTHON) -m pytest tests/ -v --cov=. --cov-report=html --cov-report=term

lint: ## Run linting with ruff
	$(PYTHON) -m ruff check .

lint-fix: ## Run linting with automatic fixes
	$(PYTHON) -m ruff check . --fix

format: ## Format code with ruff
	$(PYTHON) -m ruff format .

type-check: ## Run type checking with mypy
	$(PYTHON) -m mypy . --ignore-missing-imports

validate: ## Run all validation (lint, format, type-check, test)
	$(MAKE) lint
	$(MAKE) format
	$(MAKE) type-check
	$(MAKE) test

clean: ## Clean up temporary files and caches
	@if exist __pycache__ rmdir /s /q __pycache__
	@if exist .pytest_cache rmdir /s /q .pytest_cache
	@if exist .coverage del .coverage
	@if exist htmlcov rmdir /s /q htmlcov
	@if exist .mypy_cache rmdir /s /q .mypy_cache
	@if exist .ruff_cache rmdir /s /q .ruff_cache
	@for /d /r . %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d"
	@for /d /r . %%d in (*.egg-info) do @if exist "%%d" rmdir /s /q "%%d"

clean-data: ## Remove generated synthetic data
	@if exist $(DATA_DIR)\*.csv del $(DATA_DIR)\*.csv
	@echo Synthetic data files removed.

reset: clean clean-data ## Full reset (clean + remove data)
	@echo Project reset complete.

# Data management
create-sample-data: ## Create sample synthetic data for testing
	$(PYTHON) -c "from services.data_service import DataService; ds = DataService(); ds.load_data(); print('Sample data created in data/ directory')"

# Development utilities
dev-setup: venv ## Complete development setup with virtual environment
	$(VENV_ACTIVATE) && $(MAKE) install-dev && $(MAKE) setup
	@echo Development environment ready!

check-deps: ## Check for outdated dependencies
	$(PIP) list --outdated

upgrade-deps: ## Upgrade all dependencies to latest versions
	$(PIP) install --upgrade pip
	$(PIP) install --upgrade -r requirements-dev.txt

# API testing
test-api: ## Test API endpoints with sample requests
	@echo Testing API endpoints...
	$(PYTHON) -c "import requests; r=requests.get('http://localhost:8000/api/info'); print('API Status:', r.status_code, r.json() if r.status_code==200 else 'Failed')" 2>nul || echo API not running. Start with 'make run' first.

demo: ## Run API with sample data and open dashboard
	@echo Starting VIEWS API Demo...
	$(MAKE) create-sample-data
	@echo Sample data created. Starting server...
	@echo Open http://localhost:8000 in your browser to view the dashboard
	$(MAKE) run

# Docker commands (if Docker is available)
docker-build: ## Build Docker image
	docker build -t views-api .

docker-run: ## Run Docker container
	docker run -p 8000:8000 views-api

docker-dev: ## Run Docker container with volume mounting for development
	docker run -p 8000:8000 -v %cd%:/app views-api

# Documentation
docs: ## Generate API documentation
	@echo API documentation available at:
	@echo   - Swagger UI: http://localhost:8000/docs
	@echo   - ReDoc: http://localhost:8000/redoc
	@echo Start the server with 'make run' to view documentation.

# Windows-specific utilities
install-python: ## Install Python dependencies (Windows specific)
	@echo Installing Python packages for Windows...
	$(PIP) install --upgrade pip setuptools wheel
	$(MAKE) install-dev

check-python: ## Check Python and pip versions
	@echo Python version:
	$(PYTHON) --version
	@echo Pip version:
	$(PIP) --version
	@echo Installation directory:
	$(PYTHON) -c "import sys; print(sys.executable)"

# Production deployment helpers
requirements: ## Generate requirements.txt from current environment
	$(PIP) freeze > requirements.txt

security-check: ## Run security checks on dependencies
	$(PYTHON) -m pip-audit

health-check: ## Check if API is running and healthy
	@echo Checking API health...
	$(PYTHON) -c "import requests; r=requests.get('http://localhost:8000/api/info'); print('✓ API is healthy' if r.status_code==200 else '✗ API health check failed')" 2>nul || echo ✗ API not reachable

# Development workflow
dev: ## Complete development workflow (setup, test, run)
	$(MAKE) setup
	$(MAKE) test
	$(MAKE) run

# Debugging helpers
debug: ## Run API in debug mode with detailed logging
	$(PYTHON) -c "import logging; logging.basicConfig(level=logging.DEBUG)"
	$(PYTHON) -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload --log-level debug

logs: ## Show recent log files (if logging to files)
	@if exist logs\*.log (
		echo Recent log entries:
		for %%f in (logs\*.log) do (
			echo === %%f ===
			type "%%f" | more
		)
	) else (
		echo No log files found in logs\ directory
	)