---
title: Configure third-party agents with Microsoft Entra SDKs
description: Learn how to integrate third-party AI agents with Microsoft Entra Agent ID to enable secure, credential-free identity and access management for autonomous systems.
ms.service: entra
ms.topic: overview
ms.date: 2026-04-23
author: GargiSinha
ms.author: gargi.sinha
manager: sharonsandhu
---

# Configure third-party agents with Microsoft Entra SDKs

Microsoft Entra Agent ID enables AI agents from third-party platforms to securely authenticate and authorize access to Microsoft resources and your own APIs—without ever handling credentials directly. This guide shows you how to integrate third-party agents using the Microsoft Entra SDK for Agent Identities and patterns that work with platforms like AWS Bedrock, GCP Vertex AI, and low-code automation tools.

## What is Entra Agent ID?

**Microsoft Entra Agent ID** is a purpose-built identity service for AI agents. Unlike traditional app authentication, which requires apps to manage secrets and tokens, Entra Agent ID:

- Removes the need for agents to handle credentials directly
- Provides workload identity federation for agents running outside Azure
- Supports multiple authentication patterns (client credentials, federated identity, on-behalf-of)
- Integrates seamlessly with third-party agent platforms via the Microsoft Entra SDK for Agent Identities

### Why third-party agent integration matters

Modern organizations use AI agents from multiple platforms—AWS Bedrock, GCP Vertex AI, n8n, and others. These agents often need to:

- Call Microsoft APIs (Microsoft Graph, Azure services)
- Access your internal APIs and resources
- Authenticate securely without storing secrets in code or configuration

Entra Agent ID solves this by providing a centralized, secure identity service that third-party agents can use to acquire tokens on demand.

---

## Two integration patterns

This guide covers two primary patterns for integrating third-party agents with Entra Agent ID:

### Pattern 1: Sidecar (Container-based)

The **sidecar pattern** runs the Microsoft Entra SDK as a companion container alongside your agent. The agent calls the sidecar to request tokens for API calls.

**Best for:**
- Containerized agents (Docker, Kubernetes)
- AWS Bedrock agents running in your own orchestration
- Local development with Docker Compose
- Organizations already using container infrastructure

**Supported platforms:**
- AWS Bedrock (Claude, other foundation models)
- Local LLMs (Ollama + LangChain)
- Any containerized agent

```
┌──────────────────────────────────────────┐
│         Container Orchestration          │
│  (Local Docker, Azure Container Apps)    │
├──────────────────────────────────────────┤
│  ┌────────────────┐  ┌────────────────┐  │
│  │  Agent        │  │  Sidecar       │  │
│  │  (AWS Bedrock,│  │  (Entra SDK)   │  │
│  │   Local LLM)  │  │  + Weather API │  │
│  └────────────────┘  └────────────────┘  │
│         (localhost:8000)  (localhost:7000)│
└──────────────────────────────────────────┘
         │
         │ (Request token)
         ▼
   ┌──────────────┐
   │ Entra Agent  │
   │ ID (tenant)  │
   └──────────────┘
```

### Pattern 2: Federation (Direct identity exchange)

The **federation pattern** uses Workload Identity Federation (WIF) to exchange credentials from external identity providers (like GCP Workload Identity or AWS STS) directly for Entra tokens. No sidecar needed.

**Best for:**
- GCP agents using Workload Identity
- AWS agents using STS and OIDC
- Organizations with existing federation infrastructure
- Agents that can't run containers

**Supported platforms:**
- GCP Workload Identity → Entra Agent ID
- AWS STS → Entra Agent ID 

