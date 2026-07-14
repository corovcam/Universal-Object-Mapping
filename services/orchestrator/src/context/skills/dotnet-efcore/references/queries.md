# EF Core LINQ queries (reading them, wrapping them as harness fragments)

EF Core queries are **LINQ over `IQueryable<T>`** obtained from a `DbSet<T>`. The provider
translates the expression tree to SQL and runs it server-side. When EF Core is the source you read
the LINQ to understand the semantics to preserve, then re-express each query as a `Query{N}.Harness`
fragment that the validation harness executes.

## The LINQ surface you will encounter

| LINQ | Meaning | SQL it becomes |
|---|---|---|
| `.Where(x => pred)` | filter | `WHERE` |
| `.OrderBy(x => k)` / `.OrderByDescending` | sort | `ORDER BY … ASC/DESC` |
| `.Skip(n).Take(m)` | paging | `OFFSET n ROWS FETCH NEXT m ROWS ONLY` |
| `collection.Contains(x.Col)` | membership | `WHERE Col IN (…)` |
| `x.StrCol.Contains(text)` | substring | `WHERE StrCol LIKE '%text%'` |
| `.Select(x => new { … })` | projection | `SELECT …` |
| `.Distinct()` | dedupe | `SELECT DISTINCT` |
| `.GroupBy(x => k).Select(g => new { g.Key, g.Count() })` | group + aggregate | `GROUP BY` |
| `.Max(x => c)` / `.Sum(x => c)` / `.Count()` | scalar aggregate | `MAX/SUM/COUNT` |
| `.Include(x => x.Nav).ThenInclude(...)` | eager load navigation | `JOIN` (or split queries) |
| `.AsSplitQuery()` | load each Include as a separate round-trip | multiple `SELECT`s |
| `.Single/.SingleOrDefault/.First/.FirstOrDefault` | materialize one | `TOP 1/2` + client check |
| `.Union(other)` / `.Intersect(other)` | set operations | in the eval source these run **in memory** over `ToList()`ed sequences |

**Read `.Contains` carefully.** `orderIds.Contains(ol.OrderID)` is an `IN` list;
`ol.Description.Contains("C++")` is a `LIKE` substring match. They translate to different target
operators (`Criteria.in(...)` vs `Criteria.regex(...)` on Mongo; different Cypher predicates).

## Wrapping a query in a harness fragment

`HarnessSupport.RunQuery` (injected — do not redeclare) is designed for **row sets**:

```csharp
public static object RunQuery<T>(Func<IQueryable<T>> q, Func<T, object>? orderBySelector = null)
// returns { count, firstSample, lastSample }
```

Pass a **unique** `orderBySelector` when the query has no deterministic order, so `firstSample`
(min) and `lastSample` (max) are stable across runs and across stores. Pass `null` when the query
already orders by a unique key.

### Row-returning query → `RunQuery`

```csharp
public static class Query1
{
    public static object Harness(SandboxDbContext ctx)
    {
        int orderId = 26866;
        return HarnessSupport.RunQuery(() => ctx.OrderLines.Where(ol => ol.OrderID == orderId),
                                       ol => ol.OrderLineID);   // unique tie-break
    }
}
```

### Paging query already ordered by a unique key → pass `null`

```csharp
public static class Query6
{
    public static object Harness(SandboxDbContext ctx)
    {
        return HarnessSupport.RunQuery(
            () => ctx.OrderLines.OrderBy(ol => ol.OrderLineID).Skip(1000).Take(50), null);
    }
}
```

### One-to-many fetch (`Include`) — sort by the root's unique key

```csharp
public static class Query10
{
    public static object Harness(SandboxDbContext ctx)
    {
        return HarnessSupport.RunQuery(
            () => ctx.Orders.Include(o => o.OrderLines).Where(o => o.OrderID == 530),
            o => o.OrderID);
    }
}
```

`SingleOrDefault(o => o.OrderID == 530)` in the source is equivalent to
`.Where(o => o.OrderID == 530)` for the harness (which counts and samples). Prefer the `Where` form
so `RunQuery` gets an `IQueryable`.

### Group + aggregate → run `RunQuery` over the grouped projection

Keep the grouping as an `IQueryable` of an anonymous/record projection and sort by the group key
(unique within a `GROUP BY`):

```csharp
public static class Query7
{
    public static object Harness(SandboxDbContext ctx)
    {
        return HarnessSupport.RunQuery(
            () => ctx.OrderLines.GroupBy(ol => ol.TaxRate)
                                .Select(g => new { TaxRate = g.Key, Count = g.Count() }),
            x => x.TaxRate);
    }
}
```

### Scalar aggregate (`Max`, `Sum`, `Count`) → build the map by hand

`RunQuery` needs an `IQueryable`, so for a single scalar build the same three-key map directly and
keep `firstSample` a **leaf scalar** so both sides serialize the identical value:

```csharp
public static class Query8
{
    public static object Harness(SandboxDbContext ctx)
    {
        decimal? max = ctx.OrderLines.Max(ol => ol.UnitPrice);
        return new { count = max.HasValue ? 1 : 0, firstSample = (object?)max, lastSample = (object?)null };
    }
}
```

The target-side harness must produce the **same** `{count, firstSample, lastSample}` for the
equivalence check to pass — coordinate the shape across both sides.

### Set operation returning a primitive list → materialize and sample

```csharp
public static class Query15
{
    public static object Harness(SandboxDbContext ctx)
    {
        var first = ctx.Suppliers.Where(s => s.SupplierID < 5).Select(s => s.SupplierID).ToList();
        var last = ctx.Suppliers.Where(s => s.SupplierID >= 5 && s.SupplierID <= 10)
                                .Select(s => s.SupplierID).ToList();
        var union = first.Union(last).OrderBy(s => s).ToList();
        return new { count = union.Count,
                     firstSample = union.Count > 0 ? (object?)union[0] : null,
                     lastSample = union.Count > 1 ? (object?)union[^1] : null };
    }
}
```

## Reminders

- **Never** name a helper `Query{N}` or call `Query{N}(...)` inside `class Query{N}`
  (`CS0542`/`CS1955`). Name helpers `Rows`/`Build`.
- Do not add filters, parameters, or a different sort than the source expresses; the unique
  `orderBySelector` is the only extra ordering allowed, and it must not change the result set.
- Emit any extra `using` your fragment needs (e.g. `using Microsoft.EntityFrameworkCore;` for
  `Include`); it is hoisted into the header. No `namespace` line.
- The result map keys are exactly `count`, `firstSample`, `lastSample` (plus optional metadata the
  serializer ignores in equivalence). Leaf/scalar values only — never walk a navigation the query
  itself did not fetch.
