# Entra Agent ID Samples

Runnable samples and walkthroughs for **Microsoft Entra Agent ID** — Entra's purpose-built identity for AI agents.

This repository shows you how to:

- Provision a **Blueprint** application, an **Agent Identity**, and a **Client SPA** in your Entra tenant.
- Run the **Microsoft Entra SDK auth sidecar** next to your agent so the agent code never sees a secret.
- Mint **autonomous (app-only)** and **on-behalf-of** tokens for the agent.
- Call a downstream API (the included `weather-api`) with a token that validates cleanly (signature, issuer, agent-identity claims).
- Deploy the whole thing to **Azure Container Apps** with *zero stored secrets* — federated credentials only.

## Start here

| If you're… | Go to |
|---|---|
| New to Entra Agent ID and want the concepts | [`sidecar/README.md`](sidecar/README.md) — the sidecar design pattern |
| Setting up your Entra tenant for the first time | [`scripts/README.md`](scripts/README.md) — PowerShell bootstrap walkthrough |
| Looking for the fastest runnable demo | [`sidecar/dev/README.md`](sidecar/dev/README.md) — local agent with Ollama |
| Running against a cloud LLM | [`sidecar/aws/README.md`](sidecar/aws/README.md) — AWS Bedrock (Claude) |
| Deploying to Azure | [`deploy/azure/container-apps/`](deploy/azure/container-apps/) |

## Table of contents

Content is laid out per [`GA-CONTENT-TOC.md`](GA-CONTENT-TOC.md).

### 1 · Getting started
- **1.1** Entra Agent ID architecture and patterns *(coming soon — owner @astaykov)*
- **1.2** [`PREREQUISITES.md`](PREREQUISITES.md) — environment setup *(coming soon — owner @Gargi-Sinha)*

### 2 · Sidecar pattern
- **2.1** [The Sidecar Design Pattern](sidecar/README.md)
- **2.2** End-to-end token flow: agent → weather API *(covered inline in §2.3 sample)*
- **2.3** [Run the sidecar locally (developer quickstart)](sidecar/dev/README.md)

### 3 · Third-party agent platforms

Sidecar pattern (container-based):
- **3.1** [AWS: Amazon Bedrock agent with Entra Agent ID sidecar](sidecar/aws/README.md)
- **3.2** GCP: Vertex AI (Gemini) agent with Entra Agent ID sidecar *(coming soon)*

Federation pattern (token exchange via FIC):
- **3.3** GCP: Workload Identity Federation with Entra Agent ID *(coming soon — owner @ArLucaID)*

Low-code:
- **3.5** N8N: low-code agent with Entra Agent ID *(coming soon — owner @astaykov)*

### 4 · Deploy
- **4.1** Deploy to Azure App Service *(coming soon)*
- **4.2** Deploy to Azure Kubernetes Service with Workload Identity *(coming soon — owner @yoelhor)*
- **4.3** [Deploy to Azure Container Apps](deploy/azure/container-apps/) — AWS Bedrock and local-LLM variants

## Repository layout

```
├── scripts/                   Shared PowerShell + bash bootstrap tooling
├── sidecar/                   Sidecar pattern samples
│   ├── weather-api/           Shared token-validated downstream API
│   ├── dev/                   Local-LLM (Ollama) edition
│   └── aws/                   AWS Bedrock edition
├── deploy/                    Deployment samples
│   └── azure/container-apps/  Azure Container Apps tutorials
└── .github/skills/            AI-led workflow skills (optional tooling)
```

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) *(coming soon)*. Content owners are listed in [`GA-CONTENT-TOC.md`](GA-CONTENT-TOC.md).

Branching model: `owner/feature → PR → dev → PR → main`.

## License and code of conduct

- [`LICENSE`](LICENSE)
- [`SECURITY.md`](SECURITY.md)
- Code of Conduct: this project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
