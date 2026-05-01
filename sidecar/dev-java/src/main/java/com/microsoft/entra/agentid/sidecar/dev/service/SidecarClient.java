package com.microsoft.entra.agentid.sidecar.dev.service;

import com.microsoft.entra.agentid.sidecar.dev.config.AppProperties;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;

import java.util.Map;

/**
 * Thin client over the Microsoft Entra SDK auth sidecar.
 * Mirrors get_agent_token / get_agent_token_obo / get_t1_token_claims in app.py.
 */
@Service
public class SidecarClient {

    private static final Logger log = LoggerFactory.getLogger(SidecarClient.class);

    private final AppProperties props;
    private final RestClient restClient;
    private final DebugLogger debug;
    private final JwtUtil jwt;

    public SidecarClient(AppProperties props, RestClient restClient, DebugLogger debug, JwtUtil jwt) {
        this.props = props;
        this.restClient = restClient;
        this.debug = debug;
        this.jwt = jwt;
    }

    /** Autonomous (app-only) Agent Identity token. */
    public String getAgentToken() {
        debug.log("2.A TOKEN REQUEST", "Requesting token for Agent: " + props.agentAppId());
        try {
            String url = props.sidecarUrl()
                    + "/AuthorizationHeaderUnauthenticated/graph-app?AgentIdentity="
                    + props.agentAppId();
            debug.log("2.B SIDECAR CALL", "Sidecar URL: " + url);

            Map<String, Object> body = restClient.get().uri(url)
                    .header("Host", "localhost")
                    .retrieve().body(Map.class);
            String authHeader = body == null ? null : (String) body.get("authorizationHeader");
            if (authHeader != null && !authHeader.isBlank()) {
                Map<String, Object> claims = jwt.decodePayload(authHeader);
                if (claims != null) {
                    debug.log("2.C TOKEN RECEIVED", "Got Agent Identity token (TR) from sidecar", Map.of(
                            "_jwt_token", Map.of(
                                    "type", "tr",
                                    "title", "🔒 TR — Autonomous Agent Token (App-Only / Client Credentials)",
                                    "css", "tr",
                                    "hl", "highlight-purple",
                                    "claims", claims)));
                }
            }
            return authHeader;
        } catch (Exception e) {
            debug.log("2. TOKEN ERROR", "Failed to get token: " + e.getMessage());
            return null;
        }
    }

    /** OBO Agent Identity token (interactive — user is signed in). */
    public String getAgentTokenObo(String userToken) {
        debug.log("OBO 2.A TOKEN REQUEST",
                "Requesting OBO token for Agent: " + props.agentAppId(),
                Map.of(
                        "endpoint", "/AuthorizationHeader/graph (authenticated)",
                        "flow", "User Token (Tc) → Sidecar → T1 (Blueprint) → OBO Exchange → TR (Interactive Agent)"));
        try {
            String url = props.sidecarUrl() + "/AuthorizationHeader/graph?AgentIdentity=" + props.agentAppId();
            String tcSnippet = "(none)";
            if (userToken != null && !userToken.isBlank()) {
                String raw = userToken.startsWith("Bearer ") ? userToken.substring(7) : userToken;
                tcSnippet = raw.length() > 52
                        ? raw.substring(0, 32) + "..." + raw.substring(raw.length() - 16)
                        : raw;
            }
            debug.log("OBO 2.B ENDPOINT", "Authenticated sidecar URL: " + url, Map.of(
                    "authorization_header", "Bearer " + tcSnippet,
                    "note", "Unlike /AuthorizationHeaderUnauthenticated, this endpoint REQUIRES a Bearer token (Tc)"));

            String authValue = userToken == null ? null
                    : (userToken.startsWith("Bearer ") ? userToken : "Bearer " + userToken);

            RestClient.RequestHeadersSpec<?> req = restClient.get().uri(url)
                    .header("Host", "localhost");
            if (authValue != null) {
                req = req.header("Authorization", authValue);
            }
            Map<String, Object> body = req.retrieve().body(Map.class);
            String authHeader = body == null ? null : (String) body.get("authorizationHeader");

            if (authHeader != null && !authHeader.isBlank()) {
                Map<String, Object> claims = jwt.decodePayload(authHeader);
                if (claims != null) {
                    debug.log("OBO 2.D TOKEN RECEIVED",
                            "Got interactive agent token (TR) via OBO exchange", Map.of(
                                    "_jwt_token", Map.of(
                                            "type", "tr",
                                            "title", "💪 TR — Agent OBO Token (Interactive)",
                                            "css", "tr",
                                            "hl", "highlight-green",
                                            "claims", claims)));
                }
            }
            return authHeader;
        } catch (Exception e) {
            debug.log("OBO 2. ERROR", "Failed to get OBO token: " + e.getMessage());
            return null;
        }
    }

    /** Get T1 (Blueprint app-only) token claims for display purposes. */
    public Map<String, Object> getT1TokenClaims() {
        try {
            String url = props.sidecarUrl()
                    + "/AuthorizationHeaderUnauthenticated/graph-app?AgentIdentity="
                    + props.agentAppId();
            Map<String, Object> body = restClient.get().uri(url)
                    .header("Host", "localhost")
                    .retrieve().body(Map.class);
            String authHeader = body == null ? null : (String) body.get("authorizationHeader");
            return authHeader == null ? null : jwt.decodePayload(authHeader);
        } catch (Exception e) {
            log.debug("T1 token fetch failed: {}", e.getMessage());
            return null;
        }
    }
}
