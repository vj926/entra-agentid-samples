# CLAUDE.md

Guidance for Claude Code (and other agent tools) working in this repository.

## What this repository is

Microsoft Entra Agent ID sample agents that demonstrate the **sidecar identity pattern**: the Microsoft Entra SDK for Agent ID runs as a companion container and handles token acquisition (client credentials, federated identity credential, on-behalf-of) so the agent code never touches secrets.

Variants:
- `sidecar/dev/` — local-LLM (Ollama + LangChain)
- `sidecar/aws/` — AWS Bedrock (Claude + Azure→AWS OIDC)
- `sidecar/weather-api/` — shared downstream API
- `deploy/azure/container-apps/` — Azure Container Apps deployment tutorials
- `scripts/` — PowerShell bootstrap for Blueprint + Agent Identity + Client SPA

## Skills

Skills live under `.claude/skills/<name>/SKILL.md`. When the user's task matches a skill's description, **read that `SKILL.md` in full before acting**:

- `entra-agent-id-setup` — Blueprint + Agent Identity + Client SPA setup in Microsoft Entra ID
- `deploy-agent-aca-dev` — deploy the local-LLM sample to Azure Container Apps
- `deploy-agent-aca-aws` — deploy the AWS Bedrock sample to Azure Container Apps

## Operational rules

- Always confirm Azure account, tenant ID, and subscription ID with the user before any deploy / provision / cleanup command.
- Never commit `.env`, `deploy-vars.sh`, tenant GUIDs, app/client GUIDs, or secrets.
- Prefer editing existing files over creating new ones.
- For pushes, PRs, merges, or force-pushes: always confirm with the user first.

## Further reading

See [`README.md`](README.md) for the high-level repository tour and [`.github/copilot-instructions.md`](.github/copilot-instructions.md) for the GitHub Copilot equivalent of this file.
