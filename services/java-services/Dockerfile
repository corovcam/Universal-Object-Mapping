FROM ubuntu:rolling

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /sandbox

# Install OpenJDK 25, Maven and OpenSSH Server
RUN apt-get update && \
  apt-get install -y --no-install-recommends openjdk-25-jdk maven openssh-server && \
  mkdir -p /var/run/sshd && \
  useradd -d /sandbox -s /bin/rbash sandbox && \
  echo 'sandbox:sandbox' | chpasswd && \
  echo 'root:root' | chpasswd && \
  sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config && \
  echo 'Match User sandbox' >> /etc/ssh/sshd_config && \
  echo '    ChrootDirectory none' >> /etc/ssh/sshd_config && \
  rm -rf /var/lib/apt/lists/*

# Copy the sandbox-pom.xml
COPY ./sandbox-pom.xml .

# Resolve dependencies
RUN chmod 711 /sandbox && mvn dependency:resolve -f sandbox-pom.xml --batch-mode

# Change user
RUN chown -R sandbox:sandbox /sandbox

EXPOSE 22

CMD ["/usr/sbin/sshd", "-D", "-o", "ListenAddress=0.0.0.0"]
