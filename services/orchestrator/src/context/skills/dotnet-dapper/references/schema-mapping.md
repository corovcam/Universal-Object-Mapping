# Dapper schema (reading the POCOs, writing the schema fragment)

Dapper has **no mapping layer**. A POCO is just a shape Dapper fills by matching `SELECT` column
names to property names (case-insensitive). There is no `DbContext`, no `ClassMapping<T>`, no
`[Table]`/`[Key]` — the table and column names live entirely in the raw SQL strings (see
`references/queries.md`). Your **schema fragment** is therefore just the plain POCO classes, plus any
projection record/tuple the queries materialize into.

## 1. The POCO

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
    public int LastEditedBy { get; set; }
    public DateTime LastEditedWhen { get; set; }
}
```

- No attributes are needed or used for mapping. Column `OrderLineID` fills property `OrderLineID`.
- If the SQL aliases a column, the alias must match the property (`COUNT(*) AS Count` → `Count`).
- `[JsonPropertyName("customerId")]` may appear on a property so the harness serializer emits the
  same JSON key casing as the target — that is serialization only, not Dapper mapping.
- Navigations (`List<OrderLine>`) exist only when a query multi-maps into them (see below); Dapper
  does not populate them automatically.

## 2. Relationships are assembled in code, not mapped

Dapper does not track relationships. A one-to-many is reconstructed by a **multi-mapping** query
that splits each joined row into two objects and a map function stitches them:

```csharp
public class Order
{
    public int OrderID { get; set; }
    public int CustomerID { get; set; }
    public List<OrderLine> OrderLines { get; set; } = [];   // filled by the map function, not Dapper
}
```

For the target, the `List<T>` still means a one-to-many: an embedded array / `@DocumentReference`
(Mongo) or a `@Relationship` (Neo4j). The join key comes from the SQL `ON` clause.

## 3. Projection records / tuples

Aggregate and set queries materialize into a value tuple or a small record. Include any named
record the query uses in the schema fragment:

```csharp
public record TaxRateCount { public decimal TaxRate { get; set; } public long Count { get; set; } }
```

Value tuples (`conn.Query<(decimal TaxRate, int Count)>(sql)`) map by **column order**, so alias the
SQL columns to match the tuple element names. A named record is more robust than a tuple — prefer it
when re-expressing an aggregate query in the harness.

## 4. JSON columns are raw strings

The eval `Person.CustomFields` and `Person.OtherLanguages` are plain `string?` properties holding
JSON text; the query reaches inside them with SQL Server `JSON_VALUE` / `OPENJSON`. Read the SQL to
learn the semantics — the POCO tells you nothing about the JSON shape.

```csharp
public class Person
{
    public int PersonID { get; set; }
    public required string FullName { get; set; }
    public string? CustomFields { get; set; }      // JSON object as text
    public string? OtherLanguages { get; set; }    // JSON array as text
}
```

## 5. .NET → Java type intent (what the target must preserve)

| .NET source type | Java target intent |
|---|---|
| `int` / `int?` | `Integer` |
| `long` / `long?` | `Long` |
| `bool` | `Boolean` |
| `decimal` / `decimal?` | `BigDecimal` (Mongo) / `Double` (Neo4j — no decimal type). **Never** `double` for money |
| `DateTime` / `DateTime?` | `LocalDateTime` (date-only intent → `LocalDate`) |
| `string` | `String` |
| `List<T>` (multi-mapped) | embedded `List<T>` / `@DocumentReference` / `@Relationship` |

Keep the source integer key as a normal field on the target; the store id is separate.
