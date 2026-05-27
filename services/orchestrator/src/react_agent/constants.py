"""Constants and enumerations for the React Agent Orchestrator service."""
from enum import Enum


class AvailableModel(str, Enum):
    """Available models from Ollama and EINFRA for UI dropdown selection."""

    # # Local Models
    # LOCAL_OLLAMA_GEMMA3_4B = "ollama/gemma3:4b"
    # LOCAL_OLLAMA_SMOLLM2 = "ollama/smollm2"

    # Ollama Models
    OLLAMA_QWEN3_6_27B = "ollama/qwen3.6:27b"
    OLLAMA_GPT_OSS = "ollama/gpt-oss:latest"
    OLLAMA_QWEN3_CODER_30B = "ollama/qwen3-coder:30b"
    OLLAMA_MISTRAL_SMALL_3_2 = "ollama/mistral-small3.2:latest"
    OLLAMA_QWEN3_EMBEDDING = "ollama/qwen3-embedding:latest"

    # EINFRA Models (OpenAI compatible)
    EINFRA_MINI = "einfra/mini"
    EINFRA_CODER = "einfra/coder"
    EINFRA_AGENTIC = "einfra/agentic"
    EINFRA_THINKER = "einfra/thinker"
    EINFRA_QWEN3_CODER = "einfra/qwen3-coder"
    EINFRA_QWEN3_CODER_30B = "einfra/qwen3-coder-30b"
    EINFRA_GPT_OSS_120B = "einfra/gpt-oss-120b"
    EINFRA_QWEN3_RERANKER_4B = "einfra/qwen3-reranker-4b"
    EINFRA_QWEN3_EMBEDDING_4B = "einfra/qwen3-embedding-4b"
    EINFRA_LLAMA_4_SCOUT_17B = "einfra/llama-4-scout-17b-16e-instruct"
    EINFRA_MXBAI_EMBED_LARGE = "einfra/mxbai-embed-large:latest"
    EINFRA_MULTILINGUAL_E5 = "einfra/multilingual-e5-large-instruct"
    EINFRA_NOMIC_EMBED_V2 = "einfra/nomic-embed-text-v2-moe"
    EINFRA_NOMIC_EMBED_V1_5 = "einfra/nomic-embed-text-v1.5"
    EINFRA_DEEPSEEK_V3_2 = "einfra/deepseek-v3.2"
    EINFRA_DEEPSEEK_V4_PRO = "einfra/deepseek-v4-pro"
    EINFRA_DEEPSEEK_V4_PRO_THINKING = "einfra/deepseek-v4-pro-thinking"
    
    EINFRA_MISTRAL_LARGE = "einfra/mistral-large"
    EINFRA_DEEPSEEK_V3_2_THINKING = "einfra/deepseek-v3.2-thinking"
    EINFRA_KIMI_K2_5 = "einfra/kimi-k2.5"
    EINFRA_KIMI_K2_6 = "einfra/kimi-k2.6"
    EINFRA_QWEN3_5 = "einfra/qwen3.5"
    EINFRA_QWEN3_CODER_NEXT = "einfra/qwen3-coder-next"
    EINFRA_QWEN3_5_122B = "einfra/qwen3.5-122b"
    EINFRA_GLM_4_7 = "einfra/glm-4.7"
    EINFRA_GLM_5 = "einfra/glm-5"
    EINFRA_GLM_5_1 = "einfra/glm-5.1"


class TranslationType(str, Enum):
    SCHEMA = "schema"
    QUERY = "query"
    BOTH = "both"


class FrameworkEnum(str, Enum):
    """Supported Object-Relational/Graph/Document Mapping targets."""

    DOTNET_EFCORE = ".NET Entity Framework Core"
    DOTNET_DAPPER = ".NET Dapper"
    DOTNET_NHIBERNATE = ".NET NHibernate"
    JAVA_SPRING_DATA_MONGODB = "Java Spring Data MongoDB"
    JAVA_SPRING_DATA_NEO4J = "Java Spring Data Neo4j"


