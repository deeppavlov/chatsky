SHELL = /bin/bash

VENV_PATH = venv

help:
	@echo "Thanks for your interest in the Dialog Flow Framework!"
	@echo
	@echo "make lint: Run linters"
	@echo "make test: Run basic tests (not testing most integrations)"
	@echo "make test-all: Run ALL tests (slow, closest to CI)"
	@echo "make format: Run code formatters (destructive)"
	@echo "make aws-lambda-layer-build: Build serverless ZIP dist package"
	@echo

venv:
	virtualenv -p python3 $(VENV_PATH)
	$(VENV_PATH)/bin/pip install -r requirements.txt
	$(VENV_PATH)/bin/pip install -r requirements_dev.txt
	$(VENV_PATH)/bin/pip install -r requirements_test.txt

dist: venv
	rm -rf dist build
	$(VENV_PATH)/bin/python setup.py sdist bdist_wheel

.PHONY: dist

format: venv
	$(VENV_PATH)/bin/tox -e linters --notest
	.tox/linters/bin/black .
.PHONY: format

test: venv
	@$(VENV_PATH)/bin/tox -e py2.7,py3.7
.PHONY: test

test-all: venv
	@TOXPATH=$(VENV_PATH)/bin/tox sh ./scripts/runtox.sh
.PHONY: test-all

check: lint test
.PHONY: check

lint: venv
	@set -e && $(VENV_PATH)/bin/tox -e linters || ( \
		echo "================================"; \
		echo "Bad formatting? Run: make format"; \
		echo "================================"; \
		false)

.PHONY: lint

docs: venv
	@$(VENV_PATH)/bin/pip install --editable .
	@$(VENV_PATH)/bin/pip install -U -r ./docs-requirements.txt
	@$(VENV_PATH)/bin/sphinx-build -W -b html docs/ docs/_build
.PHONY: docs

docs-hotfix: docs
	@$(VENV_PATH)/bin/pip install ghp-import
	@$(VENV_PATH)/bin/ghp-import -pf docs/_build
.PHONY: docs-hotfix
