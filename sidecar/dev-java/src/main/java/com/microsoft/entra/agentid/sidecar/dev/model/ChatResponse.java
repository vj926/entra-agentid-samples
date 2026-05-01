package com.microsoft.entra.agentid.sidecar.dev.model;

import java.util.List;

public record ChatResponse(
        String response,
        List<DebugEntry> debug,
        boolean success,
        String agentType,
        String tokenFlow
) {
}
