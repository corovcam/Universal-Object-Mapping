# Universal Object Mapping (UOM)

> [!WARNING]
> Work in progress.

[![ORMConvertor tests](https://github.com/corovcam/Universal-Object-Mapping/actions/workflows/ormconvertor-tests.yml/badge.svg)](https://github.com/corovcam/Universal-Object-Mapping/actions/workflows/ormconvertor-tests.yml)

Universal Object Mapping (UOM) is a research project focused on automating the translation and optimization of database schemas and queries across diverse Object-Relational/Document/Graph Mapping (ORM/ODM/OGM) frameworks. 

The project leverages an **LLM-driven iterative translation architecture** to bridge the gap between relational, document, and graph databases.

## Key Features

- **Automated Translation**: Migrate .NET (EF Core, Dapper, NHibernate) entity mappings and LINQ queries to Java Spring Data (MongoDB, Neo4j).
- **LLM Orchestration**: Uses a ReAct agent for autonomous code correction with tool calls.
- **Isolated Benchmarking**: Measures ORM overhead (mapping/translation) independently of database latency via a specialized mocking layer.
- **Intelligent Advisor**: Suggests optimal ORM/ODM configurations using Integer Linear Programming (ILP) based on benchmark data.
- **Multi-Database Support**: MSSQL, MongoDB, and Neo4j integration.

## Architecture

The system is built as a set of modular microservices and tools coordinated by a Python-based orchestrator.

- **Orchestrator (`services/orchestrator`)**: Python/LangGraph service driving the translation workflow.
- **Service Layer**: 
  - **[.NET Service](services/dotnet-service)**: Compilation and validation for C#.
  - **[Java Service](services/java-services)**: Compilation and validation for Java.
- **[ORMConvertor](ORMConvertor/)**: The original .NET-based tool providing input frontend, heuristic reference logic and the ILP-based Advisor.
- **[Benchmarks](benchmarks/)**: A comprehensive suite for measuring ORM performance.

Detailed architectural documentation can be found in [**notes/architecture.md**](notes/architecture.md).

## Getting Started

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [.NET 8 SDK](https://dotnet.microsoft.com/download/dotnet/8.0)
- [Python 3.11+](https://www.python.org/) (managed with [uv](https://astral.sh/uv/))
  - Tested with Python 3.14
  
### Development Environment

- Ideally Linux (e.g. Ubuntu 24.04+) or WSL2 on Windows for best compatibility with Python tools, and WSL2 (or Windows) for .NET development.
- [.NET 10 SDK](https://dotnet.microsoft.com/download/dotnet/10.0) (for .NET services)
- [OpenJDK 25+](https://jdk.java.net/25/) (for Java services)
- [Maven](https://maven.apache.org/download.cgi) (for Java services)
- [Node.js 24](https://nodejs.org/en/download/)

### Development Setup

1. **Spin up the stack**:
   ```bash
   docker compose up -d
   ```
2. **Configure Environment**:
   Copy `.env.example` to `.env` and configure your LLM provider keys (Ollama or OpenAI-compatible).

3. **Explore Documentation**:
   - [Architecture](notes/architecture.md)
   - [Roadmap](notes/future_specification.md)
   - [Orchestrator Architecture](notes/orchestrator-architecture.md)

## Acknowledgements
Part of the `ORMConvertor` and the `benchmarks` source code, including some workflows and diagrams, were developed by Milan Abrahám as part of his Master thesis titled _Framework-Agnostic Query Adaptation: Ensuring SQL Compatibility Across .NET Database Frameworks_. The thesis is available at http://hdl.handle.net/20.500.11956/203083, and the source code is available at https://github.com/milan252525/orm-convertor.
