# Universal Object Mapping (UOM) Project Specification

## Stack

- Ollama self-hosted or robust reasoning LLM
- Setup bash scripts setting up databases (MS SQL Server, MongoDB, Neo4J), setting up and calling ETL pipelines (see https://github.com/corovcam/Query-Languages-Analysis-Thesis)
- docker compose microservices - kubernetes? helm chat?
  - Python FastAPI - LLM orchestrator - rest api (or grpc) calling with translated source codes
    - LangGraph (or LangChain) (LLM orchestrator/translator) - Iterative LLM workflow
    - Calling .NET and Java services, sending there schema and query source codes in parallel - schema reverse-engineered from DB, or code-first→migrate
      - code first→migrate:
        - LLM context: classes, mapping-files (relmig, neo4j-json), custom prompts, etc.
      - reverse-engineered:
        - LLM context: database schema extracted from DB, custom prompts, etc.
    - Getting output from these services, parsing possible errors → iterating on that
    - For queries, user writes in one query language or orm/odm/ogm-language and translates to the selected one
      - queries are sent to respective services, compiled, and query plan, query output schema (data types, length,…) and possibly output rows/documents are streamed back to the orchestrator (all of them or subset?)
      - orchestrator agent iteratively modifies queries up to certain timeout, retries
    - Valid queries are benchmarked in respective services (like BenchmarkDotNet in .NET) → output to orchestrator
  - ASP.NET - `dotnet init; dotnet build;` CLI schema compilation, dynamic Roslyn query compiling, benchmarking; possibly whole ORMorpher project
  - Java Spring Boot, Spring Data Neo4j, Spring Data MongoDB
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
8. Prompt are engineered and sent to create Spring Data Neo4j and Spring Data MongoDB schemas
9. Translator waits for response from ASP.NET and Java Spring services (object mapping has to be valid according to loaded data in ETL stage - 1st stage)
10. If errors are encountered, fix them iteratively
11. Queries are processed similarly - iterative process, but with Query Plans, Output Schema, and possibly whole query execution (challenges with results data model differences and amount of data)
12. Valid queries are benchmarked using similar approach as ORMConvertor
13. Lastly, results are shown either in extended ORMorpher UI (or some CLI)
