# Entra Agent ID Samples

Runnable samples for **Microsoft Entra Agent ID** — Entra's purpose-built identity for AI agents.

## What's here

| Folder | What it is |
|---|---|
| [`sidecar/`](sidecar/) | Sidecar-pattern samples (agent + Entra SDK auth sidecar) with local-LLM and AWS Bedrock editions |
| [`scripts/`](scripts/) | PowerShell + bash tooling to provision Blueprint, Agent Identity, and Client SPA in your tenant |
| [`deploy/`](deploy/) | Deploy the samples to Azure (Container Apps today; App Service and AKS coming) |
| [`n8n/`](n8n/) | Full end-to-end integrated deployment of n8n platform on Azure Container Apps.|

## Quick start

1. Provision Entra objects: [`scripts/README.md`](scripts/README.md)
2. Run a local demo:
   - Local-LLM (Ollama, offline): [`sidecar/dev/README.md`](sidecar/dev/README.md)
   - AWS Bedrock (Claude): [`sidecar/aws/README.md`](sidecar/aws/README.md)
3. Deploy to Azure Container Apps: [`deploy/azure/container-apps/dev/README.md`](deploy/azure/container-apps/dev/README.md) (local-LLM) or [`deploy/azure/container-apps/aws/README.md`](deploy/azure/container-apps/aws/README.md) (AWS Bedrock)

> [!TIP]
> **Deploying to Azure is much faster with an AI assistant.** Each Azure deployment tutorial ships with a paired skill under [`.claude/skills/`](.claude/skills/) that works with **Claude Code** and **GitHub Copilot Chat**. The assistant walks through SKU choices, federation wiring, and post-deploy manual steps — typically cutting a multi-hour manual deploy down to minutes.

## Learn more

- [Microsoft Entra Agent ID overview](https://learn.microsoft.com/en-us/entra/agent-id/)
- [Microsoft Entra SDK for Agent Identities](https://learn.microsoft.com/en-us/entra/agent-id/identity-platform/microsoft-entra-sdk-for-agent-identities)

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md).

## License and code of conduct

Copyright (c) Microsoft Corporation. All rights reserved.

Licensed under the MIT License - see the [`LICENSE`](LICENSE) file for details. This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).

- [`SECURITY.md`](SECURITY.md)
- 
