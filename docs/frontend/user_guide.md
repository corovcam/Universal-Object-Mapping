# UOM Assistant Frontend: User & Operator Guide

This guide is designed for database administrators, software engineers, and system architects who use the **Universal Object Mapping (UOM) Assistant** to migrate frameworks to any framework, currently tailored towards database schemas and queries from [ASP.NET](https://dotnet.microsoft.com/en-us/apps/aspnet) ORMs ([Entity Framework Core](https://learn.microsoft.com/en-us/ef/core/), [NHibernate](https://nhibernate.info/), [Dapper](https://github.com/DapperLib/Dapper)) to target [Java Spring](https://spring.io/) ORM/ODM/OGM ([Spring Data MongoDB](https://spring.io/projects/spring-data-mongodb/), [Spring Data Neo4j](https://spring.io/projects/spring-data-neo4j/)) architectures, and vice versa.

> [!NOTE]
> The Web APP is made for Desktop Browsers (preferably newer Google Chrome) and **IS NOT** optimized for mobile devices! The functionality is not tested there.

---

## 1. Getting Started: The Translation Workspace

When you open the web application at `http://localhost:3001` (in local development), you are presented with the main translation workspace.

![UOM Translation Workspace - Empty State](img/uom-newthreadpage.png)

### 1.1 The Navigation Sidebar
*   **New Thread**: Click the **New Thread** button at the top of the sidebar to spin up a clean translation session. Each thread represents a separate migration pipeline execution with its own LangGraph checkpoint history.
*   **Thread List**: Lists your active and past migration sessions. You can click on any thread to reload its conversational state and inspect its generated artifacts.
*   **Thread Actions**: Hover over any thread in the list and click the `...` menu to **Rename**, **Archive**, or **Delete** the session.
*   **Settings**: Click the **Settings** gear to access database connection strings and LLM configurations.
*   **Theme Toggle**: Switch between **Light Mode** and **Dark Mode**.

### 1.2 Conversation Thread Suggestion Cards
For new sessions, the chat workspace displays four pre-configured translation suggestion cards. Clicking any card loads the corresponding source code inputs into the composer:
1.  **EF Core to Spring Data MongoDB**: Translates Entity Framework Core 10 mappings to target Spring Data MongoDB 5.0 documents.
2.  **EF Core to Spring Data Neo4j**: Translates Entity Framework Core 10 mappings to Spring Data Neo4j 8.0 nodes and relationships.
3.  **Dapper to Spring Data MongoDB**: Translates Dapper SQL queries into MongoDB document aggregation pipelines.
4.  **NHibernate to Spring Data MongoDB**: Translates NHibernate XML mappings or fluent class structures to target MongoDB collections.

![Translation Run - Step 2.1: Tool Calls Detailed View](img/uom-newthreadpage-filled.png "Translation Run - Step 2.1: Tool Calls Detailed View")

![Translation Run - Step 2.2: Schema Inspection Summary](img/uom-newthreadpage-filled-light.png "Translation Run - Step 2.2: Schema Inspection Summary")

---

## 2. Onboarding & Configuration Panel

Before running your first translation, configure the settings modal (click the **Settings** gear in the sidebar footer).

<div style="display: flex; flex-direction: column; gap: 20px; margin-bottom: 30px;">
<details>
  <summary style="font-size: 18px;">Onboarding</summary>
  <img src="img/uom-settings-onboarding1.png" alt="image-description"/>
  <img src="img/uom-settings-onboarding2.png" alt="image-description"/>
</details>

<details>
  <summary style="font-size: 18px;">LLM Settings</summary>
  <img src="img/uom-settings-llm.png" alt="image-description"/>
</details>

<details>
  <summary style="font-size: 18px;">Database Settings</summary>
  <img src="img/uom-settings-db.png" alt="image-description"/>
</details>

<details>
  <summary style="font-size: 18px;">Daytona (Sandboxes) Settings</summary>
  <img src="img/uom-settings-daytona.png" alt="image-description"/>
</details>
</div>

### 2.1 Configuration Tabs & Settings Persistence
The settings modal is divided into four tabs:
1.  **General Tab**:
    *   **Ollama Host**: Configure your local Ollama address (defaults to `http://localhost:11434`).
    *   **Select Model**: Select which LLM will act as the translation generator and evaluator. We recommend the Metacentrum `einfra/kimi-k2.6` or `einfra/deepseek-v4-pro-thinking` for complex schemas.
    *   **OpenAI API URL & Key**: If using remote vLLM clusters (like e-INFRA CZ), supply your API endpoint credentials here.
2.  **Databases Tab**:
    *   **SQL Server Connection**: Connection string for the source relational SQL Server database (defaults to `WideWorldImporters`).
    *   **MongoDB Connection**: Connection URI for the target MongoDB instance.
    *   **Neo4j URI & Password**: Credentials for the target Neo4j Graph database.
3.  **Sandboxes Tab**:
    *   **Daytona API URL**: The endpoint of the Daytona container orchestration daemon.
    *   **Daytona API Key**: Authorization token to provision containers.
    *   **Region Target**: Binds sandbox containers to your preferred cloud host region (e.g. US or EU).
    *   **Compilation Timeout**: Hard timeout in seconds for compilation commands.
4.  **Setup & Guides Tab**:
    *   Links to setup guides and documentation files.

Once saved, the configuration is serialized as a JSON string and persisted in `localStorage` under the `"uom_translator_config"` key. It also sets `uom_config_onboarded` to `"true"` to prevent the modal from opening automatically on subsequent visits.

---

## 3. Running a Translation Pipeline

To execute a migration, paste your C# source schema and query code in the composer input box and click **Send**.

<!-- ![alt-text-1](img/uom-threadrun-toolcalls-schema.png "title-1") ![alt-text-2](img/uom-threadrun-schema.png "title-2") -->

### 3.1 Translation Run - Submitting Input

<p align="center">
  <img src="img/uom-threadrun-start-dark.png" alt="Translation Run - Step 1: Submitting Input" title="Translation Run - Step 1: Submitting Input" />
</p>

### 3.2 Translation Run - DB Schema Inspection Tool Calls (left) and Schema Inspection Summary (right)

<p align="center" style="display: flex; justify-content: center; gap: 5px;">
  <img src="img/uom-threadrun-toolcalls-schema.png" width="49%" alt="Translation Run - Step 2.1: Tool Calls Detailed View" title="Translation Run - Step 2.1: Tool Calls Detailed View" />
  <img src="img/uom-threadrun-schema.png" width="49%" alt="Translation Run - Step 2.2: Schema Inspection Summary" title="Translation Run - Step 2.2: Schema Inspection Summary" /> 
</p>

### 3.3 Translation Run - Daytona Sandbox Code Compilation & Validation (left) and DeepDiff Equivalence Evaluation (right)

<p align="center" style="display: flex; justify-content: center; gap: 5px">
  <img src="img/uom-threadrun-translation-validation.png" width="49%" alt="Translation Run - Step 3: Daytona Sandbox Code Compilation" title="Translation Run - Step 3: Daytona Sandbox Code Compilation" />
  <img src="img/uom-threadrun-equivalence-evaluation.png" width="49%" alt="Translation Run - Step 4: DeepDiff Query Equivalence Check" title="Translation Run - Step 4: DeepDiff Query Equivalence Check" />
</p>

### 3.5 Translation Run - Completed Run with Final Output

<p align="center">
  <img src="img/uom-threadrun-end-light.png" alt="Translation Run - Step 5: Completed Run (Light Theme)" title="Translation Run - Step 5: Completed Run (Light Theme)" />
</p>

### 3.1 Stepper Nodes & Execution Progress
During execution, a progress banner and/or specific graph prompts (hidden in accordions) is shown at the top/bottom of the current message, which indicates the current active pipeline step:

- **Extracting Input**: The assistant is parsing your framework types, versions, and code blocks.
- **Inspecting Database Schema**: The assistant is querying your source SQL Server and target MongoDB/Neo4j DBMS via MCP to gather database metadata.
- **Translating Code**: The LLM is generating the equivalent  target classes and queries.
- **Validating Schema / Query**: The assistant is spinning up Daytona containers to compile, run your generated C# and Java code harnesses concurrently.
- **Evaluating Translation**: The assistant is running [DeepDiff](https://github.com/qlustered/deepdiff) comparison checks between JSON- serialized entities from relational MS SQL Server outputs and NoSQL (MongoDB, Neo4j) query executions by their respective frameworks: ASP .NET Entity Framework Core and Spring Data MongoDB/Spring Data Neo4j.

---

## 4. Troubleshooting & Manual Interventions

When validation compilation fails or the semantic equivalence check identifies differences after 3 attempts, the orchestrator suspends the graph execution.

### 4.1 The Manual Invervention Control Card
When execution is suspended, a warning card is displayed in the chat thread with text "The translation pipeline reached the maximum automatic retries (3)." The card contains three sections:
1.  **Validation Failures**: Displays the error messages from the Daytona compilation step (e.g. `javac error: cannot find symbol. Symbol: class OrderItem`).
2.  **Equivalence DeepDiff Payload**: Shows the JSON diff output from the DeepDiff evaluation (e.g. `{ "values_changed": { "root['orders'][0].price": { "new": 10.5 } } }`).
3.  **Decision Assessment**: Provides buttons to either **Accept & Save** the current output or **Reject & Correct** with targeted feedback for the assistant to re-run the translation loop with corrections.

### 4.2 Actioning Suspended Gates
1.  **Accepting Output**: If you determine the compilation failure is a false positive (e.g. a minor mock mapping mismatch) or want to write the corrections yourself, select **Accept & Save** and click **Submit**. The frontend sends the resume command:
    ```json
    { "resume": "accept" }
    ```
    The orchestrator will output the final code and exit the loop.
2.  **Rejecting & Correcting**:
    *   Select **Reject & Correct**.
    *   A text area labeled **Targeted Agent Correction Pointers** will appear.
    *   Type clear debugging instructions for the assistant (e.g. *"Line 24 in order entity has a missing getter"* or *"Ensure Neo4j query uses relationship DIRECTION of Outgoing"*).
    *   Click **Submit**. The frontend serializes your feedback and sends it as a resume payload:
        ```json
        { "resume": "{\"decision\":\"reject\",\"feedback\":\"The OrderItem class was not generated...\"}" }
        ```
        The assistant will ingest your hints, reset the retry counter, and execute a corrected translation loop.
