# Local GRC Evidence Plan

This project is now local-first. The portfolio story is no longer an AWS deployment; it is a controlled local Kubernetes environment that demonstrates the same security and governance ideas without cloud cost.

## SOC 2-Oriented Controls

| Control Theme | Implementation | Evidence to Capture |
| --- | --- | --- |
| Confidentiality | Document chunks carry `classification` metadata and search applies a server-side Qdrant filter before context reaches Ollama. | API logs from upload/search, screenshots showing clearance changes, sample denied Restricted upload as Student-Only. |
| Availability | Kubernetes requests, limits, ResourceQuota, readiness probes, and backend HPA. | `kubectl describe quota -n uni-rag`, `kubectl get hpa -n uni-rag`, pod restart/status screenshots. |
| Least Privilege | Qdrant is reachable only from backend pods through NetworkPolicy. | `kubectl describe networkpolicy -n uni-rag`. |
| Auditability | App emits JSON logs for health checks, ingestion, privilege blocks, and retrieval events. | `kubectl logs deploy/backend -n uni-rag` or `docker compose logs backend`. |
| Data Governance | Supported classifications are `Public`, `Student-Only`, and `Restricted-Internal`. | Upload examples and search responses showing source classifications. |

## Local Evidence Commands

```powershell
kubectl apply -k k8s/local
kubectl get all -n uni-rag
kubectl describe quota uni-rag-quota -n uni-rag
kubectl describe networkpolicy backend-to-qdrant-only -n uni-rag
kubectl logs deploy/backend -n uni-rag
```
