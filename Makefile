.PHONY: clean clean-test clean-pyc clean-build docs help
.DEFAULT_GOAL := help

define BROWSER_PYSCRIPT
import os, webbrowser, sys

try:
	from urllib import pathname2url
except:
	from urllib.request import pathname2url

webbrowser.open("file://" + pathname2url(os.path.abspath(sys.argv[1])))
endef
export BROWSER_PYSCRIPT

define PRINT_HELP_PYSCRIPT
import re, sys

for line in sys.stdin:
	match = re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("%-20s %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT

BROWSER := python -c "$$BROWSER_PYSCRIPT"

help:
	@python -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

clean: clean-build clean-pyc clean-test ## remove all build, test, coverage and Python artifacts

clean-build: ## remove build artifacts
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . \( -path ./env -o -path ./venv -o -path ./.env -o -path ./.venv \) -prune -o -name '*.egg-info' -exec rm -fr {} +
	find . \( -path ./env -o -path ./venv -o -path ./.env -o -path ./.venv \) -prune -o -name '*.egg' -exec rm -f {} +

clean-pyc: ## remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test: ## remove test and coverage artifacts
	rm -fr .tox/
	rm -f .coverage
	rm -fr htmlcov/
	rm -fr .pytest_cache
	rm tests/calamari_models/*

lint: ## check style with flake8
	flake8 ocrd_butler tests

test-init: ## download current checkpoint data files from Calamari OCR github repo
        ifeq ("$(wildcard tests/calamari_models/*.ckpt.h5)", "")
	for i in 0 1 2 3 4; do for f in json h5; \
		do wget "https://raw.githubusercontent.com/Calamari-OCR/calamari_models/master/gt4histocr/$${i}.ckpt.$${f}" -O "tests/calamari_models/$${i}.ckpt.$${f}" ; \
	done; done
        endif

test: test-init ## run tests quickly with the default Python
	PROFILE=test TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata py.test

test-all: ## run tests on every Python version with tox
	tox

coverage: ## check code coverage quickly with the default Python
	coverage run --source ocrd_butler -m pytest
	coverage report -m
	coverage html
	$(BROWSER) htmlcov/index.html

docs: ## generate Sphinx HTML documentation, including API docs
	rm -f docs/ocrd_butler.rst
	rm -f docs/modules.rst
	sphinx-apidoc -o docs/ ocrd_butler
	$(MAKE) -C docs clean
	$(MAKE) -C docs html
	$(BROWSER) docs/_build/html/index.html

servedocs: docs ## compile the docs watching for changes
	watchmedo shell-command -p '*.rst' -c '$(MAKE) -C docs html' -R -D .

release: dist ## package and upload a release
	twine upload dist/*
executable:
	pyinstaller --name ocrd_butler ocrd_butler/cli.py

dist: clean ## builds source and wheel package
	python setup.py sdist
	python setup.py bdist_wheel
	ls -l dist

install: clean ## install the package to the active Python's site-packages
	python setup.py install

run-celery:
	. ../ocrd_all/venv/bin/activate; TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata celery worker -A ocrd_butler.celery_worker.celery -E -l info

run-flask:
	. ../ocrd_all/venv/bin/activate; FLASK_APP=ocrd_butler/app.py flask run

run-flower:
	. ../ocrd_all/venv/bin/activate; flower --broker redis://localhost:6379 --persistent=True --db=flower [--log=debug

tesseract-model: ## install trained model for tesseract
	ocrd resmgr download ocrd-tesserocr-recognize Fraktur_GT4HistOCR.traineddata -a

calamari-model: ## install trained model for calamari
	mkdir -p /data && cd /data; \
	ocrd resmgr download ocrd-calamari-recognize qurator-gt4histocr-1.0 -al cwd

textline-detector-model: ## install trained model for sbb textline detector
	mkdir -p /data && cd /data; \
	ocrd resmgr download ocrd-sbb-textline-detector default -al cwd

sbb-binarize-model: ## install trained model for the sbb binarization processor
	mkdir -p /data && cd /data; \
	ocrd resmgr download ocrd-sbb-binarize default -al cwd
