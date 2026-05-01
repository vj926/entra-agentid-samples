package com.microsoft.entra.agentid.sidecar.dev.model;

public record ChatRequest(
        String message,
        Boolean useLangchain,
        String tokenFlow,
        String userToken
) {
    public boolean obo() {
        return "obo".equalsIgnoreCase(tokenFlow);
    }

    public boolean useLangchainOrDefault() {
        return useLangchain == null ? Boolean.TRUE : useLangchain;
    }
}