class DotnetFramework(str, Enum):
    DOTNET_EFCORE = FrameworkEnum.DOTNET_EFCORE.value
    DOTNET_DAPPER = FrameworkEnum.DOTNET_DAPPER.value
    DOTNET_NHIBERNATE = FrameworkEnum.DOTNET_NHIBERNATE.value


class JavaFramework(str, Enum):
    JAVA_SPRING_DATA_MONGODB = FrameworkEnum.JAVA_SPRING_DATA_MONGODB.value
    JAVA_SPRING_DATA_NEO4J = FrameworkEnum.JAVA_SPRING_DATA_NEO4J.value


class SourceFramework(str, Enum):
    DOTNET_EFCORE = FrameworkEnum.DOTNET_EFCORE.value
    DOTNET_DAPPER = FrameworkEnum.DOTNET_DAPPER.value
    DOTNET_NHIBERNATE = FrameworkEnum.DOTNET_NHIBERNATE.value


class TargetFramework(str, Enum):
    JAVA_SPRING_DATA_MONGODB = FrameworkEnum.JAVA_SPRING_DATA_MONGODB.value
    JAVA_SPRING_DATA_NEO4J = FrameworkEnum.JAVA_SPRING_DATA_NEO4J.value


class SandboxType(str, Enum):
    DOTNET_10_SANDBOX = "dotnet-10-sandbox"
    JAVA_25_SANDBOX = "java-25-sandbox"


FRAMEWORK_TO_NORMALIZED_NAME = {
    FrameworkEnum.DOTNET_EFCORE: "dotnet_efcore",
    FrameworkEnum.DOTNET_DAPPER: "dotnet_dapper",
    FrameworkEnum.DOTNET_NHIBERNATE: "dotnet_nhibernate",
    FrameworkEnum.JAVA_SPRING_DATA_MONGODB: "java_spring_data_mongodb",
    FrameworkEnum.JAVA_SPRING_DATA_NEO4J: "java_spring_data_neo4j",
}

NORMALIZED_FRAMEWORK_TO_FRAMEWORK = {
    "dotnet_efcore": FrameworkEnum.DOTNET_EFCORE,
    "dotnet_dapper": FrameworkEnum.DOTNET_DAPPER,
    "dotnet_nhibernate": FrameworkEnum.DOTNET_NHIBERNATE,
    "java_spring_data_mongodb": FrameworkEnum.JAVA_SPRING_DATA_MONGODB,
    "java_spring_data_neo4j": FrameworkEnum.JAVA_SPRING_DATA_NEO4J,
}

FRAMEWORK_TO_SNIPPET_FILES = {
    FrameworkEnum.DOTNET_EFCORE: (
        "EFCoreSchemaValidationEntrypoint.cs",
        "EFCoreQueryEntrypoint.cs",
    ),
    FrameworkEnum.DOTNET_DAPPER: (
        "DapperSchemaValidationEntrypoint.cs",
        "DapperQueryEntrypoint.cs",
    ),
    FrameworkEnum.DOTNET_NHIBERNATE: (
        "NHibernateSchemaValidationEntrypoint.cs",
        "NHibernateQueryEntrypoint.cs",
    ),
    FrameworkEnum.JAVA_SPRING_DATA_MONGODB: (
        "MongoSchemaValidationEntrypoint.java",
        "MongoQueryEntrypoint.java",
    ),
    FrameworkEnum.JAVA_SPRING_DATA_NEO4J: (
        "Neo4jSchemaValidationEntrypoint.java",
        "Neo4jQueryEntrypoint.java",
    ),
}

