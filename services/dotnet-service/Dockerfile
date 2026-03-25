FROM mcr.microsoft.com/dotnet/sdk:10.0
WORKDIR /src
COPY ["dotnet-service.csproj", "./"]
RUN dotnet restore "dotnet-service.csproj"

COPY . .
RUN dotnet build "dotnet-service.csproj" -c Release

RUN apt-get update && \
    apt-get install -y openssh-server && \
    mkdir -p /var/run/sshd && \
    echo 'root:root' | chpasswd && \
    sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config && \
    rm -rf /var/lib/apt/lists/*

# We use the SDK image as runtime to perform dynamic compilation with Roslyn later on
# Expose port and start
EXPOSE 5073 22
ENV ASPNETCORE_HTTP_PORTS=5073
CMD /usr/sbin/sshd && dotnet run --no-launch-profile
