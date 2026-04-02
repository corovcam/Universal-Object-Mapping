# Universal Object Mapping (UOM)

[![ORMConvertor tests](https://github.com/corovcam/Universal-Object-Mapping/actions/workflows/ormconvertor-tests.yml/badge.svg)](https://github.com/corovcam/Universal-Object-Mapping/actions/workflows/ormconvertor-tests.yml)

Universal Object Mapping (UOM) is a research project focused on automating the translation and optimization of database schemas and queries across diverse Object-Relational/Document/Graph Mapping (ORM/ODM/OGM) frameworks. 

The project leverages an **LLM-driven iterative translation architecture** to bridge the gap between relational, document, and graph databases. It extends the earlier work of ORMorpher, replacing its heuristic rule engine with an LLM-driven pipeline.

## Key Features

- **Automated Translation**: Migrate .NET (EF Core, Dapper, NHibernate) entity mappings and LINQ queries to Java Spring Data (MongoDB, Neo4j).
- **LLM Orchestration**: Uses a ReAct agent powered by LangGraph for autonomous code generation, validation, and correction with tool calls.
- **Isolated Benchmarking**: Measures ORM overhead (mapping/translation) independently of database latency via a specialized mocking layer.
- **Intelligent Advisor**: Suggests optimal ORM/ODM configurations using Integer Linear Programming (ILP) based on benchmark data.
- **Multi-Database Support**: MS SQL Server (relational), MongoDB (document), and Neo4j (graph) integration.
- **ETL Pipelines**: Pre-configured ETL processes to map and load data from relational schemas to NoSQL targets.

## Architecture

The system is built as a set of modular microservices and tools coordinated by a Python-based orchestrator, managed via Docker Compose.

- **Orchestrator (`services/orchestrator`)**: Python/LangGraph service driving the translation workflow using a "Council of Models" and a ReAct agent.
- **Service Layer**: 
  - **[.NET Service](services/dotnet-service)**: Compilation and validation for C# (EF Core, NHibernate, Dapper).
  - **[Java Service](services/java-services)**: Compilation and validation for Java (Spring Data MongoDB, Spring Data Neo4j).
- **[ORMConvertor](ORMConvertor/)**: The original .NET-based tool providing the web UI, heuristic reference logic, and the ILP-based Advisor.
- **[Benchmarks](benchmarks/)**: A comprehensive suite for measuring ORM performance.

Detailed architectural documentation can be found in [**notes/architecture.md**](notes/architecture.md).

## Getting Started

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) or Docker Engine with Compose
- [.NET 8 SDK](https://dotnet.microsoft.com/download/dotnet/8.0) (or 10.0)
- [Python 3.11+](https://www.python.org/) (managed with [uv](https://astral.sh/uv/))
- [OpenJDK 25+](https://jdk.java.net/25/) and [Maven](https://maven.apache.org/download.cgi) (for Java services)
- [Node.js 24](https://nodejs.org/en/download/) (for Frontend)
  
### Development Setup

1. **Spin up the stack**:
   ```bash
   docker compose up -d --build
   ```
2. **Configure Environment**:
   Copy `.env.example` to `.env` and configure your LLM provider keys (Ollama or OpenAI-compatible like E-Infra vLLM).

3. **Explore Documentation**:
   - [Project Specification (LaTeX)](notes/project-specification/specification-llm-advisor.tex)
   - [C4 Architecture Diagrams](notes/architecture)

## Acknowledgements
Part of the `ORMConvertor` and the `benchmarks` source code, including some workflows and diagrams, were developed by Milan Abrahám as part of his Master thesis titled _Framework-Agnostic Query Adaptation: Ensuring SQL Compatibility Across .NET Database Frameworks_. The thesis is available at http://hdl.handle.net/20.500.11956/203083, and the source code is available at https://github.com/milan252525/orm-convertor.