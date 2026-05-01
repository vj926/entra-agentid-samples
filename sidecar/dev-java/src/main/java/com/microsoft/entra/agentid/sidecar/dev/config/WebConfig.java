package com.microsoft.entra.agentid.sidecar.dev.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.HttpComponentsClientHttpRequestFactory;
import org.springframework.web.client.RestClient;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@Configuration
public class WebConfig implements WebMvcConfigurer {

    /**
     * DEMO ONLY — allows all origins. Restrict in production.
     */
    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/**")
                .allowedOriginPatterns("*")
                .allowedMethods("GET", "POST", "OPTIONS")
                .allowedHeaders("*");
    }

    /**
     * Default RestClient using Apache HttpComponents 5.
     * Apache (unlike JDK HttpClient) does NOT silently strip restricted headers
     * like {@code Host}, which the Entra Agent SDK sidecar requires set to
     * {@code localhost} regardless of the actual destination host.
     */
    @Bean
    RestClient restClient() {
        return RestClient.builder()
                .requestFactory(new HttpComponentsClientHttpRequestFactory())
                .build();
    }
}
