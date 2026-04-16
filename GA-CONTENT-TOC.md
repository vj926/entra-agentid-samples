# Entra Agent ID – GA Content TOC (Final)

## Content Location

| Type | Where it lives |
|---|---|
| **Article** (concept, how-to) | learn.microsoft.com/en-us/entra/agent-id/ (reference section) |
| **Sample** (runnable code + walkthrough README) | github.com/microsoft/entra-agentid-samples |
| Articles link → GitHub samples. Sample READMEs link → learn.ms articles. |

---

## Repo Structure

```
microsoft/entra-agentid-samples/
│
├── README.md                              ← Navigation hub
├── PREREQUISITES.md                       ← Section 1.3
├── CONTRIBUTING.md | LICENSE.md | SECURITY.md | CODE_OF_CONDUCT.md
├── .devcontainer/                         ← Codespaces support
├── .github/
│   ├── ISSUE_TEMPLATE/
│   └── CODEOWNERS
│
├── scripts/
│   └── EntraAgentID-Functions.ps1         ← Shared PowerShell tooling
│
├── sidecar/                               ← SIDECAR PATTERN (container-based)
│   ├── README.md                          ← Sidecar pattern overview
│   ├── .env.example                       ← Shared Entra config
│   │
│   ├── weather-api/                       ← SHARED — token-validated Weather API
│   │   ├── app.py
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── README.md
│   │
│   ├── dev/                               ← Local dev edition (Ollama)
│   │   ├── app.py
│   │   ├── Dockerfile
│   │   ├── docker-compose.yml
│   │   ├── requirements.txt
│   │   ├── docs/
│   │   └── README.md
│   │
│   ├── aws/                               ← Amazon Bedrock edition
│   │   ├── app.py
│   │   ├── Dockerfile
│   │   ├── docker-compose.yml
│   │   ├── requirements.txt
│   │   ├── docs/
│   │   └── README.md
│   │
│   └── gcp/                               ← Google Vertex AI edition
│       ├── app.py
│       ├── Dockerfile
│       ├── docker-compose.yml
│       ├── requirements.txt
│       ├── docs/
│       └── README.md
│
├── federation/                            ← FEDERATION PATTERN (token exchange via FIC)
│   ├── README.md                          ← Federation pattern overview
│   ├── gcp/                               ← GCP Workload Identity → Entra
│   │   └── README.md
│   └── aws/                               ← (Future) AWS STS → Entra
│       └── README.md
│
├── n8n/                                   ← N8N — own integration pattern (no sidecar)
│   ├── README.md
│   └── ...                                ← TBD (Owner: Anton)
│
└── deploy/                                ← DEPLOYMENT samples
    ├── azure/                             ← Azure deployments
    │   ├── app-service/                   ← App Service + ACR
    │   │   ├── README.md
    │   │   ├── docker-compose.app-service.yml
    │   │   ├── infra/app-service.bicep
    │   │   └── deploy.sh
    │   │
    │   └── aks/                           ← AKS + Workload Identity
    │       ├── README.md
    │       ├── k8s/
    │       ├── infra/aks.bicep
    │       └── deploy.sh
    │
    ├── aws/                               ← (Future) AWS deployments
    └── gcp/                               ← (Future) GCP deployments
```

---

## Full TOC

### Section 1 — Getting Started

| # | Title |
|---|---|
| 1.1 | Entra Agent ID: Architecture and Patterns *(Anton)* |
| 1.2 | Prerequisites and Environment Setup |

### Section 2 — Sidecar

| # | Title |
|---|---|
| 2.1 | The Sidecar Design Pattern |
| 2.2 | End-to-End Token Flow: Agent to Weather API |
| 2.3 | Run the Sidecar Locally — Developer Quickstart |

### Section 3 — Third-Party Agent Platforms

**Sidecar Pattern** (`sidecar/`)

| # | Title |
|---|---|
| 3.1 | AWS: Amazon Bedrock Agent with Entra Agent ID Sidecar |
| 3.2 | GCP: Vertex AI (Gemini) Agent with Entra Agent ID Sidecar |

