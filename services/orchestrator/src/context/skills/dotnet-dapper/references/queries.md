# Dapper queries (reading the raw SQL, wrapping it as harness fragments)

Dapper executes **raw T-SQL** and maps result rows onto POCOs. There is no LINQ and no expression
tree — the semantics live in the SQL string. You read the SQL to learn what the target must
reproduce, and you keep the SQL verbatim in the harness fragment.

## The Dapper query surface

| Method | Returns | Use |
|---|---|---|
| `conn.Query<T>(sql, param)` | `IEnumerable<T>` (buffered) | row sets |
| `conn.QueryFirstOrDefault<T>(sql, param)` / `QuerySingle<T>` | one `T` | single-row |
| `conn.ExecuteScalar<T>(sql, param)` | one scalar `T` | `MAX`/`SUM`/`COUNT` etc. |
| `conn.Query<T1,T2,TReturn>(sql, map, splitOn: "…")` | `IEnumerable<TReturn>` | multi-mapping a JOIN into related objects |
| `conn.QueryMultiple(sql, param)` → `GridReader` | `.Read<T>()` / `.ReadSingle<T>()` | several result sets in one round-trip |

### Parameters

`@name` placeholders bind to an anonymous object's properties:

```csharp
string sql = @"SELECT * FROM Sales.OrderLines WHERE OrderID = @OrderID";
conn.Query<OrderLine>(sql, new { OrderID = 26866 });
```

- **`IN`**: `WHERE OrderID IN @Ids` with `new { Ids = orderIds }` — Dapper expands the collection and
  adds the parentheses. Do **not** write `IN (@Ids)`.
- **`LIKE`**: `WHERE Description LIKE @Pattern` with `new { Pattern = "%C++%" }` — the wildcards are
  part of the value.
- **Paging**: `ORDER BY OrderLineID OFFSET @Skip ROWS FETCH NEXT @Take ROWS ONLY`.
- **JSON**: `WHERE JSON_VALUE(CustomFields, '$.Title') = @Title` (nested field match);
  `EXISTS (SELECT 1 FROM OPENJSON(OtherLanguages) WHERE value = @Language)` (array membership).
- **Set ops**: `SELECT … UNION SELECT …` / `… INTERSECT …` (in the SQL itself, unlike EF Core/
  NHibernate where the eval does them in memory).

### Multi-mapping (one-to-many reconstruction)

```csharp
static Order MapRow(Order o, OrderLine ol) { if (ol != null) o.OrderLines.Add(ol); return o; }

string sql = @"SELECT o.*, ol.*
               FROM Sales.Orders o
               LEFT JOIN Sales.OrderLines ol ON o.OrderID = ol.OrderID
               WHERE o.OrderID = 530";
var rows = conn.Query<Order, OrderLine, Order>(sql, MapRow, splitOn: "OrderLineID");
var orders = rows.GroupBy(o => o.OrderID).Select(g => {
    var order = g.First();
    order.OrderLines = g.SelectMany(o => o.OrderLines).ToList();
    return order;
}).ToList();
```

`splitOn` names the first column of the **second** object (here the JOIN's `ol.*` starts at
`OrderLineID`); the default is `Id`, so it almost always must be set explicitly. Note the map
helper is named `MapRow`, **not** `Query10` — a member named like the enclosing `Query10` class is a
compile error (`CS0542`).

## Wrapping a query in a harness fragment

Dapper materializes rows, so the harness helper is `HarnessSupport.RunRows` (injected — do not
redeclare it): a `Func<IEnumerable<T>>` + an optional **unique** sort selector →
`{ count, firstSample, lastSample }`. Pass a unique selector when the SQL has no `ORDER BY` of its
own; pass `null` when it already orders by a unique column. For a scalar (`ExecuteScalar<T>`) build
the same map by hand.

### Row query → `RunRows`

