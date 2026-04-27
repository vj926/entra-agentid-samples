# Entra Agent ID – GA Content TOC (Final)

## Content Location

| Type | Where it lives |
|---|---|
| **Sample** (runnable code + walkthrough README) | github.com/microsoft/entra-agentid-samples |

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
│   ├── README.md                          ← PowerShell bootstrap walkthrough (ties to §1.2)
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
    │   ├── container-apps/                ← Azure Container Apps (zero-secret, federated)
    │   │   ├── aws/README.md              ← AWS Bedrock agent + sidecar on ACA
    │   │   └── dev/README.md              ← Local-LLM (Ollama) agent + sidecar on ACA
    │   │

```

---

## Full TOC

### Section 1 — Getting Started

| # | Title | Owner |Status|
|---|---|---|---|
| 1.1 | Introduction/Pre-reqs/Setup | Gargi ([@Gargi-Sinha](https://github.com/Gargi-Sinha)) | https://github.com/microsoft/entra-agentid-samples/blob/dev/Configure-third-party-agents-with-Microsoft-Entra-SDKs.md (initial draft) |

### Section 2 — Sidecar

| # | Title | Owner |Status|
|---|---|---|---|
| 2.1 | The Sidecar Design Pattern | Razi ([@razi-rais](https://github.com/rbinrais)) |https://github.com/microsoft/entra-agentid-samples/blob/dev/sidecar/README.md (Done open for review)|
| 2.2 | End-to-End Token Flow: Agent to Weather API | Razi ([@razi-rais](https://github.com/rbinrais)) | https://github.com/microsoft/entra-agentid-samples/blob/dev/sidecar/weather-api/README.md (Done open for review)|
| 2.3 | Run the Sidecar Locally — Developer Quickstart | Razi ([@razi-rais](https://github.com/rbinrais)) |https://github.com/microsoft/entra-agentid-samples/blob/dev/sidecar/dev/README.md(Done open for review)|

### Section 3 — Third-Party Agent Platforms

**Sidecar Pattern** (`sidecar/`)

| # | Title | Owner |Status|
|---|---|---|---|
| 3.1 | AWS: Amazon Bedrock Agent with Entra Agent ID Sidecar | Razi ([@razi-rais](https://github.com/rbinrais)) |https://github.com/microsoft/entra-agentid-samples/blob/dev/sidecar/aws/README.md (Done open for review)|


**Federation Pattern** (`federation/`)

| # | Title | Owner |Status|
|---|---|---|---|
| 3.3 | GCP: Workload Identity Federation with Entra Agent ID | Arturo ([@ArLucaID](https://github.com/ArLucaID)) |(In-progress)|
| 3.4 | *(Future) AWS: Identity Federation with Entra Agent ID* | Arturo ([@ArLucaID](https://github.com/ArLucaID)) |(In-progress)|

**Low-Code** (`n8n/`)

| # | Title | Owner |Status|
|---|---|---|---|
| 3.5 | N8N: Low-Code Agent with Entra Agent ID | Anton ([@astaykov](https://github.com/astaykov)) | https://github.com/microsoft/entra-agentid-samples/blob/dev/README.md (Done ready for review) |

### Section 4 — Deploy

| # | Title | Owner |Status|
|---|---|---|---|
| 4.1 | Deploy to Azure App Service | Vijaya ([@Vijaya] / Razi(rbinrais)  |(In-progress)|
| 4.2 | Deploy to Azure Container Apps | Razi ([@razi-rais](https://github.com/rbinrais)) |https://github.com/microsoft/entra-agentid-samples/blob/dev/deploy/azure/container-apps/dev/README.md (Done open for review)|

**Reminder** to update the AI skills and make sure its reflecting in the repo. 

---

**PHASE 2 
**
Deploy - 
| 4.2 | Deploy to Azure Kubernetes Service with Workload Identity | ([@yoelhor](https://github.com/yoelhor)) | Pushed because of no activity 
| 3.2 | GCP: Vertex AI (Gemini) Agent with Entra Agent ID Sidecar | Razi ([@razi-rais](https://github.com/rbinrais)) |
| 1.1 | Entra Agent ID: Architecture and Patterns | Anton ([@astaykov](https://github.com/astaykov)) |Anton mentioned this is done and in the GA PR repo already. 


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
| `razi/repo-setup` | @razi-rais | README, PREREQUISITES, scripts/, .github/, .devcontainer/ | `dev` |
| `razi/sidecar` | @razi-rais | `sidecar/` (dev, aws, gcp, weather-api) | `dev` |
| `razi/deploy` | @razi-rais | `deploy/azure/app-service/` | `dev` |
| `yoel/deploy-aks` | @yoelhor | `deploy/azure/aks/` | `dev` |
| `anton/n8n` | @astaykov | `n8n/` | `dev` |
| `gargi/prerequisites` | @Gargi-Sinha | `PREREQUISITES.md` | `dev` |
| `arturo/federation` | @ArLucaID | `federation/gcp/` | `dev` |

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
| Restrict who can merge | @rbinrais, @yoelhor, @astaykov, @Gargi-Sinha, @ArLucaID |
| Allow force pushes | ❌ No |
| Allow deletions | ❌ No |

---

## Summary

| Section | Samples (GitHub) |
|---|---|
| Section 1 | 1.1, 1.2 (PREREQUISITES.md) |
| Section 2 | 2.1, 2.2, 2.3 (sidecar/dev/) |
| Section 3 | 3.1 (sidecar/aws/), 3.2 (sidecar/gcp/), 3.3 (federation/gcp/), 3.4, 3.5 (n8n/) |
| Section 4 | 4.1 (deploy/azure/app-service/), 4.2 (deploy/azure/aks/) |
