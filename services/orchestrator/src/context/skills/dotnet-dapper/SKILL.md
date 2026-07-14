---
name: dotnet-dapper
description: >-
  Expert guidance for reading and writing .NET Dapper 2.1 code (Dapper 2.1 on .NET 10 / C# 14,
  Microsoft.Data.SqlClient, raw T-SQL, System.Text.Json). Use whenever the SOURCE side of a
  translation is Dapper — reading its plain POCO models, its raw SQL query bodies (parameterized
  `@name` params + anonymous param objects, `Query<T>`, `ExecuteScalar<T>`, `QueryMultiple`,
  multi-mapping `Query<T1,T2,TReturn>` + `splitOn`, `IN @ids`, `LIKE @pattern`, `OFFSET/FETCH`
  paging, `UNION`/`INTERSECT`, `JSON_VALUE`/`OPENJSON`), and whenever authoring the Dapper
  source-side validation harness fragment (Query{N}.Harness(SqlConnection) using
  HarnessSupport.RunRows). Trigger even when the user only says "Dapper", "SqlConnection",
  "conn.Query", "raw SQL", "splitOn", "QueryMultiple", or "micro-ORM" without naming the version,
  and when fixing CS-compile errors in a Dapper harness fragment. Its purpose is correctly
  interpreting the raw-SQL Dapper source and producing a version-correct, compilable source harness.
  Do NOT use for: the TARGET side (Spring Data MongoDB / Neo4j — their own skills), EF Core
  DbContext/LINQ, NHibernate mapping-by-code, ADO.NET without Dapper, or SQL Server DBA operations.
---

# .NET Dapper 2.1 Expert (source side)

This skill makes you a reliable engineer for **Dapper 2.1** on **.NET 10 / C# 14**. In the Universal
Object Mapping pipeline, Dapper is a **source** framework — you translate *from* it into a Java
target (Spring Data MongoDB or Neo4j). So this skill buys you two things:

1. **Correctly reading the Dapper source** — plain POCO models plus **raw T-SQL** query strings. The
   semantics to preserve live in the SQL itself (the `WHERE`, `ORDER BY`, `GROUP BY`, `JOIN`,
   `UNION`/`INTERSECT`, `JSON_VALUE`/`OPENJSON`), not in any mapping layer.
2. **Authoring a version-correct Dapper validation-harness fragment** that compiles against Dapper
   2.1 on SQL Server. Dapper is a thin micro-ORM: the fragment runs the raw SQL with
   `conn.Query<T>(...)`/`ExecuteScalar<T>(...)` and materializes rows, so the harness helper is
   `HarnessSupport.RunRows` (row sequences), not `RunQuery`.

What makes Dapper different from EF Core and NHibernate: **there is no object model and no LINQ**.
The query IS the SQL string. You read SQL to understand intent, and you keep the SQL verbatim in the
harness. The POCOs are just row-shape targets Dapper fills by matching column names to properties.

If unsure which namespace a type lives in, **consult `references/imports.md`** — Dapper's `Query`
family are extension methods that need `using Dapper;`.

## Source stack (assume this unless told otherwise)

| Component | Version | Why it matters |
|---|---|---|
| .NET | 10.0 (`net10.0`) | C# 14; `required`, raw string literals `""" … """`, collection expressions `[]` |
| Dapper | 2.1.x | `Query<T>`, `ExecuteScalar<T>`, `QueryMultiple`, multi-mapping — all extension methods on `IDbConnection` |
| ADO provider | `Microsoft.Data.SqlClient` 7.0.x | `SqlConnection` — the connection the fragment receives |
| Serialization | `System.Text.Json` | the harness serializer (injected — do not re-author it) |
| `ImplicitUsings` | enabled | `System`, `System.Linq`, `System.Collections.Generic` etc. in scope |

## How to use this skill

1. Decide what you are producing: **schema fragment** (POCOs + projection records), **query
   fragments**, or **both**.
2. Read the matching reference file(s) before writing code:
   - `references/schema-mapping.md` — plain POCOs, column-to-property name matching, projection
     records/tuples, and the .NET → Java type intent.
   - `references/queries.md` — raw SQL + `@` parameters + anonymous param objects, the `Query<T>` /
     `ExecuteScalar<T>` / `QueryMultiple` / multi-mapping (`splitOn`) surface, and how to wrap each
     query in a `Query{N}.Harness` fragment with `HarnessSupport.RunRows`.
   - `references/imports.md` — the canonical `using` set and the traps.
3. Write the code following the rules below.
4. If the code must run, re-check `using Dapper;` and `using Microsoft.Data.SqlClient;` are present
   (they are in the prelude) and that param object property names match the `@names` in the SQL.

## Non-negotiable rules

**Keep the SQL verbatim; parameterize with `@name` + an anonymous object.** Dapper binds
`new { OrderID = 26866 }` to `@OrderID`. The anonymous object's property names must match the `@`
placeholders exactly. Never string-concatenate values into the SQL.