FRAMEWORK_TO_CONFIG_FILES = {
    FrameworkEnum.DOTNET_EFCORE: "efcore-sandbox.csproj",
    FrameworkEnum.DOTNET_DAPPER: "dapper-sandbox.csproj",
    FrameworkEnum.DOTNET_NHIBERNATE: "nhibernate-sandbox.csproj",
    FrameworkEnum.JAVA_SPRING_DATA_MONGODB: "mongo-pom.xml",
    FrameworkEnum.JAVA_SPRING_DATA_NEO4J: "neo4j-pom.xml",
}

MODEL_PROFILE_CACHE: dict[str, dict] = {}

MAX_EXTRACTION_LOOPS = 3

MAX_TRANSLATION_LOOPS = 3

GENERAL_SANDBOX_README = """# Universal Object Mapping - Sandbox Environment

Welcome to the Sandbox Environment! 
This directory (`/sandbox`) contains dynamically generated projects created by the AI assistant during the database schema and query translation process.

## Navigation
Each validation execution is isolated in its own folder named with the pattern: `sandbox-<thread_id>-<timestamp>`.
Navigate to the specific folder to see the generated code, configuration, and execution results.

## Environment Details
- **Daytona Instance**: This sandbox is managed by Daytona Workspace API.
  - **URL**: `{daytona_url}`
  - **Login Email**: `dev@daytona.io`
  - **Password**: `password`
- **Databases Context**:
  - Relational Database (SQL Server): `{ms_sql_connection_string}`
  - MongoDB: `{mongodb_uri}`
  - Neo4j: `{neo4j_uri}`
    - Neo4j Browser: `{neo4j_browser_uri}`

## Documentation
- [Daytona Documentation](https://www.daytona.io/docs)
- [Universal Object Mapping Overview](https://github.com/corovcam/Universal-Object-Mapping)
"""

DOTNET_EFCORE_SANDBOX_README = """# .NET Entity Framework Core Sandbox

This sandbox was generated for thread `{thread_id}` at `{timestamp}`.

## What is this?
This project is an automated code validation sandbox for `{framework}`. It contains dynamically generated C# code and configuration to compile and test database queries or schema mappings.

## How to run
The execution script is provided in `run.sh`. You can execute it by running:
```bash
./run.sh
```

## Dependencies
- .NET 10.0 SDK
- Target Framework: `{framework}`

## Databases
- Connection String: `{connection_string}`

## Documentation
- [.NET Documentation](https://learn.microsoft.com/en-us/dotnet/)
- [Entity Framework Core Documentation](https://learn.microsoft.com/en-us/ef/core/)

## Next Steps
Check the `results/` folder (if applicable) for the JSON output of the execution, or look at `Program.cs` for the generated source code.
"""

DOTNET_DAPPER_SANDBOX_README = """# .NET Dapper Sandbox

This sandbox was generated for thread `{thread_id}` at `{timestamp}`.

## What is this?
This project is an automated code validation sandbox for `{framework}`. It contains dynamically generated C# code and configuration to compile and test database queries or schema mappings.

## How to run
The execution script is provided in `run.sh`. You can execute it by running:
```bash
./run.sh
```

## Dependencies
- .NET 10.0 SDK
- Target Framework: `{framework}`

## Databases
- Connection String: `{connection_string}`

## Documentation
- [.NET Documentation](https://learn.microsoft.com/en-us/dotnet/)
- [Dapper Documentation](https://github.com/DapperLib/Dapper)

## Next Steps
Check the `results/` folder (if applicable) for the JSON output of the execution, or look at `Program.cs` for the generated source code.
"""

DOTNET_NHIBERNATE_SANDBOX_README = """# .NET NHibernate Sandbox

This sandbox was generated for thread `{thread_id}` at `{timestamp}`.

## What is this?
This project is an automated code validation sandbox for `{framework}`. It contains dynamically generated C# code and configuration to compile and test database queries or schema mappings.

## How to run
The execution script is provided in `run.sh`. You can execute it by running:
```bash
./run.sh
```

## Dependencies
- .NET 10.0 SDK
- Target Framework: `{framework}`

## Databases
- Connection String: `{connection_string}`

## Documentation
- [.NET Documentation](https://learn.microsoft.com/en-us/dotnet/)
- [NHibernate Documentation](https://nhibernate.info/)

## Next Steps
Check the `results/` folder (if applicable) for the JSON output of the execution, or look at `Program.cs` for the generated source code.
"""

