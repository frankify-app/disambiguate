SHELL := bash
.ONESHELL:
.SHELLFLAGS := -eu -o pipefail -c
.DELETE_ON_ERROR:
MAKEFLAGS += --warn-undefined-variables
MAKEFLAGS += --no-builtin-rules

.DEFAULT_GOAL := help

.PHONY: help ## Shows help for all PHONY targets with help text
help:
	@grep -E '^.PHONY:.*?## .*$$' $(MAKEFILE_LIST) \
	| sort \
	| sed 's/^Makefile:.PHONY: //' \
	| awk ' \
		BEGIN {FS = " *?## "}; \
		{printf "\033[36m%-30s\033[0m %s\n", $$1, $$2} \
	' \
	;

.SECONDEXPANSION:

include .env
export

RUN := uv run
PYTHON := uv python
RUN_MODULE := $(PYTHON) -m
SRC_PATH := src/disambiguate
TEST_PATH := tests

.env:
	cp .env.example $@
	@echo "Created .env from .env.example"

.PHONY: install ## Installs all dependencies
install: .env install-uv
	$(RUN) pre-commit

.PHONY: install-uv ## Installs all dependencies via uv
install-uv:
	uv sync

.PHONY: install-pip ## Installs all dependencies via pip
install-pip:
	$(RUN_MODULE) pip install -r requirements.txt

.PHONY: requirements.txt ## Refresh requirements.txt file
requirements.txt:
	uv pip export -f requirements.txt --output requirements.txt

.PHONY: check ## Runs all code checks and tests
check: auto-format lint type-check test

.PHONY: type-check ## Run all type checks
type-check: mypy

.PHONY: auto-format ## Auto-format all code
auto-format: $(SRC_PATH) $(TEST_PATH)
	$(RUN) black $^
	$(RUN) isort $^
	$(RUN) ruff --fix $^

.PHONY: lint ## Run all linters
lint: mypy

.PHONY: mypy ## Run mypy
mypy: $(SRC_PATH) tests
	$(RUN) mypy $^

.PHONY: main ## Runs the main program
main:
	$(RUN) disambiguate add 21 42

.PHONY: run ## Run everything
run: main

.PHONY: test ## Run all tests
test: unit-test e2e-test

.PHONY: unit-test ## Run all unit tests
unit-test:
	$(RUN) pytest -v -s --disable-warnings $(TEST_PATH)/unit

.PHONY: e2e-test ## Run all end-to-end tests
e2e-test:
	echo "No e2e tests yet"
