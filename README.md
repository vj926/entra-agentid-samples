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

This project welcomes contributions and suggestions. Most contributions require you to agree to a Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us the rights to use your contribution. For details, visit https://cla.opensource.microsoft.com.

When you submit a pull request, a CLA bot will automatically determine whether you need to provide a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions provided by the bot. You will only need to do this once across all repos using our CLA.


## Security
Microsoft takes the security of our software products and services seriously, which includes all source code repositories in our GitHub organizations.
Please do not report security vulnerabilities through public GitHub issues.
For security reporting information, locations, contact information, and policies, please review the latest guidance for Microsoft repositories at https://aka.ms/SECURITY.md.

## License and code of conduct

Copyright (c) Microsoft Corporation. All rights reserved. 
Licensed under the MIT License - see the [`LICENSE`](LICENSE) file for details.
This project has adopted the Microsoft Open Source Code of Conduct. For more information see the Code of Conduct FAQ or contact opencode@microsoft.com with any additional questions or comments.