JAVA_SPRING_DATA_MONGODB_SANDBOX_README = """# Java Spring Data MongoDB Sandbox

This sandbox was generated for thread `{thread_id}` at `{timestamp}`.

## What is this?
This project is an automated code validation sandbox for `{framework}`. It contains dynamically generated Java code and Maven configuration to compile and test database queries or schema mappings.

## How to run
The execution script is provided in `run.sh`. You can execute it by running:
```bash
./run.sh
```

## Dependencies
- Java 25 (OpenJDK)
- Maven
- Target Framework: `{framework}`

## Databases
- MongoDB URI: `{mongodb_uri}`

## Documentation
- [Spring Data MongoDB Reference](https://docs.spring.io/spring-data/mongodb/reference/index.html)
- [MongoDB Java Driver Documentation](https://www.mongodb.com/docs/drivers/java/sync/current/)

## Next Steps
Check the `results/` folder (if applicable) for the JSON output of the execution, or look at `src/main/java/uom/services/` for the generated source code.
"""

JAVA_SPRING_DATA_NEO4J_SANDBOX_README = """# Java Spring Data Neo4j Sandbox

This sandbox was generated for thread `{thread_id}` at `{timestamp}`.

## What is this?
This project is an automated code validation sandbox for `{framework}`. It contains dynamically generated Java code and Maven configuration to compile and test database queries or schema mappings.

## How to run
The execution script is provided in `run.sh`. You can execute it by running:
```bash
./run.sh
```

## Dependencies
- Java 25 (OpenJDK)
- Maven
- Target Framework: `{framework}`

## Databases
- Neo4j URI: `{neo4j_uri}`

## Documentation
- [Spring Data Neo4j Reference](https://docs.spring.io/spring-data/neo4j/reference/index.html)
- [Neo4j Java Driver Documentation](https://neo4j.com/docs/java-manual/current/)

## Next Steps
Check the `results/` folder (if applicable) for the JSON output of the execution, or look at `src/main/java/uom/services/` for the generated source code.
"""

DOTNET_VSCODE_EXTENSIONS = """{
  "recommendations": [
    "ms-dotnettools.csharp",
    "ms-dotnettools.vscode-dotnet-runtime",
    "mtxr.sqltools",
    "mtxr.sqltools-driver-mssql"
  ]
}"""

JAVA_VSCODE_EXTENSIONS = """{
  "recommendations": [
    "vscjava.vscode-java-pack",
    "vscjava.vscode-maven",
    "redhat.java",
    "vmware.vscode-spring-boot",
    "mongodb.mongodb-vscode"
  ]
}"""

AGENTS_MD_CONTENT = """# Universal Object Mapping - AI Sandbox Agent Instructions

This sandbox environment was generated for the Universal Object Mapping (UOM) project. You are an AI coding assistant connected to a Daytona Sandbox Workspace.

## Directory Structure
- `/sandbox`: Root directory for all validation sandboxes.
- `/sandbox/sandbox-<thread_id>-<timestamp>`: A specific generated database schema or query translation test project (either .NET or Java).

## Databases Context
Real database instances are provided via environment variables in the specific sandbox `run.sh` script.

## MCP Server
An MCP server is configured in `.vscode/.mcp` to interact with the broader Orchestrator or database context.
"""

MCP_CONFIG_CONTENT = """{{
    "servers": {{
        "universal-object-mapping-mcp": {{
            "url": "http://{host_gateway_ip}:8123/mcp/",
            "type": "http"
        }}
    }}
}}"""
