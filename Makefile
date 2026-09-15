.PHONY: help run install migrate upgrade downgrade test lint format clean fernet
.DEFAULT_GOAL := help

help:  ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

run:  ## Start the development server with hot reload
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

install:  ## Install project dependencies
	uv sync

migrate:  ## Generate a new migration (usage: make migrate message="your message")
	uv run alembic revision --autogenerate -m "$(message)"

upgrade:  ## Apply all pending migrations
	uv run alembic upgrade head

downgrade:  ## Revert the last migration
	uv run alembic downgrade -1

fernet:  ## Generate a Fernet key for GOOGLE_SHEETS_TOKEN_ENCRYPTION_KEY
	uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

test:  ## Run test suite
	uv run pytest tests/ -v

lint:  ## Check code for linting errors
	uv run ruff check ./app/ ./tests/

format:  ## Format codebase
	uv run ruff format ./app/ ./tests/

clean:  ## Remove all cache and generated files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
