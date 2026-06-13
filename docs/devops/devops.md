# Universal Object Mapping (UOM): DevOps & Deployment Operations Guide

This guide provides comprehensive technical documentation for the development, operations, configuration, and deployment architecture of the **Universal Object Mapping (UOM)** monorepo. It details network topologies, container specifications, service orchestration, environment variables, automation scripts, and sandbox lifecycles.

---

## 1. System Topology & Container Architecture

The UOM platform runs as a distributed multi-container environment divided into two main execution namespaces: the **Core Services Compose Stack** and the **Daytona Sandbox Workspace Namespace**. They communicate via a dedicated bridge network and the host gateway interface.

### 1.1 Architectural Data Flow Diagram

```mermaid
flowchart TD
    subgraph ClientSpace ["Developer / Client Space"]
        Browser["Next.js Web Browser (Port 3001)"]
        IDE["Local IDE (VS Code / Cursor)"]
    end

    subgraph CoreCompose ["Core Docker Compose Stack ('uom' network)"]
        frontend["Frontend UI Service<br/>(Next.js App Router / Port 3020)"]
        langgraph_api["LangGraph API Gateway<br/>(Port 8000 / 2024 proxy)"]
        redis["LangGraph Checkpoint Redis<br/>(Port 6389)"]
        postgres["LangGraph Vector Database<br/>(Port 5433)"]
        
        db_toolbox["Database Toolbox MCP<br/>(Port 5010)"]
        mongodb_mcp["MongoDB MCP Server<br/>(Port 3010)"]
        
        mssql_db["MS SQL Server 2022<br/>(Source Relational / Port 1333)"]
        mongodb["MongoDB 8.2<br/>(Target Document / Port 27027)"]
        neo4j["Neo4j 2026.02<br/>(Target Graph / Port 7697 / 7484)"]
        
        migrator["MongoDB Relational Migrator<br/>(Port 8091)"]
        tunnel["Ollama AutoSSH Tunnel<br/>(Port 11434)"]
    end

    subgraph DaytonaEnv ["Daytona Sandbox Environment ('uom' network)"]
        daytona_daemon["Daytona Sandbox Daemon<br/>(Port 3000)"]
        dotnet_sandbox[".NET Sandbox Container<br/>(mcr.microsoft.com/dotnet/sdk:10.0)"]
        java_sandbox["Java Sandbox Container<br/>(bellsoft/liberica-openjdk-debian:25-cds)"]
    end

    %% Client Interactions
    Browser <-->|HTTP / SSE / WebSocket| frontend
    frontend <-->|API Proxy /api/*| langgraph_api
    IDE <-->|SSH tunnel / Deep Links| daytona_daemon

    %% Core Services Communication
    langgraph_api <-->|State Persistence| redis
    langgraph_api <-->|Vector Context| postgres
    langgraph_api <-->|Inspect Metadata| db_toolbox
    langgraph_api <-->|Inspect Metadata| mongodb_mcp
    langgraph_api <-->|Manage Sandboxes| daytona_daemon

    %% MCP to Databases
    db_toolbox <-->|JDBC / Bolt| mssql_db
    db_toolbox <-->|Bolt Query| neo4j
    mongodb_mcp <-->|Mongo Protocol| mongodb

    %% Sandbox execution
    daytona_daemon <-->|Spawns / Lifecycle| dotnet_sandbox
    daytona_daemon <-->|Spawns / Lifecycle| java_sandbox
    
    %% Compiler container connection
    dotnet_sandbox <-->|Compile Verification / host.docker.internal| mssql_db
    java_sandbox <-->|Compile Verification / host.docker.internal| mongodb
    java_sandbox <-->|Compile Verification / host.docker.internal| neo4j

    %% ETL Flows
    migrator -->|JDBC Source| mssql_db
    migrator -->|Target Write| mongodb
```

### 1.2 Network & Boundary Isolation
*   **`uom` External Network**: All database engines, MCP servers, orchestrator API containers, and Daytona daemons share an external bridge network named `uom`. This guarantees that services can resolve each other using Docker DNS names (e.g., `mssql_db`, `mongodb`, `neo4j`, `db-toolbox`) while remaining protected from outside intrusion.
*   **Host Gateway Translation**: Ephemeral compilation sandboxes spawned inside the Daytona daemon namespace execute raw compiler runs. To evaluate C# or Java code connecting to SQL Server or MongoDB, the system maps connections to `host.docker.internal`. The host gateway IP is dynamically resolved during project initialization and injected as `OUTER_HOST_GATEWAY_IP` to route sandbox network packets back to the database ports bound on the host machine.

