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
