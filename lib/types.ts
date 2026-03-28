export type FrameworkType =
  | "ms_sql_native"
  | "csharp_efcore_linq"
  | "csharp_dapper"
  | "csharp_nhibernate_hql"
  | "java_spring_data_jpa"
  | "java_spring_data_mongodb"
  | "java_spring_data_neo4j";

export interface Framework {
  id: FrameworkType;
  name: string;
  language: "csharp" | "java" | "sql";
  description: string;
  color: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: Date;
  sourceFramework?: FrameworkType;
  targetFramework?: FrameworkType;
  sourceCode?: string;
  translatedCode?: string;
  isStreaming?: boolean;
}

export interface Conversation {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt: Date;
  updatedAt: Date;
}

export type PipelineStep =
  | "idle"
  | "extract_input"
  | "schema_inspection"
  | "council_of_models"
  | "translation_agent"
  | "complete"
  | "error";

export interface PipelineState {
  currentStep: PipelineStep;
  completedSteps: PipelineStep[];
  stepDetails: Record<string, string>;
  error?: string;
}

export interface ToolCall {
  id: string;
  name: string;
  args: Record<string, unknown>;
  status: "pending" | "running" | "completed" | "error";
  result?: unknown;
}

export interface StreamState {
  messages: ChatMessage[];
  isStreaming: boolean;
  pipeline: PipelineState;
  activeTools: ToolCall[];
  sourceCode?: string;
  schemaTranslatedCode?: string;
  queryTranslatedCode?: string;
}