**Federation Pattern** (`federation/`)

| # | Title |
|---|---|
| 3.3 | GCP: Workload Identity Federation with Entra Agent ID |
| 3.4 | *(Future) AWS: Identity Federation with Entra Agent ID* |

**Low-Code** (`n8n/`)

| # | Title |
|---|---|
| 3.5 | N8N: Low-Code Agent with Entra Agent ID |

### Section 4 — Deploy

| # | Title |
|---|---|
| 4.1 | Deploy to Azure App Service |
| 4.2 | Deploy to Azure Kubernetes Service with Workload Identity |
| 4.3 | *(Future) Deploy to AWS* |
| 4.4 | *(Future) Deploy to GCP* |

---

## Cross-Linking Model

**learn.ms article → GitHub:**
```
> [!div class="nextstepaction"]
> [Run the Amazon Bedrock sample](https://github.com/microsoft/entra-agentid-samples/tree/main/sidecar/aws)
```

**GitHub sample README → learn.ms:**
```markdown
📖 **Concept article**: [The Sidecar Design Pattern](https://learn.microsoft.com/en-us/entra/agent-id/reference/...)
📖 **Official docs**: [What is Microsoft Entra Agent ID?](https://learn.microsoft.com/en-us/entra/agent-id/)
```

---

## Migration Plan

**Source:** `razi-rais/3P-Agent-ID-Demo` (read-only, code source only)
**Target:** `microsoft/entra-agentid-samples`

1. Copy `sidecar/` folder as-is (structure already matches)
2. Copy `EntraAgentID-Functions.ps1` → `scripts/`
3. Polish READMEs with final titles
4. Add `deploy/`, `.devcontainer/`, `.github/`
5. Add root `README.md` navigation hub + `PREREQUISITES.md`
6. Archive `razi-rais/3P-Agent-ID-Demo` with redirect notice

---

## Branch Strategy

### Convention: `{owner}/{feature}`

| Branch | Owner | What goes in | Merges Into |
|---|---|---|---|
| `main` | — | Production — GA-ready only | — |
| `dev` | — | Integration — all PRs target here | `main` |
| `razi/repo-setup` | Razi | README, PREREQUISITES, scripts/, .github/, .devcontainer/ | `dev` |
| `razi/sidecar` | Razi | `sidecar/` (dev, aws, gcp, weather-api) | `dev` |
| `razi/deploy` | Razi | `deploy/azure/app-service/` | `dev` |
| `yoel/deploy-aks` | Yoel | `deploy/azure/aks/` | `dev` |
| `anton/n8n` | Anton | `n8n/` | `dev` |
| `gargi/prerequisites` | Gargi | `PREREQUISITES.md` | `dev` |
| `arturo/federation` | Arturo | `federation/gcp/` | `dev` |

### Flow

```
owner/feature → PR → dev → PR → main
```

### Branch Protection: `main`

| Setting | Value |
|---|---|
| Require pull request before merging | ✅ Yes |
| Required approvals | 1 minimum |
| Dismiss stale PR reviews on new pushes | ✅ Yes |
| Require status checks to pass | ✅ Yes |
| Restrict who can merge | `rbinrais`, `yoelhor`, `antongeorgiev`, `gargi-sinha`, `arturoloop` *(confirm handles)* |
| Allow force pushes | ❌ No |
| Allow deletions | ❌ No |

---

## Summary: 13 Deliverables

| | Articles (learn.ms) | Samples (GitHub) |
|---|---|---|
| Section 1 | 1.1 | 1.2 (PREREQUISITES.md) |
| Section 2 | 2.1, 2.2 | 2.3 (sidecar/dev/) |
| Section 3 | 3.1, 3.2, 3.3, 3.5 | 3.1 (sidecar/aws/), 3.2 (sidecar/gcp/), 3.3 (federation/gcp/), 3.5 (n8n/) |
| Section 4 | 4.1, 4.2 | 4.1 (deploy/azure/app-service/), 4.2 (deploy/azure/aks/) |
| **Total** | **9 articles** | **8 samples** (+ README hub) |
