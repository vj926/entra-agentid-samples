package com.microsoft.entra.agentid.sidecar.dev.controller;

import com.microsoft.entra.agentid.sidecar.dev.config.AppProperties;
import com.microsoft.entra.agentid.sidecar.dev.model.ChatRequest;
import com.microsoft.entra.agentid.sidecar.dev.model.ChatResponse;
import com.microsoft.entra.agentid.sidecar.dev.model.DebugEntry;
import com.microsoft.entra.agentid.sidecar.dev.service.*;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@RestController
public class ChatController {

    private final AppProperties props;
    private final SidecarClient sidecar;
    private final WeatherClient weather;
    private final WeatherTool weatherTool;
    private final WeatherAgent weatherAgent;
    private final QueryParser queryParser;
    private final OllamaHealth ollama;
    private final DebugLogger debug;
    private final JwtUtil jwt;

    public ChatController(AppProperties props, SidecarClient sidecar, WeatherClient weather,
                          WeatherTool weatherTool, WeatherAgent weatherAgent, QueryParser queryParser,
                          OllamaHealth ollama, DebugLogger debug, JwtUtil jwt) {
        this.props = props;
        this.sidecar = sidecar;
        this.weather = weather;
        this.weatherTool = weatherTool;
        this.weatherAgent = weatherAgent;
        this.queryParser = queryParser;
        this.ollama = ollama;
        this.debug = debug;
        this.jwt = jwt;
    }

    @PostMapping("/api/chat")
    public ResponseEntity<?> chat(@RequestBody ChatRequest req) {
        if (req == null || req.message() == null || req.message().isBlank()) {
            return ResponseEntity.badRequest().body(Map.of("error", "No message provided"));
        }
        if (req.obo() && (req.userToken() == null || req.userToken().isBlank())) {
            return ResponseEntity.badRequest()
                    .body(Map.of("error", "OBO flow requires a user token. Please sign in first."));
        }

        String userToken = req.obo() ? req.userToken() : null;
        weatherTool.setUserToken(userToken);

        if (userToken != null) {
            Map<String, Object> tcClaims = jwt.decodePayload(userToken);
            if (tcClaims != null) {
                debug.log("OBO 0.A USER TOKEN (Tc)",
                        "Decoded user access token from MSAL sign-in",
                        Map.of("_jwt_token", Map.of(
                                "type", "tc",
                                "title", "🔑 Tc — User Token (from MSAL sign-in)",
                                "css", "tc",
                                "hl", "highlight",
                                "claims", tcClaims)));
            }
        }

        String tokenFlow = req.obo() ? "obo" : "autonomous";
        ChatResponse result;
        if (req.useLangchainOrDefault() && ollama.modelReady()) {
            result = weatherAgent.run(req.message(), weatherTool);
        } else {
            result = runDirect(req.message(), userToken);
        }

        // Maybe insert T1 (Blueprint) entry before the OBO 2.D entry
        if (req.obo()) {
            Map<String, Object> t1Claims = sidecar.getT1TokenClaims();
            if (t1Claims != null) {
                DebugEntry t1Entry = new DebugEntry(
                        "OBO 2.C T1 (Blueprint)",
                        "Blueprint app-only token used as client_assertion in OBO exchange",
                        Map.of("_jwt_token", Map.of(
                                "type", "t1",
                                "title", "📜 T1 — Blueprint Token (App-Only / Client Credentials)",
                                "css", "t1",
                                "hl", "highlight-purple",
                                "claims", t1Claims)));
                debug.insertBefore("OBO 2.D", t1Entry);
            }
        }
        debug.append(new DebugEntry("DOCS", "_doc_links", null));

        // Rebuild response from latest debug state
        ChatResponse finalResp = new ChatResponse(
                result.response(),
                debug.snapshot(),
                result.success(),
                result.agentType(),
                tokenFlow);
        return ResponseEntity.ok(finalResp);
    }

