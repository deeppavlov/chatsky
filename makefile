SHELL = /bin/bash

# VENV_PATH = venv
VENV_PATH = venv3.7

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
	@$(VENV_PATH)/bin/python -m pytest --cov-report html --cov-report term --cov=dff tests/
.PHONY: test

test-all: venv test lint
`.PHONY: test-all

# dist: venv
# 	rm -rf dist build
# 	$(VENV_PATH)/bin/python setup.py sdist bdist_wheel

# .PHONY: dist

# docs: venv
# 	@$(VENV_PATH)/bin/pip install --editable .
# 	@$(VENV_PATH)/bin/pip install -U -r ./docs-requirements.txt
# 	@$(VENV_PATH)/bin/sphinx-build -W -b html docs/ docs/_build
# .PHONY: docs

# docs-hotfix: docs
# 	@$(VENV_PATH)/bin/pip install ghp-import
# 	@$(VENV_PATH)/bin/ghp-import -pf docs/_build
# .PHONY: docs-hotfix
