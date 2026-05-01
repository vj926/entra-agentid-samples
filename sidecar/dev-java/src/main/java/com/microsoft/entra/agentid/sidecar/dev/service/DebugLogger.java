package com.microsoft.entra.agentid.sidecar.dev.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.microsoft.entra.agentid.sidecar.dev.model.DebugEntry;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.context.annotation.RequestScope;

import java.util.ArrayList;
import java.util.List;

/**
 * Per-request debug log so the chat UI can render the full trace.
 * Replaces the module-level `debug_logs` list in app.py.
 */
@Component
@RequestScope
public class DebugLogger {

    private static final Logger log = LoggerFactory.getLogger(DebugLogger.class);
    private final List<DebugEntry> entries = new ArrayList<>();
    private final ObjectMapper objectMapper;

    public DebugLogger(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    public void log(String step, String message) {
        log(step, message, null);
    }

    public void log(String step, String message, Object data) {
        entries.add(new DebugEntry(step, message, data));
        log.info("[{}] {}", step, message);
        if (data != null && log.isDebugEnabled()) {
            try {
                String json = objectMapper.writeValueAsString(data);
                log.debug("    Data: {}", json.length() > 500 ? json.substring(0, 500) : json);
            } catch (Exception ignored) {
                // best-effort
            }
        }
    }

    public List<DebugEntry> snapshot() {
        return new ArrayList<>(entries);
    }

    public void insertBefore(String stepFragment, DebugEntry entry) {
        for (int i = 0; i < entries.size(); i++) {
            if (entries.get(i).step() != null && entries.get(i).step().contains(stepFragment)) {
                entries.add(i, entry);
                return;
            }
        }
        entries.add(entry);
    }

    public void append(DebugEntry entry) {
        entries.add(entry);
    }
}
