package com.microsoft.entra.agentid.sidecar.dev.service;

import com.microsoft.entra.agentid.sidecar.dev.config.AppProperties;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;

import java.util.List;
import java.util.Map;

/**
 * Polls Ollama to confirm the configured model is available before invoking the agent.
 * Mirrors check_ollama_available in app.py.
 */
@Service
public class OllamaHealth {

    private final AppProperties props;
    private final RestClient restClient;

    public OllamaHealth(AppProperties props, RestClient restClient) {
        this.props = props;
        this.restClient = restClient;
    }

    public boolean modelReady() {
        try {
            Map<String, Object> body = restClient.get()
                    .uri(props.ollamaUrl() + "/api/tags")
                    .retrieve()
                    .body(Map.class);
            if (body == null) return false;
            Object modelsRaw = body.get("models");
            if (!(modelsRaw instanceof List<?> models)) return false;
            String wanted = props.ollamaModel().split(":")[0];
            for (Object m : models) {
                if (m instanceof Map<?, ?> entry) {
                    Object name = entry.get("name");
                    if (name != null && name.toString().split(":")[0].equals(wanted)) {
                        return true;
                    }
                }
            }
        } catch (Exception ignored) {
            // ollama not reachable / not ready
        }
        return false;
    }
}
