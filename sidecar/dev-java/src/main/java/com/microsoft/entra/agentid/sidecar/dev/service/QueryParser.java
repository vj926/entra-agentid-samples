package com.microsoft.entra.agentid.sidecar.dev.service;

import org.springframework.stereotype.Component;

import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Heuristic city extractor for the no-LLM fallback path.
 * Mirrors the regex flow inside process_without_llm in app.py.
 */
@Component
public class QueryParser {

    private static final Pattern IN_PATTERN = Pattern.compile("\\bin\\s+([A-Za-z][A-Za-z\\s]*?)$", Pattern.CASE_INSENSITIVE);
    private static final Pattern FOR_PATTERN = Pattern.compile("\\bfor\\s+([A-Za-z][A-Za-z\\s]*?)$", Pattern.CASE_INSENSITIVE);
    private static final Set<String> COMMON_WORDS = Set.of("weather", "what", "is", "the", "how", "today", "now", "like");

    public String extractCity(String query) {
        if (query == null || query.isBlank()) {
            return "Seattle";
        }
        String clean = query.strip();
        while (clean.endsWith("?") || clean.endsWith(".")) {
            clean = clean.substring(0, clean.length() - 1);
        }

        Matcher m = IN_PATTERN.matcher(clean);
        if (m.find()) {
            return m.group(1).strip();
        }
        m = FOR_PATTERN.matcher(clean);
        if (m.find()) {
            return m.group(1).strip();
        }
        String[] words = clean.split("\\s+");
        if (words.length > 0) {
            String last = words[words.length - 1];
            if (!COMMON_WORDS.contains(last.toLowerCase())) {
                return last;
            }
        }
        return "Seattle";
    }
}
