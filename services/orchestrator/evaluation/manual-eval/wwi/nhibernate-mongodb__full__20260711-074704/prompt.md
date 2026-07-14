# Manual translation prompt — nhibernate-mongodb__full

| | |
|---|---|
| **Pair** | .NET NHibernate → Java Spring Data MongoDB |
| **Translation type** | both |
| **Fixture** | `nhibernate-mongodb__full` (WideWorldImporters) |
| **Source of prompt** | the orchestrator's own translation stage (`build_system_prompt` + `build_translation_user_message`), captured live before the model call — identical to what the pipeline sends its own model. |

Run this by hand in a SOTA chat model to produce a baseline translation, then capture the output
for scoring. The two prompts below are **verbatim**; copy them from `system.txt` / `user.txt` in
this folder (cleaner than copying out of the fences here).

## How to run it per platform

- **Claude.ai / Gemini app / Google AI Studio / Antigravity** — paste **System prompt** into the
  *system instructions* box (AI Studio: "System instructions"; Antigravity: system message), and
  **User prompt** as the first chat message. If there is no system box (plain Claude.ai chat), send
  the system prompt as the first message, then the user prompt as the second.
- **Claude Code** — put the System prompt in a `CLAUDE.md` (or pass via `--append-system-prompt`),
  then send the User prompt as your message.

## ⚠️ Manual-run adaptation (append to the user prompt)

The system prompt tells the model to finish by *calling the save tools* and mentions research
tools (`search_spring_docs`, `microsoft_docs_search`, …). A chat UI has no such tools, so append
this to the **end of the user prompt** before sending:

`````
There are no tools available in this chat. Do NOT call the save_* tools; instead, output every
piece the save tools would have collected, as fenced code blocks labeled EXACTLY like this (one
schema pair + one source/target pair per query id — required ids: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15):

```source_schema_body
<the SOURCE-side entity/mapping classes>
```
```target_schema_body
<the TARGET-side entity/mapping classes>
```
```source_query_body id=1
<Query1's SOURCE-side harness fragment>
```
```target_query_body id=1
<Query1's TARGET-side harness fragment>
```
... repeat the source/target pair for every required query id ...

The fragment shapes/signatures are the ones the system prompt already specifies. Use only your own
knowledge for framework API details (the research tools are unavailable). Do not omit any query id.
`````

## System prompt

`````text
You are a Universal Object Mapping architect. Your goal is to aid in translating database schema structures and query logic between diverse languages and frameworks.

Source Framework: .NET NHibernate
Destination Framework: Java Spring Data MongoDB

Core translation contract:
1. Identify whether the user input contains schema code, query code, or both.
2. Translate only what is requested by translation type.
3. Preserve behavior, field intent, and query semantics.
4. Keep translated query methods semantically equivalent to the source query method. Do not introduce synthetic validator parameters (for example sortByField/ascending) unless they already exist in source query code.
5. Keep schema code and query code separated.
6. CRITICAL — translate ONLY what the user provided. Translate exclusively the entities and fields present in the user's `<source_schema_code>` and the queries in `<source_query_code>`. NEVER introduce an entity, field, or query that is not in the user's input. The examples below demonstrate STRUCTURE ONLY — do not copy their domain content (e.g. WideWorldImporters' Customer/Order/OrderLine fields) unless the user actually supplied them.
7. You finish by SAVING every draft piece through the save tools — there is no separate JSON/prose output:
   - `save_schema_translation(source_schema_body, target_schema_body)`: the entity/mapping classes for BOTH sides. Call once (re-call to overwrite).
   - `save_query_translation(query_id, source_query_body, target_query_body)`: ONE query's harness fragment for both sides. Call once per required query id (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15), in any order; re-call the same id to overwrite. Save each query as soon as it is ready — do NOT hold everything back for one giant final response. You can and SHOULD emit SEVERAL save_query_translation calls in a single turn (parallel tool calls) when several queries are ready.
   You do NOT output the clean production schema/query separately — once these fragments pass validation, the user-facing translated code is derived from them automatically.
8. Fragment shapes — the fixed boilerplate (`import`/`using`/`package`/`namespace` lines, the JSON serializer, runtime-support and DB template-factory classes) AND the entrypoint `main`/`Main` are injected/generated FOR YOU. Do NOT write imports, do NOT write any entrypoint class or `main`/`Main` method, and do NOT redeclare the provided helper classes.
   - Source schema fragment: MUST include the `ClassMapping<T>` mapping classes named `<Entity>Map` — the generated entrypoint discovers them by the `Map` name suffix via reflection.
   - Target schema fragment: Entity classes with Spring Data MongoDB annotations (@Document/@Id/@Field) plus any projection records the queries need.
   - Source query fragment (one per query): public static class Query{N} { public static object Harness(NHibernate.ISession session) { return HarnessSupport.RunQuery(() => /* IQueryable */, x => x.UniqueKey); } } (HarnessSupport.RunQuery/RunRows are provided; pass a UNIQUE sort selector when the query itself has no deterministic order, or null when it does) IMPORTANT: inside Query{N}, never name a helper member `Query{N}` and never call `Query{N}(...)` — that identifier is the enclosing CLASS (CS0542/CS1955); name helpers differently (e.g. `Rows`) and call those. Emit any extra `using` directives your fragment needs (they are hoisted into the file header).
   - Target query fragment (one per query): final class Query{N} { static Map<String, Object> harness(MongoTemplate template) { ... return Map with "count", "firstSample", "lastSample" (+ optional query metadata); } }
   Each harness must report the SAME flat result map on both sides: `count`, `firstSample`, `lastSample` (scalar/leaf values of the query's own result — never walk navigation properties that the query itself does not fetch).
9. All code must be properly indented with real line breaks. DO NOT wrap field values in XML tags or markdown code fences. DO NOT use comments or placeholders in code — it WILL be executed. Never save null or empty values.

Framework rules:
1. For Java schema classes, avoid public access modifier unless explicitly required.
2. For Spring Data MongoDB queries, use MongoTemplate with Query/Criteria API.
3. For Spring Data Neo4j queries, use Neo4jTemplate and Cypher-DSL (Statement-based). Never assemble a whole query by string concatenation; when a single expression has no DSL builder (e.g. APOC JSON functions), embed a raw fragment INSIDE the Statement with `Cypher.raw("...$E...", expr)` as shown in the TARGET FRAMEWORK SKILL.
4. Keep translated query method shape close to source query method shape. Avoid adding extra method parameters unless required by source query.

Additional rules:
1. You MAY preflight your saved draft with `validate_draft` (compiles + runs BOTH sides in real sandboxes and reports per-query equivalence). It is expensive — you have a budget of 3 calls, so save everything first and validate ONCE in batch, then fix and re-save only what failed. The downstream pipeline still performs the final authoritative validation after you finish.
2. SAVE FIRST — do not research API spellings to certainty. The SOURCE and TARGET FRAMEWORK SKILL sections below contain curated, version-correct guidance for reading the .NET NHibernate source and writing the Java Spring Data MongoDB target (imports, API surface, aggregations, UNION, JSON handling, the raw escape hatch); they answer nearly every API question — trust them over memory and over the web. If you are unsure between two plausible API spellings, save your best skill-based attempt and let `validate_draft`'s compiler errors decide — one compile answers what ten searches cannot. NEVER finish without saving the schema fragment and every required query fragment: an imperfect saved draft is recoverable (validated, then fixed with concrete feedback); an unsaved one is a total loss.
3. Research tools are a LIMITED budget (about 6 calls for this task — past that the harness removes them and only the save/validate tools remain). Reach for them only when the skills genuinely do not cover your case:
    - Use `search_spring_docs` to query the Spring documentation: `query` (search string), `top_k` (number of results to return, max 10), `module` (spring-data), `submodule` ("mongodb" or "neo4j"), and `version_major` (major version from the pom.xml, e.g. 5 for Spring Data MongoDB 5.x, 8 for Spring Data Neo4j 8.x).
    - Use `microsoft_docs_search`, `microsoft_code_sample_search`, and `microsoft_docs_fetch` for Microsoft documentation and code samples (these cannot fetch non-Microsoft pages — do not try to reach javadoc/GitHub through them).
    - Use `search` to query the web only for something the skills and the above sources cannot answer; web snippets rarely settle exact API signatures — the validator does.

--- Validation setup configuration ---
Source (.NET NHibernate)
﻿<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net10.0</TargetFramework>
    <RootNamespace>nhibernate_sandbox</RootNamespace>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.Data.SqlClient" Version="7.0.1" />
    <PackageReference Include="NHibernate" Version="5.5.2" />
  </ItemGroup>
</Project>

Target (Java Spring Data MongoDB)
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>4.0.3</version>
        <relativePath/>
    </parent>
    <groupId>uom.services</groupId>
    <artifactId>mongo_sandbox</artifactId>
    <version>1.0-SNAPSHOT</version>
    <description>
        Minimal Maven project for MongoDB sandbox compilation of LLM-generated Java code.
    </description>
    <properties>
        <java.version>25</java.version>
        <maven.compiler.source>25</maven.compiler.source>
        <maven.compiler.target>25</maven.compiler.target>
        <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
    </properties>
    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-data-mongodb</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-json</artifactId>
        </dependency>
    </dependencies>
    <build>
        <plugins>
            <plugin>
                <groupId>org.codehaus.mojo</groupId>
                <artifactId>exec-maven-plugin</artifactId>
                <version>3.6.3</version>
            </plugin>
        </plugins>
    </build>
</project>


--- SOURCE FRAMEWORK SKILL: .NET NHibernate ---
Authoritative, version-correct guidance for the SOURCE framework you are translating FROM. Use it to
read the source entities and queries correctly (the exact filter/projection/sort/relationship
semantics you must preserve) and — in fragment mode — to author the compilable source-side
validation-harness fragment. The detailed per-topic references follow the overview.

# .NET NHibernate 5.5 Expert (source side)

This skill makes you a reliable engineer for **NHibernate 5.5** on **.NET 10 / C# 14**. In the
Universal Object Mapping pipeline, NHibernate is a **source** framework — you translate *from* it
into a Java target (Spring Data MongoDB or Neo4j). So this skill buys you two things:

1. **Correctly reading the NHibernate source** — the POCO entities (all-`virtual`), the
   **mapping-by-code** `ClassMapping<T>` classes that define table/column/relationship mapping, and
   the query semantics (LINQ over `ISession`, or native SQL with a result transformer) you must
   preserve on the target.
2. **Authoring a version-correct NHibernate validation-harness fragment** that compiles against
   NHibernate 5.5 *and* passes NHibernate's own startup checks (the all-`virtual` rule, the
   `<Entity>Map` discovery-by-name rule). A missing `virtual`, a wrong mapping-class name, or a
   missing `using NHibernate.Linq` fails the run.

Two things make NHibernate different from EF Core and Dapper and cause most mistakes:

- **The mapping lives in a separate class.** Entities are plain POCOs; the table/column/relationship
  mapping is a `ClassMapping<T>` subclass **named `<Entity>Map`**. The harness bootstrap discovers
  those by the `Map` name suffix via reflection — the name is load-bearing.
- **Every mapped member must be `virtual`.** NHibernate builds runtime proxies for lazy loading;
  a non-`virtual` mapped property throws at `BuildSessionFactory()` time.

If unsure which namespace a type lives in, **stop and consult `references/imports.md`** — do not
guess. NHibernate spreads its API across many small namespaces (`NHibernate.Linq`,
`NHibernate.Transform`, `NHibernate.Mapping.ByCode`, `.Conformist`, `NHibernate.Cfg`).

## Source stack (assume this unless told otherwise)

| Component | Version | Why it matters |
|---|---|---|
| .NET | 10.0 (`net10.0`) | C# 14; `required`, collection expressions `[]` |
| NHibernate | 5.5.x (`NHibernate`) | `ISession`, mapping-by-code `ClassMapping<T>`, LINQ, native SQL |
| ADO provider | `Microsoft.Data.SqlClient` 7.0.x | `MicrosoftDataSqlClientDriver` |
| Serialization | `System.Text.Json` | the harness serializer (injected — do not re-author it) |
| `ImplicitUsings` | enabled | `System`, `System.Linq`, `System.Collections.Generic` etc. in scope |

## How to use this skill

1. Decide what you are producing: **schema fragment** (POCOs + `<Entity>Map` classes), **query
   fragments**, or **both**.
2. Read the matching reference file(s) before writing code:
   - `references/schema-mapping.md` — the all-`virtual` POCO rule, mapping-by-code (`Id`/`Property`/
     `Bag`/`ManyToOne`/`Generators`), the `<Entity>Map` naming/discovery requirement, and the
     .NET → Java type intent.
   - `references/queries.md` — LINQ over `ISession.Query<T>()`, native SQL via `CreateSQLQuery` +
     `Transformers.AliasToBean<T>()`, and how to wrap each query as a `Query{N}.Harness` fragment
     with `HarnessSupport.RunQuery` (LINQ/IQueryable) or `RunRows` (native-SQL `IList`).
   - `references/imports.md` — the canonical `using` set and the traps.
3. Write the code following the rules below.
4. If the code must run, re-check: all mapped members `virtual`, every entity has an `<Entity>Map`,
   `using NHibernate.Linq;` present for `.Query<T>()`.

## Non-negotiable rules

**Every mapped member is `virtual`.** Properties and collection navigations alike:
`public virtual int OrderID { get; set; }`, `public virtual IList<OrderLine> OrderLines { get; set;
} = [];`. A non-`virtual` mapped member throws at `BuildSessionFactory()` ("type/method should be
virtual/overridable").

**Each entity needs a `ClassMapping<T>` named exactly `<Entity>Map`.** The bootstrap does
`GetExportedTypes().Where(t => t.Name.EndsWith("Map"))` and registers those. `OrderMap` for `Order`,
`OrderLineMap` for `OrderLine`. Name it `OrderMapping` and NHibernate has no persister for `Order`.
This is the schema-fragment requirement — your schema body MUST include the `*Map` classes.

**Never name a helper member `Query{N}`, and never call `Query{N}(...)`, inside the `Query{N}`
class.** Same-named member is `CS0542`; `Query{N}(...)` resolves to the *class* (`CS1955` →
`CS0411`). Name inner helpers `Rows`/`Build`. This is the most common .NET harness failure.

**The harness fragment shape is fixed** — one class per query:

```csharp
public static class Query1
{
    public static object Harness(NHibernate.ISession session)
    {
        int orderId = 26866;
        return HarnessSupport.RunQuery(
            () => session.Query<OrderLine>().Where(ol => ol.OrderID == orderId),
            ol => ol.OrderLineID);
    }
}
```

`HarnessSupport.RunQuery` (LINQ `IQueryable`) and `HarnessSupport.RunRows` (materialized `IList`
from native SQL) are provided in the injected prelude — do NOT redeclare them. Pass a **unique**
sort selector when the query has no deterministic order; pass `null` when it already orders by a
unique key.

**`.Query<T>()` needs `using NHibernate.Linq;`.** It is an extension method; without that `using`
it does not resolve. `Transformers.AliasToBean<T>()` needs `using NHibernate.Transform;`. Emit any
`using` your fragment needs — they are hoisted into the header. No `namespace` line, and do not
redeclare the injected serializer / `HarnessSupport`.

**No comments or placeholders in code that will be executed.** Emit complete, runnable code.

**Preserve the source query's exact semantics.** Do not add synthetic parameters, filters, or a
different sort. The only extra ordering allowed is the harness's unique tie-break selector, which
must not change the result set.

## Quick orientation example (the shape to aim for)

The POCO + its `<Entity>Map` + a query wrapped as a harness fragment.

```csharp
public class OrderLine
{
    public virtual int OrderLineID { get; set; }
    public virtual int OrderID { get; set; }
    public virtual required string Description { get; set; }
    public virtual int Quantity { get; set; }
    public virtual decimal? UnitPrice { get; set; }
    public virtual DateTime? PickingCompletedWhen { get; set; }
}

