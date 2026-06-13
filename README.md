# Cloud-Native URL Shortener — Production-Grade DevOps Platform

A complete, end-to-end demonstration of how a real service is built, shipped,
and operated in production. A small but realistic microservice (a URL
shortener) wrapped in the full platform a FAANG-style team would run it on:
**Infrastructure as Code, containers, Kubernetes, CI/CD, GitOps, and
observability.**

> The point isn't the app — it's everything *around* the app.

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-multi--stage-2496ED?logo=docker&logoColor=white)
![Kubernetes](https://img.shields.io/badge/Kubernetes-Helm-326CE5?logo=kubernetes&logoColor=white)
![Terraform](https://img.shields.io/badge/Terraform-AWS%20EKS-7B42BC?logo=terraform&logoColor=white)
![ArgoCD](https://img.shields.io/badge/GitOps-ArgoCD-EF7B4D?logo=argo&logoColor=white)
![Prometheus](https://img.shields.io/badge/Observability-Prometheus%20%2B%20Grafana-E6522C?logo=prometheus&logoColor=white)
![CI](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-2088FF?logo=githubactions&logoColor=white)

---

## What this demonstrates

| Capability | How it's shown here |
| --- | --- |
| **Application engineering** | FastAPI service, Redis storage, Prometheus metrics, health/readiness split, unit-tested with a fake store |
| **Containerization** | Multi-stage Dockerfile, non-root user, read-only rootfs, dropped capabilities, healthcheck |
| **Infrastructure as Code** | Terraform → AWS VPC (3 AZ) + EKS + managed node group + IRSA, remote state |
| **Orchestration** | Helm chart: HPA, PodDisruptionBudget, probes, topology spread, security context, ServiceMonitor |
| **CI/CD** | GitHub Actions: lint → test → IaC validate → build → Trivy scan → push to GHCR |
| **GitOps** | ArgoCD auto-syncs the cluster to git; deploys are commits; rollback is `git revert` |
| **Observability** | `/metrics`, Grafana dashboard, SLO-based Prometheus alerts |
| **Operability** | Architecture doc with trade-offs + an on-call runbook |

## Architecture

```
                          ┌──────────────┐
   Push to main ─► CI ───►│ GHCR (image) │
                  │       └──────────────┘
                  └─► CD: bump image tag, commit ─► Git ◄── ArgoCD watches
                                                              │ sync
   User ─HTTPS─► Ingress ─► Service ─► [api pods] ─► Redis    ▼
                                          ▲                 EKS cluster
                              Prometheus ─┘─► Grafana / Alertmanager
```

Full diagrams and design trade-offs: **[docs/architecture.md](docs/architecture.md)**

## Repository layout

```
.
├── app/                    # FastAPI service + tests + Dockerfile
├── terraform/              # AWS VPC + EKS (IaC)
├── deploy/helm/            # Helm chart (HPA, PDB, probes, ServiceMonitor)
├── argocd/                 # ArgoCD Application + Project (GitOps)
├── monitoring/             # Prometheus alert rules + Grafana dashboard
├── .github/workflows/      # CI + CD pipelines
├── scripts/kind-up.sh      # One-command local Kubernetes demo
└── docs/                   # Architecture + runbook
```

## Quickstart

### 1. Run locally (Docker Compose)

```bash
make compose-up
# create a short link
curl -X POST localhost:8000/api/shorten \
  -H 'content-type: application/json' \
  -d '{"url":"https://www.anthropic.com"}'
# follow the redirect
curl -iL localhost:8000/<code>
```

Interactive API docs at <http://localhost:8000/docs>.

### 2. Run the test suite

```bash
make install && make test     # 8 unit tests, no Redis required (fake store)
make lint
```

### 3. Deploy to a local Kubernetes cluster (kind)

```bash
make kind-up                  # build image, load into kind, helm install
```

### 4. Provision real infra (AWS)

```bash
cd terraform && terraform init && terraform apply
aws eks update-kubeconfig --name url-shortener-eks
kubectl apply -f argocd/      # ArgoCD takes over from here
```

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/shorten` | Create a short link (optional `custom_code`) |
| `GET` | `/{code}` | 307 redirect to the original URL |
| `GET` | `/api/links/{code}` | Inspect a link without redirecting |
| `GET` | `/healthz` | Liveness probe |
| `GET` | `/readyz` | Readiness probe (checks Redis) |
| `GET` | `/metrics` | Prometheus metrics |

## Resume bullets (steal these)

- Built and operated a cloud-native microservice on **AWS EKS**, provisioned
  end-to-end with **Terraform** (VPC across 3 AZs, managed node groups, IRSA).
- Designed a **GitOps** delivery pipeline (**GitHub Actions + ArgoCD**) where
  every production change is an auditable, instantly-revertable git commit;
  images are vulnerability-scanned with **Trivy** before promotion.
- Packaged the service as a hardened **Helm** chart with autoscaling (HPA),
  **PodDisruptionBudgets**, liveness/readiness probes, and a non-root,
  read-only-rootfs security context.
- Instrumented the service with **Prometheus** metrics and **Grafana**
  dashboards, and codified **SLO-based alerts** (error-rate and p99 latency)
  plus an on-call runbook.

## Tech stack

Python 3.12 · FastAPI · Redis · Docker · Kubernetes · Helm · Terraform ·
AWS (EKS/VPC) · ArgoCD · GitHub Actions · Prometheus · Grafana · Trivy

## License

MIT — see [LICENSE](LICENSE).
