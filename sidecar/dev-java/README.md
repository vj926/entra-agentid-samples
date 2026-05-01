# Local Dev Edition (Java / Spring Boot + LangChain4j)

Java port of [`sidecar/dev/`](../dev/) — same architecture, same docker-compose topology, same UI. Built with Spring Boot 3 and [LangChain4j](https://github.com/langchain4j/langchain4j) for Ollama tool-calling.

> The original Python sample (`sidecar/dev/`) and this Java edition are **interchangeable**: both expose the same REST contract (`/api/chat`, `/api/status`, `/api/config`, `/health`) and use the same auth sidecar, weather API, and Ollama image.

## Architecture

```
Browser ──HTTP──▶  llm-agent (Spring Boot, port 3004)
                      │
                      ├──▶ sidecar  (Microsoft Entra SDK auth-sidecar, internal)
                      │       └──▶ Microsoft Entra ID
                      │
                      ├──▶ weather-api (token-validated downstream)
                      │
                      └──▶ ollama (qwen2.5:1.5b by default)
```

Token flows demonstrated:
- **Autonomous (TR)** — app-only / client credentials.
- **OBO (TR)** — exchanges the user's MSAL token (Tc) → Blueprint app-only (T1) → Interactive Agent (TR).

## Prerequisites

- Docker + Docker Compose
- An Entra tenant with the **Blueprint app**, **Agent app**, and (optional) **Client SPA** registered. See [`scripts/`](../../scripts/) and the [`entra-agent-id-setup`](../../.claude/skills/entra-agent-id-setup) skill.

## Quick start

```bash
cd sidecar/dev-java
cp .env.example .env
# fill in TENANT_ID / BLUEPRINT_APP_ID / AGENT_APP_ID / CLIENT_SPA_APP_ID / BLUEPRINT_CLIENT_SECRET

docker compose --env-file .env up --build

# pull the model once (in another shell):
docker exec -it ollama-dev-java ollama pull qwen2.5:1.5b
```

Open <http://localhost:3004>.

> Port `3004` is used so this can run alongside the Python sample (which uses `3003`). Adjust in `docker-compose.yml` if needed.

## Local development (without Docker)

```bash
mvn -q -DskipTests package
java -jar target/sidecar-dev-java-1.0.0.jar
```

Set the same env vars (`SIDECAR_URL`, `WEATHER_API_URL`, `AGENT_APP_ID`, `BLUEPRINT_APP_ID`, `TENANT_ID`, `CLIENT_SPA_APP_ID`, `OLLAMA_URL`, `OLLAMA_MODEL`) — defaults assume the docker-compose network names.

## Project layout

```
src/main/java/com/microsoft/entra/agentid/sidecar/dev/
├── Application.java
├── config/         AppProperties (env binding), WebConfig (CORS, RestClient)
├── controller/     ChatController (/api/chat, /api/status, /api/config, /health), HomeController
├── model/          ChatRequest, ChatResponse, DebugEntry
└── service/
    ├── DebugLogger        @RequestScope per-request trace for the UI
    ├── JwtUtil            Base64 JWT payload decode (display only)
    ├── OllamaHealth       /api/tags poll
    ├── QueryParser        Fallback regex city extractor
    ├── SidecarClient      Calls the Entra SDK auth sidecar (TR + OBO + T1)
    ├── WeatherClient      Calls weather-api with the bearer token
    ├── WeatherTool        @Tool exposed to the LLM
    └── WeatherAgent       AiServices wrapper around Ollama + WeatherTool
```

## Mapping to the Python edition

| Python (`sidecar/dev/app.py`)     | Java (`sidecar/dev-java/...`)               |
|-----------------------------------|---------------------------------------------|
| `Flask` + `flask_cors`            | Spring Boot Web + `WebConfig`               |
| `requests`                        | Spring `RestClient`                         |
| `langchain` + `langchain-ollama`  | LangChain4j (`langchain4j-ollama`)          |
| `@tool`                           | `@dev.langchain4j.agent.tool.Tool`          |
| `create_agent(llm, tools)`        | `AiServices.builder(...).tools(...).build()`|
| Module-global `debug_logs`        | `@RequestScope DebugLogger`                 |
| Module-global `_current_user_token` | `@RequestScope WeatherTool#userToken`     |
| `templates/index.html` + Jinja    | `src/main/resources/static/index.html`      |

## What this demo showcases

**Microsoft Entra Agent Identity** — a real, distinct identity for an AI agent (separate from the human user and the host app). The demo proves two ways an agent can obtain a token to call a downstream API (`weather-api`):

| Flow | Principal | Token | When |
|---|---|---|---|
| **Autonomous** | Just the agent (app-only / client-credentials) | **TR** | "Use LLM" off, or no user signed in |
| **OBO** (On-Behalf-Of) | Agent acting *for* a signed-in user | **Tc → T1 → TR** | User signed in via MSAL |

The agent process **never holds long-lived secrets**. It asks the **auth sidecar** (a Microsoft-shipped container) for a fresh token on every call. The sidecar holds the Blueprint app's credential and brokers everything — in production this becomes a Managed Identity signed assertion (zero secrets).

### Step 1 — procure the token (`SidecarClient.java`)

**Autonomous** ([`getAgentToken`](src/main/java/com/microsoft/entra/agentid/sidecar/dev/service/SidecarClient.java)):

```java
String url = props.sidecarUrl()
    + "/AuthorizationHeaderUnauthenticated/graph-app?AgentIdentity="
    + props.agentAppId();                    // who am I asking a token FOR

Map<String, Object> body = restClient.get().uri(url)
    .header("Host", "localhost")             // sidecar quirk — see Notes
    .retrieve().body(Map.class);

String authHeader = (String) body.get("authorizationHeader");  // "Bearer eyJ..."
```

One GET → the sidecar performs client-credentials with the Blueprint app secret, mints a **TR** (Agent token) for `agentAppId`, and hands back `"Bearer eyJ…"`. No MSAL, no cert handling, no token cache in our code.

**OBO** ([`getAgentTokenObo`](src/main/java/com/microsoft/entra/agentid/sidecar/dev/service/SidecarClient.java)) — almost identical, two differences:

```java
String url = props.sidecarUrl() + "/AuthorizationHeader/graph?AgentIdentity=...";
//                            ^^^ authenticated endpoint (no "Unauthenticated")
req.header("Authorization", "Bearer " + userTc);   // pass the USER's token
```

The sidecar takes the user's **Tc**, exchanges **Tc → T1** (Blueprint app-only) **→ TR** (agent acting for user). The resulting TR carries `xms_par_app_azp` (the user) so the API can see *who* the agent is acting for.

### Step 2 — call the API (`WeatherClient.java`)

```java
Map<String, Object> body = restClient.get()
    .uri(props.weatherApiUrl() + "/weather?city=" + city)
    .header("Authorization", token)          // the TR we just got
    .retrieve()
    .body(Map.class);
```

That's it — **one HTTP GET with one header**. The weather API (separate container) validates the JWT signature against Entra's JWKS, checks `iss` / `exp` / `aud`, and inspects `xms_frd=FederatedAgent` to confirm it's an Agent Identity token.

### Why this matters

- **Zero secret management in the agent process** — the Java code never sees the Blueprint client secret.
- **First-class agent identity in Entra** — the API authorizes agents differently from users or plain apps via `xms_frd`.
- **OBO preserves user context** — the API can apply the user's permissions even when an agent makes the call.

The whole "auth complexity" reduces to **one GET to the sidecar, one GET to the API**.

## Notes

- The HTML UI is reused **verbatim** from the Python sample. It has no server-side templating, so it ships as a Spring static resource.
- Tool-calling on small Ollama models (e.g. `qwen2.5:1.5b`) can be flaky — the controller falls back to the no-LLM "Direct" path when Ollama isn't ready.
- CORS is wide-open (`*`) for the demo. Lock down for production.
- `RestClient` is wired with **Apache HttpComponents 5** (not the JDK `HttpClient`). The Entra SDK auth-sidecar requires `Host: localhost` regardless of the destination host, and the JDK client silently strips restricted headers like `Host`.
- Frontend ↔ backend JSON uses **snake_case** (`use_langchain`, `token_flow`, `user_token`, `agent_type`). Configured globally via `spring.jackson.property-naming-strategy: SNAKE_CASE`.
