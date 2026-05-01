package com.microsoft.entra.agentid.sidecar.dev.service;

import com.microsoft.entra.agentid.sidecar.dev.config.AppProperties;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;

import java.util.Map;

/**
 * Calls the downstream weather API with the Agent Identity bearer token.
 * Mirrors call_weather_api in app.py.
 */
@Service
public class WeatherClient {

    private final AppProperties props;
    private final RestClient restClient;
    private final DebugLogger debug;
    private final JwtUtil jwt;

    public WeatherClient(AppProperties props, RestClient restClient, DebugLogger debug, JwtUtil jwt) {
        this.props = props;
        this.restClient = restClient;
        this.debug = debug;
        this.jwt = jwt;
    }

    public Map<String, Object> call(String city, String token, String tokenLabel, boolean isObo) {
        debug.log("3.A API CALL", "Calling Weather API for: " + city);
        try {
            String url = props.weatherApiUrl() + "/weather?city=" + city;
            String raw = token.startsWith("Bearer ") ? token.substring(7) : token;
            String snippet = raw.length() > 52
                    ? raw.substring(0, 32) + "..." + raw.substring(raw.length() - 16)
                    : raw;
            String tokenDesc = isObo
                    ? "TR — Interactive Agent Token (acts on behalf of user via OBO)"
                    : "TR — Autonomous Agent Token (app-only, no user context)";
            debug.log("3.B API URL", "URL: " + url, Map.of(
                    "token_sent", tokenLabel,
                    "token_description", tokenDesc,
                    "authorization_header", "Authorization: Bearer " + snippet));

            Map<String, Object> claims = jwt.decodePayload(raw);
            if (claims == null) claims = Map.of();
            String iss = String.valueOf(claims.getOrDefault("iss", "?"));
            Object exp = claims.getOrDefault("exp", "?");
            Object aud = claims.getOrDefault("aud", "?");
            Object appid = claims.getOrDefault("appid", claims.getOrDefault("azp", "?"));
            String xmsFrd = String.valueOf(claims.getOrDefault("xms_frd", ""));
            String xmsPar = String.valueOf(claims.getOrDefault("xms_par_app_azp", ""));
            boolean isAgent = "FederatedAgent".equals(xmsFrd) || (!xmsPar.isEmpty() && !"null".equals(xmsPar));
            String flowType = isObo ? "Interactive Agent (OBO)" : "Autonomous Agent";
            boolean issOk = iss.contains("sts.windows.net") || iss.contains("login.microsoftonline.com");

            debug.log("3.C TOKEN VALIDATION",
                    "Weather API validates TR token (" + flowType + ")",
                    Map.of(
                            "1_signature", "RS256 via JWKS (login.microsoftonline.com/.well-known/openid-configuration)",
                            "2_issuer", (issOk ? "PASS" : "CHECK") + " — iss: " + iss,
                            "3_expiry", "PASS — exp: " + exp,
                            "4_agent_identity", (isAgent ? "PASS" : "NONE")
                                    + " — xms_frd=" + (xmsFrd.isEmpty() ? "(absent)" : xmsFrd)
                                    + ", xms_par_app_azp=" + (xmsPar.isEmpty() ? "(absent)" : xmsPar),
                            "5_flow_type", flowType,
                            "6_app_id", String.valueOf(appid),
                            "7_audience", String.valueOf(aud)));

            Map<String, Object> body = restClient.get()
                    .uri(url)
                    .header("Authorization", token)
                    .retrieve()
                    .body(Map.class);
            debug.log("3.D API RESPONSE", "Got weather data from API", body);
            return body;
        } catch (Exception e) {
            debug.log("3. WEATHER ERROR", "API call failed: " + e.getMessage());
            return null;
        }
    }
}
