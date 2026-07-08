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
	$(PYTHON) -m pytest tests

smoke:
	powershell -NoProfile -Command "$$server = Start-Process python -ArgumentList 'src/main.py' -PassThru; Start-Sleep -Seconds 2; try { Invoke-RestMethod 'http://localhost:8080/health' | Out-Null; Write-Host 'Smoke test passed' } finally { Stop-Process -Id $$server.Id }"

clean:
	$(PYTHON) -c "import shutil, pathlib; \
		root = pathlib.Path('.'); \
		dirs = ['__pycache__', '.pytest_cache', 'htmlcov', 'build', 'dist']; \
		[shutil.rmtree(p, ignore_errors=True) for d in dirs for p in root.rglob(d)]; \
		[p.unlink() for ext in ('*.pyc', '*.pyo', '.coverage') for p in root.rglob(ext)]"

docker-build:
	docker compose build

docker-run:
	docker compose up downloader

docker-test:
	docker compose run --rm downloader-tests

docker-down:
	docker compose down