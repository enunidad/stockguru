.PHONY: help install test run clean docker-build docker-run docker-test docker-down

PYTHON := py
PIP := py -m pip

help:
	@echo "StocksGuru Downloader"
	@echo ""
	@echo "Local commands:"
	@echo "  make install      Install Python dependencies"
	@echo "  make test         Run tests locally"
	@echo "  make run          Run downloader locally"
	@echo "  make clean        Remove Python cache files"
	@echo ""
	@echo "Docker commands, optional:"
	@echo "  make docker-build Build Docker image"
	@echo "  make docker-run   Run service with docker compose"
	@echo "  make docker-test  Run tests with docker compose"
	@echo "  make docker-down  Stop docker compose"

install:
	$(PIP) install -r requirements.txt

test:
	$(PYTHON) -m pytest tests -v

smoke:
	$(PYTHON) -m src.main

run:
	$(PYTHON) -m src.main

clean:
	@$(PYTHON) -c "import shutil, pathlib; \
		root = pathlib.Path('.'); \
		dirs = ['__pycache__', '.pytest_cache', 'htmlcov', 'build', 'dist']; \
		[shutil.rmtree(p, ignore_errors=True) for d in dirs for p in root.rglob(d)]; \
		[p.unlink() for ext in ('*.pyc', '*.pyo', '.coverage') for p in root.rglob(ext)]"

clean-cache:
	@$(PYTHON) -c "import shutil, pathlib; \
		data = pathlib.Path('data'); \
		[shutil.rmtree(p, ignore_errors=True) for p in data.iterdir() if p.is_dir()] if data.exists() else None"

docker-build:
	docker compose build

docker-run:
	docker compose up downloader

docker-test:
	docker compose run --rm downloader-tests

docker-down:
	docker compose down