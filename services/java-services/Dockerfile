FROM ubuntu:rolling

ENV DEBIAN_FRONTEND=noninteractive

# Install OpenJDK 25 and Maven
RUN apt-get update && \
  apt-get install -y --no-install-recommends openjdk-25-jdk maven && \
  rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the pom.xml and source code
COPY . .

# Download dependencies and compile without running tests initially
# to ensure it can be rebuilt dynamically later
RUN mvn clean compile -DskipTests

EXPOSE 8080

CMD ["mvn", "spring-boot:run"]
