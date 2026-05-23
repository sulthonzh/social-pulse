# Kubernetes Deployment

Deploy SocialPulse to a Kubernetes cluster using raw manifests.

## Prerequisites

- kubectl configured against a target cluster
- Container image `social-pulse:latest` pushed to a registry accessible by the cluster
- (Optional) A `LocalStorage` or cloud-backed StorageClass named `standard`

## Quick Start

```bash
# Apply all manifests in order
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/pvc-data.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deployment-api.yaml
kubectl apply -f k8s/service-api.yaml
kubectl apply -f k8s/deployment-worker.yaml
kubectl apply -f k8s/deployment-crawl-worker.yaml
kubectl apply -f k8s/deployment-gold-builder.yaml
```

Or apply everything at once (namespace must exist first):

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/ -R
```

## Override the Image

Edit each deployment or use `kubectl set image`:

```bash
kubectl set image deployment/socialpulse-api api=your-registry/social-pulse:v1.2.0 -n socialpulse
kubectl set image deployment/socialpulse-worker worker=your-registry/social-pulse:v1.2.0 -n socialpulse
kubectl set image deployment/socialpulse-crawl-worker crawl-worker=your-registry/social-pulse:v1.2.0 -n socialpulse
kubectl set image deployment/socialpulse-gold-builder gold-builder=your-registry/social-pulse:v1.2.0 -n socialpulse
```

## Secrets

Create a secret for sensitive values that should not live in the ConfigMap:

```bash
kubectl create secret generic socialpulse-secrets \
  --namespace socialpulse \
  --from-literal=SOCIALPULSE_API_KEY=<your-api-key> \
  --from-literal=SOCIALPULSE_TWITTER_BEARER_TOKEN=<your-token>
```

Then add `envFrom` referencing this secret in the relevant deployment manifests.

## Verify

```bash
kubectl get pods -n socialpulse
kubectl get svc -n socialpulse
kubectl logs -f deployment/socialpulse-api -n socialpulse
```

## Manifest Summary

| File | Resource | Purpose |
|------|----------|---------|
| `namespace.yaml` | Namespace | `socialpulse` namespace |
| `pvc-data.yaml` | PVC | 10Gi persistent data volume |
| `configmap.yaml` | ConfigMap | Non-sensitive env vars |
| `deployment-api.yaml` | Deployment | FastAPI server (port 8000, probes on /healthz, /readyz) |
| `service-api.yaml` | Service | ClusterIP on port 80 targeting port 8000 |
| `deployment-worker.yaml` | Deployment | AI enrichment worker (health on :8081) |
| `deployment-crawl-worker.yaml` | Deployment | Crawl worker (health on :8082) |
| `deployment-gold-builder.yaml` | Deployment | Gold table builder (health on :8083) |