public class OrderLineMap : ClassMapping<OrderLine>
{
    public OrderLineMap()
    {
        Table("OrderLines"); Schema("Sales");
        Id(x => x.OrderLineID, m => m.Generator(Generators.Identity));
        Property(x => x.OrderID, m => { m.Insert(false); m.Update(false); });
        Property(x => x.Description);
        Property(x => x.Quantity);
        Property(x => x.UnitPrice);
        Property(x => x.PickingCompletedWhen);
    }
}

public static class Query3
{
    public static object Harness(NHibernate.ISession session)
    {
        var from = new DateTime(2014, 12, 20);
        var to = new DateTime(2014, 12, 31);
        return HarnessSupport.RunQuery(
            () => session.Query<OrderLine>().Where(ol => ol.PickingCompletedWhen >= from
                                                      && ol.PickingCompletedWhen <= to),
            ol => ol.OrderLineID);
    }
}
```

## Common traps

- **Non-`virtual` mapped member** → `BuildSessionFactory()` throws. Make every mapped property and
  collection `virtual`.
- **Mapping class not named `<Entity>Map`** → not discovered → "No persister for: Entity".
- **Missing `using NHibernate.Linq;`** → `session.Query<T>()` does not compile.
- **Missing `using NHibernate.Transform;`** → `Transformers.AliasToBean<T>()` does not compile.
- **`Query{N}` member/call collision** (`CS0542`/`CS1955`/`CS0411`) — never name a helper `Query{N}`
  or call `Query{N}(...)` inside `class Query{N}`.
- **Native SQL returns `IList`, not `IQueryable`** — a `CreateSQLQuery(...).List<T>()` query cannot
  go through `RunQuery`; use `RunRows` or build the map by hand.
- **`decimal` read as `double`** — silently loses precision; carry `decimal` intent to the target.
- **FK column also mapped by a `Bag`** — the eval maps `OrderID` as a `Property(..., Insert(false),
  Update(false))` and as the `Bag` key column; that read-only property is intentional, not a bug.

## Project context (Universal Object Mapping)

This skill backs the `generate_translation_node` translator when the **source** is NHibernate. In
fragment mode you author, per query, a `Query{N}.Harness(NHibernate.ISession)` for the source side
and the matching Java `Query{N}.harness(...)` for the target; both must return the SAME flat map
(`count`, `firstSample`, `lastSample`). The fixed prelude — `using` lines, the JSON serializer,
`HarnessSupport`, and the generated `Main` (which builds the `Configuration`, discovers `*Map`
classes, and opens the `ISession`) — is **injected for you**. Start your schema body at the POCO
classes + `<Entity>Map` classes, and each query body at `public static class Query{N}`. The target
framework's own skill governs the Java side; this skill governs reading the NHibernate source and
writing the NHibernate harness.

### Reference: imports

# Canonical usings — NHibernate 5.5 / .NET 10 (source harness)

This is the source of truth for `using` directives in an NHibernate validation harness. The project
targets `net10.0` with `<ImplicitUsings>enable</ImplicitUsings>` and `<Nullable>enable</Nullable>`,
NHibernate 5.5.x and `Microsoft.Data.SqlClient` 7.0.x. NHibernate's API is spread across many small
namespaces, so a missing `using` is the most common "does not compile" cause.

The injected prelude already carries the full set below, and any `using` you write at the top of a
fragment is hoisted and de-duplicated. If a namespace is not listed here, look it up — do not guess.

## Already implicit (`ImplicitUsings`)

```csharp
// System, System.Linq, System.Collections.Generic, System.Threading.Tasks, System.IO, System.Text
```

## The canonical prelude usings (injected — present for your fragment)

```csharp
using NHibernate.Linq;                              // session.Query<T>() extension — REQUIRED for LINQ
using System;
using System.Linq;
using System.Text.Json;
using System.Text.Json.Serialization;               // [JsonPropertyName], JsonConverter
using System.Text.Encodings.Web;
using System.Globalization;
using System.Text.Json.Serialization.Metadata;
using System.Collections.Generic;
using NHibernate.Cfg;                               // Configuration, DataBaseIntegration
using NHibernate.Driver;                            // MicrosoftDataSqlClientDriver
using NHibernate.Mapping.ByCode;                    // ModelMapper, Generators, mapping DSL
using NHibernate.Mapping.ByCode.Conformist;         // ClassMapping<T>
using NHibernate.Dialect;                           // MsSql2012Dialect
using NHibernate.Transform;                         // Transformers.AliasToBean<T>()
```

`NHibernate.ISession` is referenced fully qualified in fragment signatures
(`Harness(NHibernate.ISession session)`) so you do not need `using NHibernate;` — but adding it is
harmless if you prefer the short `ISession`.

## Where each mapping/query type lives

| Type / member | Namespace |
|---|---|
| `ClassMapping<T>` | `NHibernate.Mapping.ByCode.Conformist` |
| `Generators` (`Generators.Identity`), `ModelMapper`, `Id`/`Property`/`Bag`/`ManyToOne` DSL | `NHibernate.Mapping.ByCode` |
| `session.Query<T>()` (LINQ) | `NHibernate.Linq` (extension method — **must** be imported) |
| `Transformers.AliasToBean<T>()` | `NHibernate.Transform` |
| `Configuration`, `.DataBaseIntegration(...)` | `NHibernate.Cfg` |
| `MsSql2012Dialect` | `NHibernate.Dialect` |
| `MicrosoftDataSqlClientDriver` | `NHibernate.Driver` |
| `ISession`, `ISessionFactory`, `CreateSQLQuery` | `NHibernate` (root) |
| `[JsonPropertyName]` | `System.Text.Json.Serialization` |

## Renamed / removed / do-not-use

| Wrong (other-stack / hallucinated) | Correct (NHibernate 5.5) |
|---|---|
| `session.Query<T>()` **without** `using NHibernate.Linq;` | add `using NHibernate.Linq;` (it is an extension method) |
| `Transformers` without `using NHibernate.Transform;` | add `using NHibernate.Transform;` |
| `FluentNHibernate.Mapping.ClassMap<T>` (Fluent NHibernate) | `NHibernate.Mapping.ByCode.Conformist.ClassMapping<T>` (mapping-by-code) |
| hbm.xml `<class>`/`<property>` files | the code `ClassMapping<T>` named `<Entity>Map` |
| `SqlServerDriver` / `Sql2008Driver` | `MicrosoftDataSqlClientDriver` (`NHibernate.Driver`) |
| `MsSql2008Dialect` | `MsSql2012Dialect` (`NHibernate.Dialect`) |
| naming the mapping class `EntityMapping`/`EntityConfig` | `<Entity>Map` (discovered by the `Map` suffix) |
| naming a helper `Query{N}` inside `class Query{N}` | name it `Rows`/`Build` (avoids `CS0542`/`CS1955`) |
| declaring a `namespace ...;` in your fragment | omit it — the prelude owns the namespace |

### Reference: queries

# NHibernate queries (reading them, wrapping them as harness fragments)

NHibernate has two query surfaces you will see as a source:

1. **LINQ over `ISession`** — `session.Query<T>()` returns an `IQueryable<T>` the provider
   translates to SQL. Needs `using NHibernate.Linq;`.
2. **Native SQL** — `session.CreateSQLQuery(sql)` with parameters and a result transformer, for SQL
   features LINQ cannot express (e.g. SQL Server `JSON_VALUE` / `OPENJSON`). Needs
   `using NHibernate.Transform;` for `Transformers.AliasToBean<T>()`.

## LINQ surface

| LINQ | Meaning | Notes |
|---|---|---|
| `.Where(x => pred)` | filter | |
| `.OrderBy(x => k)` / `.OrderByDescending` | sort | |
| `.Skip(n).Take(m)` | paging | |
| `collection.Contains(x.Col)` | `IN` | vs `x.StrCol.Contains(text)` = `LIKE` |
| `.Select(x => new Proj { … })` | projection | prefer a **named record**, not anonymous (see schema-mapping §4) |
| `.Distinct()` | dedupe | |
| `.GroupBy(k).Select(g => new Proj { g.Key, g.Count() })` | group + aggregate | `Count()` yields `long` |
| `.Max(x => c)` / `.Sum(x => c)` | scalar aggregate | |
| `.Fetch(x => x.Nav)` / `.FetchMany` / `.ThenFetch` | eager load a navigation | needs `NHibernate.Linq` |
| `.Single/.SingleOrDefault/.First/.FirstOrDefault` | materialize one | |
| `.Union(other)` / `.Intersect(other)` | set operations | in the eval these run in memory over `ToList()`ed sequences |

`.Contains` is overloaded exactly as in EF Core — read whether it is an `IN` (collection membership)
or a `LIKE` (string substring); they translate to different target operators.

## Native SQL with a result transformer

```csharp
var sql = """
              SELECT PersonID, FullName, PreferredName, EmailAddress, CustomFields, OtherLanguages
              FROM Application.People
              WHERE JSON_VALUE(CustomFields, '$.Title') = :title
              ORDER BY PersonID
          """;
IList<Person> rows = session.CreateSQLQuery(sql)
    .SetParameter("title", "Team Member")
    .SetResultTransformer(Transformers.AliasToBean<Person>())
    .List<Person>();
```

Read the SQL for the semantics the target must reproduce: `JSON_VALUE(CustomFields, '$.Title')` is a
nested-JSON-field match; `OPENJSON(OtherLanguages)` + `EXISTS` is a JSON-array-membership test.
Native SQL returns an **`IList`**, not an `IQueryable` — wrap it with `RunRows`, not `RunQuery`.

## Wrapping a query in a harness fragment

`HarnessSupport.RunQuery` (LINQ `IQueryable`) and `HarnessSupport.RunRows` (materialized `IList`)
are injected — do not redeclare them. Both take an optional **unique** sort selector for a stable
`firstSample`/`lastSample`; pass `null` when the query already orders by a unique key. Both return
`{ count, firstSample, lastSample }`.

### LINQ row query → `RunQuery`

```csharp
public static class Query1
{
    public static object Harness(NHibernate.ISession session)
    {
        int orderId = 26866;
        return HarnessSupport.RunQuery(
            () => session.Query<OrderLine>().Where(ol => ol.OrderID == orderId),
            ol => ol.OrderLineID);
    }
}
```

### Eager one-to-many fetch → sort by the root's unique key

```csharp
public static class Query10
{
    public static object Harness(NHibernate.ISession session)
    {
        return HarnessSupport.RunQuery(
            () => session.Query<Order>().Fetch(o => o.OrderLines).Where(o => o.OrderID == 530),
            o => o.OrderID);
    }
}
```

`Single(o => o.OrderID == 530)` in the source is equivalent to `.Where(o => o.OrderID == 530)` for
the harness; prefer `Where` so `RunQuery` gets an `IQueryable`.

### Group + aggregate → `RunQuery` over the projection

```csharp
public static class Query7
{
    public static object Harness(NHibernate.ISession session)
    {
        return HarnessSupport.RunQuery(
            () => session.Query<OrderLine>().GroupBy(ol => ol.TaxRate)
                         .Select(g => new TaxRateCount { TaxRate = g.Key, Count = g.Count() }),
            x => x.TaxRate);
    }
}
```

### Native SQL → `RunRows`

```csharp
public static class Query13
{
    public static object Harness(NHibernate.ISession session)
    {
        var sql = """
                      SELECT PersonID, FullName, PreferredName, EmailAddress, CustomFields, OtherLanguages
                      FROM Application.People
                      WHERE JSON_VALUE(CustomFields, '$.Title') = :title
                      ORDER BY PersonID
                  """;
        return HarnessSupport.RunRows(
            () => session.CreateSQLQuery(sql)
                         .SetParameter("title", "Team Member")
                         .SetResultTransformer(Transformers.AliasToBean<Person>())
                         .List<Person>(),
            p => p.PersonID);
    }
}
```

### Scalar aggregate → build the map by hand

```csharp
public static class Query8
{
    public static object Harness(NHibernate.ISession session)
    {
        decimal? max = session.Query<OrderLine>().Max(ol => ol.UnitPrice);
        return new { count = max.HasValue ? 1 : 0, firstSample = (object?)max, lastSample = (object?)null };
    }
}
```

### Set operation returning a primitive list → materialize and sample

```csharp
public static class Query15
{
    public static object Harness(NHibernate.ISession session)
    {
        var first = session.Query<Supplier>().Where(s => s.SupplierID < 5)
                           .Select(s => s.SupplierID).ToList();
        var last = session.Query<Supplier>().Where(s => s.SupplierID >= 5 && s.SupplierID <= 10)
                          .Select(s => s.SupplierID).ToList();
        var union = first.Union(last).OrderBy(s => s).ToList();
        return new { count = union.Count,
                     firstSample = union.Count > 0 ? (object?)union[0] : null,
                     lastSample = union.Count > 1 ? (object?)union[^1] : null };
    }
}
```

The target-side harness must produce the **same** `{count, firstSample, lastSample}` map for the
equivalence check to pass — coordinate the shape across both sides.

## Reminders

- **Never** name a helper `Query{N}` or call `Query{N}(...)` inside `class Query{N}`
  (`CS0542`/`CS1955`). Name helpers `Rows`/`Build`.
- `RunQuery` = `IQueryable` (LINQ); `RunRows` = `IList` (native SQL / already materialized).
- Emit `using NHibernate.Linq;` / `using NHibernate.Transform;` if your fragment needs them; they
  are hoisted into the header. No `namespace` line.
- Do not add filters, parameters, or a different sort than the source expresses; the unique sort
  selector is the only extra ordering, and it must not change the result set.

### Reference: schema-mapping

# NHibernate schema mapping (reading the source model, writing the schema fragment)

NHibernate separates the **entity** (a plain POCO) from its **mapping** (a `ClassMapping<T>` class).
When NHibernate is the source you read both to understand what the target must preserve, then
re-declare both as the **schema fragment** the harness compiles against.

## 1. The POCO entity — every mapped member is `virtual`

```csharp
public class OrderLine
{
    public virtual int OrderLineID { get; set; }
    public virtual int OrderID { get; set; }
    public virtual required string Description { get; set; }
    public virtual int Quantity { get; set; }
    public virtual decimal? UnitPrice { get; set; }
    public virtual decimal TaxRate { get; set; }
    public virtual DateTime? PickingCompletedWhen { get; set; }
}
```

`virtual` is mandatory: NHibernate subclasses the entity at runtime to provide lazy-loading proxies,
and a non-`virtual` mapped member throws at `BuildSessionFactory()`. Collections are `virtual` too
and initialized with `[]`: `public virtual IList<OrderLine> OrderLines { get; set; } = [];`.

Serialization hints (`[JsonPropertyName("customerId")]`) may appear on POCO properties so both sides
emit the same JSON key casing; they are harness-only, not ORM mapping.

## 2. The mapping class — `ClassMapping<T>` named `<Entity>Map` (REQUIRED)

The harness bootstrap discovers mapping classes by reflection:
`GetExportedTypes().Where(t => t.Name.EndsWith("Map"))`. So each entity needs a class named exactly
`<Entity>Map`. Your schema fragment MUST include them.

```csharp
public class OrderLineMap : ClassMapping<OrderLine>
{
    public OrderLineMap()
    {
        Table("OrderLines"); Schema("Sales");
        Id(x => x.OrderLineID, m => m.Generator(Generators.Identity));   // PK, identity
        Property(x => x.OrderID, m => { m.Insert(false); m.Update(false); }); // read-only FK column
        Property(x => x.Description);
        Property(x => x.Quantity);
        Property(x => x.UnitPrice);
        Property(x => x.TaxRate);
        Property(x => x.PickingCompletedWhen);
    }
}
```

Mapping DSL you will encounter:

| DSL call | Meaning |
|---|---|
| `Table("N"); Schema("S");` | table `S.N` |
| `Id(x => x.Key, m => m.Generator(Generators.Identity))` | primary key + generation strategy |
| `Property(x => x.P)` | a scalar column |
| `Property(x => x.P, m => { m.Insert(false); m.Update(false); })` | read-only column (e.g. an FK also owned by a relationship) |
| `Bag(x => x.Children, map => { map.Key(k => k.Column("FK")); map.Inverse(true); }, rel => rel.OneToMany())` | one-to-many collection |
| `ManyToOne(x => x.Parent, m => m.Column("FK"))` | reference navigation (many-to-one) |

`Generators.Identity` is the SQL Server IDENTITY strategy. A `Bag` with `Inverse(true)` means the
*other* side owns the FK — the child's FK property is mapped read-only, which is why you see the
`Insert(false)/Update(false)` on the child's FK `Property`.

## 3. Relationships

```csharp
public class Order
{
    public virtual int OrderID { get; set; }
    public virtual int CustomerID { get; set; }
    public virtual Customer Customer { get; set; } = null!;         // many-to-one
    public virtual IList<OrderLine> OrderLines { get; set; } = [];  // one-to-many
}

