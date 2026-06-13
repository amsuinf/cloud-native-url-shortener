# Observability

The service exposes Prometheus metrics at `/metrics`. The Helm chart ships a
`ServiceMonitor`, so once the **kube-prometheus-stack** is installed, scraping
is automatic.

## Install the monitoring stack

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace
```

## Load the assets

```bash
# Alerting rules
kubectl apply -f monitoring/rules/alerts.yaml

# Grafana dashboard — import monitoring/dashboards/url-shortener.json
# (Grafana UI → Dashboards → Import) or via a ConfigMap with the
# grafana_dashboard=1 label for the sidecar to auto-load.
```

## Metrics exported by the app

| Metric | Type | Meaning |
| --- | --- | --- |
| `http_requests_total` | counter | requests by method/endpoint/status |
| `http_request_duration_seconds` | histogram | request latency |
| `links_created_total` | counter | short links created |
| `redirects_total` | counter | redirects served |

## SLOs encoded as alerts

- **Availability:** 5xx error ratio < 5% (critical)
- **Latency:** p99 < 500ms (warning)
- **Liveness:** at least one healthy scrape target (critical)