---

## 2. Environment Variable Configuration Matrix

The project requires environment files at the root level, in the frontend directory, and in the orchestrator directory. 

### 2.1 Workspace Root Configuration (`.env`)
The workspace root `.env` configures database connection ports, access credentials, and tunnels. It is created by copying [`.env.example`](../../.env.example).

| Variable Name | Purpose / Description | Default Value | Network Visibility |
| :--- | :--- | :--- | :--- |
| `XRG13_SSH_USERNAME` | SSH username to metacentrum cluster for remote Ollama access. | (Required in dev) | Host system |
| `XRG13_SSH_PRIVATE_KEY_PATH` | Path to the private key used for tunneling to metacentrum. | (Required in dev) | Bound to `autossh` container |
| `FRONTEND_PORT` | Port where Next.js UI is exposed to the developer. | `3020` | Host bound |
| `OLLAMA_PORT` | Port of the local Ollama LLM provider endpoint. | `11434` | Host bound |
| `DOTNET_SERVICE_PORT` | Port of the fallback .NET service. | `5083` | Host bound |
| `JAVA_SERVICE_PORT` | Port of the fallback Java service. | `8090` | Host bound |
| `MONGODB_MIGRATOR_PORT` | Web console port for MongoDB Relational Migrator. | `8091` | Host bound |
| `DB_TOOLBOX_PORT` | Port of the GenAI Database Toolbox MCP server. | `5010` | Host bound |
| `MSSQL_PORT` | Exposed host port for Microsoft SQL Server. | `1333` | Host bound |
| `MSSQL_SA_USER` | SQL Server System Administrator username. | `sa` | Container internal |
| `MSSQL_SA_PASSWORD` | SQL Server System Administrator password. | `Testingorms123` | Container internal |
| `MSSQL_DATABASE` | Default database name populated by the backup restore. | `WideWorldImporters` | Container internal |
| `MSSQL_USER` | Application read-only SQL Server username. | `uom_readonly` | Container internal |
| `MSSQL_PASSWORD` | Application read-only SQL Server password. | `Uomreadonly123` | Container internal |
| `MONGODB_PORT` | Exposed host port for MongoDB database. | `27027` | Host bound |
| `MONGODB_USER` | Application read-only MongoDB username. | `uom_readonly` | Container internal |
| `MONGODB_PASSWORD` | Application read-only MongoDB password. | `uom_readonly` | Container internal |
| `MONGODB_DATABASE` | Default MongoDB database name. | `uom` | Container internal |
| `NEO4J_PORT` | Exposed host port for Neo4j Bolt protocol. | `7697` | Host bound |
| `NEO4J_BROWSER_PORT` | Exposed host port for Neo4j browser console. | `7484` | Host bound |
| `NEO4J_USERNAME` | Neo4j administrator username. | `neo4j` | Container internal |
| `NEO4J_PASSWORD` | Neo4j administrator password. | `password` | Container internal |
| `NEO4J_DATABASE` | Default Neo4j database namespace. | `neo4j` | Container internal |
| `NEO4J_URI` | Bolt connection string used by internal services. | `neo4j://neo4j:7687` | Container internal (`uom`) |
| `MONGODB_URI` | MongoDB connection string used by internal services. | `mongodb://uom_readonly:uom_readonly@mongodb:27017/uom` | Container internal (`uom`) |
| `MSSQL_HOST` | Hostname of the SQL Server container. | `mssql_db` | Container internal (`uom`) |
| `DB_TOOLBOX_URI` | Endpoint of the MCP toolbox service. | `http://db-toolbox:5000` | Container internal (`uom`) |
| `REDIS_PORT` | Exposed host port for LangGraph state cache. | `6389` | Host bound |

### 2.2 Orchestrator Configuration (`services/orchestrator/.env`)
The python orchestrator uses local variables to negotiate with Daytona and target APIs:
*   `DAYTONA_SERVER_URL`: URL of the active Daytona daemon (default: `http://localhost:3000` or `http://daytona-api:3000` in container).
*   `DAYTONA_API_KEY`: API authorization key.
*   `OUTER_HOST_GATEWAY_IP`: Gateway IP address used to translate host connections from sandboxes.
*   `LLM_API_KEY` / `LLM_BASE_URL`: OpenAI-compatible cluster or Ollama endpoints.
*   `LOGFIRE_TOKEN`: Structured log tracing credential token.

