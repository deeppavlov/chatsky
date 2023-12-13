.ONESHELL:

SHELL = /bin/bash

PYTHON = python3
VENV_PATH = venv
VERSIONING_FILES = setup.py makefile docs/source/conf.py dff/__init__.py
CURRENT_VERSION = 0.6.4
TEST_COVERAGE_THRESHOLD=95
TEST_ALLOW_SKIP=all  # for more info, see tests/conftest.py

PATH := $(VENV_PATH)/bin:$(PATH)
PWD := $(shell pwd)

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
	black --line-length=120 --exclude='venv|build|tutorials' .
	black --line-length=80 tutorials
.PHONY: format

lint: venv
	flake8 --max-line-length=120 --exclude venv,build,tutorials --per-file-ignores='**/__init__.py:F401' .
	flake8 --max-line-length=100 --per-file-ignores='**/3_load_testing_with_locust.py:E402 **/4_streamlit_chat.py:E402'  tutorials
	@set -e && black --line-length=120 --check --exclude='venv|build|tutorials' . && black --line-length=80 --check tutorials || ( \
		echo "================================"; \
		echo "Bad formatting? Run: make format"; \
		echo "================================"; \
		false)
	# TODO: Add mypy testing
	# @mypy . --exclude venv*,build
.PHONY: lint

docker_up:
	docker compose --profile context_storage --profile stats --profile ext up -d --build --wait
.PHONY: docker_up

test: venv
	source <(cat .env_file | sed 's/=/=/' | sed 's/^/export /') && pytest -m "not no_coverage" --cov-fail-under=$(TEST_COVERAGE_THRESHOLD) --cov-report html --cov-report term --cov=dff --allow-skip=$(TEST_ALLOW_SKIP) tests/
.PHONY: test

test_all: venv docker_up test lint
.PHONY: test_all

build_drawio:
	docker run --rm --name="drawio-convert" -v $(PWD)/docs/source/drawio_src:/data rlespinasse/drawio-export -f png --on-changes --remove-page-suffix
	docker run --rm --name="drawio-chown" -v $(PWD)/docs/source/drawio_src:/data --entrypoint chown rlespinasse/drawio-export -R "$(shell id -u):$(shell id -g)" /data
	for folder in docs/source/drawio_src/*; do
		foldername=`basename $${folder}`
		for file in $${folder}/*; do
			filename=`basename $${file}`
			if [[ -d $${file} && $${filename} == "export" ]]; then
				mkdir -p docs/source/_static/drawio/$${foldername}
				cp -r $${file}/* docs/source/_static/drawio/$${foldername}
			fi
		done
	done
.PHONY: build_drawio

doc: venv clean_docs build_drawio
	python3 docs/source/utils/patching.py
	sphinx-apidoc -e -E -f -o docs/source/apiref dff
	sphinx-build -M clean docs/source docs/build
	source <(cat .env_file | sed 's/=/=/' | sed 's/^/export /') && export DISABLE_INTERACTIVE_MODE=1 && sphinx-build -b html -W --keep-going docs/source docs/build
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
	rm -rf docs/tutorials
	rm -rf docs/source/apiref
	rm -rf docs/source/_misc
	rm -rf docs/source/tutorials
	rm -rf docs/source/_static/drawio
	rm -rf docs/source/drawio_src/**/export
.PHONY: clean_docs

clean: clean_docs
	rm -rf $(VENV_PATH)
	rm -rf .pytest_cache
	rm -rf *.egg-info
	rm -rf htmlcov
	rm -f .coverage
	rm -rf build
.PHONY: clean
