---
name: dotnet-efcore
description: >-
  Expert guidance for reading and writing .NET Entity Framework Core 10 code (EF Core 10 on
  .NET 10 / C# 14, SQL Server provider, System.Text.Json). Use whenever the SOURCE side of a
  translation is EF Core — reading its entity model (data annotations [Table]/[Key]/[ForeignKey]/
  [Column]/[Precision], the DbContext + DbSet<T> shape, OnModelCreating fluent config, OwnsOne/
  ToJson owned types) or its LINQ query bodies (IQueryable, Where/OrderBy/Skip/Take, Include/
  ThenInclude, GroupBy aggregations, Distinct, set operations), and whenever authoring the EF Core
  source-side validation harness fragment (Query{N}.Harness(SandboxDbContext) using
  HarnessSupport.RunQuery). Trigger even when the user only says "EF Core", "EFCore", "DbContext",
  "DbSet", "LINQ query", "[Table]/[Key] annotations", or "IQueryable" without naming the version,
  and when fixing CS-compile errors in an EF Core harness fragment. Its purpose is correctly
  interpreting the EF Core source and producing a version-correct, compilable source harness. Do
  NOT use for: the TARGET side (Spring Data MongoDB @Document/Criteria, Spring Data Neo4j @Node/
  Cypher — those have their own skills), Dapper raw SQL, NHibernate mapping-by-code, EF6/EF Classic,
  or SQL Server server/DBA operations.
---

# .NET Entity Framework Core 10 Expert (source side)

This skill makes you a reliable engineer for the **EF Core 10 generation** on **.NET 10 / C#
13**. In the Universal Object Mapping pipeline, EF Core is a **source** framework — you translate
*from* it into a Java target (Spring Data MongoDB or Neo4j). So this skill buys you two things:

1. **Correctly reading the EF Core source** — the entity model expressed with data annotations and
   a `DbContext`, and the LINQ query semantics you must preserve on the target (the exact filter,
   projection, sort, grouping, and result shape).
2. **Authoring a version-correct EF Core validation-harness fragment** that actually compiles
   against EF Core 10 on SQL Server. The harness runs the *source* query so its result can be
   compared, row-for-row, against the translated target. A single wrong `using`, a naming
   collision, or a missing `SandboxDbContext` fails the whole build.

The biggest EF-Core-specific trap when authoring a harness fragment is a **class/member name
collision** — see the naming rule under "Non-negotiable rules". If unsure which namespace a type
lives in, **stop and consult `references/imports.md`** — do not guess.

## Source stack (assume this unless told otherwise)

| Component | Version | Why it matters |
|---|---|---|
| .NET | 10.0 (`net10.0`) | C# 14; primary constructors, collection expressions `[]`, `required` members |
| EF Core | 10.0.x (`Microsoft.EntityFrameworkCore.SqlServer`) | `DbContext`/`DbSet<T>`, LINQ provider, `OwnsOne(...).ToJson()` |
| ADO provider | `Microsoft.Data.SqlClient` 7.0.x | the underlying SQL Server driver EF Core uses |
| Serialization | `System.Text.Json` | the harness serializer (injected — do not re-author it) |
| `ImplicitUsings` | enabled | `System`, `System.Linq`, `System.Collections.Generic`, `System.Threading.Tasks` etc. are already in scope |

## How to use this skill

1. Decide what you are producing: **schema (entity) fragment**, **query fragments**, or **both**.
2. Read the matching reference file(s) before writing code:
   - `references/schema-mapping.md` — data annotations, the `DbContext`/`DbSet<T>` requirement,
     `OnModelCreating` fluent config, owned types / JSON columns (`OwnsOne(...).ToJson()`), and the
     .NET → Java type intent you must carry to the target.
   - `references/queries.md` — the LINQ query surface (`Where`, `OrderBy`/`OrderByDescending`,
     `Skip`/`Take`, `Contains`, `Include`/`ThenInclude`, `GroupBy`, `Max`/`Sum`, `Distinct`, set
     operations) and how to wrap each query in a `Query{N}.Harness` fragment with
     `HarnessSupport.RunQuery`.
   - `references/imports.md` — the canonical `using` set, what `ImplicitUsings` already covers, and
     the traps.
3. Write the code following the rules below.
4. If the code must run (validation harness), re-check every `using` against `references/imports.md`
   and confirm the schema fragment declares `SandboxDbContext`.

## Non-negotiable rules

These are the rules that most often separate a harness that compiles and runs from one that does
not.

**The schema fragment MUST declare `SandboxDbContext`.** The generated entrypoint does
`new SandboxDbContext(...)`, so your schema body must include the context class with a `DbSet<T>`
property for every entity:

```csharp
public class SandboxDbContext(DbContextOptions<SandboxDbContext> options) : DbContext(options)
{
    public DbSet<Order> Orders => Set<Order>();
    public DbSet<OrderLine> OrderLines => Set<OrderLine>();
}
```

If (and only if) an entity uses an owned type mapped to JSON, override `OnModelCreating` in the
context — see `references/schema-mapping.md`.

**Never name a helper member `Query{N}`, and never call `Query{N}(...)`, inside the `Query{N}`
class.** The enclosing class is already named `Query{N}`; a same-named method is `CS0542` ("member
names cannot be the same as their enclosing type") and calling `Query{N}(...)` resolves to the
*class* (`CS1955`), which cascades into `CS0411` inference failures. Name inner helpers something
else (e.g. `Rows`, `Build`) and call those. This is the single most common .NET harness failure.

**The harness fragment shape is fixed.** One class per query:

```csharp
public static class Query1
{
    public static object Harness(SandboxDbContext ctx)
    {
        return HarnessSupport.RunQuery(() => ctx.OrderLines.Where(ol => ol.OrderID == 26866),
                                       ol => ol.OrderLineID);
    }
}
```

`HarnessSupport.RunQuery` (provided in the injected prelude — do NOT redeclare it) takes a
`Func<IQueryable<T>>` and an optional **unique** sort selector, and returns
`{ count, firstSample, lastSample }`. Pass a unique selector when the query has no deterministic
order of its own; pass `null` when it already orders by a unique key. For scalar/aggregate queries
(`Max`, `Sum`, a grouped dictionary, a set-operation list) do not force `RunQuery` — build the same
`count`/`firstSample`/`lastSample` map yourself. See `references/queries.md`.

**Emit any extra `using` directives your fragment needs.** They are hoisted into the file header,
so an EF Core `using Microsoft.EntityFrameworkCore;` (for `Include`, `ToQueryString`, etc.) placed
at the top of your fragment is fine even though the prelude usually already has it. Do NOT write a
`namespace` line and do NOT redeclare the injected serializer/`HarnessSupport`.

**No comments or placeholders in code that will be executed.** The fragment is compiled and run.
`// TODO`, `...`, or stub bodies break it. Emit complete, runnable code.

**Preserve the source query's exact semantics.** Do not add synthetic parameters, extra filters, or
a different sort than the source query expresses. The *only* ordering you may add is a deterministic
tie-break inside the harness (the unique sort selector) so `firstSample`/`lastSample` are stable —
that ordering must not change which rows the query returns.

**Carry .NET types to the target faithfully.** `decimal`/`decimal?` is money/exact — it becomes
`BigDecimal` on a document target and `Double` on a Neo4j target (Neo4j has no decimal type), never
a lossy `double` by accident. `DateTime` → `LocalDateTime` (date-only intent → `LocalDate`). A
`List<T>` navigation is a one-to-many relationship. See `references/schema-mapping.md`.

## Quick orientation example (the shape to aim for)

An EF Core entity with data annotations, the `SandboxDbContext`, and a query wrapped as a harness
fragment. This is the source you *read* and the harness you *write*.

```csharp
[Table("OrderLines", Schema = "Sales")]
public class OrderLine
{
    [Key]
    public int OrderLineID { get; set; }
    [ForeignKey(nameof(Order))]
    public int OrderID { get; set; }
    public required string Description { get; set; }
    public int Quantity { get; set; }
    public decimal? UnitPrice { get; set; }        // money -> BigDecimal (Mongo) / Double (Neo4j)
    public decimal TaxRate { get; set; }
    public DateTime? PickingCompletedWhen { get; set; }
}

public class SandboxDbContext(DbContextOptions<SandboxDbContext> options) : DbContext(options)
{
    public DbSet<OrderLine> OrderLines => Set<OrderLine>();
}

public static class Query3
{
    public static object Harness(SandboxDbContext ctx)
    {
        var from = new DateTime(2014, 12, 20);
        var to = new DateTime(2014, 12, 31);
        return HarnessSupport.RunQuery(
            () => ctx.OrderLines.Where(ol => ol.PickingCompletedWhen >= from
                                          && ol.PickingCompletedWhen <= to),
            ol => ol.OrderLineID);
    }
}
```

## Common traps

- **`Query{N}` member/call collision** (`CS0542`/`CS1955`/`CS0411`) — the dominant .NET harness
  failure. Never name a helper `Query{N}` or call `Query{N}(...)` inside `class Query{N}`.
- **Forgetting `SandboxDbContext`** in the schema fragment → the generated entrypoint cannot
  instantiate the context.
- **Owned type not configured** — a JSON/owned property (e.g. `CustomFields`) needs
  `OwnsOne(p => p.CustomFields, cb => cb.ToJson())` in `OnModelCreating`, or EF Core treats it as a
  separate table and the query fails.
- **`decimal` read as `double`** — silently loses precision and drifts the equivalence check.
- **`new DateTime(2014, 12, 20)`** is correct in C# (unlike Java's deprecated `new Date`); keep it
  as-is in the source harness, but translate it to `LocalDate.of(...)`/`LocalDateTime.of(...)` on
  the Java target.
- **`.Contains` is overloaded** — `collection.Contains(x)` compiles to SQL `IN`, while
  `string.Contains(text)` compiles to `LIKE '%text%'`. They translate to different target operators;
  read which one the source means.
- **Client vs. server evaluation** — set operations in the eval source (`first.Union(last)`) run in
  memory over `ToList()`ed sequences, not as SQL `UNION`. Keep that shape; it returns a materialized
  `List<T>`, so build the result map by hand rather than via `RunQuery`.

## Project context (Universal Object Mapping)

This skill backs the `generate_translation_node` translator when the **source** is EF Core. In
fragment mode you author, per query, a `Query{N}.Harness(SandboxDbContext)` for the source side and
the matching Java `Query{N}.harness(...)` for the target side; both must return the SAME flat map
(`count`, `firstSample`, `lastSample`). The fixed prelude — `using` lines, the JSON serializer,
`HarnessSupport`, and the generated `Main` — is **injected for you**; start your schema body at the
entity classes and `SandboxDbContext`, and start each query body at `public static class Query{N}`.
The target framework's own skill (Spring Data MongoDB or Neo4j) governs the Java side; this skill
governs reading the EF Core source and writing the EF Core harness.
