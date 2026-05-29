export interface QueryValidationResults {
  count?: number;
  firstSample?: any;
  lastSample?: any;
  error?: string | null;
  sqlString?: string;
  cypher?: string;
  mongoQuery?: string;
  mongoAggregation?: string;
}

export interface QueryEquivalenceDeepDiff {
  deepdiff_mapping?: any;
  count_diff?: any;
  first_sample_diff?: any;
  last_sample_diff?: any;
  error?: string | null;
}

export interface UomConfig {
  ollamaHost?: string;
  model?: string;
  openaiApiUrl?: string;
  openaiApiKey?: string;
  mssqlConnectionString?: string;
  mongodbUri?: string;
  neo4jUri?: string;
  neo4jPassword?: string;
  daytonaTimeout?: number;
  dbToolboxUri?: string;
  mongodbMcpUri?: string;
}

export interface BackendState {
  messages?: any[];
  source_schema_code?: string | null;
  source_query_code?: string | null;
  translation_type?: string | null;
  source_target?: string | null;
  source_target_version?: string | null;
  destination_target?: string | null;
  destination_target_version?: string | null;
  translated_schema_code?: string | null;
  translated_query_code?: string | null;
  source_validation_schema_code?: string | null;
  source_validation_harness_code?: string | null;
  target_validation_schema_code?: string | null;
  target_validation_harness_code?: string | null;
  explanation_message?: string | null;
  is_last_step?: boolean;
  source_validation_entry_type_name?: string | null;
  target_validation_entry_type_name?: string | null;
  source_query_validation_results?: QueryValidationResults | null;
  target_query_validation_results?: QueryValidationResults | null;
  query_equivalence_deep_diffs?: Record<string, QueryEquivalenceDeepDiff> | null;
  schema_context?: string;
  translation_messages?: any[];
  extraction_loop_count?: number;
  translation_loop_count?: number;
}

export enum AvailableModel {
  // Ollama Models
  OLLAMA_QWEN3_6_27B = "ollama/qwen3.6:27b",
  OLLAMA_GPT_OSS = "ollama/gpt-oss:latest",
  OLLAMA_QWEN3_CODER_30B = "ollama/qwen3-coder:30b",
  OLLAMA_MISTRAL_SMALL_3_2 = "ollama/mistral-small3.2:latest",

  // EINFRA Models (OpenAI compatible)
  EINFRA_MINI = "einfra/mini",
  EINFRA_CODER = "einfra/coder",
  EINFRA_AGENTIC = "einfra/agentic",
  EINFRA_THINKER = "einfra/thinker",
  EINFRA_QWEN3_CODER = "einfra/qwen3-coder",
  EINFRA_QWEN3_CODER_30B = "einfra/qwen3-coder-30b",
  EINFRA_GPT_OSS_120B = "einfra/gpt-oss-120b",
  EINFRA_LLAMA_4_SCOUT_17B = "einfra/llama-4-scout-17b-16e-instruct",
  EINFRA_DEEPSEEK_V4_PRO = "einfra/deepseek-v4-pro",
  EINFRA_DEEPSEEK_V4_PRO_THINKING = "einfra/deepseek-v4-pro-thinking",
  EINFRA_MISTRAL_LARGE = "einfra/mistral-large",
  EINFRA_KIMI_K2_5 = "einfra/kimi-k2.5",
  EINFRA_KIMI_K2_6 = "einfra/kimi-k2.6",
  EINFRA_QWEN3_5 = "einfra/qwen3.5",
  EINFRA_QWEN3_CODER_NEXT = "einfra/qwen3-coder-next",
  EINFRA_QWEN3_5_122B = "einfra/qwen3.5-122b",
  EINFRA_GLM_4_7 = "einfra/glm-4.7",
  EINFRA_GLM_5 = "einfra/glm-5",
  EINFRA_GLM_5_1 = "einfra/glm-5.1"
}

export enum FrameworkType {
  /** Supported Object-Relational/Graph/Document Mapping targets. */
  DOTNET_EFCORE = "dotnet_efcore",
  DOTNET_NHIBERNATE = "dotnet_nhibernate",
  DOTNET_DAPPER = "dotnet_dapper",
  JAVA_SPRING_DATA_MONGODB = "java_spring_data_mongodb",
  JAVA_SPRING_DATA_NEO4J = "java_spring_data_neo4j"
}

export enum LanguageType {
  DOTNET = "dotnet",
  JAVA = "java"
}

export enum TranslationType {
  SCHEMA = "schema",
  QUERY = "query",
  BOTH = "both"
}

export enum SandboxType {
  DOTNET_10_SANDBOX = "dotnet-10-sandbox",
  JAVA_25_SANDBOX = "java-25-sandbox"
}

export interface FrameworkInfoType {
  name: string;
  language: LanguageType;
  sandbox: SandboxType;
  is_source: boolean;
  is_target: boolean;
}

export enum LanggraphCustomEventKeys {
  DOTNET_SANDBOX_SNAPSHOT_CREATION = "dotnet_sandbox_snapshot_creation",
  JAVA_SANDBOX_SNAPSHOT_CREATION = "java_sandbox_snapshot_creation",
  DOTNET_SANDBOX_COMMAND_EXECUTION_STDOUT = "dotnet_sandbox_command_execution_stdout",
  DOTNET_SANDBOX_COMMAND_EXECUTION_STDERR = "dotnet_sandbox_command_execution_stderr",
  JAVA_SANDBOX_COMMAND_EXECUTION_STDOUT = "java_sandbox_command_execution_stdout",
  JAVA_SANDBOX_COMMAND_EXECUTION_STDERR = "java_sandbox_command_execution_stderr",
  UNKNOWN = "unknown"
}
