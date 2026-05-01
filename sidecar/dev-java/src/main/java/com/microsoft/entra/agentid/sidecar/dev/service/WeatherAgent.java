package com.microsoft.entra.agentid.sidecar.dev.service;

import com.microsoft.entra.agentid.sidecar.dev.config.AppProperties;
import com.microsoft.entra.agentid.sidecar.dev.model.ChatResponse;
import dev.langchain4j.model.chat.ChatLanguageModel;
import dev.langchain4j.model.ollama.OllamaChatModel;
import dev.langchain4j.service.AiServices;
import org.springframework.stereotype.Service;

import java.time.Duration;

/**
 * Builds and invokes a LangChain4j AiServices agent backed by Ollama, using
 * the per-request WeatherTool. Mirrors process_with_langchain in app.py.
 */
@Service
public class WeatherAgent {

    interface ChatAssistant {
        String chat(String userQuery);
    }

    private final AppProperties props;
    private final DebugLogger debug;

    public WeatherAgent(AppProperties props, DebugLogger debug) {
        this.props = props;
        this.debug = debug;
    }

    public ChatResponse run(String userQuery, WeatherTool tool) {
        debug.log("0.A START", "User query: " + userQuery);
        debug.log("0.B LANGCHAIN", "Sending query to LangChain4j agent (Ollama tool-calling)");

        try {
            ChatLanguageModel model = OllamaChatModel.builder()
                    .baseUrl(props.ollamaUrl())
                    .modelName(props.ollamaModel())
                    .temperature(0.7)
                    .timeout(Duration.ofSeconds(120))
                    .build();

            ChatAssistant assistant = AiServices.builder(ChatAssistant.class)
                    .chatLanguageModel(model)
                    .tools(tool)
                    .build();

            debug.log("0.C AGENT READY",
                    "LangChain4j agent created with Ollama (" + props.ollamaModel() + ")");

            String output = assistant.chat(userQuery);
            debug.log("5. COMPLETE", "LangChain4j agent finished processing");

            return new ChatResponse(output, debug.snapshot(), true, "langchain", null);
        } catch (Exception e) {
            debug.log("ERROR", "LangChain4j agent failed: " + e.getMessage());
            return new ChatResponse("Agent error: " + e.getMessage(),
                    debug.snapshot(), false, "langchain", null);
        }
    }
}