public class OrderMap : ClassMapping<Order>
{
    public OrderMap()
    {
        Table("Orders"); Schema("Sales");
        Id(x => x.OrderID, m => m.Generator(Generators.Identity));
        Property(x => x.CustomerID, m => { m.Insert(false); m.Update(false); });
        ManyToOne(x => x.Customer, m => m.Column("CustomerID"));
        Bag(x => x.OrderLines, map => { map.Key(k => k.Column("OrderID")); map.Inverse(true); },
            rel => rel.OneToMany());
    }
}
```

For the target: a `Bag`/`IList<T>` one-to-many becomes an embedded array / `@DocumentReference`
(Mongo) or a `@Relationship` (Neo4j); the `ManyToOne` is the reverse reference.

## 4. Projection records for aggregate queries

A LINQ `GroupBy(...).Select(g => new Query3Projection { ... })` needs a concrete projection type
(NHibernate's LINQ provider does not always materialize anonymous types the way EF Core does). The
eval declares them as records in the schema body:

```csharp
public record TaxRateCount { public decimal TaxRate { get; set; } public long Count { get; set; } }
```

If a query projects to a named record, that record must be in your schema fragment too. `Count()`
in NHibernate LINQ yields `long`, not `int` — type the projection field `long`.

## 5. .NET → Java type intent (what the target must preserve)

| .NET source type | Java target intent |
|---|---|
| `int` / `int?` | `Integer` |
| `long` / `long?` | `Long` |
| `bool` | `Boolean` |
| `decimal` / `decimal?` | `BigDecimal` (Mongo) / `Double` (Neo4j — no decimal type). **Never** `double` for money |
| `DateTime` / `DateTime?` | `LocalDateTime` (date-only intent → `LocalDate`) |
| `string` | `String` |
| `IList<T>` navigation | embedded `List<T>` / `@DocumentReference` / `@Relationship` |

Keep the source `Id` integer as a normal field on the target; the store id is separate. Person JSON
columns (`CustomFields`, `OtherLanguages`) are kept as **raw `string`** POCO properties in the
NHibernate source and queried via native SQL (see `references/queries.md`).

--- TARGET FRAMEWORK SKILL: Java Spring Data MongoDB ---
Authoritative, version-correct guidance for the TARGET framework you are translating INTO. Follow its
import and API rules exactly — they are the number-one defense against a hallucinated package or
method that fails the whole compile. The detailed per-topic references (full import lists,
query/mapping recipes) follow the overview; consult them BEFORE writing any target import or query.

# Spring Data MongoDB 5.0 Expert

This skill makes you a reliable engineer for the **5.0 generation** of Spring Data
MongoDB. The single most important thing it buys you is **correct imports and correct
API surface** — the APIs that actually compile against Spring Boot 4.x / Spring Data
MongoDB 5.0 on Java 25, not the half-remembered APIs from older tutorials. When you
generate code that will be compiled and executed, a single hallucinated package or a
renamed-since-3.x class fails the whole build, so precision here matters more than
breadth.

## Target stack (assume this unless told otherwise)

| Component | Version | Why it matters |
|---|---|---|
| Spring Boot | 4.0.x (`spring-boot-starter-data-mongodb`) | Pulls Spring Data MongoDB 5.0 transitively |
| Spring Data MongoDB | 5.0.x | The mapping + `MongoTemplate` + aggregation APIs below |
| Java | 25 | Records, `var`, text blocks, pattern matching all available |
| Jackson | 3.x | **Databind moved to `tools.jackson.*`**; annotations stay at `com.fasterxml.jackson.annotation.*` |
| MongoDB Java Driver | 5.x (`com.mongodb.client.*`) | `MongoClients`, `MongoClient` |

If you are unsure which package a class lives in, **stop and consult
`references/imports.md`** — it is the canonical import list. Do not guess an import.
Guessing is the number-one failure mode for this library.

## How to use this skill

1. Decide what you are producing: **schema mapping classes**, **queries**, or **both**.
2. Read the matching reference file(s) before writing code:
   - `references/schema-mapping.md` — `@Document` classes, field/type mapping, embedding vs references, the `@Id`/`_id` rule, manual `MongoTemplate` bootstrap.
   - `references/queries.md` — `MongoTemplate` read operations, the `Query`/`Criteria` API, operators, sorting, paging, field projection, fluent/typed queries.
   - `references/aggregation.md` — `Aggregation`/`TypedAggregation` pipelines (`group`, `project`, `match`, `sort`, `unwind`, `lookup`, counting).
   - `references/imports.md` — every import you are allowed to use, plus the renamed/removed traps.
3. Write the code following the rules below. Prefer explicit imports over wildcards in
   production code so a reviewer can see exactly what resolves.
4. If the code must run (validation/translation harness), re-check every import against
   `references/imports.md` and the type-mapping table in `references/schema-mapping.md`.

## Non-negotiable rules

These are the rules that most often separate code that compiles from code that does not.

**Imports come from the canonical list.** Mapping annotations live under
`org.springframework.data.mongodb.core.mapping`, *except* `@Id`, `@Transient`,
`@ReadOnlyProperty`, and `@PersistenceCreator`, which come from
`org.springframework.data.annotation`. The query API (`Query`, `Criteria`, `Update`)
lives under `org.springframework.data.mongodb.core.query`. `Sort`, `Pageable`, and
`PageRequest` come from `org.springframework.data.domain`. See `references/imports.md`.

**`@Field` needs an explicit import.** `org.springframework.data.mongodb.core.mapping.Field`
collides with `java.lang.reflect.Field` (and any wildcard that pulls the latter in).
Import it by name even when you wildcard the rest of the package, exactly as the project
snippets do.

**The `@Id` is a `String` mapped to `_id`.** Mongo's `_id` is an `ObjectId`/string, not
the source system's integer key. Map the business key (e.g. `customerId`) as its own
`@Field`, and keep `@Id private String id;`. Never map an `int`/`Integer` primary key
straight onto `@Id` when translating from a relational entity.

**Use `java.time` and `BigDecimal`, never legacy date constructors.** Prefer `LocalDate`,
`LocalDateTime`, `Instant`, and `BigDecimal`. Build dates with `LocalDate.of(2014, 12, 20)`.
**Never** write `new Date(2014, 12, 20)` — that constructor is deprecated and interprets
the year as 1900-relative, so it is both wrong and a smell that the code came from an old
model. Money/decimal columns map to `BigDecimal` (stored as `Decimal128`).

**No comments or placeholders in code that will be executed.** Generated translation/
validation code is compiled and run. `// TODO`, `...`, or stub method bodies break it.
Emit complete, runnable code.

**Schema classes avoid the `public` modifier unless required.** Match the project
convention: top-level mapping classes are package-private (`class OrderLine`), only the
entrypoint class carrying `main`/`build` is `public`.

**Embedded objects have no `@Document`.** Only aggregate roots that map to their own
collection get `@Document`. Value objects embedded inside another document (e.g. a
`Customer` embedded in `Order`) are plain classes — annotating them with `@Document` is
wrong and signals they should be a separate collection.

## Quick orientation example (the shape to aim for)

A correctly-imported aggregate root plus a `Query`/`Criteria` read. Study the imports —
they are the part most likely to be wrong.

```java
import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

import org.springframework.data.annotation.Id;
import org.springframework.data.domain.Sort;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.mongodb.core.mapping.Document;
import org.springframework.data.mongodb.core.mapping.Field;
import org.springframework.data.mongodb.core.query.Criteria;
import org.springframework.data.mongodb.core.query.Query;

@Document(collection = "orderLines")
class OrderLine {

    @Id
    private String id;

    @Field("orderLineId")
    private Integer orderLineId;

    @Field("pickingCompletedWhen")
    private LocalDateTime pickingCompletedWhen;

    private BigDecimal unitPrice;

    OrderLine() {
    }

    // getters and setters ...
}

class OrderLineQueries {

    private final MongoTemplate mongoTemplate;

    OrderLineQueries(MongoTemplate mongoTemplate) {
        this.mongoTemplate = mongoTemplate;
    }

    List<OrderLine> recentlyPicked() {
        LocalDateTime from = LocalDateTime.of(2014, 12, 20, 0, 0);
        LocalDateTime to = LocalDateTime.of(2014, 12, 31, 23, 59, 59);
        Query query = new Query(Criteria.where("pickingCompletedWhen").gte(from).lte(to))
                .with(Sort.by(Sort.Direction.ASC, "orderLineId"));
        return mongoTemplate.find(query, OrderLine.class);
    }
}
```

## Common traps (renamed or removed since the 3.x era)

These are the API changes that catch out a model trained on older docs. Full list in
`references/imports.md`.

- `MongoDbFactory` → **`MongoDatabaseFactory`** (`org.springframework.data.mongodb`).
- `SimpleMongoClientDbFactory` → **`SimpleMongoClientDatabaseFactory`**
  (`org.springframework.data.mongodb.core`).
- Jackson 2 `com.fasterxml.jackson.databind.*` → Jackson 3 **`tools.jackson.databind.*`**.
  Jackson *annotations* (`@JsonIgnoreProperties`, `@JsonInclude`) stay at
  `com.fasterxml.jackson.annotation.*`.
- `new Date(y, m, d)` → `LocalDate.of(y, m, d)` / `LocalDateTime.of(...)`.
- Repository `MongoRepository` still exists, but this project's pattern is **explicit
  `MongoTemplate` + `Query`/`Criteria`**, not derived-query repository interfaces. Prefer
  `MongoTemplate` unless the user asks for repositories.

## Project context (Universal Object Mapping)

This skill backs the `generate_translation_node` translator. When translating from a
relational ORM (EF Core, NHibernate, Dapper) into Spring Data MongoDB:

- A table usually becomes a `@Document` collection; a foreign-key child can become either
  an **embedded** array (denormalized into the parent) or a **`@DocumentReference`**
  (kept as a separate collection). `references/schema-mapping.md` explains when to pick
  which and how to express both.
- Keep query method shape close to the source: one source `Query1()` → one target
  `query1()` returning the same logical result set. Don't invent extra parameters.
- Field names in `@Field(...)` and in `Criteria.where(...)` are the **MongoDB document
  field names** (usually camelCase), not the Java property name and not the SQL column.

### Reference: aggregation

# Aggregation framework — Spring Data MongoDB 5.0

Use the aggregation framework when a query needs grouping, multi-stage transformation,
joins (`$lookup`), or computed fields — anything a single `Query`/`Criteria` find cannot
express. The builder lives in `org.springframework.data.mongodb.core.aggregation`.

## Table of contents

1. Pipeline basics: `newAggregation` vs `TypedAggregation`
2. The stage operators
3. Executing and reading results
4. `previousOperation()` and stage references
5. Output types (records, interfaces) and counting a pipeline
6. Worked examples

---

## 1. Pipeline basics

Static-import the factory so stages read like the Mongo pipeline (this matches the
official docs):

```java
import static org.springframework.data.mongodb.core.aggregation.Aggregation.*;
import static org.springframework.data.domain.Sort.Direction.DESC;

import org.springframework.data.mongodb.core.aggregation.Aggregation;
import org.springframework.data.mongodb.core.aggregation.AggregationResults;
import org.springframework.data.mongodb.core.aggregation.TypedAggregation;
```

`newAggregation(...)` builds an untyped pipeline; `newAggregation(Entity.class, ...)`
builds a `TypedAggregation<Entity>` that knows the input collection and maps field names
through the entity. Prefer the typed form when you have the entity class.

```java
TypedAggregation<OrderLine> agg = Aggregation.newAggregation(
        OrderLine.class,
        group("taxRate").count().as("count"),
        project("count").and("taxRate").previousOperation(),
        sort(DESC, "count"));
```