### 2.3 Frontend Configuration (`frontend/uom-translator-ui/.env.development` / `.env.production`)
*   `LANGGRAPH_API_URL`: Points to Next.js API proxy (`http://localhost:3020/api` or `http://langgraph-api:8000`).
*   `NEXT_PUBLIC_LANGGRAPH_ASSISTANT_ID`: Routing ID of the graph.

---

## 3. Docker Compose Stack Analysis

The deployment maps services across separate files to isolate concerns between core infrastructure, development servers, and sandboxes.

### 3.1 `docker-compose.yml` (Core Services Stack)
This file defines the primary database engines, MCP servers, Portainer console, and the Next.js frontend:
*   **`frontend`**: Built from the Next.js Dockerfile, exposes port `3020` on the host, and connects to the `uom` network to communicate with the backend.
*   **`ollama-autossh-tunnel`**: Establishes an encrypted SSH tunnel to Metacentrum hosts (`xrg13.ms.mff.cuni.cz:1302`) to securely route remote LLM requests via port `11434` without storing keys outside `/id_rsa` volume mounts.
*   **`mssql_db`**: Restores the `WideWorldImporters` dataset and exposes port `1333`.
*   **`mongodb`**: Boots Mongo 8.2, runs `init-mongodb.sh` to initialize credentials, and exposes port `27027`.
*   **`neo4j`**: Boots Neo4j 2026.02, sets procedures to allow APOC plugins (`apoc.*`), sets heap limits (`7900m`) and page cache size (`10000m`), and exposes browser port `7484` and Bolt port `7697`.
*   **`mongodb-relational-migrator`**: Runs the MongoDB migrator tool UI on port `8091`.
*   **`db-toolbox`**: Hosts the MCP Database Toolbox, executing direct schema and metadata query mappings.

### 3.2 `docker-compose.prod.yml` (Production Targets)
*   Sets `NODE_ENV: production` for the Next.js build.
*   Extends volume definitions to preserve database files (`mssql_data`, `mongodb_data`, `neo4j_data`) across container recreation.
*   Binds services to standard production ports (e.g., mapping Portainer on `9020`).

### 3.3 `docker-compose.langgraph.override.yml` (Development Overrides)
Binds custom mounts to enable hot-reloading in python services:
*   **`langgraph-api`**: Configures Docker compose watch rules:
    ```yaml
    develop:
      watch:
        - action: rebuild
          path: ./src
          target: /deps/orchestrator/src
        - action: sync
          path: ./scripts
          target: /deps/orchestrator/scripts
    ```
*   Exposes `langgraph-redis` on port `6389` to let developer scripts examine Checkpointer state tables.

### 3.4 `docker-compose.daytona.override.yml` (Daytona Services Override)
Configures the Daytona Sandbox host daemon to interact with database engines:
*   **`runner`**: Injects `OUTER_HOST_GATEWAY_IP` into the container's hosts table using `extra_hosts`:
    ```yaml
    extra_hosts:
      - "host.docker.internal:${OUTER_HOST_GATEWAY_IP:-host-gateway}"
    ```
*   **`dex`**: Exposes the OIDC auth server on port `5356`.
*   **`registry`**: Configures internal container registry overrides on port `6058`.

---

## 4. Initialization & Destruction Bash Scripts

Automation scripts are placed in the [`scripts/`](../../scripts) folder to manage monorepo setup lifecycles.

### 4.1 `scripts/init-project.sh`
This script coordinates submodules, networks, environment settings, and boots the docker compose services:
1.  **Initialize Git Submodules**:
    ```bash
    git submodule update --init --recursive
    ```
2.  **Setup Docker Network**:
    Validates if the external network `uom` exists; creates it if not:
    ```bash
    docker network inspect "uom" >/dev/null 2>&1 || docker network create uom
    ```
3.  **Compute Host Gateway IP**:
    Extracts the default gateway IP of the `uom` network bridge and exports it as `OUTER_HOST_GATEWAY_IP` to allow sandboxes to route to databases on the host:
    ```bash
    HOST_GW="$(docker network inspect "uom" --format '{{(index .IPAM.Config 0).Gateway}}')"
    export OUTER_HOST_GATEWAY_IP="$HOST_GW"
    ```
4.  **Boot Stacks**:
    Launches the core services stack and Daytona engine overrides:
    ```bash
    docker compose up -d --remove-orphans
    # Daytona engine overrides
    docker compose -f external/daytona/docker/docker-compose.yaml -f docker-compose.daytona.override.yml up -d --remove-orphans
    ```

