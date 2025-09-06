# Makefile for uv-based development workflow

.PHONY: setup sync install run test lint format clean help

# Default target
help:
	@echo "Available commands:"
	@echo "  setup    - Create virtual environment and install dependencies"
	@echo "  sync     - Sync dependencies with pyproject.toml"
	@echo "  install  - Install dependencies from requirements.txt"
	@echo "  run      - Run the FastAPI application"
	@echo "  test     - Run tests"
	@echo "  lint     - Run linting"
	@echo "  format   - Format code with black"
	@echo "  clean    - Clean up cache files"

# Setup development environment
setup:
	uv venv .venv
	uv sync

# Sync with pyproject.toml
sync:
	uv sync

# Install from requirements.txt (legacy)
install:
	uv pip install -r requirements.txt

# Run the application
run:
	uv run uvicorn app.main:app --reload

# Run tests
test:
	uv run pytest tests/ -v

# Run linting
lint:
	uv run flake8 app/ tests/

# Format code
format:
	uv run black app/ tests/

# Clean up
clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache/
	rm -rf htmlcov/
