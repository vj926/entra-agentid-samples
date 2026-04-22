# Entra Agent ID Samples

Runnable samples for **Microsoft Entra Agent ID** — Entra's purpose-built identity for AI agents.

## What's here

| Folder | What it is |
|---|---|
| [`sidecar/`](sidecar/) | Sidecar-pattern samples (agent + Entra SDK auth sidecar) with local-LLM and AWS Bedrock editions |
| [`scripts/`](scripts/) | PowerShell + bash tooling to provision Blueprint, Agent Identity, and Client SPA in your tenant |
| [`deploy/`](deploy/) | Deploy the samples to Azure (Container Apps today; App Service and AKS coming) |

## Quick start

1. Provision Entra objects: [`scripts/README.md`](scripts/README.md)
2. Run a local demo: [`sidecar/dev/README.md`](sidecar/dev/README.md)

## Learn more

- [Microsoft Entra Agent ID overview](https://learn.microsoft.com/en-us/entra/agent-id/)
- [Microsoft Entra SDK for Agent Identities](https://learn.microsoft.com/en-us/entra/agent-id/identity-platform/microsoft-entra-sdk-for-agent-identities)

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md).

## License and code of conduct

- [`LICENSE`](LICENSE)
- [`SECURITY.md`](SECURITY.md)
- This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