### 4.2 `scripts/destroy-containers.sh`
Tears down and purges the docker-compose services:
```bash
# Tears down database compose stacks, purging anonymous volumes (-v) and local builds
docker compose down -v --remove-orphans --rmi local
# Tears down Daytona services, clearing workspaces and caches
docker compose -f external/daytona/docker/docker-compose.yaml -f docker-compose.daytona.override.yml down -v --remove-orphans --rmi local
```

### 4.3 `scripts/update-submodules.sh`
Polls external submodules, fetches tags, and checks out the newest release tag:
```bash
git submodule update --init --recursive
for dir in external/*; do
    if [ -d "$dir" ]; then
        cd "$dir"
        git fetch --tags
        NEXT_TAG=$(git describe --tags --abbrev=0 --exclude=$(git describe --tags --abbrev=0) 2>/dev/null || echo "")
        if [ -n "$NEXT_TAG" ]; then
            git checkout "$NEXT_TAG"
        fi
        cd ..
    fi
done
```

---

## 5. Service-Specific DevOps Configurations

### 5.1 Orchestrator Service (`services/orchestrator`)
*   **Package Management**: Uses `uv` for python environments. Run `uv sync --all-extras` to prepare dependencies.
*   **Dockerfile**: Compiles the FastAPI web application, loads environment parameters from `.env`, and runs on port `8000` (which is mapped to proxy endpoint `3001` or standard FastAPI routes).
*   **LangGraph CLI**: Runs hot-reloading servers using `langgraph dev`.

### 5.2 .NET Compilation Sandbox Service (`services/dotnet-service`)
*   **Container Build**: Built using [`services/dotnet-service/Dockerfile`](../../services/dotnet-service/Dockerfile).
*   **Core SDK**: `mcr.microsoft.com/dotnet/sdk:10.0`.
*   **Sandbox Lockdown**: Installs `openssh-server`. Creates a restricted user account `sandbox` shell bound to `/bin/rbash` (restricted bash) to block execution outside authorized path bounds.
*   **Dependency Caching**: Runs `dotnet restore` during container build to cache core assemblies (EF Core, Dapper, SQL Server Drivers) inside the `/sandbox` folder.

### 5.3 Java Compilation Sandbox Service (`services/java-services`)
*   **Container Build**: Built using [`services/java-services/Dockerfile`](../../services/java-services/Dockerfile).
*   **SDK & Build Manager**: Installs `openjdk-25-jdk` and `maven` over a baseline `ubuntu:rolling` image.
*   **Security Lock**: SSH daemon configured to run restricted shell users (`sandbox` with `/bin/rbash`).
*   **Dependency Resolution**: Runs `mvn dependency:resolve -f sandbox-pom.xml --batch-mode` at build time. This downloads Spring Data Neo4j, Spring Data MongoDB, Cypher drivers, and test frameworks, caching them inside the container to avoid network overhead during dynamic evaluations.

### 5.4 Database ETL Initialization Pipelines (`services/etl`)

#### MS SQL Server Database Restore
The relational source engine (`mssql_db`) downloads a WideWorldImporters backup database file on start. 
*   The [`Dockerfile`](../../services/etl/mssql/Dockerfile) pulls the Microsoft full database backup file:
    ```dockerfile
    curl -L -o /var/opt/mssql/backup/WideWorldImporters-Full.bak https://github.com/Microsoft/sql-server-samples/releases/download/wide-world-importers-v1.0/WideWorldImporters-Full.bak
    ```
*   The entrypoint script [`init-db.sh`](../../services/etl/mssql/init-db.sh) starts the service, waits for the SQL Server daemon, runs a `RESTORE DATABASE` command, processes relational configurations (`UOM-WideWorldImporters_SQL_SERVER_config.sql`), and provisions a read-only login (`uom_readonly`).

#### MongoDB Database Init
The `mongodb` container executes [`init-mongodb.sh`](../../services/etl/mongodb/init-mongodb.sh) on startup. This initializes the database, configures user profiles, and sets target database permissions.

#### Neo4j ETL Process
The Neo4j database uses a mapping file and a bash driver to run bulk imports:
*   **`run-neo4j-etl.sh`**: Runs inside the `universal-object-mapping-neo4j-1` container.
*   It copies JDBC drivers (`mssql-jdbc-13.4.0.jre11.jar`) to the ETL classpath to prevent class loading issues.
*   Triggers the `neo4j-etl export` CLI to translate database schemas using the mapping JSON, exporting results to temporary CSV files.
*   Executes `neo4j-admin database import full` to import CSV structures into graph databases.
*   Runs `configure-db.sh` to update database indexes and constraints.

---

