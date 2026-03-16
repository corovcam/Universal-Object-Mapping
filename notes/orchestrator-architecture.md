# LangGraph Orchestrator Architecture

## Overview
The Orchestrator Service is the core intelligence component of the Universal Object Mapping (UOM) project. It utilizes an iterative LangGraph workflow to translate and validate Database Schemas (DDL/Code-First mappings) and Queries across different languages and frameworks (.NET, Java, MS SQL, Neo4j, MongoDB).

## Core Architecture Stack
- **LangGraph API Server**: Provides the execution environment, state management, and API endpoints for the orchestrator graph.
- **LLM Providers**:
  - Local: Ollama (`gpt-oss`, `qwen3`, `mistral`)
  - Remote: E-infra OpenAI-compatible API
  - Note: Models are configurable at runtime via LangGraph configuration parameters.
- **Tools / Capabilities (Model Context Protocol)**:
  - **Database Toolbox MCP** (`googleapis/genai-toolbox`): Extracts schemas, connects to databases, and evaluates queries directly.
  - **Serena MCP**: Semantic code analysis and manipulation agent. Wraps standard Language Servers (C#, Java) to analyze ASTs, validate syntax, and detect symbol references without requiring fully isolated microservices.
  - **CLI Fallbacks**: Direct host invocation of `dotnet`, `java`, or `mvn` when deeper compilation or test running is necessary.

## Graph Design

The orchestrator operates over a [State](file:///c:/Users/marti/Documents/Uni/DP/Universal-Object-Mapping/services/orchestrator/src/react_agent/state.py#41-61) containing:
- Initial inputs: `source_code` (e.g. C# EFCore), `source_target` (e.g., MS SQL), `destination_target` (e.g. Java Spring Data MongoDB)
- Iteration metadata: `error_count`, `max_retries`, `council_responses`
- Intermediate outputs: `translated_code`, `schema_validation_result`, `query_validation_result`
- Flags: `HIL_requested` (Human-in-the-loop)

### Node Workflow

1. `council_of_models`:
   - Triggers parallel LLM generation from diverse models (e.g. 1x Ollama, 2x E-infra).
   - Compares the generated strategies and picks the best one for schema/query generation.
2. `cot_translation`:
   - Uses the selected strategy to perform Chain-of-Thought translation. Output is drafted in `translated_code`.
3. `validation_stage`:
   - Evaluates the syntactical and semantic validity of the draft. Also queries the MS SQL for relational schema DDL for additional context.
   - For Java (Spring Data Neo4j/MongoDB, etc.), calls `java_validator` (Serena MCP / CLI).
   - For .NET (EFCore, Dapper, NHibernate, etc.), calls `dotnet_validator` (Serena MCP / CLI).
4. `database_sync_stage`:
   - Uses Database Toolbox MCP to verify runtime DB constraints, fetch expected query result shapes, and validate cross-language query equivalency.
5. `evaluate_end_condition`:
   - Conditional router. If no errors (validation passes), transition to `__end__`.
   - If errors found, increment `error_count`, transition back to `cot_translation` with error feedback.
   - If `error_count >= max_retries`, transition to `human_intervention`.
6. `human_intervention`:
   - Triggers LangGraph standard `interrupt()`.
   - Waits for human review. Once human provides an override/fix, state is updated and the graph resumes validation.

## Modularity Considerations
Both the logic handling tools (`java_validator`, `dotnet_validator`) and the LLM configurations are designed to be explicitly modular. Rather than hard-coding EFCore, the `.NET` tool detects or requests the ORM type from context and adjusts its validation commands (e.g., MSBuild flags, dependent package checks) accordingly.
