# UOM Orchestrator

The UOM Orchestrator is the core LLM orchestration engine for the Universal Object Mapping (UOM) system. It is a Python-based service utilizing [LangGraph](https://github.com/langchain-ai/langgraph) to drive the iterative ORM-to-ORM/ODM/OGM translation workflow.

## What it does

The Orchestrator uses a semi-deterministic graph-based workflow to translate database schemas and queries from .NET frameworks (EF Core, NHibernate, Dapper) to Java frameworks (Spring Data MongoDB, Spring Data Neo4j).

The workflow consists of:
1. **Extraction**: Parses incoming user requests to identify the source code, source framework, and destination framework.
2. **Council of Models**: Queries multiple LLMs (local Ollama and remote OpenAI-compatible APIs like E-Infra vLLM) in parallel to brainstorm translation strategies.
3. **Translation Agent (ReAct)**: An autonomous reasoning and acting agent that generates the translation and iteratively refines it by calling validation tools (.NET compilation, Java Maven compilation, database schema extraction).
4. **Human-in-the-Loop**: If the agent exhausts its retry limit without achieving a valid translation, execution is paused for manual user correction.

## Stack

- **Runtime:** Python 3.11+ managed with `uv`
- **Framework:** LangGraph / LangChain
- **API Server:** FastAPI / LangGraph API
- **LLM Providers:** Ollama (local) and OpenAI-compatible endpoints (e.g., E-Infra vLLM)
- **State Persistence:** PostgreSQL with pgvector (via Docker Compose)

## Setup

1. Copy `.env.example` to `.env` and configure your API keys (e.g., `OPENAI_API_KEY` for E-Infra, `OLLAMA_HOST`).
2. Run the LangGraph development server:
   ```bash
   langgraph dev
   ```
3. Or run the full stack via Docker Compose from the repository root:
   ```bash
   docker compose up --build
   ```

## Development

- Install dependencies: `uv sync --group dev`
- Run tests: `make test` and `make integration_tests`
- Formatting & Linting: `make format` and `make lint`

See `GEMINI.md` for AI agent instructions and conventions.