package com.microsoft.entra.agentid.sidecar.dev.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "agent")
public record AppProperties(
        String sidecarUrl,
        String weatherApiUrl,
        String agentAppId,
        String blueprintAppId,
        String tenantId,
        String clientSpaAppId,
        String ollamaUrl,
        String ollamaModel
) {
}
