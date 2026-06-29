"""Constants and enumerations for the React Agent Orchestrator service."""
from enum import Enum

from typing_extensions import Literal


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
    EINFRA_QWEN3_CODER_30B = "einfra/qwen3-coder-30b"
    EINFRA_GPT_OSS_120B = "einfra/gpt-oss-120b"
    EINFRA_QWEN3_RERANKER_4B = "einfra/qwen3-reranker-4b"
    EINFRA_QWEN3_EMBEDDING_4B = "einfra/qwen3-embedding-4b"
    EINFRA_LLAMA_4_SCOUT_17B = "einfra/llama-4-scout-17b-16e-instruct"
    EINFRA_MXBAI_EMBED_LARGE = "einfra/mxbai-embed-large:latest"
    EINFRA_MULTILINGUAL_E5 = "einfra/multilingual-e5-large-instruct"
    EINFRA_NOMIC_EMBED_V2 = "einfra/nomic-embed-text-v2-moe"
    EINFRA_NOMIC_EMBED_V1_5 = "einfra/nomic-embed-text-v1.5"
    EINFRA_DEEPSEEK_V4_PRO = "einfra/deepseek-v4-pro"
    EINFRA_DEEPSEEK_V4_PRO_THINKING = "einfra/deepseek-v4-pro-thinking"
    
    EINFRA_MISTRAL_LARGE = "einfra/mistral-large"
    EINFRA_KIMI_K2_6 = "einfra/kimi-k2.6"
    EINFRA_KIMI_K2_7 = "einfra/kimi-k2.7"
    EINFRA_QWEN3_5 = "einfra/qwen3.5"
    EINFRA_QWEN3_CODER_NEXT = "einfra/qwen3-coder-next"
    EINFRA_QWEN3_5_122B = "einfra/qwen3.5-122b"
    EINFRA_GLM_5_2 = "einfra/glm-5.2"
    EINFRA_GEMMA4 = "einfra/gemma4"


class TranslationType(str, Enum):
    """The type of translation being requested (schema only, query only, or both)."""

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
    """Supported C#/.NET database frameworks for translation source."""

    DOTNET_EFCORE = FrameworkEnum.DOTNET_EFCORE.value
    DOTNET_DAPPER = FrameworkEnum.DOTNET_DAPPER.value
    DOTNET_NHIBERNATE = FrameworkEnum.DOTNET_NHIBERNATE.value


class JavaFramework(str, Enum):
    """Supported Java database frameworks for translation targets."""

    JAVA_SPRING_DATA_MONGODB = FrameworkEnum.JAVA_SPRING_DATA_MONGODB.value
    JAVA_SPRING_DATA_NEO4J = FrameworkEnum.JAVA_SPRING_DATA_NEO4J.value


class SourceFramework(str, Enum):
    """Supported source frameworks for translating queries/schemas (relational C#/.NET)."""

    DOTNET_EFCORE = FrameworkEnum.DOTNET_EFCORE.value
    DOTNET_DAPPER = FrameworkEnum.DOTNET_DAPPER.value
    DOTNET_NHIBERNATE = FrameworkEnum.DOTNET_NHIBERNATE.value


class TargetFramework(str, Enum):
    """Supported target database frameworks for migration (Java MongoDB/Neo4j)."""

    JAVA_SPRING_DATA_MONGODB = FrameworkEnum.JAVA_SPRING_DATA_MONGODB.value
    JAVA_SPRING_DATA_NEO4J = FrameworkEnum.JAVA_SPRING_DATA_NEO4J.value


class SandboxType(str, Enum):
    """Supported Daytona validation sandbox types representing isolated runtime environments."""

    DOTNET_10_SANDBOX = "dotnet-10-sandbox"
    JAVA_25_SANDBOX = "java-25-sandbox"


class LanguageType(str, Enum):
    """Supported programming language types for code generation and validation."""

    CSHARP = "csharp"
    JAVA = "java"


