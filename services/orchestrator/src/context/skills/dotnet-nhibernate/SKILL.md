---
name: dotnet-nhibernate
description: >-
  Expert guidance for reading and writing .NET NHibernate 5.5 code (NHibernate 5.5 on .NET 10 /
  C# 14, SQL Server, mapping-by-code, System.Text.Json). Use whenever the SOURCE side of a
  translation is NHibernate — reading its POCO entities (every mapped member `virtual`), its
  mapping-by-code `ClassMapping<T>` classes named `<Entity>Map` (Id/Property/Bag/ManyToOne with
  Generators), its LINQ over `ISession.Query<T>()`, or its native SQL via `CreateSQLQuery` +
  `Transformers.AliasToBean<T>()`, and whenever authoring the NHibernate source-side validation
  harness fragment (Query{N}.Harness(NHibernate.ISession) using HarnessSupport.RunQuery/RunRows).
  Trigger even when the user only says "NHibernate", "ISession", "ClassMapping", "mapping-by-code",
  "session.Query", "CreateSQLQuery", or "HBM/AliasToBean" without naming the version, and when
  fixing CS-compile or NHibernate-startup errors in an NHibernate harness fragment. Its purpose is
  correctly interpreting the NHibernate source and producing a version-correct, compilable source
  harness. Do NOT use for: the TARGET side (Spring Data MongoDB / Neo4j — their own skills), EF Core
  DbContext/LINQ, Dapper raw SQL, hbm.xml-only mapping, or SQL Server DBA operations.
---

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