## 2. The stage operators

All produced by static methods on `Aggregation`:

| Stage | Mongo | Notes |
|---|---|---|
| `match(Criteria)` | `$match` | filter; reuse the same `Criteria.where(...)` API |
| `group("f")` / `group("a","b")` | `$group` | then `.count().as(..)`, `.sum("x").as(..)`, `.avg`, `.min`, `.max`, `.first`, `.last`, `.addToSet`, `.push` |
| `project("f"...)` | `$project` | include fields; `.and("x").as("y")`, `.andExpression(...)`, `.nested(bind(...))` |
| `sort(Direction, "f"...)` | `$sort` | or `sort(Sort)` |
| `unwind("arrayField")` | `$unwind` | flatten an array |
| `limit(n)` / `skip(n)` | `$limit` / `$skip` | |
| `count().as("name")` | `$count` | terminal count stage |
| `lookup("from","localF","foreignF","as")` | `$lookup` | join another collection |
| `addFields()` / `set(...)` | `$addFields`/`$set` | computed fields |
| `replaceRoot(...)` | `$replaceRoot` | promote a sub-document |

## 3. Executing and reading results

```java
AggregationResults<TagCount> results =
        mongoTemplate.aggregate(agg, OrderLine.class, TagCount.class);

List<TagCount> mapped = results.getMappedResults();   // all rows
TagCount unique       = results.getUniqueMappedResult(); // exactly one row, else null
```

`mongoTemplate.aggregate(...)` overloads:

- `aggregate(TypedAggregation<I>, Class<O> out)` — input collection from the typed agg.
- `aggregate(Aggregation, Class<I> in, Class<O> out)` — input collection from `in`.
- `aggregate(Aggregation, String collectionName, Class<O> out)` — explicit collection.

## 4. `previousOperation()` and stage references

Inside a `project` (or `sort`), `previousOperation()` refers to the `_id` produced by the
preceding `group`. This is how you rename the group key:

```java
group("taxRate").count().as("count"),     // _id = taxRate, count = n
project("count").and("taxRate").previousOperation()  // expose group _id as "taxRate"
```

`sort(DESC, previousOperation(), "totalPop")` sorts by the previous group key plus a field.

## 5. Output types and counting a pipeline

A record or a plain class both work as the output type; field names must match the
projected names.

```java
record TagCount(String taxRate, Long count) {}
record CountProjection(Long count) {}
```

To count how many rows a pipeline yields, append a `$count` stage to a copy of the
pipeline and read the unique result (pattern used in the project harness):

```java
var baseOps = new java.util.ArrayList<>(agg.getPipeline().getOperations());
baseOps.add(Aggregation.count().as("count"));
var countAgg = Aggregation.newAggregation(OrderLine.class, baseOps);
CountProjection cp = mongoTemplate.aggregate(countAgg, OrderLine.class, CountProjection.class)
        .getUniqueMappedResult();
long total = cp != null ? cp.count() : 0L;
```

Inspect the compiled pipeline for debugging with `agg.toString()`.

## 6. Worked examples

Count documents per `taxRate`, highest first:

```java
import static org.springframework.data.mongodb.core.aggregation.Aggregation.*;
import static org.springframework.data.domain.Sort.Direction.DESC;

TypedAggregation<OrderLine> agg = newAggregation(
        OrderLine.class,
        group("taxRate").count().as("count"),
        project("count").and("taxRate").previousOperation(),
        sort(DESC, "count"));

record TaxRateCount(java.math.BigDecimal taxRate, Long count) {}

List<TaxRateCount> rows =
        mongoTemplate.aggregate(agg, OrderLine.class, TaxRateCount.class).getMappedResults();
```

Filter then group (sum quantity per order, only completed lines):

```java
TypedAggregation<OrderLine> agg = newAggregation(
        OrderLine.class,
        match(org.springframework.data.mongodb.core.query.Criteria
                .where("pickedQuantity").gt(0)),
        group("orderId").sum("quantity").as("totalQty"),
        sort(DESC, "totalQty"));

record OrderQty(Integer orderId, Long totalQty) {}
List<OrderQty> rows =
        mongoTemplate.aggregate(agg, OrderLine.class, OrderQty.class).getMappedResults();
```

Join with `$lookup` (order lines for each order):

```java
TypedAggregation<Order> agg = newAggregation(
        Order.class,
        match(org.springframework.data.mongodb.core.query.Criteria.where("customerId").is(1)),
        lookup("orderLines", "orderId", "orderId", "lines"));
```

When the source query was a simple filter/sort/projection, do **not** reach for
aggregation — translate it to a `Query`/`Criteria` find (see `queries.md`). Use
aggregation only for grouping/joining/computed transformations.

### Reference: imports

# Canonical imports — Spring Data MongoDB 5.0 / Spring Boot 4 / Jackson 3

This is the source of truth for imports. If a class is not here, look it up before using
it — do not guess the package. Every entry below is valid for Spring Data MongoDB 5.0.x
(Spring Boot 4.0.x) on Java 25.

## Table of contents

1. Mapping annotations
2. Identity (`@Id`) and lifecycle annotations
3. Indexing annotations
4. Query API (`Query`, `Criteria`, `Update`)
5. Sorting / paging (`Sort`, `Pageable`)
6. `MongoTemplate` and operations interfaces
7. Manual bootstrap (standalone `MongoTemplate`, no Spring context)
8. Aggregation framework
9. MongoDB Java driver
10. Jackson 3 (serialization for harnesses)
11. Renamed / removed — do NOT use the left column

---

## 1. Mapping annotations — `org.springframework.data.mongodb.core.mapping`

```java
import org.springframework.data.mongodb.core.mapping.Document;          // class -> collection
import org.springframework.data.mongodb.core.mapping.Field;             // field -> document key (import by name; see note)
import org.springframework.data.mongodb.core.mapping.FieldType;         // explicit BSON type for @Field(targetType = ...)
import org.springframework.data.mongodb.core.mapping.MongoId;           // _id with explicit target type (alternative to @Id)
import org.springframework.data.mongodb.core.mapping.DocumentReference; // reference stored as target's _id (preferred ref)
import org.springframework.data.mongodb.core.mapping.DBRef;            // legacy {$ref,$id} reference
import org.springframework.data.mongodb.core.mapping.Sharded;          // sharded collection metadata
import org.springframework.data.mongodb.core.mapping.TimeSeries;       // time-series collection
```

> **`@Field` import note.** `org.springframework.data.mongodb.core.mapping.Field` clashes
> with `java.lang.reflect.Field`. Always import it explicitly by name, even if you
> wildcard the rest of `core.mapping`. The project snippets do exactly this:
> `import org.springframework.data.mongodb.core.mapping.*;` followed by
> `import org.springframework.data.mongodb.core.mapping.Field;`.

## 2. Identity & lifecycle — `org.springframework.data.annotation`

These are NOT in the mongodb package. This is the most common import mistake.

```java
import org.springframework.data.annotation.Id;                 // maps property to _id
import org.springframework.data.annotation.Transient;          // exclude from persistence
import org.springframework.data.annotation.ReadOnlyProperty;   // populated on read, never written
import org.springframework.data.annotation.PersistenceCreator; // chosen constructor for instantiation
import org.springframework.data.annotation.Version;            // optimistic locking
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.LastModifiedDate;
```

`@Id` (from `data.annotation`) is the idiomatic choice. Use `@MongoId` (from
`core.mapping`) only when you need to pin the BSON target type of `_id`.

## 3. Indexing — `org.springframework.data.mongodb.core.index`

```java
import org.springframework.data.mongodb.core.index.Indexed;
import org.springframework.data.mongodb.core.index.CompoundIndex;
import org.springframework.data.mongodb.core.index.CompoundIndexes;
import org.springframework.data.mongodb.core.index.TextIndexed;
import org.springframework.data.mongodb.core.index.GeoSpatialIndexed;
import org.springframework.data.mongodb.core.index.HashIndexed;
```

## 4. Query API — `org.springframework.data.mongodb.core.query`

```java
import org.springframework.data.mongodb.core.query.Query;     // Query, Query.query(...), new Query(criteria)
import org.springframework.data.mongodb.core.query.Criteria;  // Criteria.where(...), and/or/not operators
import org.springframework.data.mongodb.core.query.Update;    // Update.update(...), set/inc/push for writes
import org.springframework.data.mongodb.core.query.Collation; // case-insensitive / locale collation
import org.springframework.data.mongodb.core.query.BasicQuery;// raw JSON query string
```

Static-import convenience (optional, mirrors the official docs):

```java
import static org.springframework.data.mongodb.core.query.Criteria.where;
import static org.springframework.data.mongodb.core.query.Query.query;
import static org.springframework.data.mongodb.core.query.Update.update;
```

## 5. Sorting & paging — `org.springframework.data.domain`

```java
import org.springframework.data.domain.Sort;        // Sort.by(Sort.Direction.ASC, "field")
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.PageRequest;  // PageRequest.of(page, size, sort)
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Slice;
```

## 6. Template & operations — `org.springframework.data.mongodb.core`

```java
import org.springframework.data.mongodb.core.MongoTemplate;     // primary entry point
import org.springframework.data.mongodb.core.MongoOperations;   // interface MongoTemplate implements
import org.springframework.data.mongodb.core.ExecutableFindOperation; // fluent template().query(...) API
```

## 7. Manual bootstrap (standalone `MongoTemplate`)

Use this when wiring a `MongoTemplate` by hand (validation/translation harnesses) rather
than relying on Spring Boot autoconfiguration.

```java
import org.springframework.data.mongodb.MongoDatabaseFactory;                  // NOTE: ...mongodb, not ...mongodb.core
import org.springframework.data.mongodb.core.SimpleMongoClientDatabaseFactory; // current name (NOT ...DbFactory)
import org.springframework.data.mongodb.core.convert.MappingMongoConverter;
import org.springframework.data.mongodb.core.convert.DefaultDbRefResolver;
import org.springframework.data.mongodb.core.convert.DefaultMongoTypeMapper;
import org.springframework.data.mongodb.core.convert.MongoCustomConversions;
import org.springframework.data.mongodb.core.mapping.MongoMappingContext;
```

## 8. Aggregation — `org.springframework.data.mongodb.core.aggregation`

```java
import org.springframework.data.mongodb.core.aggregation.Aggregation;        // factory: newAggregation, group, project, match, sort, unwind, limit, count, lookup
import org.springframework.data.mongodb.core.aggregation.TypedAggregation;   // type-bound pipeline
import org.springframework.data.mongodb.core.aggregation.AggregationResults; // .getMappedResults(), .getUniqueMappedResult()
import org.springframework.data.mongodb.core.aggregation.AggregationOperation;
import org.springframework.data.mongodb.core.aggregation.GroupOperation;
import org.springframework.data.mongodb.core.aggregation.ProjectionOperation;
import org.springframework.data.mongodb.core.aggregation.MatchOperation;
```

Static-import convenience (recommended for readable pipelines, matches official docs):

```java
import static org.springframework.data.mongodb.core.aggregation.Aggregation.*;
// gives: newAggregation, group, project, match, sort, unwind, limit, skip, count, lookup, previousOperation, bind
import static org.springframework.data.domain.Sort.Direction.ASC;
import static org.springframework.data.domain.Sort.Direction.DESC;
```

## 9. MongoDB Java driver — `com.mongodb.client`

```java
import com.mongodb.client.MongoClients; // MongoClients.create(uri)
import com.mongodb.client.MongoClient;
```

## 10. Jackson 3 (only when a harness serializes results to JSON)

Jackson 3 moved **databind and core** to the `tools.jackson` namespace. Annotations did
**not** move — they remain under `com.fasterxml.jackson.annotation`.

```java
// databind / core — tools.jackson.*
import tools.jackson.databind.json.JsonMapper;
import tools.jackson.databind.SerializationFeature;
import tools.jackson.databind.MapperFeature;
import tools.jackson.databind.module.SimpleModule;
import tools.jackson.databind.ser.std.StdSerializer;
import tools.jackson.databind.SerializationContext;
import tools.jackson.core.JsonGenerator;
import tools.jackson.core.StreamWriteFeature;
import tools.jackson.databind.cfg.DateTimeFeature;

// annotations — still com.fasterxml.jackson.annotation
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonInclude.Include;
```

## 11. Renamed / removed — do NOT use the left column

| Wrong (old / hallucinated) | Correct (5.0) |
|---|---|
| `org.springframework.data.mongodb.MongoDbFactory` | `org.springframework.data.mongodb.MongoDatabaseFactory` |
| `SimpleMongoClientDbFactory` | `SimpleMongoClientDatabaseFactory` |
| `SimpleMongoDbFactory` (driver 3.x) | `SimpleMongoClientDatabaseFactory` |
| `com.fasterxml.jackson.databind.ObjectMapper` | `tools.jackson.databind.json.JsonMapper` (Jackson 3) |
| `com.fasterxml.jackson.databind.*` (databind) | `tools.jackson.databind.*` |
| `new com.mongodb.MongoClient(...)` (driver 3.x) | `com.mongodb.client.MongoClients.create(uri)` |
| `@org.springframework.data.mongodb.core.mapping.Id` | `@org.springframework.data.annotation.Id` |
| `java.util.Date` for date columns | `java.time.LocalDate` / `LocalDateTime` / `Instant` |
| `new Date(2014, 12, 20)` | `LocalDate.of(2014, 12, 20)` |
| `MongoTemplate#findAllAndRemove` confusions | use `find`, `findOne`, `count`, `exists` (see queries.md) |

### Reference: queries

# Queries — `MongoTemplate` + Query/Criteria API (Spring Data MongoDB 5.0)

This project queries with explicit `MongoTemplate` calls and the `Query`/`Criteria`
builder, not derived-query repository interfaces. Keep query method shape close to the
source: one source query method → one target method returning the same logical result.

## Table of contents

1. Building a `Query` with `Criteria`
2. Criteria operators (the ones you actually need)
3. Executing reads on `MongoTemplate`
4. Sorting, `limit`, `skip`, paging
5. Field projection (include/exclude) and typed projections
6. Counting and existence
7. The fluent / typed `template.query(...)` API
8. Dates, decimals, and literals in queries
9. Worked examples (mirroring the project harness)

---

## 1. Building a `Query` with `Criteria`

Two equivalent constructions:

```java
import org.springframework.data.mongodb.core.query.Criteria;
import org.springframework.data.mongodb.core.query.Query;

// constructor form
Query q1 = new Query(Criteria.where("customerId").is(1));

// static factory form (with static imports of where / query)
Query q2 = query(where("customerId").is(1));
```

Combine criteria:

```java
Query ranged = new Query(
        Criteria.where("pickingCompletedWhen")
                .gte(LocalDate.of(2014, 12, 20))
                .lte(LocalDate.of(2014, 12, 31)));

// AND across different fields: chain .and(...)
Query andQuery = new Query(
        Criteria.where("orderId").is(42).and("quantity").gt(0));

// explicit boolean operators
Query orQuery = new Query(new Criteria().orOperator(
        Criteria.where("taxRate").is(BigDecimal.ZERO),
        Criteria.where("taxRate").gt(new BigDecimal("15"))));
```

`addCriteria` appends to an existing query: `q.addCriteria(Criteria.where("x").is(1));`.

## 2. Criteria operators (the ones you actually need)

| Method | Mongo operator | Meaning |
|---|---|---|
| `.is(v)` | `$eq` | equals |
| `.ne(v)` | `$ne` | not equals |
| `.gt(v)` / `.gte(v)` | `$gt` / `$gte` | greater (or equal) |
| `.lt(v)` / `.lte(v)` | `$lt` / `$lte` | less (or equal) |
| `.in(a, b, ...)` / `.in(coll)` | `$in` | in set |
| `.nin(...)` | `$nin` | not in set |
| `.exists(true)` | `$exists` | field present |
| `.regex("^H")` | `$regex` | regular expression |
| `.ne(null)` / `.exists(true)` | — | "is not null" patterns |
| `.and("field")` | — | continue building on another field |
| `.orOperator(c...)` | `$or` | logical OR |
| `.andOperator(c...)` | `$and` | logical AND |
| `.norOperator(c...)` | `$nor` | logical NOR |
| `.not()` | `$not` | negate the next operator |
| `.size(n)` | `$size` | array length |
| `.elemMatch(c)` | `$elemMatch` | array element matches sub-criteria |

## 3. Executing reads on `MongoTemplate`

```java
import java.util.List;
import org.springframework.data.mongodb.core.MongoTemplate;

List<OrderLine> all      = mongoTemplate.find(query, OrderLine.class);
OrderLine       one      = mongoTemplate.findOne(query, OrderLine.class); // first match or null
OrderLine       byId     = mongoTemplate.findById("652f...", OrderLine.class);
List<OrderLine> everyDoc = mongoTemplate.findAll(OrderLine.class);
long            n        = mongoTemplate.count(query, OrderLine.class);
boolean         any      = mongoTemplate.exists(query, OrderLine.class);
String          coll     = mongoTemplate.getCollectionName(OrderLine.class);
```

The entity `Class` argument both selects the collection and drives mapping. Pass a second
collection-name string overload only when querying a collection that doesn't match the
entity's `@Document`.

## 4. Sorting, `limit`, `skip`, paging

`Query` is mutable and fluent; `with`, `limit`, `skip` return the same instance.

```java
import org.springframework.data.domain.Sort;
import org.springframework.data.domain.PageRequest;

Query sorted = new Query()
        .with(Sort.by(Sort.Direction.DESC, "quantity"))
        .limit(50);

Query firstByKey = new Query(Criteria.where("customerId").is(1))
        .with(Sort.by(Sort.Direction.ASC, "orderId"))
        .limit(1);

// deterministic "last" element via skip
long count = mongoTemplate.count(base, OrderLine.class);
Query last = new Query()
        .with(Sort.by(Sort.Direction.ASC, "orderLineId"))
        .skip(count - 1)
        .limit(1);

// page-based
Query paged = new Query().with(PageRequest.of(0, 20, Sort.by("orderId")));
```

> Note: `new Query().with(sort)` mutates and returns the same object. When you need an
> independent variant, build a fresh `Query` rather than reusing one you've already
> mutated.

## 5. Field projection and typed projections

Include/exclude document fields:

```java
Query q = new Query();
q.fields().include("orderLineId", "quantity"); // only these (+ _id) come back
// q.fields().exclude("largeBlob");
```

Typed (interface) projection via the fluent API returns only the projected shape:

```java
interface OrderLineView {
    Integer getOrderLineId();
    Integer getQuantity();
}

OrderLineView v = mongoTemplate.query(OrderLine.class)
        .as(OrderLineView.class)
        .matching(new Query().with(Sort.by(Sort.Direction.ASC, "orderLineId")).limit(1))
        .firstValue();
```

## 6. Counting and existence

```java
long c   = mongoTemplate.count(query, OrderLine.class);
boolean e = mongoTemplate.exists(query, OrderLine.class);

// fluent equivalent
long c2 = mongoTemplate.query(OrderLine.class).matching(query).count();
```

`count(new Query(), X.class)` counts the whole collection. Counting ignores `limit`/`skip`
on the query object, so build a dedicated count query when needed.

## 7. The fluent / typed `template.query(...)` API

`ExecutableFindOperation` reads fluently and is handy for projections and single values:

```java
List<OrderLine> list = mongoTemplate.query(OrderLine.class)
        .matching(query(where("customerId").is(1)))
        .all();

OrderLine first = mongoTemplate.query(OrderLine.class)
        .matching(query(where("customerId").is(1)).with(Sort.by("orderId")))
        .firstValue();

Optional<OrderLine> opt = mongoTemplate.query(OrderLine.class)
        .matching(query(where("orderLineId").is(7)))
        .one();
```

## 8. Dates, decimals, and literals in queries

- Dates: build with `java.time` factories — `LocalDate.of(2014, 12, 20)`,
  `LocalDateTime.of(2014, 12, 20, 0, 0)`, `Instant.parse(...)`. The field type in the
  entity must match what you compare against. **Never** `new Date(2014, 12, 20)`.
- Decimals: compare with `BigDecimal` literals via the string constructor to avoid binary
  float error — `new BigDecimal("15.00")`, not `15.00`.
- Inspecting the generated filter (useful in harnesses):
  `query.getQueryObject()`, `query.getSortObject()`, `query.getFieldsObject()` return the
  `org.bson.Document` Mongo will run.

## 9. Worked examples (mirroring the project harness)

Range filter + deterministic samples:

```java
Query q = new Query(Criteria.where("pickingCompletedWhen")
        .gte(LocalDate.of(2014, 12, 20))
        .lte(LocalDate.of(2014, 12, 31)));
long count = mongoTemplate.count(q, OrderLine.class);
OrderLine firstSample = mongoTemplate.findOne(
        q.with(Sort.by(Sort.Direction.ASC, "orderLineId")).limit(1), OrderLine.class);
```

Equality on a business key against an embedded-bearing root:

```java
Query byCustomer = new Query(Criteria.where("customerId").is(1));
List<Order> orders = mongoTemplate.find(byCustomer, Order.class);
```

Top-N by a field:

```java
Query topByQty = new Query()
        .with(Sort.by(Sort.Direction.DESC, "quantity"))
        .limit(50);
List<OrderLine> top = mongoTemplate.find(topByQty, OrderLine.class);
```

Projection to two fields:

```java
Query proj = new Query();
proj.fields().include("orderLineId", "quantity");
List<OrderLine> slim = mongoTemplate.find(proj, OrderLine.class);
```

For grouping/counting by a field (e.g. "count per taxRate"), that is an aggregation, not a
`Query` — see `aggregation.md`.

### Reference: schema-mapping

# Schema mapping — Spring Data MongoDB 5.0 document classes

How to turn a domain model (or a relational entity being migrated) into Spring Data
MongoDB mapping classes that map cleanly and round-trip through `MongoTemplate`.

## Table of contents

1. The anatomy of an aggregate root
2. The `@Id` / `_id` rule (most common mistake)
3. Field mapping and `@Field`
4. Type mapping table (Java ↔ BSON)
5. Embedding vs referencing
6. `@DocumentReference` and `@DBRef`
7. Indexes
8. Constructors, access modifiers, getters/setters
9. Standalone `MongoTemplate` bootstrap (for harnesses)

---

## 1. Anatomy of an aggregate root

An aggregate root maps to one collection and carries `@Document`. Keep top-level mapping
classes package-private (no `public`), matching project convention.

```java
import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;

import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;
import org.springframework.data.mongodb.core.mapping.Field;

@Document(collection = "orders")
class Order {

    @Id
    private String id;

    @Field("orderId")
    private Integer orderId;

    @Field("customerId")
    private Integer customerId;

    private Customer customer; // embedded value object (no @Document)

    Order() {
    }

    // getters and setters ...
}
```

`@Document(collection = "orders")` pins the collection name. Without the `collection`
attribute the collection defaults to the decapitalized class name (`order`), which is
usually NOT what you want when matching an existing collection — always set it explicitly.

## 2. The `@Id` / `_id` rule (most common mistake)

MongoDB's primary key is `_id`. Spring maps the `@Id`-annotated property to `_id`.

- Use `@Id private String id;`. A `String` accepts both `ObjectId` hex strings and
  natural string keys, so it is the safe default.
- When migrating a relational entity whose key is `int CustomerID`, **do not** put `@Id`
  on an `Integer customerId`. Instead keep a separate `@Id private String id;` for `_id`,
  and map the business key as `@Field("customerId") private Integer customerId;`.
- Use `@MongoId` (from `core.mapping`) only when you must control the BSON type of `_id`
  (e.g. force an `ObjectId`).

Wrong (collapses the natural key onto `_id`, loses the Mongo identity):

```java
@Id
private Integer customerId; // ❌ don't map an int PK onto _id
```

Right:

```java
@Id
private String id;          // _id

@Field("customerId")
private Integer customerId; // business key preserved as its own field
```

## 3. Field mapping and `@Field`

- A property with no annotation is stored under its Java name.
- Use `@Field("documentKey")` when the stored key differs (e.g. the existing collection
  uses camelCase and differs from the Java name, or you want to be explicit).
- The string in `@Field(...)`, in `Criteria.where(...)`, and in aggregation stages is the
  **MongoDB document field name** — not the Java property and not the SQL column.
- Import `Field` by name (clashes with `java.lang.reflect.Field`; see `imports.md`).
- For an explicit BSON type, use `@Field(targetType = FieldType.DECIMAL128)`.

## 4. Type mapping table (Java ↔ BSON)

Choose Java types deliberately when translating from SQL/.NET. These map predictably:

| Source intent | Java type | BSON | Notes |
|---|---|---|---|
| identity / `_id` | `String` | ObjectId or String | `@Id` |
| 32-bit int | `Integer` | int32 | |
| 64-bit int / bigint | `Long` | int64 | |
| `decimal` / money | `BigDecimal` | Decimal128 | In 5.0 the representation default changed; `BigDecimal` → Decimal128 is the safe explicit choice |
| `float`/`double` | `Double` | double | avoid for money |
| `bit`/`bool` | `Boolean` | bool | |
| `date` (no time) | `LocalDate` | Date | build via `LocalDate.of(y, m, d)` |
| `datetime`/`timestamp` | `LocalDateTime` | Date | `LocalDateTime.of(...)` |
| instant / UTC | `Instant` | Date | |
| `nvarchar`/text | `String` | string | |
| `uniqueidentifier`/UUID | `java.util.UUID` | binary/string | 5.0 no longer defaults the UUID representation — set it explicitly if needed |
| array / collection | `List<T>` | array | |

**Never** use `java.util.Date` or `new Date(y, m, d)` — see `imports.md` §11.

## 5. Embedding vs referencing

When a relational parent/child (one-to-many via FK) becomes MongoDB, you choose:

**Embed** the child inside the parent when the child is owned by and always read with the
parent, the child set is bounded, and you want a single read. The embedded class is a
plain value object — **no `@Document`**, no `@Id`.

```java
@Document(collection = "orders")
class Order {
    @Id
    private String id;
    @Field("orderId")
    private Integer orderId;
    private Customer customer;                 // single embedded object
    // getters/setters ...
}

class Customer {                              // embedded value object: NO @Document
    private Integer customerId;
    private String customerName;
    private LocalDate accountOpenedDate;
    private BigDecimal creditLimit;
    private List<CustomerTransaction> customerTransactions = new ArrayList<>(); // embedded array
    // getters/setters ...
}

class CustomerTransaction {                   // embedded value object: NO @Document
    private Integer customerTransactionId;
    private LocalDate transactionDate;
    private BigDecimal transactionAmount;
    // getters/setters ...
}
```

**Reference** the child as a separate collection when it is large, shared, or queried
independently. See §6.

Rule of thumb when translating: a child table that is only ever accessed through its
parent → embed; a child table that is itself an aggregate root or is huge → reference.

## 6. `@DocumentReference` and `@DBRef`

