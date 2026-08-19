.PHONY: setup voice-setup infra-up infra-down docker-up docker-down docker-logs docker-status migrate api web workers test lint benchmark dev launch share voiceover voiceover-math stop sample clean

PYTHON ?= python3.12
VENV := .venv
BIN := $(VENV)/bin

setup:
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install --upgrade pip
	$(BIN)/pip install -e '.[dev,ocr,voice]'
	npm install
	./scripts/extract_sample_corpus.sh
	./scripts/setup_local_voice.sh

voice-setup:
	@./scripts/setup_local_voice.sh

infra-up:
	docker compose up -d postgres redis

infra-down:
	docker compose down

docker-up:
	docker compose up --build --detach

docker-down:
	docker compose down

docker-logs:
	docker compose logs --follow api worker web

docker-status:
	docker compose ps

migrate:
	$(BIN)/alembic upgrade head

api:
	$(BIN)/uvicorn scidoc_api.main:app --reload --host 127.0.0.1 --port 8000

web:
	npm run dev

workers:
	$(BIN)/dramatiq scidoc_jobs.tasks --processes 1 --threads 4

test:
	$(BIN)/pytest
	npm test

lint:
	$(BIN)/ruff check .
	$(BIN)/ruff format --check .
	$(BIN)/mypy apps/api/src packages cli/src
	npm run lint
	npm run typecheck

benchmark:
	$(BIN)/scidoc benchmark benchmark/datasets/source-documents/input

sample:
	./scripts/extract_sample_corpus.sh
	$(BIN)/scidoc process 'benchmark/datasets/source-documents/input/Formula.pdf'

dev:
	./scripts/start_dev.sh

launch:
	@./scripts/start_dev.sh

share:
	@SCIDOC_SHARE=1 ./scripts/start_dev.sh

voiceover:
	@./scripts/test_voiceover.sh

voiceover-math:
	@./scripts/test_voiceover.sh math

stop:
	@bash ./scripts/stop_dev.sh

clean:
	find . -type d -name __pycache__ -prune -exec rm -r {} +
