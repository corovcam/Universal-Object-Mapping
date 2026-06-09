FROM mcr.microsoft.com/devcontainers/base:ubuntu-24.04

ARG TARGETARCH
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        wget \
        git \
        unzip \
        zip \
        jq \
        openssh-client \
        build-essential \
        pkg-config \
        libssl-dev \
        libffi-dev \
        python3 \
        python3-venv \
        python3-pip \
        maven \
    && rm -rf /var/lib/apt/lists/*

# uv (Python package manager used by the orchestrator)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# uv-managed Python runtimes
ENV UV_PYTHON_INSTALL_DIR=/opt/uv-python \
    UV_PYTHON_PREFERENCE=only-managed
RUN mkdir -p "$UV_PYTHON_INSTALL_DIR" \
    && uv python install 3.13 3.14 \
    && chown -R vscode:vscode "$UV_PYTHON_INSTALL_DIR"

# .NET SDKs for net8.0 and net10.0 projects
ENV DOTNET_ROOT=/usr/share/dotnet
ENV PATH="${DOTNET_ROOT}:${PATH}"
RUN curl -fsSL https://dot.net/v1/dotnet-install.sh -o /tmp/dotnet-install.sh \
    && chmod +x /tmp/dotnet-install.sh \
    && /tmp/dotnet-install.sh --install-dir "$DOTNET_ROOT" --channel 8.0 \
    && /tmp/dotnet-install.sh --install-dir "$DOTNET_ROOT" --channel 10.0 \
    && rm /tmp/dotnet-install.sh

# JDK 25 for Spring Boot 4 services
ENV JAVA_HOME=/opt/java/jdk-25
ENV PATH="${JAVA_HOME}/bin:${PATH}"
RUN case "$TARGETARCH" in \
        amd64) JAVA_ARCH=x64 ;; \
        arm64) JAVA_ARCH=aarch64 ;; \
        *) echo "Unsupported architecture: $TARGETARCH" && exit 1 ;; \
    esac \
    && curl -fsSL "https://api.adoptium.net/v3/binary/latest/25/ga/linux/${JAVA_ARCH}/jdk/hotspot/normal/eclipse" -o /tmp/jdk.tar.gz \
    && mkdir -p /opt/java \
    && JDK_DIR=$(tar -tzf /tmp/jdk.tar.gz | head -1 | cut -d/ -f1) \
    && tar -xzf /tmp/jdk.tar.gz -C /opt/java \
    && ln -sfn "/opt/java/${JDK_DIR}" /opt/java/jdk-25 \
    && rm /tmp/jdk.tar.gz

# nvm with Node.js 20 + 24 (default: 24)
ENV NVM_DIR=/usr/local/nvm
RUN mkdir -p "$NVM_DIR" \
    && curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.2/install.sh -o /tmp/install-nvm.sh \
    && bash /tmp/install-nvm.sh \
    && rm /tmp/install-nvm.sh \
    && bash -lc "source ${NVM_DIR}/nvm.sh \
        && nvm install 20 \
        && nvm install 24 \
        && nvm alias default 24 \
        && nvm use 24 \
        && corepack enable \
        && corepack prepare pnpm@latest --activate" \
    && chown -R vscode:vscode "$NVM_DIR"

RUN printf 'export NVM_DIR="%s"\n[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"\nnvm use default >/dev/null\n' "$NVM_DIR" > /etc/profile.d/nvm.sh

USER vscode
