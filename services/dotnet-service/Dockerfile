FROM mcr.microsoft.com/dotnet/sdk:10.0
WORKDIR /src
COPY ["dotnet-service.csproj", "./"]
RUN dotnet restore "dotnet-service.csproj"

COPY . .
RUN dotnet build "dotnet-service.csproj" -c Release

# We use the SDK image as runtime to perform dynamic compilation with Roslyn later on
# Expose port and start
EXPOSE 8080
ENV ASPNETCORE_HTTP_PORTS=8080
CMD ["dotnet", "run", "--no-launch-profile"]
