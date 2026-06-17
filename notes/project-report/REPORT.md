# LLM Advisor for Migration Between ORM/ODM/OGM Frameworks: Project Report

## 1. Introduction
The Universal Object Mapping (UOM) Assistant (or "LLM Advisor for Migration Between ORM/ODM/OGM Frameworks" as per the research project name) utilizes an LLM-driven iterative translation pipeline to migrate schemas, queries, and related configuration across different Object-Relational Mapping (ORM), Object-Document Mapping (ODM), and Object-Graph Mapping (OGM) paradigms.

This report serves as a concise summary of the project's execution, focusing on specification deviations, met requirements, and challenges encountered during implementation. In the end, it provides a list of Deliverables for the committee's review.

For comprehensive User and Programming Documentation, please refer directly to our **[Public Documentation Site](https://uom-demo.vercel.app/docs)** or explore the **[Production (DEMO) Deployment](https://uom-demo.vercel.app/)**. For video tutorial and practical user guide, please refer to the **[User Guide](https://uom-demo.vercel.app/docs/user_docs/user_guide)** section of the documentation.

**IMPORTANT:** The DEMO production deployment was not part of the original specification but was added to provide a tangible demonstration of the system's capabilities. Please, refrain from any kind of misuse (since there is a e-INFRA LLM API key with access to SOTA open-source models to be used freely but reasonably if possible) and avoid any attempts to perform stress/penetration testing on the public deployment. If bugs occur, please take note of them (we need any feedback to further improve the system), but do not take it into consideration as a failure to meet the specification, since the UI was not the main focus of the research project and was implemented as a proof-of-concept to demonstrate the practical applicability of the translation pipeline. The system's core functionality and architectural design remain the primary focus of this research project. If DEMO deployment becomes unavailable, or if any issues arise, we will show the committee local development instances and provide detailed logs and traces to demonstrate the system's capabilities and performance during defense.

**NOTE:** The Web UI is made for Desktop Browsers with wide-screen (width > 1920px; preferably newer Google Chrome; other browsers haven't been tested) and IS NOT optimized for mobile devices! The functionality is not tested there.

**NOTE:** To review Observability logs/stack traces and more on LogFire, use this link: https://logfire-eu.pydantic.dev/l/join-corovcam/xasSDeTa0YObservability (Note that ONLY 2 additional View-only seats are available for committee members, use appropriately). LangSmith Observability platform is also available for review, but it does not have the option to invite external users, so we will provide the committee with exported JSON traces of the evaluation runs instead.
Platforms cannot assign more seats in free plans.

## 2. Specification Deviations
While the core translation pipeline successfully implements the reasoning-and-acting (ReAct) agent workflow, a few practical deviations from the original specification occurred:
* **Validation Sandboxes:** The original design proposed a dedicated .NET and Java validation microservices. While during the development, we experimented with that, but as anticipated in the specification, in the end, we decided to move forward with more robust and future-proof solution. We adopted the open-source [Daytona sandbox framework](https://www.daytona.io/), which provides a more flexible and secure environment for compiling and executing generated code in any isolated Docker container (Docker-in-Docker setup) with configurable Dockerfile. See the [Developer Documentation](https://uom-demo.vercel.app/docs/backend/sandbox_environment) for details on the sandbox architecture and implementation.
* **(N01) Execution Performance:** The specification estimated end-to-end translations under 5 minutes. In reality, translation takes approximately 12 minutes. This is primarily due to the `generate_translation` stage, where injecting massive ground-truth schema context and enforcing temperature 0 for deterministic output throttles the generation speed. Furthermore, the self-repair loop actively consumes time validating and rectifying compilation errors.
* **(F10) UI Plugin to Standalone Web Application:** The specification outlined a UI Plugin Widget integrated inside existing ORMorpher UI. However, since the two projects are marginally different in their scope and target users, we decided to implement the UOM Assistant as a standalone web application with its own dedicated UI and IDE (VSCode, Cursor) integration via integrated web-browser, MCP (Model Context Protocol), and ACP (Agent Client Protocol) interfaces.
* **(N05) Open-Source to Closed-Source Transition:** The project was initially planned as a fully open-source repository. However, this decision is currently under reconsideration due to the potential commercial applications of the developed technology and the need to protect intellectual property. The source code is now hosted in a private GitHub repository with controlled access for the committee's review. The documentation with detailed architectural explanations, design rationales, and user/developer guides remains publicly accessible. This approach will be revisited in the near future.

## 3. Functional and Non-Functional Requirements & Programming Documentation

This section details the core requirements as outlined in the initial specification and expands upon the architectural programming documentation.

### 3.1 Functional Requirements Fulfillment
The project successfully implemented the following functional requirements from the specification:
* **(F01) ETL Pipeline:** Developed automation scripts and workflows to initialize MS SQL Server (source) and map data to MongoDB and Neo4j (targets) using MongoDB Relational Migrator and Neo4j ETL Tool.
* **(F02) Schema Translation:** Implemented accurate translations of entity classes from .NET frameworks (EF Core, NHibernate, Dapper) into Java equivalents (Spring Data MongoDB, Spring Data Neo4j).
* **(F04) Query Translation:** Successfully implemented translation of LINQ and Dapper-SQL queries into logically equivalent target queries for Java frameworks.
* **(F06) Iterative Refinement:** The core LangGraph orchestrator correctly implements the reasoning-and-acting (ReAct) loop, automatically feeding compilation and validation errors back to the LLM to refine the code until success or retry exhaustion.
* **(F07) Manual Intervention:** The workflow correctly halts upon retry limits. As discussed in Section 2, the interactive real-time IDE widget for manual correction was deferred to future iterations.
* **(F10 & F11) UI Plugin & REST API:** The LangGraph API Server and Daytona successfully expose REST API endpoints (https://api.uom.dyn.cloud.e-infra.cz/docs and https://daytona.uom.dyn.cloud.e-infra.cz/api). Instead of a simple plugin, a dedicated standalone web application was developed with its own UI and IDE integrations.
* **(F12) Configurable LLM Backend:** The system robustly supports swappable LLM providers, including the faculty's local Ollama server and remote E-Infra vLLM APIs, configured via environment variables and in the UI Settings panel.

### 3.2 Non-Functional Requirements Fulfillment
* **(N01) Performance:** As noted in the deviations, the 5-minute constraint was exceeded (~12 minutes) due to strict temperature 0 generation and large context payload sizes.
* **(N02) Observability:** Fully achieved via [LangSmith](https://www.langchain.com/langsmith/observability) and [Pydantic Logfire](https://pydantic.dev/logfire) for Backend monitoring, and [Vercel](https://vercel.com/) for frontend monitoring, capturing detailed execution traces, token consumption, tool invocations, logs, performance metrics, and user interactions for comprehensive analysis and debugging.
* **(N03) Deployment:** The entire ecosystem is heavily containerized using Docker Compose, orchestrating the LLM pipeline, UI, databases, and ETL tools seamlessly.
* **(N04) Security:** Validation sandboxes were implemented using the secure Daytona framework to provide isolated Docker-in-Docker execution environments and network isolation, preventing malicious code execution on the host. The databases, services, and production deployment are likewise secured with best practices.
* **(N05) Open Source:** The repository was transitioned to closed-source to protect intellectual property, though extensive documentation remains public.

### 3.3 System Architecture and Orchestration
Following the structural approach of a typical research project report, the system's architecture is decoupled into distinct, containerized layers. The design utilizes a microservices-inspired approach centered around the LangGraph Orchestrator.

* **Frontend Layer (ORMorpher / UOM UI):** Built with Angular/React, providing the primary user interface to submit source schemas and track the LLM iterative translation via REST and Server-Sent Events (SSE).
* **Orchestration Layer (LangGraph):** The brain of the system, written in Python. It manages the translation pipeline, coordinates interactions between the LLM agents, and maintains graph state.
* **Validation Layer (Daytona Sandboxes):** Replaced the initially proposed static .NET and Java services. These sandboxes dynamically provision isolated environments for C# and Java compilation (using Roslyn and Maven, respectively) to ensure structural and semantic correctness of the translated code.
* **Data and Persistence Layer:** 
  * **PostgreSQL:** Persists LangGraph state and stores vector embeddings for RAG-based context retrieval.
  * **Redis:** Provides fast, in-memory caching for LLM agents.
  * **Relational/NoSQL Stores:** MS SQL Server 2022 serves as the source relational database, while MongoDB 8 and Neo4j 2026 serve as the targets.

More details on the architecture, component interactions, and design rationales can be found in the **[Developer Documentation for Backend](https://uom-demo.vercel.app/docs/backend/architecture)** and **[Developer Documentation for Frontend](https://uom-demo.vercel.app/docs/frontend/architecture)**.

## 4. Implementation Challenges and Realized Risks
During development, several anticipated risks materialized and required active mitigation:
* **Context Explosion:** Constructing accurate prompts with Mapping-by-Code, MongoTemplate, and Neo4jTemplate ground-truths frequently approached LLM context limits. This necessitated heavy "context engineering" to prune unnecessary database metadata.
* **Data Model Heterogeneity:** Bridging relational models to graph/document properties (e.g., EFCore LINQ to MongoDB Query/Criteria or Cypher-DSL) caused instances of hallucinated framework APIs. The system heavily relied on its iterative self-repair mechanism to catch Java compilation errors and re-prompt the LLM to fix its own logical fallacies.
* **Orchestration Latency:** The strict requirement for high-quality generation forced the use of temperature 0. Combined with long prompt processing, this made the LLM generation phase the absolute slowest bottleneck of the application.
* **assistant-ui + LangGraph Runtime Compatibility:** The assistant-ui frontend library was not fully compatible with the LangGraph Runtime, leading to more complicated development and debugging. We had to implement custom adapters and workarounds to ensure smooth integration. Future development iterations may include switching to more compatible frontend library (e.g., CopilotKit + AG-UI Protocol).

## 5. Known Issues and Limitations
* **Reasoning Blocks in UI:** The current UI may occasionally freeze streaming reasoning tokens in the Thread view. This is a known issue assistant-ui + LangGraph Runtime, specifically when using ChatLiteLLM Interface and custom vLLM provider in LangGraph (e-INFRA is using Hugging Face models with custom non-openai-compatible JSON body key-value pairs). But know that the backend is still processing the request, unless a visible error message is shown.
* **Thread messages streaming in UI may seem stuck:** Unless a visible error message Alert or Toast comes up, the backend is still processing the request. Some features of assistant-ui are not fully compatible with LangGraph Agent Server runtime (even if their documentation says otherwise).
* **Time to complete translation:** The end-to-end translation time is approximately 12 minutes, if the e-INFRA server is not under heavy load. The time may vary depending on the LLM provider, server load, and network latency. If translation exceeds considerably, please cancel the request and retry later or try different translation pair.
* **Thread history does not persist all messages/reasoning tokens/events:** The assistant-ui + LangGraph Runtime does not persist all messages/reasoning tokens/events in the Thread view upon loading it again from Thread List, so Thread State during streaming and after loading it again may differ. This is a known issue with how LangGraph stores the messages, discards reasoning tokens. The order of messages also differ slightly because of the asynchronous nature of the streaming and event handling in assistant-ui.
* **External Service Exceptions:** The system may encounter exceptions when interacting with external services, such as database connections or API calls. These exceptions are handled with exponential backoff and native LangGraph error handling, but this may impact the overall performance and reliability of the application.
* **Streaming Interrupted/Aborted by External Factors:** The messages Thread streaming may be aborted unexpectedly due to external factors such as network issues, production deployment configuration (e.g., Vercel config, Nginx config, Proxy Tunnel config, etc.), React rerendering unexpectedly, user navigates away from the Thread (this is a feature, stream should be cancelled), or other unforeseen issues. New Thread must be created to retry the request. Thread cannot be resumed after its completion/cancellation.
* **Context Explosion in Translation Stage:** The translation stage may hit the LLM context limit due to large ground-truth schema context, and the large structured output of translation source code. The Time to First Token (TTFT) may be long, and the LLM may fail to generate a valid structured output (some necessary are missing), so the self-repair loop will be triggered to fix the output. This may take several iterations, and the translation may fail if the LLM cannot generate a valid output within the retry limit. This is planned to be mitigated in the future by implementing a more intelligent context retrieval and pruning mechanism, and by optimizing the prompt engineering to reduce unnecessary context.

## 5. Deliverables
The final project deliverables are provided as follows:

1. (D2, D4) **Public Production (DEMO) Deployment:** Hosted at [https://uom-demo.vercel.app/](https://uom-demo.vercel.app/) (Mirror: [https://uom.dyn.cloud.e-infra.cz/](https://uom.dyn.cloud.e-infra.cz/)).
   * API Subdomain: [https://api.uom.dyn.cloud.e-infra.cz](https://api.uom.dyn.cloud.e-infra.cz)
   * Daytona Subdomain: [https://daytona.uom.dyn.cloud.e-infra.cz/](https://daytona.uom.dyn.cloud.e-infra.cz/)
   * Migrator Subdomain: [https://migrator.uom.dyn.cloud.e-infra.cz/](https://migrator.uom.dyn.cloud.e-infra.cz/)
   * Neo4j Browser Subdomain: [https://neo4j.uom.dyn.cloud.e-infra.cz/](https://neo4j.uom.dyn.cloud.e-infra.cz/)
2. (D2, D4) **Project Source Code:** Provided as a `.ZIP` archive inside the deliverables folder, and available via the private GitHub repository (collaborator access required): [https://github.com/corovcam/Universal-Object-Mapping](https://github.com/corovcam/Universal-Object-Mapping).
3. (D1, D6) **Documentation:** Hosted on the public website [https://uom-demo.vercel.app/docs](https://uom-demo.vercel.app/docs), alongside a `.ZIP` archive of the documentation repository: [https://github.com/corovcam/uom-docs](https://github.com/corovcam/uom-docs).
4. (D3, D5) **Evaluation Traces:** Evaluation of translation correctness was conducted manually and is given to the committee for manual review if needed. The traces are exported as JSON files in the deliverables folder and also published online. Below are the public links to 4 sample traces from the LangSmith Observability platform demonstrating the pipeline's capabilities:
   * **EFCore $\rightarrow$ Mongo:** [https://eu.smith.langchain.com/public/8c8e3bd4-9119-45f7-97c8-7019b90e5c72/r/](https://eu.smith.langchain.com/public/8c8e3bd4-9119-45f7-97c8-7019b90e5c72/r/)
   * **EFCore $\rightarrow$ Neo4j:** TODO
   * **Dapper $\rightarrow$ Mongo:** TODO
   * **NHibernate $\rightarrow$ Mongo:** TODO
