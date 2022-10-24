SHELL = /bin/bash

VENV_PATH = venv
VERSIONING_FILES =  setup.py makefile docs/source/conf.py df_stats/__init__.py
CURRENT_VERSION = 0.1.0
DB_PASSWORD=${POSTGRES_PASSWORD}

help:
	@echo "Thanks for your interest in Dialog Flow Framework!"
	@echo
	@echo "make lint: Run linters"
	@echo "make test: Run basic tests (not testing most integrations)"
	@echo "make test-all: Run ALL tests (slow, closest to CI)"
	@echo "make format: Run code formatters (destructive)"
	@echo "make build_doc: Build Sphinx docs; activate your virtual environment before execution"
	@echo "make pre_commit: Register a git hook to lint the code on each commit"
	@echo "make version_major: increment version major in metadata files 8.8.1 -> 9.0.0"
	@echo "make version_minor: increment version minor in metadata files 9.1.1 -> 9.2.0"
	@echo "make version_patch: increment patch number in metadata files 9.9.1 -> 9.9.2"
	@echo "make collect_examples: Run examplesEnter DB_PASSWORD value after target"
	@echo "make docker_up: create containers for all databases."
	@echo "make wait_db: wait until container creation is over."
	@echo

venv:
	echo "Start creating virtual environment";\
	python3 -m venv $(VENV_PATH);\
	
	$(VENV_PATH)/bin/pip install -e . ;
	$(VENV_PATH)/bin/pip install -r requirements_dev.txt ;
	$(VENV_PATH)/bin/pip install -r requirements_test.txt ;
	
docker_up:
	docker-compose up -d
.PHONY: docker_up	
	
wait_db: docker_up
	while ! docker-compose exec psql pg_isready; do sleep 1; done > /dev/null
.PHONY: wait_db

collect-examples: venv
	@$(VENV_PATH)/bin/python examples/collect_stats.py cfg_from_file --db.password=$(DB_PASSWORD) examples/example_config.yaml
.PHONY: collect-examples

format: venv
	@$(VENV_PATH)/bin/python -m black --exclude="setup\.py|venv\/" --line-length=120 .
.PHONY: format

check: lint test
.PHONY: check

lint: venv
	@set -e && $(VENV_PATH)/bin/python -m black --exclude="setup\.py|venv\/" --line-length=120 --check . || ( \
		echo "================================"; \
		echo "Bad formatting? Run: make format"; \
		echo "================================"; \
		false)

.PHONY: lint

test: venv
	@$(VENV_PATH)/bin/python -m pytest --cov-report html --cov-report term --cov=df_stats tests/
.PHONY: test

test_all: venv test lint
.PHONY: test_all

doc: venv
	$(VENV_PATH)/bin/sphinx-apidoc -e -f -o docs/source/apiref df_stats
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