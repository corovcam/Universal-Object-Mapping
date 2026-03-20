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

The orchestrator operates over a [State](file:///c:/Users/marti/Documents/Uni/DP/Universal-Object-Mapping/services/orchestrator/src/react_agent/state.py) containing:

- Initial inputs: `source_code` (e.g. C# EFCore), `source_target` (e.g., MS SQL), `destination_target` (e.g. Java Spring Data MongoDB)
- Iteration metadata: `council_responses`
- Messages: Full conversation history, including tool calls and outputs.

### Node Workflow

The graph follows a linear sequence, but the intelligence is concentrated in a **ReAct Agent** that performs internal iteration.

1. `extract_input`:
   - Analyzes recent messages to extract `source_code`, `source_target`, and `destination_target` using structured LLM output (`ExtractionOutput`).
2. `council_of_models`:
   - Triggers parallel LLM generation from diverse models (e.g. 1x Ollama Qwen3-Coder, 1x E-infra GLM-4).
   - Generates multiple translation strategies stored in `council_responses`.
3. `translation_agent`:
   - A **ReAct Agent** implemented using `create_agent`. It takes the brainstormed strategies as part of its prompt.
   - It performs the translation and iteratively uses tools to validate and fix the code.
   - **Tools available**:
     - `validate_java_code`: Compiles/validates Java Spring Data code.
     - `validate_dotnet_code`: Compiles/validates .NET (EF Core, Dapper, etc.) code.
     - `search`: Web search (Tavily) for documentation and examples.
   - The agent continues its tool-use loop until it produces a valid `TranslationOutput` or hits internal retry limits.
4. `__end__`:
   - The final state contains the full sequence of messages, including the validated translation.

## Modularity Considerations

Both the logic handling tools (`java_validator`, `dotnet_validator`) and the LLM configurations are designed to be explicitly modular. Rather than hard-coding EFCore, the `.NET` tool detects or requests the ORM type from context and adjusts its validation commands (e.g., MSBuild flags, dependent package checks) accordingly.
