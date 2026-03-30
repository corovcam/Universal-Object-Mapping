# Universal Object Mapping (UOM) Architecture

## Overview

Universal Object Mapping (UOM) is an advanced translation and optimization system designed to migrate database schemas (DDL/Code-First mappings) and queries across different programming languages and Object-Relational/Document/Graph Mapping (ORM/ODM/OGM) frameworks.

The system replaces traditional heuristic-based parsing with a modern **LLM-based iterative translation architecture**, utilizing a "Council of Models" and a ReAct agent for autonomous validation and correction.

---

## Core Components

### 1. Orchestrator (`services/orchestrator`)
The brain of the system, implemented as a Python service using **LangGraph**.
- **Council of Models**: Parallel brainstorming using diverse LLMs:
  - **Local**: Ollama (e.g., `qwen3-coder:30b`, `gpt-oss`).
  - **Remote**: E-infra (vLLM OpenAI-compatible API).
- **Translation Agent (ReAct)**: An autonomous agent that takes the brainstormed strategies and iteratively performs:
  - **Translation**: Generating target schema/queries.
  - **Validation**: Calling external tools (Serena MCP, .NET/Java services) to check for errors.
  - **Correction**: Fixing compilation or syntax errors based on tool feedback.

### 2. Service Layer
Provides the environment for compilation, validation, and benchmarking.
- **.NET Service (`services/dotnet-service`)**:
  - Compiles and validates C# (EF Core, Dapper, NHibernate).
  - Executes benchmarks using **BenchmarkDotNet**.
- **Java Service (`services/java-services`)**:
  - Compiles and validates Java (Spring Data JPA, MongoDB, Neo4j).
  - Handles Spring-specific validation and benchmarking.

### 3. Model Context Protocol (MCP) Integration
UOM leverages the MCP standard for seamless tool integration:
- **Serena MCP**: Performs semantic code analysis (AST manipulation, symbol tracking) without full microservice isolation.
- **Context7 / Database Toolbox MCP**: Connects directly to databases (MSSQL, MongoDB, Neo4j) to extract real schemas for LLM context and to evaluate query plans.

### 4. Database Layer
Supports a hybrid polyglot environment:
- **Relational**: MS SQL Server (source), Postgres (orchestrator state/pgvector).
- **NoSQL**: MongoDB, Neo4j.
- **Migration**: Uses MongoDB Relational Migrator and Neo4j ETL tools for initial data movement.

---

## Data Flow (Updated LLM Workflow)

1.  **Input Extraction**: The orchestrator extracts source code, target frameworks, and source/destination database types from the user request.
2.  **Schema Context**: The **Database Toolbox MCP** extracts the current database schema (DDL) to provide ground truth to the LLMs.
3.  **Brainstorming**: Multiple LLMs generate alternative translation strategies (e.g., how to map a SQL `JOIN` to a Cypher `MATCH`).
4.  **Iterative Fix Loop**:
    -   The ReAct agent produces an initial translation.
    -   It calls the `.NET` or `Java` validation tool.
    -   If errors occur (e.g., missing imports, syntax errors), the agent uses the error messages to refine the code.
5.  **Validation & Benchmarking**: Once valid, the code is benchmarked to measure ORM overhead (query translation, object mapping) using the isolated mocking mechanism.
6.  **Optimization**: The ILP-based **Advisor** (from the original ORMConvertor project) suggests the optimal configuration based on benchmark results.

---

## Legacy Integration
The original **ORMConvertor** project remains part of the repository, serving as:
-   **Frontend Interface**: The web UI and API endpoints for user interaction. LLM orchestrator UI is integrated here using LangChain's React `assistant-ui` components.
-   **Reference Implementation**: Ground truth for heuristic-based parsing.
-   **Context Provider**: Roslyn-based parsers extract structured metadata to augment LLM prompts.
-   **Advisor Logic**: The native C-based ILP solver is still used for the final optimization suggestion.
