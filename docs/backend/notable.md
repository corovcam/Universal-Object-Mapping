# Universal Object Mapping (UOM) Orchestrator: Internal Logic and Algorithms

This document provides a highly detailed explanation of the complex constructs, algorithms, data structures, and edge cases implemented in the `uom-orchestrator` service (located in `services/orchestrator/src`).

---

## 1. Core State Machine and Translation Workflow

The UOM Orchestrator is structured as a semi-deterministic, stateful workflow using **LangGraph**. The execution flow proceeds through a series of specialized nodes designed to inspect schemas, orchestrate multiple LLM brains, compile and validate target code in Docker, check query equivalence, and evaluate output acceptability.

<!-- ```mermaid
WIP
``` -->

---

## 2. Comprehensive Analysis of Key Algorithms

### 2.1 Query Equivalence and DeepDiff (in `query_validator.py`)
To guarantee that a translated query is semantically equivalent to its SQL/LINQ source, the system executes both queries in their respective sandboxes and captures the result metadata:
- **Count**: Total records returned.
- **First Sample**: The full dictionary/JSON representation of the first row.
- **Last Sample**: The full dictionary/JSON representation of the last row.

The comparison is handled via `check_query_equivalence` which utilizes `deepdiff.DeepDiff` with specialized arguments to tolerate ordering and floating-point variances.

#### The Equivalence Verification Algorithm:
1. **Direct Alignment Check**:
   It compares the target `count` to the source `count` directly. Then it compares `firstSample` and `lastSample` respectively using:
   ```python
   diff_first = DeepDiff(src_first, tgt_first, ignore_order=True, report_repetition=True, significant_digits=3, cutoff_intersection_for_pairs=1, cutoff_distance_for_pairs=1, get_deep_distance=True)
   ```
   Setting `ignore_order=True` is critical to ignore column/field ordering in JSON responses. Setting `significant_digits=3` is critical to ignore precision differences when float values are retrieved from database mappings.
2. **Reverse Sorting Robustness (Swapped Samples Edge Case)**:
   In database queries, sorting direction or stable sort behaviors can vary between SQL Server and MongoDB/Neo4j. If direct first-to-first and last-to-last sample checks show differences, but the count is identical, we check if the samples are swapped (i.e. source first equals target last, and source last equals target first):
   ```python
   diff_swapped_first = DeepDiff(src_first, tgt_last, ignore_order=True, ...)
   diff_swapped_last = DeepDiff(src_last, tgt_first, ignore_order=True, ...)
   ```
   If these swapped deep distances are zero, the queries are marked **Equivalent**, resolving a common false-rejection edge case.

---

### 2.2 Sandbox Caching and Snapshot Provisioning (in `sandboxes.py`)
Provisioning and booting sandboxes for C# compilation and Java Maven builds is heavily resource-intensive. `ValidationSandbox` manages the Daytona snapshot and container lifecycles to minimize overhead.

```
[Daytona API Client]
         │
         ├──► 1. get_sandbox()
         │        │
         │        ├──► 2. create_snapshot()
         │        │        │
         │        │        ├──► Check if snapshot exists? (daytona.snapshot.get)
         │        │        │    ├──► YES: Return cached snapshot
         │        │        │    └──► NO: create snapshot (exponential backoff retry loop)
         │        │
         │        └──► 3. create_validation_sandbox()
         │                 │
         │                 ├──► Check if container running? (daytona.sandbox.get)
         │                 │    ├──► YES: Return cached container
         │                 │    └──► NO: create sandbox from snapshot (inject DB env vars)
```

#### Snapshot Exponential Backoff Retry Loop:
Building a clean openjdk or dotnet SDK snapshot can hit transient network or rate-limiting failures. The sandbox manager wraps snapshot creation in a retry block (up to 5 attempts) backed by exponential delay scaling:
$$\text{delay} = 2^{\text{attempt}} \text{ seconds}$$
This ensures robustness under high load.

---

### 2.3 Dynamic Output Model Extraction (in `graph.py`)
In standard LangGraph template setups, LLM structured outputs are defined via a hardcoded Pydantic class. However, UOM demands dynamic fields depending on which source code files are loaded.

`_create_translation_output_model` implements a runtime Pydantic class generator:
1. It inspects the `state.source_schema_code` and splits files.
2. It generates a dictionary of fields using `pydantic.Field` annotations.
3. It constructs the target model using `pydantic.create_model`:
   ```python
   PydanticTranslationOutputModel = create_model(
       "DynamicTranslationOutputModel",
       __base__=BaseTranslationOutput,
       **new_fields
   )
   ```
This dynamic generation ensures the LLM generates a complete drop-in replacement file structure for every input class compiled.

---

## 3. Data Structures

### 3.1 LangGraph `State` (in `state.py`)
The state dictionary acts as the thread-scoped memory for the translator. Key attributes include:
- `messages`: Standard chat history.
- `translation_messages`: Isolated chat history focused on generation and validation feedback (preventing context window pollution).
- `source_schema_code` / `source_query_code`: Extracted C# LINQ inputs.
- `translated_schema_code` / `translated_query_code`: Generated target Java entities/Cypher/Mongo scripts.
- `source_query_validation_results` / `target_query_validation_results`: Extracted JSON execution metadata (`count`, `firstSample`, `lastSample`).
- `query_equivalence_deep_diffs`: DeepDiff comparison reports.
- `translation_loop_count`: Number of auto-correction loops executed (capped at 3).

### 3.2 Configurations `Context` (in `context.py`)
A custom Pydantic-dataclass capturing service-wide configurations read from environment variables, including db hosts, sandbox timeouts, and model selections.

---

## 4. Edge Cases and Mitigations

| Edge Case | Problem | Mitigation |
| :--- | :--- | :--- |
| **Precision Differences** | Floating-point discrepancies in sample results between decimal types in SQL Server and double types in Mongo. | Configured DeepDiff with `significant_digits=3` to round and compare values safely. |
| **Stability of Sandbox Containers** | Containers can crash or lose connectivity during complex Maven compilation routines. | Snapshot caching avoids state corruption; active container lookup checks are executed before every command to guarantee a fresh or healthy shell instance. |
| **JSON Field Order Variance** | Source and target serializer libraries output JSON properties in different sequences. | Configured DeepDiff with `ignore_order=True` during evaluation. |
| **Missing Class Declarations** | LLMs occasionally output raw methods without class wrappers, breaking C# compilation. | Pre-compilation deterministic regex checks inspect for `"class "` or `"record "` keywords and return immediate structured errors, short-circuiting sandbox creation. |
