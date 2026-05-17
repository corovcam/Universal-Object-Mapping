// Types for the LLM Advisor Chat Plugin

export type MessageRole = "user" | "assistant" | "system";

export type AgentStatus = 
  | "fetching_docs" 
  | "validating_java" 
  | "validating_dotnet"
  | "generating"
  | "thinking"
  | "complete"
  | "error";

export interface AgentActivity {
  id: string;
  status: AgentStatus;
  label: string;
  startTime: number;
  endTime?: number;
}

export interface CodeBlock {
  language: string;
  code: string;
  filename?: string;
}

export interface TraceStep {
  id: string;
  node: string;
  status: "pending" | "running" | "complete" | "error";
  startTime?: number;
  endTime?: number;
  details?: string;
}

export interface LangGraphTrace {
  id: string;
  steps: TraceStep[];
  isExpanded: boolean;
}

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: number;
  activities?: AgentActivity[];
  codeBlocks?: CodeBlock[];
  trace?: LangGraphTrace;
  isStreaming?: boolean;
}

export interface ConversationHistoryItem {
  id: string;
  title: string;
  migrationBadge?: {
    source: string;
    target: string;
  };
  timestamp: number;
  preview?: string;
}

export interface MigrationConfig {
  translationType: "schema" | "query" | "both";
  sourceFramework: string;
  sourceVersion: string;
  destinationFramework: string;
  destinationVersion: string;
  sourceSchemaCode?: string;
  sourceQueryCode?: string;
}

export type Framework = {
  id: string;
  name: string;
  language: ".NET" | "Java";
  type: "ORM" | "ODM" | "OGM";
};

export const SOURCE_FRAMEWORKS: Framework[] = [
  { id: "efcore", name: "Entity Framework Core", language: ".NET", type: "ORM" },
  { id: "nhibernate", name: "NHibernate", language: ".NET", type: "ORM" },
  { id: "dapper", name: "Dapper", language: ".NET", type: "ORM" },
];

export const TARGET_FRAMEWORKS: Framework[] = [
  { id: "spring-mongodb", name: "Spring Data MongoDB", language: "Java", type: "ODM" },
  { id: "spring-neo4j", name: "Spring Data Neo4j", language: "Java", type: "OGM" },
];

export type ThemeMode = "light" | "dark";

export interface ChatWidgetState {
  isOpen: boolean;
  isMaximized: boolean;
  theme: ThemeMode;
  messages: ChatMessage[];
  history: ConversationHistoryItem[];
  currentConfig: MigrationConfig;
  isConfigExpanded: boolean;
}
