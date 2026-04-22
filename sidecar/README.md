# The Sidecar Design Pattern

How the **Microsoft Entra Agent ID sidecar** lets an AI agent call downstream APIs with a secure, per-agent identity — without the agent code ever seeing a secret.

For runnable samples, see:
- [`dev/`](dev/README.md) — local-LLM (Ollama) edition
- [`aws/`](aws/README.md) — AWS Bedrock (Claude) edition
- [`weather-api/`](weather-api/README.md) — shared downstream API used by both

For the PowerShell bootstrap that creates the Entra objects used by every sample, see [`../scripts/README.md`](../scripts/README.md).

## The problem

Two common approaches to agent authentication both fall short:

1. **Hard-coded secrets in agent code.** Every agent image holds a copy of your app's `client_secret`. Any compromise, any log leak, any forgotten `.env` committed to Git is a full tenant breach.
2. **Delegated user tokens for everything.** The agent is reduced to acting only when a human is present, and you lose individual auditability — every call looks like the same service principal.

Entra Agent ID gives each agent its own identity. The sidecar pattern makes that identity easy to use.

## What the sidecar does

The **[Microsoft Entra SDK auth sidecar](https://mcr.microsoft.com/en-us/product/entra-sdk/auth-sidecar/about)** (`mcr.microsoft.com/entra-sdk/auth-sidecar`) runs as a second container next to your agent. It exposes a small HTTP API on the pod-local network and handles:

- Client-credentials exchange with `login.microsoftonline.com`
- Blueprint → Agent Identity token exchange (T1 → T2)
- On-Behalf-Of (OBO) flows for user-context calls
- Token caching, refresh, and expiry
- Credential source abstraction — `ClientSecret` for dev, `SignedAssertionFromManagedIdentity` for production, same API

Your agent asks the sidecar *"give me an authorization header for this API"* and gets back `Bearer eyJ…`. Credentials never live in agent memory.

| Agent (your code) | Sidecar (Microsoft Entra SDK) |
|---|---|
| Decide when to call the API | Acquire and cache the right token |
| Build the HTTP request | Perform client-credentials and OBO exchange |
| Pass through user token for OBO | Validate and forward user assertion |
| Handle business logic | Talk to `login.microsoftonline.com` |

The security boundary is explicit: the sidecar has no host port. Only services inside the same network (your agent, not your browser, not random processes on the host) can request tokens.

## The identity objects

| Object | Role | Where it lives |
|---|---|---|
| **Blueprint application** | Factory / template that issues Agent Identities. Holds the client credential (secret or federated). | Your Entra tenant |
| **Agent Identity** | The individual AI agent. Has its own app ID, its own permission grants (e.g. `User.Read.All`), its own audit trail. | Your Entra tenant |
| **Client SPA** (OBO only) | Web UI that signs the user in and exchanges the user's token into an Agent token on their behalf. | Your Entra tenant |
| **Sidecar container** | Runs client-credentials and OBO flows. Knows the Blueprint credential. | Next to your agent |
| **Agent container** | Your application code. Asks the sidecar for headers. | Your pod / compose / App Service |

Provisioning is covered in [`../scripts/README.md`](../scripts/README.md) — the `Start-EntraAgentIDWorkflow` PowerShell cmdlet creates all three Entra objects in one shot.

## Two token flows

### Autonomous (app-only) — **TR**

The agent runs on its own schedule (cron, queue trigger, MCP request from another service). There is no user in the loop.

```
    ┌────────────┐   GET /AuthorizationHeader/graph           ┌──────────────────┐
    │   Agent    ├────────────────────────────────────────────▶│ Sidecar          │
    │ (your app) │   ?AgentIdentity=<agent-app-id>             │                  │
    └────────────┘                                             │   T1: Blueprint  │
          ▲                                                    │       token      │
          │  Authorization: Bearer <T2>                        │         │        │
          │                                                    │         ▼        │
          └────────────────────────────────────────────────────┤   T2: Agent      │
                                                               │       token      │
    ┌────────────┐                                             └──────────────────┘
    │ Downstream │  ← Agent calls with T2                               │
    │    API     │                                                     ▼
    └────────────┘                                        Microsoft Entra ID
```

### On-Behalf-Of (OBO) — **TF1**

A signed-in user asks the agent to do something on their behalf. The downstream API must see the user's identity, not just the agent's.

```
    User ──sign-in──▶ Client SPA ──(Tc: user token)──▶ Agent ──▶ Sidecar
                                                                    │
                                                                    │ OBO exchange:
                                                                    │   Tc + Blueprint
                                                                    ▼
                                                         Microsoft Entra ID
                                                                    │
                                                                    ▼
                                                               TF1 = Agent-on-behalf-of-user
                                                                    │
                                                                    ▼
                                                         Agent ──▶ Downstream API
                                                                    (sees both user and agent claims)
```

Both flows are demonstrated end-to-end in [`dev/`](dev/README.md) and [`aws/`](aws/README.md).

## How the samples fit together

```
┌──────────────────────────────────────────────────────────────┐
│                  sidecar/ samples                            │
│                                                              │
│  dev/    ─┐                                                  │
│  aws/    ─┼──▶  weather-api/  (shared, validates tokens)    │
│  (gcp/)  ─┘                                                  │
│                                                              │
│  Each agent sample includes its own auth sidecar container.  │
│  All three call the same weather-api for an apples-to-apples │
│  cross-cloud demo.                                           │
└──────────────────────────────────────────────────────────────┘
```

- **[`dev/`](dev/README.md)** — LangChain + Ollama (local), runs entirely offline via `docker-compose`. Fastest path to a working demo.
- **[`aws/`](aws/README.md)** — LangChain + AWS Bedrock (Claude) with Azure→AWS OIDC federation via the `azure-token-refresher` companion.
- **[`weather-api/`](weather-api/README.md)** — minimal token-validated mock API. RS256 signature check via JWKS, issuer and audience validation, agent-identity claim verification.

For deploying any of the above to Azure, see [`../deploy/azure/container-apps/`](../deploy/azure/container-apps/) — zero stored secrets, federated credentials only.

## What you'll learn by running the samples

- The difference between a Blueprint and an Agent Identity, and why agents need their own identity.
- How the sidecar exposes `/AuthorizationHeader` (get token) and `/DownstreamApi` (token + proxied call) endpoints.
- How to hand a user's token (`Tc`) to the agent and have the sidecar mint an OBO Agent token (`TF1`).
- How the downstream API validates agent tokens cryptographically — signature, issuer, `xms_par_app_azp`, audience.
- How to swap from `ClientSecret` (dev) to `SignedAssertionFromManagedIdentity` (Azure production) without changing a line of agent code.

## Next steps

| To… | Go to |
|---|---|
| Set up Blueprint + Agent Identity in your Entra tenant | [`../scripts/README.md`](../scripts/README.md) |
| Run a local-LLM demo in five minutes | [`dev/README.md`](dev/README.md) |
| Run the same demo against AWS Bedrock | [`aws/README.md`](aws/README.md) |
| Deploy to Azure Container Apps (no stored secrets) | [`../deploy/azure/container-apps/`](../deploy/azure/container-apps/) |

## Further reading

- [Microsoft Entra SDK for Agent Identities](https://learn.microsoft.com/en-us/entra/agent-id/identity-platform/microsoft-entra-sdk-for-agent-identities)
- [SDK endpoints reference](https://learn.microsoft.com/en-us/entra/msidweb/agent-id-sdk/endpoints)
- [Call a downstream API](https://learn.microsoft.com/en-us/entra/msidweb/agent-id-sdk/scenarios/call-downstream-api)
- [Python integration examples](https://learn.microsoft.com/en-us/entra/msidweb/agent-id-sdk/scenarios/using-from-python)