```csharp
public static class Query4
{
    public static object Harness(SqlConnection conn)
    {
        var orderIds = new[] { 1, 10, 100, 1000, 10000 };
        string sql = @"SELECT * FROM Sales.OrderLines WHERE OrderID IN @Ids";
        return HarnessSupport.RunRows(() => conn.Query<OrderLine>(sql, new { Ids = orderIds }),
                                      ol => ol.OrderLineID);
    }
}
```

### Multi-mapped one-to-many → `RunRows`, sort by the root key

```csharp
public static class Query10
{
    static Order MapRow(Order o, OrderLine ol) { if (ol != null) o.OrderLines.Add(ol); return o; }

    public static object Harness(SqlConnection conn)
    {
        string sql = @"SELECT o.*, ol.*
                       FROM Sales.Orders o
                       LEFT JOIN Sales.OrderLines ol ON o.OrderID = ol.OrderID
                       WHERE o.OrderID = 530";
        // Explicit <Order>: a block-bodied lambda's return type is not always inferred for the
        // Func<IEnumerable<T>> parameter, which is exactly the CS0411 zone — spell T out.
        return HarnessSupport.RunRows<Order>(() =>
        {
            var rows = conn.Query<Order, OrderLine, Order>(sql, MapRow, splitOn: "OrderLineID");
            return rows.GroupBy(o => o.OrderID).Select(g =>
            {
                var order = g.First();
                order.OrderLines = g.SelectMany(o => o.OrderLines).ToList();
                return order;
            });
        }, o => o.OrderID);
    }
}
```

### Aggregate projection (`GROUP BY`) → `RunRows` over the projection

```csharp
public static class Query7
{
    public static object Harness(SqlConnection conn)
    {
        string sql = @"SELECT TaxRate, COUNT(*) AS Count FROM Sales.OrderLines
                       GROUP BY TaxRate ORDER BY Count DESC";
        return HarnessSupport.RunRows(() => conn.Query<TaxRateCount>(sql), x => x.TaxRate);
    }
}
```

### Scalar aggregate (`ExecuteScalar`) → build the map by hand

```csharp
public static class Query8
{
    public static object Harness(SqlConnection conn)
    {
        string sql = @"SELECT MAX(UnitPrice) FROM Sales.OrderLines";
        decimal? max = conn.ExecuteScalar<decimal?>(sql);
        return new { count = max.HasValue ? 1 : 0, firstSample = (object?)max, lastSample = (object?)null };
    }
}
```

### Set operation returning primitives → `RunRows`, sort by value

```csharp
public static class Query15
{
    public static object Harness(SqlConnection conn)
    {
        string sql = @"SELECT SupplierID FROM Purchasing.Suppliers WHERE SupplierID < 5
                       UNION
                       SELECT SupplierID FROM Purchasing.Suppliers WHERE SupplierID BETWEEN 5 AND 10
                       ORDER BY SupplierID";
        return HarnessSupport.RunRows(() => conn.Query<int>(sql), x => x);
    }
}
```

The target-side harness must produce the **same** `{count, firstSample, lastSample}` map for the
equivalence check to pass — coordinate the shape across both sides.

## Reminders

- **Never** name a helper `Query{N}` or call `Query{N}(...)` inside `class Query{N}`
  (`CS0542`/`CS1955`). Name helpers `Rows`/`MapRow`/`Build`.
- `RunRows` is the Dapper helper (rows are always materialized); there is no `RunQuery` path here.
- When you pass a **block-bodied** lambda (`() => { … return …; }`) to `RunRows`, give the type
  argument explicitly — `RunRows<Order>(() => { … })` — so element-type inference cannot fail with
  `CS0411`. An expression-bodied lambda (`() => conn.Query<OrderLine>(…)`) infers fine.
- `IN @ids` (no parens); param-object property names must match the `@names`; `splitOn` must name the
  real object boundary column.
- Emit `using Dapper;` if you re-emit a fragment header; it is hoisted. No `namespace` line.
- Keep the SQL verbatim; the only extra ordering allowed is the harness's unique sort selector, and
  it must not change which rows return.