## 6. Daytona Sandboxes Lifecycle & Snapshotting

Dynamic C# and Java query compilations run inside isolated **Daytona Sandboxes**. The orchestrator manages their lifecycle using the `ValidationSandbox` class defined in [`sandboxes.py`](../../services/orchestrator/src/react_agent/utils/sandboxes.py).

### 6.1 Sandbox Configuration
```python
DAYTONA_SANDBOX_IMAGES: dict[SandboxType, Image] = {
    SandboxType.DOTNET_10_SANDBOX: Image.base("mcr.microsoft.com/dotnet/sdk:10.0"),
    SandboxType.JAVA_25_SANDBOX: Image.base("bellsoft/liberica-openjdk-debian:25-cds")
        .run_commands("apt-get update && apt-get install -y --no-install-recommends maven && rm -rf /var/lib/apt/lists/*")
}
```

### 6.2 Snapshot Exponential Backoff Retry Loop
Creating base environment snapshots requires pulling large Docker images and resolving packages, which can fail due to network glitches or API rate limits.
To handle this, `ValidationSandbox.create_snapshot` wraps snapshot creation in a retry loop with exponential backoff:
```python
max_retries = 5
for attempt in range(max_retries):
    try:
        # Check if snapshot already exists
        existing_snapshot = await daytona.snapshot.get(params.name)
        return
    except Exception:
        try:
            # Create a new snapshot if missing
            await daytona.snapshot.create(params, on_logs=...)
            break
        except Exception as e:
            if attempt < max_retries - 1:
                # Exponential backoff wait: 1s, 2s, 4s, 8s, 16s
                await asyncio.sleep(2 ** attempt)
            else:
                raise
```

### 6.3 Sandbox State Machine Recovery
The `create_validation_sandbox` method manages Daytona container state transitions:
1.  **`GET_STATE`**: Inspects container state (`daytona.get(name)`).
2.  **Zombie Recovery**: If the sandbox is in an `ERROR` or `BUILD_FAILED` state, it deletes the container and schedules a clean rebuild.
3.  **Resuming Stopped Containers**: If the sandbox is `STOPPED` or `STOPPING`, it waits for the shutdown to complete, calls `start()`, and waits for the container to reach a running state.
4.  **Active Creation Wait**: If the state is `CREATING` or `PENDING_BUILD`, it blocks execution until the container transitions to `STARTED`.
5.  **Auto-Stop Timeout**: Sandboxes are configured with `auto_stop_interval=60` to automatically shut down after 60 minutes of inactivity, preserving host system resources.

---

## 7. Deployment Instructions

### 7.1 Development Environment Setup
To run the monorepo for local development and hot-reloading:

1.  **Copy Environment Files**:
    ```bash
    cp .env.example .env
    cp .env.example .env.development
    ```
2.  **Install Frontend Dependencies**:
    ```bash
    cd frontend/uom-translator-ui
    pnpm install
    ```
3.  **Initialize the Docker Stack**:
    Run the initialization script from the project root:
    ```bash
    ./scripts/init-project.sh
    ```
4.  **Start the LangGraph Dev Server**:
    Start the orchestrator graph with hot-reloading from the orchestrator directory:
    ```bash
    cd services/orchestrator
    uv sync --all-extras
    make dev
    ```
5.  **Start Next.js in Dev Mode**:
    Launch the development server on `http://localhost:3001` (to avoid conflicting with the Daytona daemon on port `3000`):
    ```bash
    cd frontend/uom-translator-ui
    pnpm run dev
    ```

### 7.2 Production Environment Setup
To build and deploy the services for production:

1.  **Configure Production Variables**:
    ```bash
    cp .env.example .env
    cp .env.example .env.production
    ```
2.  **Build and Run the Production Stack**:
    Start the stack using the production compose configuration:
    ```bash
    docker compose -f docker-compose.prod.yml up -d --build
    ```
3.  **Configure Database ETL Pipelines**:
    *   Access the MongoDB migrator dashboard at `http://localhost:8091` to import [`UOM WideWorldImporters.relmig`](../../services/etl/mongodb/UOM%20WideWorldImporters.relmig) and run the SQL-to-Mongo ETL.
    *   Run the Neo4j ETL script to migrate SQL data to the graph database:
        ```bash
        cd services/etl/neo4j
        ./run-neo4j-etl.sh
        ```
4.  **Deploy the Production API Gateway**:
    Build and start the Python API service and LangGraph production engine:
    ```bash
    docker compose -f services/orchestrator/docker-compose.yml up -d --build
    ```
