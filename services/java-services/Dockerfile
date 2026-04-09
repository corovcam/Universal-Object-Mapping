FROM ubuntu:rolling

ENV DEBIAN_FRONTEND=noninteractive

# Install OpenJDK 25, Maven and OpenSSH Server
RUN apt-get update && \
  apt-get install -y --no-install-recommends openjdk-25-jdk maven openssh-server && \
  mkdir -p /var/run/sshd && \
  useradd -d /app/sandbox -s /bin/rbash sandbox && \
  echo 'sandbox:sandbox' | chpasswd && \
  echo 'root:root' | chpasswd && \
  sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config && \
  echo 'Match User sandbox' >> /etc/ssh/sshd_config && \
  echo '    ChrootDirectory none' >> /etc/ssh/sshd_config && \
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
  chmod 711 /app && \
  cp /app/sandbox-pom.xml /app/sandbox/sandbox-pom.xml 2>/dev/null || true && \
  if [ -f /app/sandbox/sandbox-pom.xml ]; then \
  cd /app/sandbox && \
  mvn dependency:resolve -f sandbox-pom.xml --batch-mode --no-transfer-progress || true && \
  cd /app; \
  fi && \
  chown -R sandbox:sandbox /app/sandbox

EXPOSE 8080 22

CMD ["/usr/sbin/sshd", "&&", "mvn", "spring-boot:run"]
