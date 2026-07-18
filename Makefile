# ============================================
#  J.A.R.V.I.S. — developer task runner
# ============================================
.PHONY: help install install-dev run test lint format clean

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install:  ## Install runtime dependencies
	pip install -r requirements.txt

install-dev: install  ## Install dev/test dependencies
	pip install pytest pytest-asyncio ruff

run:  ## Launch the interactive CLI
	python -m jarvis

test:  ## Run the test suite
	python -m pytest -q

lint:  ## Lint the codebase
	ruff check jarvis tests

format:  ## Auto-format the codebase
	ruff format jarvis tests

clean:  ## Remove caches and build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache build dist *.egg-info
