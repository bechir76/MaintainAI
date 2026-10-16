.PHONY: help install up up-replay down logs test test-unit lint format ingest eval manuals datasets real-manuals simulate mcp api web kind-deploy kind-delete

UV ?= uv
COMPOSE ?= docker compose

help:
	@grep -E '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'

install: ## Install Python and web dependencies
	$(UV) sync
	cd web && npm ci

up: ## Start the full stack (db, simulator, MCP server, API, web) and ingest manuals
	$(COMPOSE) up --build -d
	@echo "Web UI:  http://localhost:8080"
	@echo "API:     http://localhost:8000/docs"
	@echo "MCP:     http://localhost:8001/mcp"

up-replay: ## Like `up`, but C-1 and P-3 replay real datasets (run `make datasets` first)
	SIM_MODE=replay $(COMPOSE) up --build -d

down: ## Stop the stack
	$(COMPOSE) down

logs: ## Tail logs of all services
	$(COMPOSE) logs -f

test: ## Run unit + integration tests with coverage (needs Docker)
	$(UV) run pytest --cov --cov-report=term-missing --cov-report=xml

test-unit: ## Run unit tests only (no Docker needed)
	$(UV) run pytest tests/unit

lint: ## Ruff, formatting check, mypy and the web type check
	$(UV) run ruff check .
	$(UV) run ruff format --check .
	$(UV) run mypy
	cd web && npm run lint

format: ## Auto-format Python code
	$(UV) run ruff check --fix .
	$(UV) run ruff format .

manuals: ## Rebuild the sample PDF manuals from Markdown sources
	$(UV) run python scripts/build_manuals.py

datasets: ## Download MetroPT-3 and CWRU bearing data into data/raw and prepare the replay files
	$(UV) run --group data python scripts/download_datasets.py

real-manuals: ## Download manufacturer manuals into data/manuals_real
	$(UV) run python scripts/download_manuals.py

ingest: ## Parse, chunk and embed the manuals into pgvector
	$(UV) run python -m ingestion

eval: ## Run the evaluation suite (offline metrics; full metrics if MISTRAL_API_KEY is set)
	$(UV) run python -m evals

simulate: ## Run the sensor simulator locally
	$(UV) run python -m simulator

mcp: ## Run the MCP server locally (streamable HTTP on :8001)
	$(UV) run python -m mcp_server

api: ## Run the agent API locally on :8000
	$(UV) run uvicorn api.main:app --reload --port 8000

web: ## Run the web UI dev server on :5173
	cd web && npm run dev

kind-deploy: ## Create a kind cluster, build + load images and install the Helm chart
	./scripts/kind-deploy.sh

kind-delete: ## Delete the kind cluster
	kind delete cluster --name maintainai
