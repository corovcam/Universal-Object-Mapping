# Project Specification

## Stack

- n8n-workflow lib in Python code (visualized in n8n web app)
- Ollama or robust reasoning LLM
- DBMS scaffolding bash script calling ETL pipeline
- docker compose microservices - kubernetes? helm chat?
    - langraph or n8n - rest api (or grpc) calling with translated source codes
    - Python FastAPI/flask - LLM orchestrator
        - Iterative LLM (using n8n) workflow
        - Calling .NET and Java services, sending there schema and query source codes in parallel - schema reverse-engineered from DB, or code-first→migrate
            - code first→migrate:
                - LLM context: classes, mapping-files (relmig, neo4j-json), prompt
        - Getting output from these services, parsing possible errors → iterating on that
        - For queries, user writes in one query language or orm/odm/ogm-language and translates to the selected one (n8n variables)
            - queries are sent to respective services, compiled, and query plan, query schema (data types, length,…) and possibly output is streamed to the orchestrator
            - orchestrator agent iteratively modifies queries up to certain timeout, retries
        - Valid queries are benchmarked in respective services → output to orchestrator
    - ASP.NET - `dotnet init; dotnet build;` CLI schema compilation, dynamic Roslyn query compiling, benchmarking; possibly whole ORMorpher project
    - Java Spring
        - Spring Cloud - service discovery server https://cloud.spring.io/spring-cloud-netflix/reference/html/
    - MS SQL Server/PostgreSQL
    - MongoDB
    - MongoDB Relational Migrator
    - Neo4j + Neo4j ETL Tool (to extract relational-graph mapping) + `[`neo4j-admin database import](https://neo4j.com/docs/operations-manual/current/import/)``

## Old Flow

1. Configuration scripts are run
    1. Databases setup
    2. ETL tools - similar processes as my https://github.com/corovcam/Query-Languages-Analysis-Thesis
2. Using ORMorpher, user input ORM schema mapping in either EFCore, NHibernate, or Dapper that works with already instantiated databases.
    1. Possibly I could just build a CLI tool similar to ORMorpher, because I don’t really need to extend the UI since its a developer tool.
3. User input Queries he want translated and benchmarked in the previously selected ORM
4. ORMorpher is run - ORM schema translation, query translation, advisor benchmarking, advisor ILP optimization, results table shown

## New Flow

1. Instead of ORMorpher heuristic-based schema+query transformation, LLM-based iterative translation is used (described also in Stack section)
2. Relational ORM schema and queries (extracted SQL query strings) are serialized and sent to LLM Translator/Orchestrator
3. Translator also extracts relational DDL schema using database connector for context
4. Prompt is engineered to create Spring Data Neo4j and Spring Data MongoDB schemas
5. Translator waits for response from [ASP.NET](http://ASP.NET) and Java Spring services (object mapping has to be valid according to loaded data in ETL stage - 1st stage)
6. If errors are encountered, fix them iteratively
7. Queries are processed similarly - iterative process, but with Query Plans, Output Schema, and possibly whole query execution (challenges with results data model differences)
8. Valid queries are benchmarked using similar approach as ORMorpher
9. Lastly, results are shown either in extended ORMorpher UI (or some CLI)