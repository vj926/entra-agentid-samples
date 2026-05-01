package com.microsoft.entra.agentid.sidecar.dev;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.ConfigurationPropertiesScan;

@SpringBootApplication
@ConfigurationPropertiesScan
public class Application {

    public static void main(String[] args) {
        System.out.println("============================================================");
        System.out.println("  3P Agent Identity Demo (Java / Spring Boot + LangChain4j)");
        System.out.println("============================================================");
        System.out.println("  Open http://localhost:3000 in your browser");
        System.out.println("============================================================");
        SpringApplication.run(Application.class, args);
    }
}
