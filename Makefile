PROJECT_ID ?= $(shell gcloud config get-value project 2>/dev/null)
REGION ?= us-east1
SERVICE_NAME ?= grocery-agent
REGISTRY = $(REGION)-docker.pkg.dev/$(PROJECT_ID)/grocery-agent
IMAGE = $(REGISTRY)/agent
GATEWAY_IMAGE ?= $(REGION)-docker.pkg.dev/$(PROJECT_ID)/ghcr-remote/eliasecchig/a2a-gateway:main
STORE_GRAPHQL_URL ?= https://your-store.com/graphql

# ---------------------------------------------------------------------------
# Local development
# ---------------------------------------------------------------------------

install:
	@command -v uv >/dev/null 2>&1 || { echo "uv is not installed. Install from https://docs.astral.sh/uv/"; exit 1; }
	uv sync

dev:
	set -a && [ -f .env ] && . .env; \
	uv run uvicorn app.fast_api_app:app --host 0.0.0.0 --port 8080 --reload

playground:
	uv run adk web --port 8501

test:
	uv run python -m pytest tests/ -xvs

lint:
	uv run ruff check . --fix && uv run ruff format . && uv run codespell .

# ---------------------------------------------------------------------------
# Cloud deployment
#
#   make deploy
#
# Builds the container image, creates secrets, then deploys everything
# via Terraform: Cloud Run, IAM, Cloud Scheduler, Secret Manager.
# ---------------------------------------------------------------------------

deploy:
	@if [ -z "$(PROJECT_ID)" ]; then \
		echo "Error: PROJECT_ID is not set."; \
		echo "Run: gcloud config set project <your-project-id>"; \
		exit 1; \
	fi
	@echo "==> [1/5] Enabling required APIs..."
	gcloud services enable \
		artifactregistry.googleapis.com \
		cloudbuild.googleapis.com \
		--project=$(PROJECT_ID) --quiet
	@echo ""
	@echo "==> [2/5] Setting up Artifact Registry..."
	-gcloud artifacts repositories create grocery-agent \
		--repository-format=docker \
		--location=$(REGION) \
		--project=$(PROJECT_ID) 2>/dev/null
	@gcloud artifacts repositories describe ghcr-remote \
		--location=$(REGION) --project=$(PROJECT_ID) >/dev/null 2>&1 || ( \
		echo "Creating ghcr-remote (Artifact Registry proxy for ghcr.io)..." && \
		gcloud artifacts repositories create ghcr-remote \
			--repository-format=docker \
			--location=$(REGION) \
			--project=$(PROJECT_ID) \
			--mode=remote-repository \
			--remote-docker-repo=https://ghcr.io \
			--quiet)
	@PROJECT_NUMBER=$$(gcloud projects describe $(PROJECT_ID) --format='value(projectNumber)') && \
		gcloud projects add-iam-policy-binding $(PROJECT_ID) \
			--member="serviceAccount:$${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
			--role="roles/artifactregistry.writer" \
			--quiet >/dev/null && \
		gcloud projects add-iam-policy-binding $(PROJECT_ID) \
			--member="serviceAccount:$${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
			--role="roles/storage.objectViewer" \
			--quiet >/dev/null
	@echo ""
	@echo "==> [3/5] Building container image..."
	gcloud builds submit . \
		--tag $(IMAGE) \
		--project=$(PROJECT_ID) --quiet
	@echo ""
	@echo "==> [4/5] Creating secrets (if missing)..."
	@gcloud secrets describe STORE_USERNAME --project=$(PROJECT_ID) >/dev/null 2>&1 || \
		(echo "Creating STORE_USERNAME secret..." && \
		 gcloud secrets create STORE_USERNAME --project=$(PROJECT_ID) --replication-policy=automatic && \
		 echo "Add a version: echo -n 'user@email.com' | gcloud secrets versions add STORE_USERNAME --data-file=- --project=$(PROJECT_ID)")
	@gcloud secrets describe STORE_PASSWORD --project=$(PROJECT_ID) >/dev/null 2>&1 || \
		(echo "Creating STORE_PASSWORD secret..." && \
		 gcloud secrets create STORE_PASSWORD --project=$(PROJECT_ID) --replication-policy=automatic && \
		 echo "Add a version: echo -n 'password' | gcloud secrets versions add STORE_PASSWORD --data-file=- --project=$(PROJECT_ID)")
	@for SECRET in GROCERY_BRAIN_DOC_ID GOOGLE_OAUTH_CLIENT_ID GOOGLE_OAUTH_CLIENT_SECRET GOOGLE_OAUTH_REFRESH_TOKEN TELEGRAM_BOT_TOKEN NUDGE_RECIPIENT_ID; do \
		gcloud secrets describe $$SECRET --project=$(PROJECT_ID) >/dev/null 2>&1 || \
		(echo "Creating $$SECRET secret..." && \
		 gcloud secrets create $$SECRET --project=$(PROJECT_ID) --replication-policy=automatic && \
		 echo "  → Add a version: echo -n 'value' | gcloud secrets versions add $$SECRET --data-file=- --project=$(PROJECT_ID)"); \
	done
	@echo ""
	@echo "==> [5/5] Deploying infrastructure (Cloud Run, IAM, Cloud Scheduler)..."
	cd deployment/terraform/single-project && terraform init -input=false && terraform apply -auto-approve \
		-var=project_id=$(PROJECT_ID) \
		-var=region=$(REGION) \
		-var=service_name=$(SERVICE_NAME) \
		-var=image=$(IMAGE) \
		-var=gateway_image=$(GATEWAY_IMAGE) \
		-var=store_graphql_url=$(STORE_GRAPHQL_URL)
	@echo ""
	@echo "==> Deployment complete!"
	@echo ""
	@cd deployment/terraform/single-project && \
		echo "  Service URL:  $$(terraform output -raw service_url)" && \
		echo "  Gateway URL:  $$(terraform output -raw gateway_url)" && \
		echo "  Agent Card:   $$(terraform output -raw service_url)/a2a/app/.well-known/agent-card.json" && \
		echo "  Scheduler:    $$(terraform output -raw scheduler_job)"

