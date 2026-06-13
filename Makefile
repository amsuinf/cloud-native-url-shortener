.DEFAULT_GOAL := help
APP_DIR := app
CHART := deploy/helm/url-shortener
IMAGE ?= url-shortener:dev

.PHONY: help install test lint run-local docker-build compose-up compose-down \
        helm-deps helm-lint helm-template kind-up kind-down tf-init tf-plan fmt

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

install: ## Install Python dev dependencies
	pip install -r $(APP_DIR)/requirements-dev.txt

test: ## Run unit tests
	cd $(APP_DIR) && pytest

lint: ## Lint application code
	cd $(APP_DIR) && ruff check .

fmt: ## Format Terraform
	cd terraform && terraform fmt -recursive

run-local: ## Run the API locally (needs Redis on :6379)
	cd $(APP_DIR) && uvicorn src.main:app --reload

docker-build: ## Build the container image
	docker build -t $(IMAGE) $(APP_DIR)

compose-up: ## Start API + Redis via docker compose
	docker compose up --build

compose-down: ## Stop the compose stack
	docker compose down -v

helm-deps: ## Fetch Helm chart dependencies
	helm dependency build $(CHART)

helm-lint: helm-deps ## Lint the Helm chart
	helm lint $(CHART)

helm-template: helm-deps ## Render manifests to stdout
	helm template url-shortener $(CHART) --api-versions monitoring.coreos.com/v1

kind-up: ## Build + deploy to a local kind cluster
	./scripts/kind-up.sh

kind-down: ## Delete the local kind cluster
	kind delete cluster --name url-shortener-local

tf-init: ## terraform init (no backend)
	cd terraform && terraform init -backend=false

tf-plan: ## terraform plan
	cd terraform && terraform plan
