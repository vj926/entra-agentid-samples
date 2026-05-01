# Multi-stage build: Maven build, then slim JRE runtime

# ---- Stage 1: build ----
FROM maven:3.9-eclipse-temurin-21 AS build
WORKDIR /workspace
COPY pom.xml .
RUN mvn -B -q dependency:go-offline
COPY src ./src
RUN mvn -B -q -DskipTests package && \
    cp target/*.jar /workspace/app.jar

# ---- Stage 2: runtime ----
FROM eclipse-temurin:21-jre
WORKDIR /app
COPY --from=build /workspace/app.jar /app/app.jar
EXPOSE 3000
ENV JAVA_OPTS=""
ENTRYPOINT ["sh", "-c", "exec java $JAVA_OPTS -jar /app/app.jar"]
