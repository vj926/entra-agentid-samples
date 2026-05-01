package com.microsoft.entra.agentid.sidecar.dev.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.util.Base64;
import java.util.Map;

@Component
public class JwtUtil {

    private static final Logger log = LoggerFactory.getLogger(JwtUtil.class);
    private final ObjectMapper objectMapper;

    public JwtUtil(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    /**
     * Decode a JWT payload (no signature verification — claims display only).
     * Mirrors decode_jwt_payload in app.py.
     */
    @SuppressWarnings("unchecked")
    public Map<String, Object> decodePayload(String token) {
        if (token == null || token.isBlank()) {
            return null;
        }
        String t = token.startsWith("Bearer ") ? token.substring(7) : token;
        String[] parts = t.split("\\.");
        if (parts.length != 3) {
            return null;
        }
        try {
            byte[] decoded = Base64.getUrlDecoder().decode(addPadding(parts[1]));
            return objectMapper.readValue(decoded, Map.class);
        } catch (Exception e) {
            log.debug("Failed to decode JWT payload: {}", e.getMessage());
            return null;
        }
    }

    private static String addPadding(String b64) {
        int rem = b64.length() % 4;
        if (rem == 0) return b64;
        return b64 + "=".repeat(4 - rem);
    }
}
