#!/usr/bin/env bash
# Spin up a local kind cluster, build the image, load it, and install the
# Helm chart with the in-cluster Redis. Lets you exercise the full Kubernetes
# path with zero cloud cost.
set -euo pipefail

CLUSTER=url-shortener-local
IMAGE=url-shortener:dev
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

command -v kind >/dev/null || { echo "kind not installed"; exit 1; }

echo "==> Creating kind cluster"
kind get clusters | grep -q "^${CLUSTER}$" || kind create cluster --name "${CLUSTER}"

echo "==> Building app image"
docker build -t "${IMAGE}" "${ROOT}/app"

echo "==> Loading image into kind"
kind load docker-image "${IMAGE}" --name "${CLUSTER}"

echo "==> Fetching Helm dependencies"
helm dependency build "${ROOT}/deploy/helm/url-shortener"

echo "==> Installing chart"
helm upgrade --install url-shortener "${ROOT}/deploy/helm/url-shortener" \
  --namespace url-shortener --create-namespace \
  --set image.repository=url-shortener \
  --set image.tag=dev \
  --set image.pullPolicy=Never \
  --set autoscaling.enabled=false \
  --set replicaCount=2 \
  --set ingress.enabled=false \
  --set metrics.serviceMonitor.enabled=false \
  --set podDisruptionBudget.enabled=false

echo "==> Waiting for rollout"
kubectl -n url-shortener rollout status deploy/url-shortener --timeout=120s

cat <<EOF

Done. Try it:
  kubectl -n url-shortener port-forward svc/url-shortener 8000:80
  curl -X POST localhost:8000/api/shorten -H 'content-type: application/json' \\
       -d '{"url":"https://anthropic.com"}'

Tear down:
  kind delete cluster --name ${CLUSTER}
EOF
