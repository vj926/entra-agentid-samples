package com.microsoft.entra.agentid.sidecar.dev.service;

import dev.langchain4j.agent.tool.Tool;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;
import org.springframework.web.context.annotation.RequestScope;

/**
 * LangChain4j tool exposed to the LLM agent. The agent invokes this method
 * with the city argument; we then thread the per-request OBO user token
 * (if any) down to the weather pipeline.
 */
@Component
@RequestScope
public class WeatherTool {

    private final SidecarClient sidecar;
    private final WeatherClient weather;
    private final DebugLogger debug;

    private String userToken;

    @Autowired
    public WeatherTool(SidecarClient sidecar, WeatherClient weather, DebugLogger debug) {
        this.sidecar = sidecar;
        this.weather = weather;
        this.debug = debug;
    }

    public void setUserToken(String userToken) {
        this.userToken = userToken;
    }

    @Tool("Get the current weather for a city. Use this when the user asks about weather. " +
            "Args: city (e.g. \"Seattle\", \"London\"). Returns weather including temperature, condition, humidity.")
    public String getWeather(String city) {
        boolean isObo = userToken != null && !userToken.isBlank();
        String flow = isObo ? "OBO" : "Autonomous";
        debug.log("1.B TOOL CALL", "Weather function called for city: " + city + " (flow: " + flow + ")");

        String token = isObo ? sidecar.getAgentTokenObo(userToken) : sidecar.getAgentToken();
        if (token == null || token.isBlank()) {
            return "Error: Could not authenticate with Agent Identity (" + flow + "). The sidecar may not be running.";
        }

        var data = weather.call(city, token, "TR", isObo);
        if (data == null) {
            return "Error: Could not get weather data for " + city + ". The API may have rejected the token.";
        }

        String result = formatWeather(city, data, flow);
        debug.log("4. TOOL RESULT", "Weather data retrieved (" + flow + ")", java.util.Map.of("result", result));
        return result;
    }

    public static String formatWeather(String city, java.util.Map<String, Object> w, String flow) {
        return String.format("""
                Weather for %s:
                - Temperature: %s°%s
                - Condition: %s
                - Humidity: %s%%
                - Wind Speed: %s %s
                - Timestamp: %s (%s)
                - Data Source: %s
                - Authentication: Validated by %s
                - Agent App ID: %s
                - Token Flow: %s""",
                w.getOrDefault("city", city),
                w.getOrDefault("temperature", "N/A"),
                w.getOrDefault("temperature_unit", "F"),
                w.getOrDefault("condition", "N/A"),
                w.getOrDefault("humidity", "N/A"),
                w.getOrDefault("wind_speed", "N/A"),
                w.getOrDefault("wind_unit", "mph"),
                w.getOrDefault("timestamp", "N/A"),
                w.getOrDefault("timezone", "UTC"),
                w.getOrDefault("data_source", "Weather API"),
                w.getOrDefault("validated_by", "Agent Identity Token"),
                w.getOrDefault("agent_app_id", "N/A"),
                flow);
    }
}