    private ChatResponse runDirect(String userMessage, String userToken) {
        boolean isObo = userToken != null;
        String flow = isObo ? "OBO" : "Autonomous";
        debug.log("0.A START", "Processing query (Direct + " + flow + "): " + userMessage);
        if (isObo) {
            debug.log("0.B OBO MODE",
                    "User token provided — will use authenticated sidecar endpoint",
                    Map.of("endpoint", "/AuthorizationHeader/graph (requires Bearer token)"));
        }
        String city = queryParser.extractCity(userMessage);
        debug.log("1.A DIRECT CALL",
                "Calling weather function directly for: " + city + " (flow: " + flow + ")");

        String token = isObo ? sidecar.getAgentTokenObo(userToken) : sidecar.getAgentToken();
        String body;
        if (token == null) {
            body = "Error: Could not authenticate with Agent Identity (" + flow + ").";
        } else {
            var data = weather.call(city, token, "TR", isObo);
            body = data == null
                    ? "Error: Could not get weather data for " + city + "."
                    : WeatherTool.formatWeather(city, data, flow);
        }

        String flowBadge = isObo ? "🔄 OBO" : "⚡ Autonomous";
        String response = "Here's what I found:\n\n" + body
                + "\n\n✅ *Securely retrieved using Agent Identity (" + flowBadge + ")*";
        debug.log("5. COMPLETE", "Query processed (Direct + " + flow + ")");
        return new ChatResponse(response, debug.snapshot(), true, "direct",
                isObo ? "obo" : "autonomous");
    }

    @GetMapping("/api/status")
    public Map<String, Object> status() {
        boolean ready = ollama.modelReady();
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("ollama_available", ready);
        out.put("ollama_url", props.ollamaUrl());
        out.put("ollama_model", props.ollamaModel());
        out.put("sidecar_url", props.sidecarUrl());
        out.put("agent_app_id",
                (props.agentAppId() == null || props.agentAppId().isBlank())
                        ? "not set"
                        : props.agentAppId().substring(0, Math.min(8, props.agentAppId().length())) + "...");
        return out;
    }

    @GetMapping("/api/config")
    public Map<String, Object> config(HttpServletRequest req) {
        String scheme = headerOr(req, "X-Forwarded-Proto", req.getScheme());
        String host = headerOr(req, "X-Forwarded-Host", req.getHeader("Host"));
        if (host == null) host = req.getServerName() + ":" + req.getServerPort();
        String redirectUri = scheme + "://" + host;

        Map<String, Object> cfg = new LinkedHashMap<>();
        cfg.put("tenant_id", props.tenantId());
        cfg.put("blueprint_app_id", props.blueprintAppId());
        cfg.put("client_spa_app_id", props.clientSpaAppId());
        cfg.put("agent_app_id", props.agentAppId());
        cfg.put("obo_scopes", props.blueprintAppId() == null || props.blueprintAppId().isBlank()
                ? List.of()
                : List.of("api://" + props.blueprintAppId() + "/access_as_user"));
        cfg.put("authority", props.tenantId() == null || props.tenantId().isBlank()
                ? ""
                : "https://login.microsoftonline.com/" + props.tenantId());
        cfg.put("redirect_uri", redirectUri);
        return cfg;
    }

    @GetMapping("/health")
    public Map<String, Object> health() {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("status", "healthy");
        out.put("service", "LLM Weather Agent (LangChain4j / Spring Boot)");
        out.put("agent_app_id",
                (props.agentAppId() == null || props.agentAppId().isBlank())
                        ? "not set"
                        : props.agentAppId().substring(0, Math.min(8, props.agentAppId().length())) + "...");
        return out;
    }

    private static String headerOr(HttpServletRequest req, String header, String fallback) {
        String v = req.getHeader(header);
        return (v == null || v.isBlank()) ? fallback : v;
    }
}
