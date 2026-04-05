FROM ubuntu:rolling

ENV DEBIAN_FRONTEND=noninteractive

# Install OpenJDK 25, Maven and OpenSSH Server
RUN apt-get update && \
  apt-get install -y --no-install-recommends openjdk-25-jdk maven openssh-server && \
  mkdir -p /var/run/sshd && \
  echo 'root:root' | chpasswd && \
  sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config && \
  rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the pom.xml and source code
COPY . .

# Download dependencies and compile without running tests initially
# to ensure it can be rebuilt dynamically later
RUN mvn clean compile -DskipTests

# Prepare sandbox for dynamic compilation:
# 1. Copy sandbox pom.xml to a known location
# 2. Pre-download sandbox dependencies so first compilation is fast
# 3. Create sandbox working directory
RUN mkdir -p /app/sandbox && \
  cp /app/sandbox-pom.xml /app/sandbox-pom.xml 2>/dev/null || true && \
  if [ -f /app/sandbox-pom.xml ]; then \
  mvn dependency:resolve -f /app/sandbox-pom.xml --batch-mode --no-transfer-progress || true; \
  fi

EXPOSE 8080 22

CMD /usr/sbin/sshd && mvn spring-boot:run