remote-test:
	@if [ -z "$(PROJECT_ID)" ]; then \
		echo "Error: PROJECT_ID is not set."; \
		exit 1; \
	fi
	@SERVICE_URL=$$(cd deployment/terraform/single-project && terraform output -raw service_url) && \
		echo "Fetching agent card..." && \
		curl -s -H "Authorization: Bearer $$(gcloud auth print-identity-token)" \
			"$${SERVICE_URL}/a2a/app/.well-known/agent.json" | python3 -m json.tool

clean:
	@if [ -z "$(PROJECT_ID)" ]; then \
		echo "Error: PROJECT_ID is not set."; \
		exit 1; \
	fi
	@echo "==> Tearing down all infrastructure..."
	cd deployment/terraform/single-project && terraform destroy -auto-approve \
		-var=project_id=$(PROJECT_ID) \
		-var=region=$(REGION) \
		-var=service_name=$(SERVICE_NAME) \
		-var=image=$(IMAGE) \
		-var=gateway_image=$(GATEWAY_IMAGE) \
		-var=store_graphql_url=$(STORE_GRAPHQL_URL) \
	|| (echo "" && \
		echo "Retrying in 60s..." && \
		sleep 60 && \
		cd deployment/terraform/single-project && terraform destroy -auto-approve \
			-var=project_id=$(PROJECT_ID) \
			-var=region=$(REGION) \
			-var=service_name=$(SERVICE_NAME) \
			-var=image=$(IMAGE) \
		-var=gateway_image=$(GATEWAY_IMAGE) \
		-var=store_graphql_url=$(STORE_GRAPHQL_URL))
	@echo "Cleanup complete."
