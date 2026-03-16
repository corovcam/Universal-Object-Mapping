# Universal Object Mapping (UOM) Project Specification

## Stack

- Ollama self-hosted or robust reasoning LLM
  - Available models: gpt-oss:latest, qwen3-coder:30b, mistral-small3.2:latest
  - Embeddings: qwen3-embedding:latest
- vLLM OpenAI-compatible API server:
  - E-infra Chat AI service API: https://llm.ai.e-infra.cz/v1/
  - Docs: https://docs.cerit.io/en/docs/ai-as-a-service/ai-api
- Setup bash scripts setting up databases (MS SQL Server, MongoDB, Neo4J), setting up and calling ETL pipelines (see https://github.com/corovcam/Query-Languages-Analysis-Thesis)
- docker compose microservices - kubernetes? helm chat?
  - LangGraph API Server - LLM orchestrator
    - LangGraph (LLM orchestrator/translator) - Iterative LLM workflow
    - Communicates with serena MCP server (or dotnet/java CLI tools as fallback) for compilation and semantic checks. Replaces dedicated microservices.
    - Reference: See `orchestrator-architecture.md` for full graph and integration details.
      - code first→migrate:
        - LLM context: classes, mapping-files (relmig, neo4j-json), custom prompts, etc.
      - reverse-engineered:
        - LLM context: database schema extracted from DB, custom prompts, etc.
    - Getting output from these services, parsing possible errors → iterating on that
    - For queries, user writes in one query language or orm/odm/ogm-language and translates to the selected one
      - queries are sent to respective services, compiled, and query plan, query output schema (data types, length,…) and possibly output rows/documents are streamed back to the orchestrator (all of them or subset?)
      - orchestrator agent iteratively modifies queries up to certain timeout, retries
    - Valid queries are benchmarked in respective services (like BenchmarkDotNet in .NET) → output to orchestrator
  - .NET Compilation via Serena MCP (incorporating a C# language server) or fallback to `dotnet` CLI for compilation, benchmarking.
  - Java Compilation via Serena MCP (incorporating a Java language server) or fallback to Java CLI.
  - Database Toolbox MCP (googleapis/genai-toolbox) used via Context7 documentation for database communication (extracting schemas, executing queries).
  - MS SQL Server
  - MongoDB
  - MongoDB Relational Migrator
  - Neo4j + Neo4j ETL Tool GUI (to extract relational-graph mapping in json) + Neo4j ETL Tool CLI with [`neo4j-admin database import`](https://neo4j.com/docs/operations-manual/current/import/)

## Old Flow

1. Configuration scripts are run
   1. Databases setup
   2. ETL tools - similar processes as my https://github.com/corovcam/Query-Languages-Analysis-Thesis
2. Using ORMConvertor, user input ORM schema mapping in either EFCore, NHibernate, or Dapper that works with already instantiated databases.
   1. Possibly I could just build a CLI tool similar to ORMorpher, because I don’t really need to extend the UI since its a developer tool.
3. User input Queries he want translated and benchmarked in the previously selected ORM
4. ORMConvertor is run - ORM schema translation, query translation, advisor benchmarking, advisor ILP optimization, results table shown

## Updated Flow

5. Instead of ORMConvertor heuristic-based schema+query transformation, LLM-based iterative translation is used (described also in Stack section)
6. Relational ORM schema (which ORMs?) and queries (+ extracted SQL query strings) are serialized and sent to LLM Translator/Orchestrator via REST API
7. Translator also extracts relational DDL schema using database connector for context
8. Prompt are engineered and sent to create Spring Data Neo4j and Spring Data MongoDB schemas. Uses E-infra models for diversity (Council of Models)
9. Translator waits for response from the compilation tools (Serena MCP or CLI)
10. If errors are encountered, fix them iteratively. If beyond max tries, trigger Human-in-the-Loop.
11. Queries are processed similarly - iterative process, but with Query Plans, Output Schema, and possibly whole query execution (challenges with results data model differences and amount of data)
12. Valid queries are benchmarked using similar approach as ORMConvertor
13. Lastly, results are shown either in extended ORMorpher UI (or some CLI)
