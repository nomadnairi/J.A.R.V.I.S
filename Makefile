# ============================================
#  J.A.R.V.I.S. — developer task runner
# ============================================
.PHONY: help install install-dev run test coverage lint typecheck check format clean

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install:  ## Install runtime dependencies
	pip install -r requirements.txt

install-dev: install  ## Install dev/test dependencies
	pip install pytest pytest-asyncio pytest-cov ruff mypy

run:  ## Launch the interactive CLI
	python -m jarvis

test:  ## Run the test suite
	python -m pytest -q

coverage:  ## Run tests with a coverage report
	python -m pytest --cov=jarvis --cov-report=term-missing

lint:  ## Lint the codebase
	ruff check jarvis tests

typecheck:  ## Static type check (advisory)
	mypy jarvis

check: lint test  ## Lint + test (the CI gate)

format:  ## Auto-format the codebase
	ruff format jarvis tests

clean:  ## Remove caches and build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache build dist *.egg-info
