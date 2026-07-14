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