class LanggraphCustomEventKeys(str, Enum):
    """Keys representing custom execution events sent to the LangGraph client for UI streaming."""

    DOTNET_SANDBOX_SNAPSHOT_CREATION = "dotnet_sandbox_snapshot_creation"
    JAVA_SANDBOX_SNAPSHOT_CREATION = "java_sandbox_snapshot_creation"
    DOTNET_SANDBOX_COMMAND_EXECUTION_STDOUT = "dotnet_sandbox_command_execution_stdout"
    DOTNET_SANDBOX_COMMAND_EXECUTION_STDERR = "dotnet_sandbox_command_execution_stderr"
    JAVA_SANDBOX_COMMAND_EXECUTION_STDOUT = "java_sandbox_command_execution_stdout"
    JAVA_SANDBOX_COMMAND_EXECUTION_STDERR = "java_sandbox_command_execution_stderr"
    UNKNOWN = "unknown"


FRAMEWORK_TO_NORMALIZED_NAME = {
    FrameworkEnum.DOTNET_EFCORE: "dotnet_efcore",
    FrameworkEnum.DOTNET_DAPPER: "dotnet_dapper",
    FrameworkEnum.DOTNET_NHIBERNATE: "dotnet_nhibernate",
    FrameworkEnum.JAVA_SPRING_DATA_MONGODB: "java_spring_data_mongodb",
    FrameworkEnum.JAVA_SPRING_DATA_NEO4J: "java_spring_data_neo4j",
}
"""Mapping used to normalize enum representations into simple snake_case strings
suitable for LLM prompt injections and JSON keys."""

NORMALIZED_FRAMEWORK_TO_FRAMEWORK = {
    "dotnet_efcore": FrameworkEnum.DOTNET_EFCORE,
    "dotnet_dapper": FrameworkEnum.DOTNET_DAPPER,
    "dotnet_nhibernate": FrameworkEnum.DOTNET_NHIBERNATE,
    "java_spring_data_mongodb": FrameworkEnum.JAVA_SPRING_DATA_MONGODB,
    "java_spring_data_neo4j": FrameworkEnum.JAVA_SPRING_DATA_NEO4J,
}
"""Mapping from normalized snake_case strings back to the original FrameworkEnum representations."""

FRAMEWORK_TO_LANGUAGE_TYPE = {
    FrameworkEnum.DOTNET_EFCORE: LanguageType.CSHARP,
    FrameworkEnum.DOTNET_DAPPER: LanguageType.CSHARP,
    FrameworkEnum.DOTNET_NHIBERNATE: LanguageType.CSHARP,
    FrameworkEnum.JAVA_SPRING_DATA_MONGODB: LanguageType.JAVA,
    FrameworkEnum.JAVA_SPRING_DATA_NEO4J: LanguageType.JAVA,
}
"""Mapping of each framework type to its corresponding programming language type for code generation and validation logic."""

FRAMEWORK_TO_SNIPPET_FILES: dict[
    FrameworkEnum, 
    dict[Literal["schema_validation", "schema_validation_entry_type_name", "query_validation", "query_validation_entry_type_name"], str]
] = {
    FrameworkEnum.DOTNET_EFCORE: {
        "schema_validation": "EFCoreSchemaValidationEntrypoint.cs",
        "schema_validation_entry_type_name": "EFCoreSchemaValidationEntrypoint",
        "query_validation": "EFCoreQueryEntrypoint.cs",
        "query_validation_entry_type_name": "EFCoreQueryEntrypoint",
    },
    FrameworkEnum.DOTNET_DAPPER: {
        "schema_validation": "DapperSchemaValidationEntrypoint.cs",
        "schema_validation_entry_type_name": "DapperSchemaValidationEntrypoint",
        "query_validation": "DapperQueryEntrypoint.cs",
        "query_validation_entry_type_name": "DapperQueryEntrypoint",
    },
    FrameworkEnum.DOTNET_NHIBERNATE: {
        "schema_validation": "NHibernateSchemaValidationEntrypoint.cs",
        "schema_validation_entry_type_name": "NHibernateSchemaValidationEntrypoint",
        "query_validation": "NHibernateQueryEntrypoint.cs",
        "query_validation_entry_type_name": "NHibernateQueryEntrypoint",
    },
    FrameworkEnum.JAVA_SPRING_DATA_MONGODB: {
        "schema_validation": "MongoSchemaValidationEntrypoint.java",
        "schema_validation_entry_type_name": "MongoSchemaValidationEntrypoint",
        "query_validation": "MongoQueryEntrypoint.java",
        "query_validation_entry_type_name": "MongoQueryEntrypoint",
    },
    FrameworkEnum.JAVA_SPRING_DATA_NEO4J: {
        "schema_validation": "Neo4jSchemaValidationEntrypoint.java",
        "schema_validation_entry_type_name": "Neo4jSchemaValidationEntrypoint",
        "query_validation": "Neo4jQueryEntrypoint.java",
        "query_validation_entry_type_name": "Neo4jQueryEntrypoint",
    },
}
"""Mapping of framework types to their corresponding schema and query snippet file names."""

