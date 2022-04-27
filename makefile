SHELL = /bin/bash

VENV_PATH = venv

help:
	@echo "Thanks for your interest in DF DB Connector!"
	@echo
	@echo "make lint: Run linters"
	@echo "make test: Run basic tests (not testing most integrations)"
	@echo "make test-all: Run ALL tests (slow, closest to CI)"
	@echo "make format: Run code formatters (destructive)"
	@echo "make build_doc: Build Sphinx docs"
	@echo "make hooks: Register a git hook to lint the code on each commit"
	@echo

venv:
	python3 -m venv $(VENV_PATH)
	$(VENV_PATH)/bin/pip install -e .
	$(VENV_PATH)/bin/pip install -r requirements_dev.txt
	$(VENV_PATH)/bin/pip install -r requirements_test.txt

format: venv
	@$(VENV_PATH)/bin/python -m black --exclude="setup\.py" --line-length=120 .
.PHONY: format

check: lint test
.PHONY: check

lint: venv
	$(VENV_PATH)/bin/python -m flake8 --config=setup.cfg df_db_connector/
	@set -e && $(VENV_PATH)/bin/python -m black --exclude="setup\.py" --line-length=120 --check . || ( \
		echo "================================"; \
		echo "Bad formatting? Run: make format"; \
		echo "================================"; \
		false)

.PHONY: lint

test: venv
	@$(VENV_PATH)/bin/python -m pytest --cov-report html --cov-report term --cov=df_db_connector tests/
.PHONY: test

test_all: venv test lint
.PHONY: test_all

build_doc:
	sphinx-apidoc -e -f -o docs/source/apiref df_db_connector
	sphinx-build -M clean docs/source docs/build
	sphinx-build -M html docs/source docs/build
.PHONY: build_doc

hooks:
	@git init .
	@cp pre-commit.sh .git/hooks/pre-commit
	@chmod +x .git/hooks/pre-commit
.PHONY: hooks
