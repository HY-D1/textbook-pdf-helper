# ALGL PDF Helper - Makefile

.PHONY: help install install-dev test test-ci test-integration update-baselines clean lint format

PYTHON := python3
PIP := $(PYTHON) -m pip

help:
	@echo "ALGL PDF Helper - Available targets:"
	@echo ""
	@echo "  install          Install package with basic dependencies"
	@echo "  install-dev      Install with all dev dependencies (server, ocr, test)"
	@echo "  test             Run all tests"
	@echo "  test-ci          Run CI-specific tests (golden fixture)"
	@echo "  test-integration Run integration tests only"
	@echo "  update-baselines Update baseline outputs for regression tests"
	@echo "  evaluate         Run evaluation on test output"
	@echo "  lint             Run linting (ruff, mypy)"
	@echo "  format           Format code with ruff"
	@echo "  clean            Clean generated files and directories"
	@echo ""

install:
	$(PIP) install -e .

install-dev:
	$(PIP) install -e '.[server,ocr,test]'
	$(PIP) install reportlab ruff mypy

test:
	pytest -v

test-ci: generate-golden
	pytest tests/test_integration_ci.py -v --tb=short

test-integration: generate-golden
	pytest tests/test_integration_ci.py -v -k "test_end_to_end" --tb=short

# Generate golden PDF fixture
generate-golden:
	$(PYTHON) tests/fixtures/generate_golden_pdf.py

# Update baseline outputs for regression tests
update-baselines: generate-golden install-dev
	@echo "Updating baselines..."
	mkdir -p tests/baselines/golden_chapter
	algl-pdf index tests/fixtures/golden_chapter.pdf \
		--out tests/baselines/golden_chapter \
		--use-aliases \
		--concepts-config tests/fixtures/golden_concepts.yaml
	@echo "✅ Baseline updated: tests/baselines/golden_chapter"

# Run evaluation on test output
evaluate: update-baselines
	@echo "Running evaluation..."
	algl-pdf evaluate tests/baselines/golden_chapter \
		--threshold 0.70 \
		--output tests/baselines/evaluation-report.json
	@echo "✅ Evaluation report: tests/baselines/evaluation-report.json"

# Run regression detection
regression-check: update-baselines
	@echo "Checking for regressions..."
	mkdir -p /tmp/current_output
	algl-pdf index tests/fixtures/golden_chapter.pdf \
		--out /tmp/current_output \
		--use-aliases \
		--concepts-config tests/fixtures/golden_concepts.yaml
	algl-pdf detect-regressions \
		tests/baselines/golden_chapter \
		/tmp/current_output \
		--tolerance 0.15 \
		--output /tmp/regression-report.json

lint:
	ruff check src/ tests/
	mypy src/algl_pdf_helper/ --ignore-missing-imports

format:
	ruff format src/ tests/

clean:
	rm -rf build/ dist/ *.egg-info/
	rm -rf .pytest_cache/ .mypy_cache/ .ruff_cache/
	rm -rf tests/baselines/golden_chapter/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -f tests/fixtures/golden_chapter.pdf
