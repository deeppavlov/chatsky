SHELL = /bin/bash

VENV_PATH = venv

help:
	@echo "Thanks for your interest in the Dialog Flow Engine!"
	@echo
	@echo "make lint: Run linters"
	@echo "make test: Run basic tests (not testing most integrations)"
	@echo "make test-all: Run ALL tests (slow, closest to CI)"
	@echo "make format: Run code formatters (destructive)"
	@echo

venv:
	virtualenv -p python3 $(VENV_PATH)
	$(VENV_PATH)/bin/pip install -r requirements.txt
	$(VENV_PATH)/bin/pip install -r requirements_dev.txt
	$(VENV_PATH)/bin/pip install -r requirements_test.txt


format: venv
	@$(VENV_PATH)/bin/python -m black --line-length=120 .
.PHONY: format

check: lint test
.PHONY: check

lint: venv
	@set -e && $(VENV_PATH)/bin/python -m black --line-length=120 --check . || ( \
		echo "================================"; \
		echo "Bad formatting? Run: make format"; \
		echo "================================"; \
		false)

.PHONY: lint

test: venv
	@$(VENV_PATH)/bin/python -m pytest --cov-report html --cov-report term --cov=df_engine tests/
.PHONY: test

test_all: venv test lint
`.PHONY: test_all

build_doc:
	sphinx-build -M clean docs docs/build
	sphinx-build -M html docs docs/build
`.PHONY: build_doc
