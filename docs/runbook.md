# Runbook — URL Shortener

On-call reference. Assumes `kubectl` is pointed at the cluster and the app
runs in the `url-shortener` namespace.

## Quick triage

```bash
kubectl -n url-shortener get pods,hpa,svc
kubectl -n url-shortener logs -l app.kubernetes.io/name=url-shortener --tail=100
kubectl -n url-shortener describe deploy/url-shortener
```

## Alert: HighErrorRate (5xx > 5%)

Likely causes & checks:

1. **Redis unreachable** → readiness fails, pods drop from rotation.
   ```bash
   kubectl -n url-shortener get pods -l app.kubernetes.io/name=redis
   kubectl -n url-shortener exec deploy/url-shortener -- \
     python -c "from src.storage import RedisStore; print(RedisStore('redis://url-shortener-redis-master:6379/0').ping())"
   ```
   If Redis is down, restart it / check its PVC and memory.

2. **Bad deploy** → check recent ArgoCD sync / image tag.
   ```bash
   kubectl -n url-shortener get deploy url-shortener -o jsonpath='{.spec.template.spec.containers[0].image}'
   ```
   **Rollback:** `git revert` the promotion commit; ArgoCD re-syncs. Or fast
   manual rollback: `kubectl -n url-shortener rollout undo deploy/url-shortener`.

## Alert: HighLatencyP99 (> 500ms)

```bash
# Are we CPU-throttled / pegged?
kubectl -n url-shortener top pods
# Is the HPA at max?
kubectl -n url-shortener get hpa url-shortener
```
If at max replicas and still slow, raise `autoscaling.maxReplicas` or node
group `max_size`. Check Redis latency too.

## Alert: ServiceDown (no healthy targets)

```bash
kubectl -n url-shortener get pods
kubectl -n url-shortener describe pod <pod>   # Events: image pull, OOMKilled, probe fails
```
- `OOMKilled` → raise memory limit in values.yaml.
- `ImagePullBackOff` → verify image tag exists in GHCR + pull secret.
- All pods `Pending` → node capacity; check `kubectl get nodes` / cluster autoscaler.

## Manual scale (emergency)

```bash
kubectl -n url-shortener scale deploy/url-shortener --replicas=10
```
(HPA will reconcile afterward — disable HPA first if you need it pinned.)

## Useful one-liners

```bash
# Tail metrics for a single pod
kubectl -n url-shortener port-forward deploy/url-shortener 8000:8000
curl -s localhost:8000/metrics | grep -E 'http_requests_total|redirects_total'

# Recent restarts
kubectl -n url-shortener get pods -o wide
```
