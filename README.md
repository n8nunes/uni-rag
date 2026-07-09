# uni-rag

Local-first enterprise document search and AI assistant for university PDFs.

The project originally had an AWS portfolio deployment phase. That path has been removed: the target architecture is now Docker Compose for daily local development and local Kubernetes for portfolio-grade security evidence.

## Current Phase

The repository is at the end of Part 1 and the beginning of Part 2:

- FastAPI backend exists and now performs PDF ingestion, metadata tagging, Ollama embeddings, Qdrant storage, secure filtered search, and Ollama answer generation.
- React dashboard exists for upload, classification, clearance selection, and RAG search.
- Docker Compose exists for backend, frontend, and Qdrant.
- Local Kubernetes manifests exist for namespace, deployments, services, resource governance, HPA, and NetworkPolicy.
- AWS-specific work is intentionally out of scope.

## Prerequisites

- Docker Desktop
- Ollama running locally
- Ollama models:

```powershell
ollama pull llama3
ollama pull nomic-embed-text
```

## Run Locally

```powershell
docker compose up --build
```

Open:

- Frontend: http://localhost:5173
- Backend health: http://localhost:8000/health
- API docs: http://localhost:8000/docs
- Qdrant: http://localhost:6333/dashboard

## Local Kubernetes

Build images into your local cluster runtime, then apply:

```powershell
kubectl apply -k k8s/local
kubectl get all -n uni-rag
```

Depending on whether you use Kind, Minikube, or Docker Desktop Kubernetes, image loading differs. Use `uni-rag-backend:local` and `uni-rag-frontend:local` to match the manifests.

## Security Model

- Users submit a clearance through local dev headers.
- Uploads cannot be tagged above the caller clearance.
- Search queries are filtered in Qdrant by classification before any context is sent to Ollama.
- JSON audit logs are emitted for ingestion, search, privilege blocks, and health checks.
- Kubernetes resources include quotas, limits, readiness checks, HPA, and a Qdrant ingress NetworkPolicy.