FRAMEWORK_TO_CONFIG_FILES = {
    FrameworkEnum.DOTNET_EFCORE: "efcore-sandbox.csproj",
    FrameworkEnum.DOTNET_DAPPER: "dapper-sandbox.csproj",
    FrameworkEnum.DOTNET_NHIBERNATE: "nhibernate-sandbox.csproj",
    FrameworkEnum.JAVA_SPRING_DATA_MONGODB: "mongo-pom.xml",
    FrameworkEnum.JAVA_SPRING_DATA_NEO4J: "neo4j-pom.xml",
}
"""Mapping of framework types to their respective project configuration file names (e.g., .csproj, pom.xml)."""

MODEL_PROFILE_CACHE: dict[str, dict] = {}
"""A global, static cache used to store LLM ModelProfile capabilities (like max token counts)
to avoid repetitively querying the AI Gateway or specific LLM endpoints."""

MAX_EXTRACTION_LOOPS = 3
"""The maximum number of retry loops the graph will allow when the LLM fails to 
correctly extract schema or query code from the user's initial prompt."""

MAX_TRANSLATION_LOOPS = 3
"""The maximum number of retry loops the graph will allow for compiling/validating
the translated code in the sandboxes before finally failing."""

MAX_STRUCTURED_OUTPUT_RETRIES = 3
"""The maximum number of times a single structured-output generation will be retried in-place
(feeding the validation error back to the model) when the provider-native response fails schema
or `@model_validator` checks, before escalating to model fallback. See
`StructuredOutputRetryMiddleware`."""


GENERAL_SANDBOX_README = """# Universal Object Mapping - Sandbox Environment

Welcome to the Sandbox Environment! 
This directory (`/sandbox`) contains dynamically generated projects created by the AI assistant during the database schema and query translation process.

## Navigation
Each validation execution is isolated in its own folder named with the pattern: `sandbox-<thread_title_or_id>-<timestamp>`.
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
    - Neo4j Browser (this is only default URI, check your own configuration if needed): `{neo4j_browser_uri}`

## Documentation
- [Daytona Documentation](https://www.daytona.io/docs)
- [Universal Object Mapping Overview](https://github.com/corovcam/Universal-Object-Mapping)

## [Open Universal Object Mapping Assistant in your IDE]({frontend_url})
"""
"""The generic README file injected into all generated Validation Sandboxes.
It provides connection strings and URLs dynamically substituted via str.format()."""

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

## [Open Universal Object Mapping Assistant in your IDE]({frontend_url})
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

## [Open Universal Object Mapping Assistant in your IDE]({frontend_url})
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

## [Open Universal Object Mapping Assistant in your IDE]({frontend_url})
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

## [Open Universal Object Mapping Assistant in your IDE]({frontend_url})
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

## [Open Universal Object Mapping Assistant in your IDE]({frontend_url})
"""

DOTNET_VSCODE_EXTENSIONS = """{
  "recommendations": [
    "ms-dotnettools.csdevkit",
    "ms-dotnettools.csharp",
    "ms-dotnettools.vscode-dotnet-runtime",
    "jetbrains.resharper-code",
    "mtxr.sqltools",
    "mtxr.sqltools-driver-mssql"
  ]
}"""

JAVA_VSCODE_EXTENSIONS = """{
  "recommendations": [
    "vscjava.vscode-java-pack",
    "vmware.vscode-boot-dev-pack",
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