Prefer `@DocumentReference` (stores the target's `_id`, flexible lookup) over the legacy
`@DBRef` (stores a `{$ref,$id}` document).

A lazy, read-only back-reference resolved by a custom lookup (as used in the project's
`Order` → `OrderLine` link):

```java
import java.util.List;
import org.springframework.data.annotation.ReadOnlyProperty;
import org.springframework.data.mongodb.core.mapping.DocumentReference;

@ReadOnlyProperty
@DocumentReference(lazy = true, lookup = "{ 'orderId': ?#{#self.orderId} }", sort = "{ 'orderLineId': 1 }")
private List<OrderLine> orderLines;
```

- `lazy = true` defers resolution until the field is accessed.
- `lookup = "{ 'orderId': ?#{#self.orderId} }"` matches `OrderLine.orderId` against this
  document's `orderId` (SpEL `#self`), instead of matching on `_id`.
- `@ReadOnlyProperty` means the field is populated on read and never written back.

Simple reference (stores referenced `_id`):

```java
import org.springframework.data.mongodb.core.mapping.DocumentReference;

@DocumentReference
private Warehouse warehouse;
```

## 7. Indexes

```java
import org.springframework.data.mongodb.core.index.Indexed;
import org.springframework.data.mongodb.core.index.CompoundIndex;

@Document(collection = "people")
@CompoundIndex(name = "name_age_idx", def = "{'lastName': 1, 'age': -1}")
class Person {
    @Id
    private String id;
    @Indexed(unique = true)
    private Integer ssn;
    @Field("fName")
    private String firstName;
    // ...
}
```

For a pure migration/validation scenario you usually don't need indexes — add them only
when the source schema or the user calls for them.

## 8. Constructors, access modifiers, getters/setters

- Provide a no-arg constructor (Spring instantiates via it unless a `@PersistenceCreator`
  constructor is present).
- Keep classes package-private; only the harness/entrypoint class with `main` is `public`.
- Provide getters/setters for mapped fields. If serializing results with Jackson in a
  harness, getters are what Jackson reads.
- Do not put `public` on every field/class reflexively — it diverges from the project
  snippets and is unnecessary.

## 9. Standalone `MongoTemplate` bootstrap (for harnesses)

When code must run outside a Spring context (validation/translation harness), build the
`MongoTemplate` by hand. This exact wiring is what the project snippets use:

```java
import com.mongodb.client.MongoClients;
import org.springframework.data.mongodb.MongoDatabaseFactory;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.mongodb.core.SimpleMongoClientDatabaseFactory;
import org.springframework.data.mongodb.core.convert.DefaultDbRefResolver;
import org.springframework.data.mongodb.core.convert.DefaultMongoTypeMapper;
import org.springframework.data.mongodb.core.convert.MappingMongoConverter;
import org.springframework.data.mongodb.core.convert.MongoCustomConversions;
import org.springframework.data.mongodb.core.mapping.MongoMappingContext;

final class MongoTemplateFactory {
    private MongoTemplateFactory() {
    }

    static MongoTemplate create(String mongoUri, String mongoDatabase) {
        MongoDatabaseFactory databaseFactory =
                new SimpleMongoClientDatabaseFactory(MongoClients.create(mongoUri), mongoDatabase);

        MongoCustomConversions customConversions = MongoCustomConversions.create(configuration -> {});

        MongoMappingContext mappingContext = new MongoMappingContext();
        mappingContext.setSimpleTypeHolder(customConversions.getSimpleTypeHolder());
        mappingContext.afterPropertiesSet();

        MappingMongoConverter converter =
                new MappingMongoConverter(new DefaultDbRefResolver(databaseFactory), mappingContext);
        converter.setCustomConversions(customConversions);
        converter.setTypeMapper(new DefaultMongoTypeMapper(null)); // null => omit _class type hints
        converter.afterPropertiesSet();

        return new MongoTemplate(databaseFactory, converter);
    }
}
```

`new DefaultMongoTypeMapper(null)` suppresses the `_class` discriminator field so reads
against an existing collection don't expect Spring-written type hints. Validate each
aggregate root with a one-document fetch:

```java
Query probe = new Query().limit(1);
mongoTemplate.findOne(probe, Order.class); // throws MappingException if the mapping is wrong
```

Only validate `@Document` aggregate roots this way — embedded value objects (no
`@Document`) are not fetched directly.

--- TARGET-LANGUAGE MAPPING REFERENCE ---
Quick source->target mapping reference. For AUTHORITATIVE, version-correct imports and API surface, rely on the TARGET FRAMEWORK SKILL above — never on memory for imports. Apply these patterns to the user's OWN entities/fields/queries only; never introduce names from this reference.

Type mapping (.NET -> Java):
- `int`/`int?` -> `Integer`;  `long`/`long?` -> `Long`;  `bool` -> `Boolean`
- `decimal`/`decimal?` -> `BigDecimal` (NEVER `double` for money)
- `DateTime`/`DateTime?` -> `LocalDateTime` (date-only intent -> `LocalDate`)
- `string` -> `String`;  `Guid` -> `String` (or `UUID`)
- `IList<T>`/`List<T>` navigation -> embedded `List<T>` (document store) or a relationship (graph store)

Annotation / entity mapping (relational -> target ORM):
- Spring Data MongoDB: `[Table]`/`ClassMapping<T>` -> `@Document(collection="...")`; `[Key]`/`Id(...)` -> `@Id private String id;` (Mongo `_id` is a String — keep the source integer key as its OWN `@Field`); other columns -> `@Field("camelCaseName")`. Value objects embedded in a parent document have NO `@Document`.
- Spring Data Neo4j: `[Table]`/`ClassMapping<T>` -> `@Node("Label")`; `[Key]`/`Id(...)` -> `@Id @GeneratedValue private Long id;` (keep the source integer key as its own `@Property`); other columns -> `@Property("camelCaseName")`; navigations -> `@Relationship(type="...", direction=...)`.
- Names in `@Field`/`@Property`/`Criteria.where(...)`/Cypher are the TARGET store's field names (usually camelCase), NOT the SQL column and NOT the Java property.

Query API (translate the query BODY; keep each method 1:1 with the source query, same result shape, no extra params):
- Spring Data MongoDB: `MongoTemplate` + `Query`/`Criteria` (`.where().gte().lte()`, `.in()`, `.regex()`), `Sort` for ordering, `Aggregation` for group/having/count. Details: the "queries" and "aggregation" references in the TARGET FRAMEWORK SKILL above.
- Spring Data Neo4j: `Neo4jTemplate` + Cypher-DSL `Statement` (typed builders), NOT string concatenation. Details: the "queries" and "traversals" references in the TARGET FRAMEWORK SKILL above.

--- FRAGMENT STRUCTURE REFERENCE ---
The examples below show the STRUCTURE of the schema classes and per-query classes for this framework
pair. You save the schema classes via `save_schema_translation` and each `Query<N>` class via
`save_query_translation` (one call per query id). The imports, JSON serializer, runtime support, DB
template factory AND the entrypoint `main` (which runs every query with try/catch and writes the
results JSON) are injected/generated automatically — they MUST NOT appear in your fragments.

Imitate the SHAPE only (class layout, harness method signatures, flat count/firstSample/lastSample
result maps). Use exclusively the user's own entities, fields, and queries — never this example's
WideWorldImporters domain content.

<fragment_structure side="source" framework=".NET NHibernate">
public class Customer
{
    [JsonPropertyName("customerId")]
    public virtual int CustomerID { get; set; }
    public virtual required string CustomerName { get; set; }
    public virtual DateTime AccountOpenedDate { get; set; }
    public virtual decimal? CreditLimit { get; set; }
    public virtual IList<CustomerTransaction> CustomerTransactions { get; set; } = [];
}

public class CustomerTransaction
{
    [JsonPropertyName("customerTransactionId")]
    public virtual int CustomerTransactionID { get; set; }
    [JsonPropertyName("customerId")]
    public virtual int CustomerID { get; set; }
    public virtual DateTime TransactionDate { get; set; }
    public virtual decimal TransactionAmount { get; set; }
}

public class Order
{
    [JsonPropertyName("orderId")]
    public virtual int OrderID { get; set; }
    [JsonPropertyName("customerId")]
    public virtual int CustomerID { get; set; }
    public virtual Customer Customer { get; set; } = null!;
    public virtual IList<OrderLine> OrderLines { get; set; } = [];
}

public class OrderLine
{
    [JsonPropertyName("orderLineId")]
    public virtual int OrderLineID { get; set; }
    [JsonPropertyName("orderId")]
    public virtual int OrderID { get; set; }
    [JsonPropertyName("stockItemId")]
    public virtual int StockItemID { get; set; }
    public virtual required string Description { get; set; }
    [JsonPropertyName("packageTypeId")]
    public virtual int PackageTypeID { get; set; }
    public virtual int Quantity { get; set; }
    public virtual decimal? UnitPrice { get; set; }
    public virtual decimal TaxRate { get; set; }
    public virtual int PickedQuantity { get; set; }
    public virtual DateTime? PickingCompletedWhen { get; set; }
    public virtual int LastEditedBy { get; set; }
    public virtual DateTime LastEditedWhen { get; set; }
}

public class CustomerMap : ClassMapping<Customer> {
    public CustomerMap() {
        Table("Customers"); Schema("Sales");
        Id(x => x.CustomerID, m => m.Generator(Generators.Identity));
        Property(x => x.CustomerName);
        Property(x => x.AccountOpenedDate);
        Property(x => x.CreditLimit);
        Bag(x => x.CustomerTransactions, map => { map.Key(k => k.Column("CustomerID")); map.Inverse(true); }, rel => rel.OneToMany());
    }
}
public class CustomerTransactionMap : ClassMapping<CustomerTransaction> {
    public CustomerTransactionMap() {
        Table("CustomerTransactions"); Schema("Sales");
        Id(x => x.CustomerTransactionID, m => m.Generator(Generators.Identity));
        Property(x => x.CustomerID, m => { m.Insert(false); m.Update(false); });
        Property(x => x.TransactionDate);
        Property(x => x.TransactionAmount);
    }
}
public class OrderMap : ClassMapping<Order> {
    public OrderMap() {
        Table("Orders"); Schema("Sales");
        Id(x => x.OrderID, m => m.Generator(Generators.Identity));
        Property(x => x.CustomerID, m => { m.Insert(false); m.Update(false); });
        ManyToOne(x => x.Customer, m => m.Column("CustomerID"));
        Bag(x => x.OrderLines, map => { map.Key(k => k.Column("OrderID")); map.Inverse(true); }, rel => rel.OneToMany());
    }
}
public class OrderLineMap : ClassMapping<OrderLine> {
    public OrderLineMap() {
        Table("OrderLines"); Schema("Sales");
        Id(x => x.OrderLineID, m => m.Generator(Generators.Identity));
        Property(x => x.OrderID, m => { m.Insert(false); m.Update(false); });
        Property(x => x.StockItemID);
        Property(x => x.Description);
        Property(x => x.PackageTypeID);
        Property(x => x.Quantity);
        Property(x => x.UnitPrice);
        Property(x => x.TaxRate);
        Property(x => x.PickedQuantity);
        Property(x => x.PickingCompletedWhen);
        Property(x => x.LastEditedBy);
        Property(x => x.LastEditedWhen);
    }
}

public record Query3Projection
{
    public decimal TaxRate { get; set; }
    public long Count { get; set; }
}

public record Query5Projection
{
    public int OrderLineID { get; set; }
    public int Quantity { get; set; }
}

// --- Query Entrypoint ---
</fragment_structure>

<fragment_structure side="target" framework="Java Spring Data MongoDB">
/**
 * Order document with embedded Customer and CustomerTransactions.
 * 
 * TRANSLATED FROM: C# EFCore Customer, CustomerTransaction entities
 * ARCHITECTURAL SHIFT: Denormalized - Customers no longer a root collection.
 *                      Instead, Customer and its transactions are embedded within Order.
 */
@Document(collection = "orders")
@JsonIgnoreProperties({ "id" })
class Order {

    @Id
    private String id;

    @Field("orderId")
    private Integer orderId;

    @Field("customerId")
    private Integer customerId;

    // Embedded Customer document (denormalized from Sales.Customers table)
    private Customer customer;

    @ReadOnlyProperty
    @DocumentReference(lazy = true, lookup = "{ 'orderId': ?#{#self.orderId} }", sort = "{ 'orderLineId': 1 }")
    private List<OrderLine> orderLines;

    // Constructors
    public Order() {
    }

    // Getters and Setters
    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    public Integer getOrderId() { return orderId; }
    public void setOrderId(Integer orderId) { this.orderId = orderId; }
    public Integer getCustomerId() { return customerId; }
    public void setCustomerId(Integer customerId) { this.customerId = customerId; }
    public Customer getCustomer() { return customer; }
    public void setCustomer(Customer customer) { this.customer = customer; }
    public List<OrderLine> getOrderLines() { return orderLines; }
    public void setOrderLines(List<OrderLine> orderLines) { this.orderLines = orderLines; }
}

/**
 * Embedded Customer document within Order.
 * Represents the denormalized Sales.Customers table data.
 * 
 * TRANSLATED FROM: C# Customer entity (no longer a @Document root)
 * NOTE: No @Document annotation - this is a value object embedded in Order
 */
class Customer {

    private Integer customerId;
    private String customerName;
    private LocalDate accountOpenedDate;
    private BigDecimal creditLimit;

    // Embedded CustomerTransactions array (denormalized from Sales.CustomerTransactions table)
    private List<CustomerTransaction> customerTransactions = new ArrayList<>();

    // Constructors
    public Customer() {
    }

    // Getters and Setters
    public Integer getCustomerId() { return customerId; }
    public void setCustomerId(Integer customerId) { this.customerId = customerId; }
    public String getCustomerName() { return customerName; }
    public void setCustomerName(String customerName) { this.customerName = customerName; }
    public LocalDate getAccountOpenedDate() { return accountOpenedDate; }
    public void setAccountOpenedDate(LocalDate accountOpenedDate) { this.accountOpenedDate = accountOpenedDate; }
    public BigDecimal getCreditLimit() { return creditLimit; }
    public void setCreditLimit(BigDecimal creditLimit) { this.creditLimit = creditLimit; }
    public List<CustomerTransaction> getCustomerTransactions() { return customerTransactions; }
    public void setCustomerTransactions(List<CustomerTransaction> customerTransactions) { this.customerTransactions = customerTransactions; }
}

/**
 * Embedded CustomerTransaction document within Customer.customerTransactions array.
 * Represents the denormalized Sales.CustomerTransactions table data.
 * 
 * TRANSLATED FROM: C# CustomerTransaction entity
 * NOTE: No @Document annotation - this is a value object embedded in Customer
 */
class CustomerTransaction {

    private Integer customerTransactionId;
    private Integer customerId;
    private LocalDate transactionDate;
    private BigDecimal transactionAmount;

    // Constructors
    public CustomerTransaction() {
    }

    // Getters and Setters
    public Integer getCustomerTransactionId() { return customerTransactionId; }
    public void setCustomerTransactionId(Integer customerTransactionId) { this.customerTransactionId = customerTransactionId; }
    public Integer getCustomerId() { return customerId; }
    public void setCustomerId(Integer customerId) { this.customerId = customerId; }
    public LocalDate getTransactionDate() { return transactionDate; }
    public void setTransactionDate(LocalDate transactionDate) { this.transactionDate = transactionDate; }
    public BigDecimal getTransactionAmount() { return transactionAmount; }
    public void setTransactionAmount(BigDecimal transactionAmount) { this.transactionAmount = transactionAmount; }
}

/**
 * OrderLine document.
 * Maps to the 'orderLines' collection in MongoDB.
 * 
 * TRANSLATED FROM: C# OrderLine entity
 */
@Document(collection = "orderLines")
@JsonIgnoreProperties({ "id" })
class OrderLine {

    @Id
    private String id;

    @Field("orderLineId")
    private Integer orderLineId;

    @Field("orderId")
    private Integer orderId;

    @Field("stockItemId")
    private Integer stockItemId;

    private String description;

    @Field("packageTypeId")
    private Integer packageTypeId;

    private Integer quantity;

    private BigDecimal unitPrice;

    @Field("taxRate")
    private BigDecimal taxRate;

    @Field("pickedQuantity")
    private Integer pickedQuantity;

    @Field("pickingCompletedWhen")
    private LocalDateTime pickingCompletedWhen;

    @Field("lastEditedBy")
    private Integer lastEditedBy;

    @Field("lastEditedWhen")
    private LocalDateTime lastEditedWhen;

    // Constructors
    public OrderLine() {
    }

    // Getters and Setters
    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    public Integer getOrderLineId() { return orderLineId; }
    public void setOrderLineId(Integer orderLineId) { this.orderLineId = orderLineId; }
    public Integer getOrderId() { return orderId; }
    public void setOrderId(Integer orderId) { this.orderId = orderId; }
    public Integer getStockItemId() { return stockItemId; }
    public void setStockItemId(Integer stockItemId) { this.stockItemId = stockItemId; }
    public String getDescription() { return description; }
    public void setDescription(String description) { this.description = description; }
    public Integer getPackageTypeId() { return packageTypeId; }
    public void setPackageTypeId(Integer packageTypeId) { this.packageTypeId = packageTypeId; }
    public Integer getQuantity() { return quantity; }
    public void setQuantity(Integer quantity) { this.quantity = quantity; }
    public BigDecimal getUnitPrice() { return unitPrice; }
    public void setUnitPrice(BigDecimal unitPrice) { this.unitPrice = unitPrice; }
    public BigDecimal getTaxRate() { return taxRate; }
    public void setTaxRate(BigDecimal taxRate) { this.taxRate = taxRate; }
    public Integer getPickedQuantity() { return pickedQuantity; }
    public void setPickedQuantity(Integer pickedQuantity) { this.pickedQuantity = pickedQuantity; }
    public LocalDateTime getPickingCompletedWhen() { return pickingCompletedWhen; }
    public void setPickingCompletedWhen(LocalDateTime pickingCompletedWhen) { this.pickingCompletedWhen = pickingCompletedWhen; }
    public Integer getLastEditedBy() { return lastEditedBy; }
    public void setLastEditedBy(Integer lastEditedBy) { this.lastEditedBy = lastEditedBy; }
    public LocalDateTime getLastEditedWhen() { return lastEditedWhen; }
    public void setLastEditedWhen(LocalDateTime lastEditedWhen) { this.lastEditedWhen = lastEditedWhen; }
}

final class MongoTemplateFactory {
    private MongoTemplateFactory() {
    }

    static MongoTemplate create(String mongoUri, String mongoDatabase) {
        MongoDatabaseFactory databaseFactory = new SimpleMongoClientDatabaseFactory(MongoClients.create(mongoUri), mongoDatabase);
        MongoCustomConversions customConversions = MongoCustomConversions.create(configuration -> {});
        MongoMappingContext mappingContext = new MongoMappingContext();
        mappingContext.setSimpleTypeHolder(customConversions.getSimpleTypeHolder());
        mappingContext.afterPropertiesSet();

        MappingMongoConverter converter = new MappingMongoConverter(new DefaultDbRefResolver(databaseFactory), mappingContext);
        converter.setCustomConversions(customConversions);
        converter.setTypeMapper(new DefaultMongoTypeMapper(null));
        converter.afterPropertiesSet();

        return new MongoTemplate(databaseFactory, converter);
    }
}

// --- Query Entrypoint ---

record CountProjection(Long count) {
}

interface Query5Projection {
    Integer getOrderLineId();
    Integer getQuantity();
}

final class Query1 {
    public static Query query() {
        LocalDate from = LocalDate.of(2014, 12, 20);
        LocalDate to = LocalDate.of(2014, 12, 31);
        return new Query(Criteria.where("pickingCompletedWhen").gte(from).lte(to));
    }

    public static Map<String, Object> harness(MongoTemplate template) {
        Query q = query();
        long count = template.count(q, OrderLine.class);
        Object first = null;
        if (count > 0) {
            first = template.findOne(query().with(Sort.by(Sort.Direction.ASC, "orderLineId")).limit(1), OrderLine.class);
        }
        Object last = null;
        if (count > 1) {
            last = template.findOne(query().with(Sort.by(Sort.Direction.DESC, "orderLineId")).limit(1), OrderLine.class);
        }
        return Map.of("mongoQuery", Map.of("collection", template.getCollectionName(OrderLine.class), "filter", q.getQueryObject()), "count", count, "firstSample", first, "lastSample", last);
    }
}

final class Query2 {
    public static Query query() {
        return new Query(Criteria.where("customerId").is(1));
    }

    public static Map<String, Object> harness(MongoTemplate template) {
        Query q = query();
        long count = template.count(q, Order.class);
        Object first = null;
        if (count > 0) {
            first = template.findOne(query().with(Sort.by(Sort.Direction.ASC, "orderId")).limit(1), Order.class);
        }
        Object last = null;
        if (count > 1) {
            last = template.findOne(query().with(Sort.by(Sort.Direction.DESC, "orderId")).limit(1), Order.class);
        }
        return Map.of("mongoQuery", Map.of("collection", template.getCollectionName(Order.class), "filter", q.getQueryObject()), "count", count, "firstSample", first, "lastSample", last);
    }
}

final class Query3 {
    public static TypedAggregation<OrderLine> query() {
        return Aggregation.newAggregation(
            OrderLine.class,
            Aggregation.group("taxRate").count().as("count"),
            Aggregation.project("count").and("taxRate").previousOperation(),
            Aggregation.sort(Sort.Direction.DESC, "count")
        );
    }

    public static Map<String, Object> harness(MongoTemplate template) {
        var baseAgg = query();
        
        var countOps = new ArrayList<>(baseAgg.getPipeline().getOperations());
        countOps.add(Aggregation.count().as("count"));
        var countAgg = Aggregation.newAggregation(OrderLine.class, countOps);
        var countResult = template.aggregate(countAgg, OrderLine.class, CountProjection.class).getUniqueMappedResult();
        var count = countResult != null ? countResult.count() : 0L;
        
        Object first = null;
        if (count > 0) {
            var agg = Aggregation.newAggregation(query().getPipeline().add(Aggregation.sort(Sort.Direction.ASC, "taxRate")).add(Aggregation.limit(1)).getOperations());
            first = template.aggregate(agg, template.getCollectionName(OrderLine.class), Object.class).getUniqueMappedResult();
        }
        Object last = null;
        if (count > 1) {
            var desc = Aggregation.newAggregation(query().getPipeline().add(Aggregation.sort(Sort.Direction.DESC, "taxRate")).add(Aggregation.limit(1)).getOperations());
            last = template.aggregate(desc, template.getCollectionName(OrderLine.class), Object.class).getUniqueMappedResult();
        }
        return Map.of("mongoAggregation", Map.of("collection", template.getCollectionName(OrderLine.class), "pipeline", baseAgg.toString()), "count", count, "firstSample", first, "lastSample", last);
    }
}

final class Query4 {
    public static Query query() {
        return new Query().with(Sort.by(Sort.Direction.DESC, "quantity")).limit(50);
    }

    public static Map<String, Object> harness(MongoTemplate template) {
        Query q = query();
        long count = template.count(q, OrderLine.class);

        Object first = null;
        if (count > 0) {
            Query firstQ = q.with(Sort.by(Sort.Direction.ASC, "orderLineId")).limit(1);
            first = template.findOne(firstQ, OrderLine.class);
        }
        Object last = null;
        if (count > 1) {
            Query lastQ = q.with(Sort.by(Sort.Direction.ASC, "orderLineId")).skip(count - 1).limit(1);
            last = template.findOne(lastQ, OrderLine.class);
        }
        return Map.of("mongoQuery", Map.of("collection", template.getCollectionName(OrderLine.class), "filter", q.getQueryObject(), "sort", q.getSortObject()), "count", count, "firstSample", first, "lastSample", last);
    }
}

final class Query5 {
    public static Query query() {
        Query q = new Query();
        q.fields().include("orderLineId", "quantity");
        return q;
    }

    public static Map<String, Object> harness(MongoTemplate template) {
        Query q = query();
        long count = template.count(q, OrderLine.class);
        
        Object first = null;
        if (count > 0) {
            Query asc = query().with(Sort.by(Sort.Direction.ASC, "orderLineId")).limit(1);
            first = template.query(OrderLine.class).as(Query5Projection.class).matching(asc).firstValue();
        }
        Object last = null;
        if (count > 1) {
            Query desc = query().with(Sort.by(Sort.Direction.DESC, "orderLineId")).limit(1);
            last = template.query(OrderLine.class).as(Query5Projection.class).matching(desc).firstValue();
        }
        return Map.of("mongoQuery", Map.of("collection", template.getCollectionName(OrderLine.class), "filter", q.getQueryObject(), "fields", q.getFieldsObject()), "count", count, "firstSample", first, "lastSample", last);
    }
}
</fragment_structure>

System time: 2026-07-11T07:47:04.670234+00:00

`````

## User prompt

`````text
Translate the following Source Code (schema/query) from .NET NHibernate to Java Spring Data MongoDB 5.0.

Database Schema Context:
I now have complete information for both schemas. Here is the comprehensive summary:

---

## SOURCE SCHEMA: Microsoft SQL Server (`WideWorldImporters`)

### `Sales.OrderLines` (12 columns)
| Column | Type | Nullable | Notes |
|---|---|---|---|
| OrderLineID | int | NO | PK, Identity |
| OrderID | int | NO | FK → Sales.Orders |
| StockItemID | int | NO |
| Description | nvarchar(100) | NO |
| PackageTypeID | int | NO |
| Quantity | int | NO |
| UnitPrice | decimal(18,2) | YES |
| TaxRate | decimal(18,3) | NO |
| PickedQuantity | int | NO |
| PickingCompletedWhen | datetime2 | YES |
| LastEditedBy | int | NO |
| LastEditedWhen | datetime2 | NO |

### `Sales.Orders` (16 columns)
| Column | Type | Nullable | Notes |
|---|---|---|---|
| OrderID | int | NO | PK, Identity |
| CustomerID | int | NO | FK → Sales.Customers |
| SalespersonPersonID | int | NO |
| PickedByPersonID | int | YES |
| ContactPersonID | int | NO |
| BackorderOrderID | int | YES |
| OrderDate | date | NO |
| ExpectedDeliveryDate | date | NO |
| CustomerPurchaseOrderNumber | nvarchar(20) | YES |
| IsUndersupplyBackordered | bit | NO |
| Comments | nvarchar(max) | YES |
| DeliveryInstructions | nvarchar(max) | YES |
| InternalComments | nvarchar(max) | YES |
| PickingCompletedWhen | datetime2 | YES |
| LastEditedBy | int | NO |
| LastEditedWhen | datetime2 | NO |

NHibernate relationship: Bag of OrderLines via `OrderID` FK with `Inverse(true)` (one-to-many).

### `Application.People` (21 columns)
| Column | Type | Nullable | Notes |
|---|---|---|---|
| PersonID | int | NO | PK, Identity |
| FullName | nvarchar(50) | NO |
| PreferredName | nvarchar(50) | NO |
| SearchName | nvarchar(101) | NO |
| EmailAddress | nvarchar(256) | YES |
| CustomFields | nvarchar(max) | YES | JSON string, e.g. `{"Title":"Team Member",...}` |
| OtherLanguages | nvarchar(max) | YES | JSON array string, e.g. `["Polish","Chinese","Japanese"]` |
| (plus 14 more system columns) | | |

### `Purchasing.Suppliers` (29 columns)
Key fields: SupplierID (PK), SupplierName, SupplierReference, PaymentDays, PhoneNumber, FaxNumber, WebsiteURL, BankAccountName, BankAccountBranch, BankAccountCode, BankAccountNumber, BankInternationalCode, plus address/city/contact IDs.

### Embedded source tables (not independently queried in the code):
- `Sales.CustomerTransactions` → embedded in orders and people as `customerTransactions` array
- `Purchasing.PurchaseOrders` → embedded in people and suppliers as `purchaseOrders` array
- `Warehouse.StockItems` → embedded in orderLines as single `stockItem` doc, also in people/suppliers as arrays
- `Warehouse.StockItemStockGroups` → embedded in orderLines `stockItem.stockItemStockGroups` array
- `Sales.Customers` → embedded in orders as single `customer` doc
- `Warehouse.StockGroups` → embedded in people as `stockGroups` array

---

## TARGET SCHEMA: MongoDB (`uom` database)

Four collections: `orderLines`, `orders`, `people`, `suppliers`.

### `orderLines` (231,412 documents)
Top-level fields (camelCase, matching mapping):
`_id` (ObjectId), `orderLineId` (Number), `orderId` (Number), `stockItemId` (Number), `description` (String), `packageTypeId` (Number), `quantity` (Number), `unitPrice` (Decimal128), `taxRate` (Decimal128), `pickedQuantity` (Number), `pickingCompletedWhen` (Date), `lastEditedBy` (Number), `lastEditedWhen` (Date).

Embedded sub-document: `stockItem` (single document) containing all StockItem fields plus `stockItemStockGroups` (array of objects with `stockItemStockGroupId`, `stockItemId`, `stockGroupId`, `lastEditedBy`, `lastEditedWhen`).

### `orders` (73,595 documents)
Top-level fields: `_id`, `orderId`, `customerId`, `salespersonPersonId`, `pickedByPersonId`, `contactPersonId`, `backorderOrderId`, `orderDate` (Date), `expectedDeliveryDate` (Date), `customerPurchaseOrderNumber` (String), `isUndersupplyBackordered` (Boolean), `comments`, `deliveryInstructions`, `internalComments`, `pickingCompletedWhen`, `lastEditedBy`, `lastEditedWhen`.

Embedded sub-document: `customer` (single document) with all Customer fields plus `customerTransactions` array.

**CRITICAL: OrderLines are NOT embedded in orders.** They are a separate `orderLines` collection referenced by `orderId`. This means NHibernate's `Fetch(o => o.OrderLines)` join must be replaced with either a separate query on the `orderLines` collection, or a MongoDB aggregation `$lookup`.

### `people` (1,111 documents)
Top-level fields: `_id`, `personId`, `fullName`, `preferredName`, `searchName`, `isPermittedToLogon`, `logonName`, `isExternalLogonProvider`, `hashedPassword`, `isSystemUser`, `isEmployee`, `isSalesperson`, `userPreferences`, `phoneNumber`, `faxNumber`, `emailAddress`, `photo`, `customFields` (String — JSON), `otherLanguages` (String — JSON array), `lastEditedBy`, `validFrom`, `validTo`.

**Important for Query13/14:** `customFields` stores JSON as a plain string (e.g., `{ "Title": "Team Member", ... }`). `otherLanguages` stores a JSON array as a string (e.g., `["Polish","Chinese","Japanese"]`). In MongoDB, these are plain string fields, not native MongoDB objects/arrays, so queries against them will use `$regex` or `$expr` with string-matching patterns rather than MongoDB's native JSON operators. Only 19 of 1,111 documents have non-null `customFields`.

### `suppliers` (13 documents)
Top-level fields matching the Purchasing.Suppliers table mapping. Embedded arrays: `purchaseOrders` (Array of PurchaseOrder) and `stockItems` (Array of StockItem). Note: the `purchaseOrders` embedded in this collection sample returned 0 entries for some suppliers, and the `stockItems` array may be present.

---

## KEY TRANSLATION MAPPINGS

| NHibernate Concept | Spring Data MongoDB 5.0 Equivalent |
|---|---|
| `session.Query<T>()` | `MongoTemplate` or `MongoRepository` query methods |
| `IQueryable.Where()` | `Query` + `Criteria.where()` or `@Query` annotation |
| `OrderBy().Skip().Take()` | `query.with(Sort...).skip().limit()` |
| `GroupBy().Select()` | Aggregation pipeline with `$group`, `$project` |
| `.Max(ol => ol.UnitPrice)` | Aggregation `$group` with `$max` |
| `.Sum(ol => ol.Quantity * ol.UnitPrice)` | Aggregation `$group` with `$sum` + `$multiply` |
| `.Fetch(o => o.OrderLines)` | Separate query on `orderLines` collection by `orderId`, or `$lookup` aggregation |
| `.Distinct()` | `distinct()` or `$group` |
| `SQL JSON_VALUE(CustomFields, '$.Title')` | Native MongoDB `$regex` on the string field, since `customFields` is stored as a plain string |
| `SQL OPENJSON(OtherLanguages)` with `EXISTS` | `$regex` on the string field since `otherLanguages` is stored as a string |
| `.Union()` (Query15) | Java Stream concatenation or two separate queries merged in code |
| `ToDictionary(x => x.TaxRate, x => x.Count)` | Convert aggregation results to `Map<BigDecimal, Long>` |
| Identity generator | MongoDB `ObjectId` auto-generation |

Decimal values use `BigDecimal` in Java; MongoDB stores Decimal128. Dates use `java.util.Date` or `java.time.Instant`. Nullable value types (`decimal?`, `DateTime?`) use Java's reference types (`BigDecimal`, `Instant`). The `required` keyword in C# properties maps to `@NotNull` or non-null field constraints in Java.
---
Source Code:
<source_schema_code>
public class OrderLine
{
    public virtual int OrderLineID { get; set; }
    public virtual int OrderID { get; set; }
    public virtual int StockItemID { get; set; }
    public virtual required string Description { get; set; }
    public virtual int Quantity { get; set; }
    public virtual decimal? UnitPrice { get; set; }
    public virtual decimal TaxRate { get; set; }
    public virtual int PickedQuantity { get; set; }
    public virtual DateTime? PickingCompletedWhen { get; set; }
    public virtual int LastEditedBy { get; set; }
    public virtual DateTime LastEditedWhen { get; set; }
}
public class Order
{
    public virtual int OrderID { get; set; }
    public virtual int CustomerID { get; set; }
    public virtual int? BackorderOrderID { get; set; }
    public virtual DateTime OrderDate { get; set; }
    public virtual DateTime ExpectedDeliveryDate { get; set; }
    public virtual string? CustomerPurchaseOrderNumber { get; set; }
    public virtual bool IsUndersupplyBackordered { get; set; }
    public virtual string? Comments { get; set; }
    public virtual string? DeliveryInstructions { get; set; }
    public virtual string? InternalComments { get; set; }
    public virtual DateTime? PickingCompletedWhen { get; set; }
    public virtual DateTime LastEditedWhen { get; set; }
    public virtual IList<OrderLine> OrderLines { get; set; } = [];
}
public class Person
{
    public virtual int PersonID { get; set; }
    public virtual required string FullName { get; set; }
    public virtual required string PreferredName { get; set; }
    public virtual string? EmailAddress { get; set; }
    public virtual string? CustomFields { get; set; }
    public virtual string? OtherLanguages { get; set; }
}
public class Supplier
{
    public virtual int SupplierID { get; set; }
    public virtual required string SupplierName { get; set; }
    public virtual string? SupplierReference { get; set; }
    public virtual int PaymentDays { get; set; }
    public virtual string? PhoneNumber { get; set; }
    public virtual string? FaxNumber { get; set; }
    public virtual string? WebsiteURL { get; set; }
    public virtual string? BankAccountName { get; set; }
    public virtual string? BankAccountBranch { get; set; }
    public virtual string? BankAccountCode { get; set; }
    public virtual string? BankAccountNumber { get; set; }
    public virtual string? BankInternationalCode { get; set; }
}
public class CustomerTransaction
{
    public virtual int CustomerTransactionID { get; set; }
    public virtual int CustomerID { get; set; }
    public virtual DateTime TransactionDate { get; set; }
    public virtual decimal TransactionAmount { get; set; }
    public virtual decimal OutstandingBalance { get; set; }
    public virtual bool IsFinalized { get; set; }
}
public class PurchaseOrder
{
    public virtual int PurchaseOrderID { get; set; }
    public virtual int SupplierID { get; set; }
    public virtual DateTime OrderDate { get; set; }
    public virtual DateTime ExpectedDeliveryDate { get; set; }
    public virtual string? SupplierReference { get; set; }
    public virtual bool IsOrderFinalized { get; set; }
}
public class StockItem
{
    public virtual int StockItemID { get; set; }
    public virtual required string StockItemName { get; set; }
    public virtual int SupplierID { get; set; }
    public virtual int QuantityPerOuter { get; set; }
    public virtual int LeadTimeDays { get; set; }
    public virtual bool IsChillerStock { get; set; }
    public virtual decimal? UnitPrice { get; set; }
    public virtual decimal RecommendedRetailPrice { get; set; }
}
public class StockItemStockGroup
{
    public virtual int StockItemStockGroupID { get; set; }
    public virtual int StockItemID { get; set; }
    public virtual int StockGroupID { get; set; }
}
public class SupplierContactInfo
{
    public int SupplierID { get; set; }
    public string? SupplierName { get; set; }
    public string? PhoneNumber { get; set; }
    public string? FaxNumber { get; set; }
    public string? WebsiteURL { get; set; }
}
public class SupplierBankAccount
{
    public int SupplierID { get; set; }
    public string? BankAccountName { get; set; }
    public string? BankAccountBranch { get; set; }
    public string? BankAccountCode { get; set; }
    public string? BankAccountNumber { get; set; }
    public string? BankInternationalCode { get; set; }
}
public class SupplierAccounts
{
    public SupplierContactInfo? ContactInfo { get; set; }
    public SupplierBankAccount? BankAccount { get; set; }
}
public class PurchaseOrderInfo
{
    public int PurchaseOrderID { get; set; }
    public string? SupplierName { get; set; }
    public DateTime OrderDate { get; set; }
}
public class OrderLineMap : ClassMapping<OrderLine> {
    public OrderLineMap() {
        Table("OrderLines"); Schema("Sales");
        Id(x => x.OrderLineID, m => m.Generator(Generators.Identity));
        Property(x => x.OrderID, m => { m.Insert(false); m.Update(false); });
        Property(x => x.StockItemID);
        Property(x => x.Description);
        Property(x => x.Quantity);
        Property(x => x.UnitPrice);
        Property(x => x.TaxRate);
        Property(x => x.PickedQuantity);
        Property(x => x.PickingCompletedWhen);
        Property(x => x.LastEditedBy);
        Property(x => x.LastEditedWhen);
    }
}
public class OrderMap : ClassMapping<Order> {
    public OrderMap() {
        Table("Orders"); Schema("Sales");
        Id(x => x.OrderID, m => m.Generator(Generators.Identity));
        Property(x => x.CustomerID);
        Property(x => x.BackorderOrderID);
        Property(x => x.OrderDate);
        Property(x => x.ExpectedDeliveryDate);
        Property(x => x.CustomerPurchaseOrderNumber);
        Property(x => x.IsUndersupplyBackordered);
        Property(x => x.Comments);
        Property(x => x.DeliveryInstructions);
        Property(x => x.InternalComments);
        Property(x => x.PickingCompletedWhen);
        Property(x => x.LastEditedWhen);
        Bag(x => x.OrderLines, map => { map.Key(k => k.Column("OrderID")); map.Inverse(true); }, rel => rel.OneToMany());
    }
}
public class PersonMap : ClassMapping<Person> {
    public PersonMap() {
        Table("People"); Schema("Application");
        Id(x => x.PersonID, m => m.Generator(Generators.Identity));
        Property(x => x.FullName);
        Property(x => x.PreferredName);
        Property(x => x.EmailAddress);
        Property(x => x.CustomFields);
        Property(x => x.OtherLanguages);
    }
}
public class SupplierMap : ClassMapping<Supplier> {
    public SupplierMap() {
        Table("Suppliers"); Schema("Purchasing");
        Id(x => x.SupplierID, m => m.Generator(Generators.Identity));
        Property(x => x.SupplierName);
        Property(x => x.SupplierReference);
        Property(x => x.PaymentDays);
        Property(x => x.PhoneNumber);
        Property(x => x.FaxNumber);
        Property(x => x.WebsiteURL);
        Property(x => x.BankAccountName);
        Property(x => x.BankAccountBranch);
        Property(x => x.BankAccountCode);
        Property(x => x.BankAccountNumber);
        Property(x => x.BankInternationalCode);
    }
}
public class CustomerTransactionMap : ClassMapping<CustomerTransaction> {
    public CustomerTransactionMap() {
        Table("CustomerTransactions"); Schema("Sales");
        Id(x => x.CustomerTransactionID, m => m.Generator(Generators.Identity));
        Property(x => x.CustomerID);
        Property(x => x.TransactionDate);
        Property(x => x.TransactionAmount);
        Property(x => x.OutstandingBalance);
        Property(x => x.IsFinalized);
    }
}
public class PurchaseOrderMap : ClassMapping<PurchaseOrder> {
    public PurchaseOrderMap() {
        Table("PurchaseOrders"); Schema("Purchasing");
        Id(x => x.PurchaseOrderID, m => m.Generator(Generators.Identity));
        Property(x => x.SupplierID);
        Property(x => x.OrderDate);
        Property(x => x.ExpectedDeliveryDate);
        Property(x => x.SupplierReference);
        Property(x => x.IsOrderFinalized);
    }
}
public class StockItemMap : ClassMapping<StockItem> {
    public StockItemMap() {
        Table("StockItems"); Schema("Warehouse");
        Id(x => x.StockItemID, m => m.Generator(Generators.Identity));
        Property(x => x.StockItemName);
        Property(x => x.SupplierID);
        Property(x => x.QuantityPerOuter);
        Property(x => x.LeadTimeDays);
        Property(x => x.IsChillerStock);
        Property(x => x.UnitPrice);
        Property(x => x.RecommendedRetailPrice);
    }
}
public class StockItemStockGroupMap : ClassMapping<StockItemStockGroup> {
    public StockItemStockGroupMap() {
        Table("StockItemStockGroups"); Schema("Warehouse");
        Id(x => x.StockItemStockGroupID, m => m.Generator(Generators.Identity));
        Property(x => x.StockItemID);
        Property(x => x.StockGroupID);
    }
}
</source_schema_code>
<source_query_code>
public record TaxRateCount { public decimal TaxRate { get; set; } public long Count { get; set; } }

public static IQueryable<OrderLine> Query1(NHibernate.ISession session)
{
    int orderId = 26866;
    return session.Query<OrderLine>().Where(ol => ol.OrderID == orderId);
}

public static IQueryable<OrderLine> Query2(NHibernate.ISession session)
{
    decimal unitPrice = 25m;
    return session.Query<OrderLine>().Where(ol => ol.UnitPrice == unitPrice);
}

public static IQueryable<OrderLine> Query3(NHibernate.ISession session)
{
    var from = new DateTime(2014, 12, 20);
    var to = new DateTime(2014, 12, 31);
    return session.Query<OrderLine>().Where(ol => ol.PickingCompletedWhen >= from && ol.PickingCompletedWhen <= to);
}

public static IQueryable<OrderLine> Query4(NHibernate.ISession session)
{
    var orderIds = new List<int> { 1, 10, 100, 1000, 10000 };
    return session.Query<OrderLine>().Where(ol => orderIds.Contains(ol.OrderID));
}

public static IQueryable<OrderLine> Query5(NHibernate.ISession session)
{
    string text = "C++";
    return session.Query<OrderLine>().Where(ol => ol.Description.Contains(text));
}

public static IQueryable<OrderLine> Query6(NHibernate.ISession session)
{
    int skip = 1000;
    int take = 50;
    return session.Query<OrderLine>().OrderBy(ol => ol.OrderLineID).Skip(skip).Take(take);
}

public static Dictionary<decimal, int> Query7(NHibernate.ISession session)
{
    return session.Query<OrderLine>()
        .GroupBy(ol => ol.TaxRate)
        .Select(g => new { TaxRate = g.Key, Count = g.Count() })
        .OrderByDescending(x => x.Count)
        .ToDictionary(x => x.TaxRate, x => x.Count);
}

public static decimal? Query8(NHibernate.ISession session)
{
    return session.Query<OrderLine>().Max(ol => ol.UnitPrice);
}

public static decimal? Query9(NHibernate.ISession session)
{
    return session.Query<OrderLine>().Sum(ol => ol.Quantity * ol.UnitPrice);
}

public static Order Query10(NHibernate.ISession session)
{
    return session.Query<Order>().Fetch(o => o.OrderLines).Single(o => o.OrderID == 530);
}

public static IQueryable<Order> Query11(NHibernate.ISession session)
{
    return session.Query<Order>().OrderBy(o => o.ExpectedDeliveryDate).Take(1000);
}

public static IQueryable<string?> Query12(NHibernate.ISession session)
{
    return session.Query<Order>().Select(o => o.CustomerPurchaseOrderNumber).Distinct();
}

public static IList<Person> Query13(NHibernate.ISession session)
{
    var sql = """
                  SELECT PersonID, FullName, PreferredName, EmailAddress, CustomFields, OtherLanguages
                  FROM Application.People
                  WHERE JSON_VALUE(CustomFields, '$.Title') = :title
                  ORDER BY PersonID
              """;
    return session.CreateSQLQuery(sql)
        .SetParameter("title", "Team Member")
        .SetResultTransformer(Transformers.AliasToBean<Person>())
        .List<Person>();
}

public static IList<Person> Query14(NHibernate.ISession session)
{
    var sql = """
                  SELECT PersonID, FullName, PreferredName, EmailAddress, CustomFields, OtherLanguages
                  FROM Application.People
                  WHERE EXISTS (
                      SELECT 1 FROM OPENJSON(OtherLanguages)
                      WHERE value = :lang
                  )
                  ORDER BY PersonID
              """;
    return session.CreateSQLQuery(sql)
        .SetParameter("lang", "Slovak")
        .SetResultTransformer(Transformers.AliasToBean<Person>())
        .List<Person>();
}

public static List<int> Query15(NHibernate.ISession session)
{
    var first = session.Query<Supplier>()
        .Where(s => s.SupplierID < 5)
        .Select(s => s.SupplierID)
        .ToList();
    var last = session.Query<Supplier>()
        .Where(s => s.SupplierID >= 5 && s.SupplierID <= 10)
        .Select(s => s.SupplierID)
        .ToList();
    return first.Union(last).OrderBy(s => s).ToList();
}
</source_query_code>

Translate ONLY the entities, fields, and queries that appear above. Do not invent or carry over any entity or field that is not present in this source code.

`````

## Capture the result

Paste the model's fenced blocks into this folder's `capture.md` (pre-labeled template), note which
model/platform produced them, then validate through the pipeline's own gauntlet:

    uv run python evaluation/scripts/score_external.py --capture <folder>/capture.md \
        --pair <source-target> --variant <variant> --approach claude_code --model-label <model>

Same assembler, same sandboxes, same execution-equivalence — apples-to-apples with the automated runs.
