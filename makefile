SHELL = /bin/bash

PYTHON = python3
VENV_PATH = venv
VERSIONING_FILES =  setup.py makefile docs/source/conf.py dff/__init__.py
CURRENT_VERSION = 0.10.1
TEST_COVERAGE_THRESHOLD=93

help:
	@echo "Thanks for your interest in Dialog Flow Framework!"
	@echo
	@echo "make lint: Run linters"
	@echo "make test: Run basic tests (not testing most integrations)"
	@echo "make test_all: Run ALL tests (slow, closest to CI)"
	@echo "make format: Run code formatters (destructive)"
	@echo "make build_doc: Build Sphinx docs; activate your virtual environment before execution"
	@echo "make pre_commit: Register a git hook to lint the code on each commit"
	@echo "make version_major: increment version major in metadata files 8.8.1 -> 9.0.0"
	@echo "make version_minor: increment version minor in metadata files 9.1.1 -> 9.2.0"
	@echo "make version_patch: increment patch number in metadata files 9.9.1 -> 9.9.2"
	@echo

venv:
	echo "Start creating virtual environment";\
	$(PYTHON) -m venv $(VENV_PATH);\
	$(VENV_PATH)/bin/pip install --upgrade pip;
	$(VENV_PATH)/bin/pip install -e .[devel_full];

venv_test:
	echo "Start creating virtual environment";\
	$(PYTHON) -m venv $(VENV_PATH);\
	$(VENV_PATH)/bin/pip install --upgrade pip;
	$(VENV_PATH)/bin/pip install -e .[test_full];
.PHONY venv_test

format: venv
	$(VENV_PATH)/bin/black --line-length=120 dff/
.PHONY: format

lint: venv
	$(VENV_PATH)/bin/flake8 --max-line-length 120 dff/
	@set -e && $(VENV_PATH)/bin/black --line-length=120 --check dff/ || ( \
		echo "================================"; \
		echo "Bad formatting? Run: make format"; \
		echo "================================"; \
		false)
	# TODO: Add mypy testing
	@# $(VENV_PATH)/bin/mypy dff/
.PHONY: lint

docker_up:
	docker-compose up -d
.PHONY: docker_up

wait_db: docker_up
	while ! docker-compose exec psql pg_isready; do sleep 1; done > /dev/null
	while ! docker-compose exec mysql bash -c 'mysql -u $$MYSQL_USERNAME -p$$MYSQL_PASSWORD -e "select 1;"'; do sleep 1; done &> /dev/null
.PHONY: wait_db

test: venv
	source <(cat .env_file | sed 's/=/=/' | sed 's/^/export /') && $(VENV_PATH)/bin/pytest --cov-fail-under=$(TEST_COVERAGE_THRESHOLD) --cov-report html --cov-report term --cov=dff tests/
.PHONY: test

test_all: venv wait_db test lint
.PHONY: test_all

doc: venv
	$(VENV_PATH)/bin/sphinx-apidoc -e -f -o docs/source/apiref dff
	$(VENV_PATH)/bin/sphinx-build -M clean docs/source docs/build
	$(VENV_PATH)/bin/sphinx-build -M html docs/source docs/build
.PHONY: doc

pre_commit: venv
	echo -e "#!/bin/sh\n\nmake test_all" > .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit
.PHONY: pre_commit

version_patch: venv
	$(VENV_PATH)/bin/bump2version --current-version $(CURRENT_VERSION) patch $(VERSIONING_FILES)
.PHONY: version_patch

version_minor: venv
	$(VENV_PATH)/bin/bump2version --current-version $(CURRENT_VERSION) minor $(VERSIONING_FILES)
.PHONY: version_minor

version_major: venv
	$(VENV_PATH)/bin/bump2version --current-version $(CURRENT_VERSION) major $(VERSIONING_FILES)
.PHONY: version_major
