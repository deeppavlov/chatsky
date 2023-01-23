SHELL = /bin/bash

PYTHON = python3
VENV_PATH = venv
VERSIONING_FILES = setup.py makefile docs/source/conf.py dff/__init__.py
CURRENT_VERSION = 0.2.0c
TEST_COVERAGE_THRESHOLD=93

PATH := $(VENV_PATH)/bin:$(PATH)

help:
	@echo "Thanks for your interest in Dialog Flow Framework!"
	@echo
	@echo "make lint: Run linters"
	@echo "make test: Run basic tests (not testing most integrations)"
	@echo "make test_all: Run ALL tests (slow, closest to CI)"
	@echo "make format: Run code formatters (destructive)"
	@echo "make doc: Build Sphinx docs; activate your virtual environment before execution"
	@echo "make pre_commit: Register a git hook to lint the code on each commit"
	@echo "make version_major: increment version major in metadata files 8.8.1 -> 9.0.0"
	@echo "make version_minor: increment version minor in metadata files 9.1.1 -> 9.2.0"
	@echo "make version_patch: increment patch number in metadata files 9.9.1 -> 9.9.2"
	@echo

venv:
	@echo "Start creating virtual environment"
	$(PYTHON) -m venv $(VENV_PATH)
	pip install --upgrade pip
	pip install -e .[devel_full]

format: venv
	black --line-length=120 --exclude='venv|build|examples' .
	black --line-length=100 examples
.PHONY: format

lint: venv
	flake8 --max-line-length=120 --exclude ./venv,./build,./examples .
	flake8 --max-line-length=100 examples
	@set -e && black --line-length=120 --check --exclude='venv|build|examples' . && black --line-length=100 --check examples || ( \
		echo "================================"; \
		echo "Bad formatting? Run: make format"; \
		echo "================================"; \
		false)
	# TODO: Add mypy testing
	# @mypy . --exclude venv*,build
.PHONY: lint

docker_up:
	docker-compose up -d
.PHONY: docker_up

wait_db: docker_up
	while ! docker-compose exec psql pg_isready; do sleep 1; done > /dev/null
	while ! docker-compose exec mysql bash -c 'mysql -u $$MYSQL_USERNAME -p$$MYSQL_PASSWORD -e "select 1;"'; do sleep 1; done &> /dev/null
.PHONY: wait_db

test: venv
	source <(cat .env_file | sed 's/=/=/' | sed 's/^/export /') && pytest --cov-fail-under=$(TEST_COVERAGE_THRESHOLD) --cov-report html --cov-report term --cov=dff tests/
.PHONY: test

test_all: venv wait_db test lint
.PHONY: test_all

doc: venv clean_docs
	sphinx-apidoc -e -E -f -o docs/source/apiref dff
	sphinx-build -M clean docs/source docs/build
	source <(cat .env_file | sed 's/=/=/' | sed 's/^/export /') && export DISABLE_INTERACTIVE_MODE=1 && sphinx-build -b html -W --keep-going -j 4 docs/source docs/build
.PHONY: doc

pre_commit: venv
	echo -e "#!/bin/sh\n\nmake test_all" > .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit
.PHONY: pre_commit

version_patch: venv
	bump2version --current-version $(CURRENT_VERSION) patch $(VERSIONING_FILES)
.PHONY: version_patch

version_minor: venv
	bump2version --current-version $(CURRENT_VERSION) minor $(VERSIONING_FILES)
.PHONY: version_minor

version_major: venv
	bump2version --current-version $(CURRENT_VERSION) major $(VERSIONING_FILES)
.PHONY: version_major


clean_docs:
	rm -rf docs/build
	rm -rf docs/examples
	rm -rf docs/source/apiref
	rm -rf docs/source/examples
.PHONY: clean_docs

clean: clean_docs
	rm -rf $(VENV_PATH)
	rm -rf .pytest_cache
	rm -rf *.egg-info
	rm -rf htmlcov
	rm -f .coverage
.PHONY: clean
