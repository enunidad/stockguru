PYTHON ?= python

.PHONY: run test clean

run:
	$(PYTHON) -m src.app

test:
	$(PYTHON) -m pytest tests -v

clean:
	$(PYTHON) -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('__pycache__')]; [p.unlink() for p in pathlib.Path('.').rglob('*.pyc')]"