#* Variables
SHELL := /usr/bin/env bash
PYTHON := python


#* Installation

.PHONY: install
install:
	poetry install -n
	yarn

.PHONY: pre-commit-install
pre-commit-install:
	poetry run pre-commit install

.PHONY: setup_git
setup_git:
	pre-commit install

.PHONY: setup-cms
setup-cms:
	poetry run python manage.py setup_pages

.PHONY: migrate
migrate:
	poetry run python manage.py migrate

.PHONY: bootstrap
bootstrap: install pre-commit-install migrate setup-cms
	touch app/settings/local.py

#* Formatters

.PHONY: codestyle
codestyle:
	poetry run pyupgrade --exit-zero-even-if-changed --py38-plus **/*.py
	poetry run isort --version
	poetry run isort --settings-path ./pyproject.toml ./
	poetry run black --version
	poetry run black --config ./pyproject.toml ./
	yarn prettier --write .

.PHONY: formatting
formatting: codestyle


#* Linting

.PHONY: test
test:
	poetry run pytest
	yarn test

.PHONY: check-codestyle
check-codestyle:
	poetry run isort --version
	poetry run isort --diff --check-only --settings-path ./pyproject.toml ./
	poetry run black --version
	poetry run black --diff --check --config pyproject.toml ./
	poetry run darglint --docstring-style google --verbosity 2 pyck
	yarn tsc --noemit
	yarn prettier --check .

.PHONY: check-safety
check-safety:
	poetry check
	poetry run safety check --full-report
	poetry run bandit -ll --recursive pyck tests

.PHONY: lint
lint: check-codestyle check-safety

.PHONY: ci
ci: lint test


#* Assets

.PHONY: build
build:
	yarn vite build
	SECRET_KEY=dummy poetry run python manage.py collectstatic --noinput --clear

.PHONY: release
release: migrate setup-cms

#* Server

.PHONY: runserver
runserver: release
	poetry run gunicorn -b 0.0.0.0:80 app.wsgi

.PHONY: run_wsgi
run_wsgi: release
	poetry run gunicorn -b 0.0.0.0:80 app.wsgi

.PHONY: run_production
run_production: release
	DJANGO_SETTINGS_MODULE=app.settings.production poetry run gunicorn -b 0.0.0.0:80 app.wsgi

.PHONY: testproduction
testproduction: release
	DEBUG=False DJANGO_SETTINGS_MODULE=app.settings.production poetry run gunicorn --worker-tmp-dir /dev/shm app.wsgi

#* Cleaning

.PHONY: pycache-remove
pycache-remove:
	find . | grep -E "(__pycache__|\.pyc|\.pyo$$)" | xargs rm -rf

.PHONY: build-remove
build-remove:
	rm -rf build/ vite/ docs/api/ docs/components/ temp/

.PHONY: clean-all
clean-all: pycache-remove build-remove
