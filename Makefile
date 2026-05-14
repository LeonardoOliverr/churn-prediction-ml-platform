.PHONY: lint format test test-unit test-integration test-cov run build dev down logs logs-all train clean help

PYTHON := python
PYTEST := python -m pytest
RUFF   := python -m ruff
APP_HOST := 0.0.0.0
APP_PORT := 8000

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt

lint:
	$(RUFF) check .
	$(RUFF) format --check .

format:
	$(RUFF) check . --fix
	$(RUFF) format .

test:
	$(PYTEST) tests/ -v --tb=short

test-unit:
	$(PYTEST) tests/unit/ -v --tb=short

test-integration:
	$(PYTEST) tests/integration/ -m integration -v --tb=short --no-cov

test-cov:
	$(PYTEST) tests/unit/ --cov=ml --cov=src --cov-report=html --cov-report=term-missing

run:
	docker compose up -d

build:
	docker compose up -d --build

dev:
	$(PYTHON) -m uvicorn src.main:app --host $(APP_HOST) --port $(APP_PORT) --reload

down:
	docker compose down

logs:
	docker compose logs -f api

logs-all:
	docker compose logs -f

train:
	$(PYTHON) -m ml.train --model random-forest --tenant ibm-telco --project telco-churn-2018

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache htmlcov .coverage

help:
	@echo "Targets disponíveis:"
	@echo "  install          Instala dependências de produção"
	@echo "  install-dev      Instala dependências de desenvolvimento"
	@echo "  lint             Verifica estilo com ruff (sem modificar)"
	@echo "  format           Formata código com ruff"
	@echo "  test             Roda todos os testes"
	@echo "  test-unit        Apenas testes unitários (sem banco)"
	@echo "  test-integration Apenas testes de integração (requer PostgreSQL)"
	@echo "  test-cov         Testes unitários com relatório de cobertura HTML"
	@echo "  run              Sobe toda a stack via docker compose (sem rebuild)"
	@echo "  build            Sobe toda a stack forçando rebuild das imagens"
	@echo "  dev              Sobe apenas a API com uvicorn --reload (sem Docker)"
	@echo "  down             Para e remove todos os containers"
	@echo "  logs             Acompanha logs do container api"
	@echo "  logs-all         Acompanha logs de todos os containers"
	@echo "  train            Treina Random Forest (ibm-telco)"
	@echo "  clean            Remove arquivos temporários e cache"