```
┌────────────────────────────────┐
│ Third-Party Platform           │
│ (GCP, AWS)                     │
│  │                             │
│  ├─ Agent (Vertex AI,         │
│  │  Bedrock, etc.)            │
│  │                             │
│  └─ Native Workload Identity   │
│     (GCP WI, AWS STS)          │
└────────────────────────────────┘
         │
         │ (OIDC token)
         ▼
┌────────────────────────────────┐
│ Entra Agent ID                 │
│ (Federated Identity Credential)│
│ → Exchange OIDC token for      │
│   Entra token                  │
└────────────────────────────────┘
         │
         │ (Entra access token)
         ▼
┌────────────────────────────────┐
│ Your APIs / Microsoft APIs     │
│ (Microsoft Graph, custom APIs) │
└────────────────────────────────┘
```

---

## Key concepts

### Sidecar design pattern

The sidecar pattern collocates the Microsoft Entra SDK with your agent in the same container or local environment. The agent never directly handles credentials; instead, it makes requests to the sidecar to acquire tokens.

**Advantages:**
- Credential-free agent code
- Works with any containerized agent
- Easy local development (Docker Compose)
- Can be deployed to Azure Container Apps, Kubernetes, or on-premises

**Trade-off:**
- Requires managing a second container

### Workload Identity Federation (WIF)

WIF allows agents running outside Azure to exchange their native credentials (OIDC token from GCP, STS token from AWS) for Entra tokens without storing secrets.

**Advantages:**
- No sidecar required
- Leverages existing infrastructure in GCP, AWS, etc.
- Direct token exchange at the identity layer

**Prerequisites:**
- Pre-configured Federated Identity Credential in Entra
- Agent platform must support OIDC or STS

### Token flow fundamentals

All patterns follow the same core token flow:

1. **Agent requests token:** Agent (or sidecar on agent's behalf) calls Entra Agent ID with authentication credentials
2. **Entra validates identity:** Verifies the agent's identity (client credentials, federated credential, etc.)
3. **Entra returns token:** Agent receives an Entra access token
4. **Agent calls API:** Agent uses the token to authenticate to Microsoft or custom APIs
5. **API validates token:** API checks token signature and claims, grants access

---

## Common scenarios

### Scenario 1: AWS Bedrock agent calling Microsoft Graph

You have an AWS Bedrock agent (e.g., Claude) that needs to query Microsoft 365 data or manage resources via Microsoft Graph. The sidecar pattern is ideal:

1. Deploy the agent + sidecar to AWS (or your own infrastructure)
2. Configure an Agent Identity in Entra with permissions to Microsoft Graph
3. Agent calls sidecar for a token
4. Sidecar acquires token from Entra Agent ID
5. Agent uses token to call Microsoft Graph

### Scenario 2: GCP Vertex AI agent accessing custom API

You have a GCP Vertex AI agent that needs to call your internal API. Use federation:

1. Configure a Federated Identity Credential in Entra (trusts GCP Workload Identity)
2. Agent authenticates to GCP Workload Identity (native to GCP)
3. Agent exchanges GCP OIDC token for Entra token via Entra Agent ID
4. Agent uses Entra token to call your internal API

### Scenario 3: Local development with Ollama

You're developing locally with a local LLM (Ollama). Use the sidecar pattern:

1. Run agent + sidecar in Docker Compose
2. Agent calls `localhost:7000/token` to request token from sidecar
3. Sidecar acquires token from Entra Agent ID
4. Test agent behavior locally before deploying

---

## Getting started

### Prerequisites

- **Microsoft Entra tenant** with agent identity capabilities enabled
- **Azure subscription** (for some deployment options)
- **Docker** and **Docker Compose** (for sidecar pattern)
- **Credentials or federation setup** (depends on pattern)
- Before starting the implementation, ensure you have:

- **PowerShell 7.5 or later** with Microsoft.Graph PowerShell module
- **Global Administrator** only for the initial setup
- **Cloud Application Administrator** or **Application Administrator** role to grant Microsoft Graph delegated permissions for agent management operations

Before you begin:

1. Ensure you have the necessary permissions to create applications and service principals in your Entra tenant
2. If deploying to Azure, confirm your subscription and resource group
3. Familiarize yourself with your agent platform (AWS Bedrock, GCP Vertex AI, etc.)

### High-level roadmap

| Step | Pattern | Task |
|------|---------|------|
| 1 | Both | Set up Agent Identity and permissions in Entra |
| 2 | Both | Choose integration pattern (sidecar or federation) |
| 3 | Sidecar | Deploy agent + sidecar containers and test locally |
| 4 | Sidecar | Deploy to production (Azure Container Apps, Kubernetes, etc.) |
| 5 | Federation | Configure federated identity credentials in Entra |
| 6 | Federation | Deploy agent to platform (GCP, AWS, etc.) |

---

## Next steps

Choose your integration pattern and platform:

### Sidecar pattern

| Platform | What you'll learn |
|----------|-------------------|
| [AWS Bedrock agent with Entra Agent ID sidecar](./sidecar-aws-bedrock.md) | How to integrate AWS Bedrock (Claude) agents with the sidecar pattern |
| [Local LLM (Ollama) with Entra Agent ID sidecar](./sidecar-local-development.md) | How to develop locally with Ollama and Docker Compose |
| [Deploy to Azure Container Apps](./deploy-sidecar-azure-container-apps.md) | How to deploy the sidecar to production on Azure |

### Federation pattern

| Platform | What you'll learn |
|----------|-------------------|
| [GCP Workload Identity federation with Entra Agent ID](./federation-gcp-workload-identity.md) | How to use GCP Workload Identity to exchange credentials for Entra tokens |
| [AWS STS federation with Entra Agent ID (coming soon)](./federation-aws-sts.md) | How to use AWS STS for direct token exchange |

### Low-code platforms

| Platform | What you'll learn |
|----------|-------------------|
| [n8n with Entra Agent ID](./n8n-entra-agent-id.md) | How to configure n8n workflows to use Entra Agent ID |

---

## Security best practices

When integrating third-party agents, follow these security principles:

1. **Never embed credentials in agent code.** Use Entra Agent ID to acquire tokens dynamically.
2. **Use least privilege.** Grant Agent Identities only the permissions they need (via roles or scopes).
3. **Validate token audience and issuer.** Always verify tokens come from your Entra tenant.
4. **Rotate credentials regularly.** If using client secrets, rotate them on a schedule. Consider federated credentials instead.
5. **Monitor token usage.** Use Entra logs to track which agents are accessing which APIs.
6. **Keep the Entra SDK updated.** Security and compatibility updates are released regularly.

---

## Troubleshooting

### Common issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Agent can't reach sidecar | Network configuration or sidecar not running | Verify sidecar is running, check DNS/networking, confirm port binding (default: 7000) |
| Sidecar fails to acquire token | Entra authentication failed | Verify Agent Identity credentials, check Entra permissions, review tenant ID and client ID |
| Token request returns 401 | Invalid Entra credentials or federated credential not configured | Confirm credentials are correct, verify federated identity credential is set up (if using federation) |
| API rejects token | Token lacks required scope or permission | Add required API permissions to Agent Identity, request token with correct scope |

For detailed troubleshooting steps, see the individual pattern guides.

---

## Resources

- **Entra Agent ID overview:** [Microsoft Entra Agent ID documentation](https://learn.microsoft.com/en-us/entra/agent-id/)
- **Entra SDK for Agent Identities:** [SDK reference and samples](https://learn.microsoft.com/en-us/entra/agent-id/identity-platform/microsoft-entra-sdk-for-agent-identities)
- **Sample code:** [microsoft/entra-agentid-samples](https://github.com/microsoft/entra-agentid-samples)
- **Workload Identity Federation:** [Configure WIF for external workloads](https://learn.microsoft.com/en-us/entra/identity-platform/workload-identity-federation)

---

## Related content

- [Set up Entra Agent Identity via PowerShell](./entra-agent-setup.md)
- [Understanding sidecar architecture](./sidecar-architecture.md)
- [Best practices for agent security](./agent-security.md)