**`IN` with a collection uses `IN @ids` — no parentheses.** `WHERE OrderID IN @Ids` with
`new { Ids = orderIds }`; Dapper expands the list and adds the parens. Writing `IN (@Ids)` is wrong.

**Never name a helper member `Query{N}`, and never call `Query{N}(...)`, inside the `Query{N}`
class.** Same-named member is `CS0542`; `Query{N}(...)` resolves to the *class* (`CS1955` →
`CS0411`). Name inner helpers `Rows`/`MapRow`/`Build`. This is the most common .NET harness failure.

**The harness fragment shape is fixed** — one class per query, using `RunRows`:

```csharp
public static class Query1
{
    public static object Harness(SqlConnection conn)
    {
        string sql = @"SELECT * FROM Sales.OrderLines WHERE OrderID = @OrderID";
        return HarnessSupport.RunRows(() => conn.Query<OrderLine>(sql, new { OrderID = 26866 }),
                                      ol => ol.OrderLineID);
    }
}
```

`HarnessSupport.RunRows` (provided in the injected prelude — do NOT redeclare it) takes a
`Func<IEnumerable<T>>` and an optional **unique** sort selector, and returns
`{ count, firstSample, lastSample }`. Pass a unique selector when the SQL has no `ORDER BY` of its
own; pass `null` when the SQL already orders by a unique column. For a scalar (`ExecuteScalar<T>`)
build the same map by hand.

**Emit any extra `using` your fragment needs** (e.g. `using Dapper;`); they are hoisted into the
header. No `namespace` line, and do not redeclare the injected serializer / `HarnessSupport`.

**No comments or placeholders in code that will be executed.** Emit complete, runnable code.

**Preserve the source SQL's exact semantics.** Do not add filters, change the projection, or reorder
results beyond the harness's unique tie-break selector (which must not change which rows return).

## Quick orientation example (the shape to aim for)

A plain POCO and a query wrapped as a harness fragment. Note there is no mapping annotation — Dapper
matches `SELECT` columns to POCO properties by name.

```csharp
public class OrderLine
{
    public int OrderLineID { get; set; }
    public int OrderID { get; set; }
    public required string Description { get; set; }
    public int Quantity { get; set; }
    public decimal? UnitPrice { get; set; }
    public decimal TaxRate { get; set; }
    public DateTime? PickingCompletedWhen { get; set; }
}

public static class Query3
{
    public static object Harness(SqlConnection conn)
    {
        var from = new DateTime(2014, 12, 20);
        var to = new DateTime(2014, 12, 31);
        string sql = @"SELECT * FROM Sales.OrderLines
                       WHERE PickingCompletedWhen >= @From AND PickingCompletedWhen <= @To";
        return HarnessSupport.RunRows(() => conn.Query<OrderLine>(sql, new { From = from, To = to }),
                                      ol => ol.OrderLineID);
    }
}
```

## Common traps

- **`Query{N}` member/call collision** (`CS0542`/`CS1955`/`CS0411`) — never name a helper `Query{N}`
  or call `Query{N}(...)` inside `class Query{N}`.
- **`IN (@Ids)` instead of `IN @Ids`** — Dapper adds the parentheses; the extra pair is a syntax
  error.
- **Param-object property name mismatch** — `new { orderId = 1 }` does not bind `@OrderID` reliably;
  keep casing consistent with the `@name`.
- **`splitOn` mismatch in multi-mapping** — `Query<T1,T2,TReturn>` splits each row into `T1`/`T2` at
  the `splitOn` column(s); the default is `Id`, so pass the real boundary column(s)
  (`splitOn: "OrderLineID"`), or every second object comes back null.
- **`decimal` read as `double`** — silently loses precision; carry `decimal` intent to the target.
- **Tuple projection column order** — `Query<(decimal TaxRate, int Count)>` maps by column; alias
  the SQL columns to match (`COUNT(*) AS Count`). A named projection record is more robust.
- **Missing `using Dapper;`** — the whole `Query`/`Execute` family are extension methods and won't
  resolve without it (it is in the prelude, but if you re-emit a fragment header, keep it).

## Project context (Universal Object Mapping)

This skill backs the `generate_translation_node` translator when the **source** is Dapper. In
fragment mode you author, per query, a `Query{N}.Harness(SqlConnection)` for the source side and the
matching Java `Query{N}.harness(...)` for the target; both must return the SAME flat map (`count`,
`firstSample`, `lastSample`). The fixed prelude — `using` lines, the JSON serializer,
`HarnessSupport`, and the generated `Main` (which opens the `SqlConnection`) — is **injected for
you**. Your schema body is just the plain POCO classes (and any projection record the queries need);
each query body starts at `public static class Query{N}`. The target framework's own skill governs
the Java side; this skill governs reading the Dapper SQL source and writing the Dapper harness.
