PYTHON ?= python

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