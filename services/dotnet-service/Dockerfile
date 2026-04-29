FROM mcr.microsoft.com/dotnet/sdk:10.0

WORKDIR /sandbox

RUN apt-get update && \
    apt-get install -y --no-install-recommends openssh-server && \
    mkdir -p /var/run/sshd && \
    useradd -d /sandbox -s /bin/rbash sandbox && \
    echo 'sandbox:sandbox' | chpasswd && \
    echo 'root:root' | chpasswd && \
    sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config && \
    echo 'Match User sandbox' >> /etc/ssh/sshd_config && \
    echo '    ChrootDirectory none' >> /etc/ssh/sshd_config && \
    rm -rf /var/lib/apt/lists/*

COPY ./sandbox.csproj .

# Restore dependencies for dynamic compilation
RUN chmod 711 /sandbox && dotnet restore

RUN chown -R sandbox:sandbox /sandbox

EXPOSE 22
CMD ["/usr/sbin/sshd", "-D", "-o", "ListenAddress=0.0.0.0"]
