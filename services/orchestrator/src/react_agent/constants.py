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
