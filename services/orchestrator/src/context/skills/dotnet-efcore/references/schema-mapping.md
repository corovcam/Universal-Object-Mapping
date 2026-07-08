# EF Core schema mapping (reading the source model, writing the schema fragment)

EF Core maps a POCO to a table with **data annotations** (and/or fluent `OnModelCreating`), and
exposes the tables through a `DbContext` with a `DbSet<T>` per entity. When EF Core is the source,
you (a) read this model to understand what the target must preserve, and (b) re-declare it as the
**schema fragment** that the source validation harness compiles against.

## 1. The entity class

```csharp
[Table("OrderLines", Schema = "Sales")]        // -> table Sales.OrderLines
public class OrderLine
{
    [Key]                                       // primary key
    public int OrderLineID { get; set; }
    [ForeignKey(nameof(Order))]                 // FK column backing the Order navigation
    public int OrderID { get; set; }
    public required string Description { get; set; }   // C# 11 `required`: non-null, must be set
    public int Quantity { get; set; }
    public decimal? UnitPrice { get; set; }     // nullable money
    public decimal TaxRate { get; set; }
    [Column(TypeName = "datetime2")]
    [Precision(7)]
    public DateTime? PickingCompletedWhen { get; set; }
}
```

Attributes you will see and what they mean for the translation:

| Attribute | Meaning | Target intent |
|---|---|---|
| `[Table("N", Schema="S")]` | table name/schema | the collection / node label name source |
| `[Key]` | primary key | source integer id — becomes the store id **plus** a normal field/property on the target |
| `[ForeignKey(nameof(Nav))]` | the scalar FK behind a navigation | a relationship / reference, or an embedded child |
| `[Column(TypeName=…)]`, `[Precision(p,s)]` | SQL column type / decimal precision | precision to preserve for `decimal` |
| `[MaxLength(n)]` / `[StringLength(n)]` | string length | informational only |
| `[JsonPropertyName("x")]` | JSON serialization name (harness only) | NOT an ORM mapping — do not carry to the target as a field name |
| `[NotMapped]` | property is not persisted | drop it |

`[JsonPropertyName]` is a **serialization** hint the harness uses so both sides emit the same JSON
key casing (e.g. `customerId`). It is not part of the object–relational mapping; do not confuse it
with a column name.

## 2. The `DbContext` (REQUIRED in the schema fragment)

The generated entrypoint runs `new SandboxDbContext(...)`, so your schema body must include it with
a `DbSet<T>` for every entity, using the project's expression-bodied convention:

```csharp
public class SandboxDbContext(DbContextOptions<SandboxDbContext> options) : DbContext(options)
{
    public DbSet<Order> Orders => Set<Order>();
    public DbSet<OrderLine> OrderLines => Set<OrderLine>();
    public DbSet<Person> People => Set<Person>();
}
```

The primary-constructor form `SandboxDbContext(DbContextOptions<SandboxDbContext> options) :
DbContext(options)` is required — the bootstrap passes options built with `.UseSqlServer(...)`.

## 3. Navigations (one-to-many / many-to-one)

A collection navigation is a one-to-many; a reference navigation is the many-to-one back-reference.
Initialize collections with the collection expression `[]`:

```csharp
public class Order
{
    [Key] public int OrderID { get; set; }
    [ForeignKey(nameof(Customer))] public int CustomerID { get; set; }
    public Customer Customer { get; set; } = null!;        // reference navigation (many-to-one)
    public List<OrderLine> OrderLines { get; set; } = [];  // collection navigation (one-to-many)
}
```

For the target: a `List<T>` navigation becomes an **embedded array** or a **`@DocumentReference`**
(Spring Data MongoDB) or a **`@Relationship`** to another `@Node` (Spring Data Neo4j). The
`[ForeignKey]` scalar carries the join key.

## 4. Owned types / JSON columns

A complex sub-object stored as a JSON column is an **owned type** configured with
`OwnsOne(...).ToJson()` in `OnModelCreating` (EF Core 8+). The eval `Person.CustomFields` is the
canonical case:

```csharp
public class CustomFields                       // owned type: NO [Table], NO [Key]
{
    public List<string>? OtherLanguages { get; set; }
    public DateTime? HireDate { get; set; }
    public string? Title { get; set; }
}

public class SandboxDbContext(DbContextOptions<SandboxDbContext> options) : DbContext(options)
{
    public DbSet<Person> People => Set<Person>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<Person>().OwnsOne(p => p.CustomFields, cb => cb.ToJson());
        base.OnModelCreating(modelBuilder);
    }
}
```

Reading it: a query like `Where(p => p.CustomFields!.Title == "Team Member")` filters *inside* the
JSON document — it translates to a nested-field match on the target (Mongo `customFields.title`,
Neo4j a nested property or JSON predicate). A `List<string>?` scalar collection (e.g.
`OtherLanguages`) maps to a JSON array; `Contains` over it is an array-membership test.

## 5. .NET → Java type intent (what the target must preserve)

| .NET source type | Java target intent |
|---|---|
| `int` / `int?` | `Integer` |
| `long` / `long?` | `Long` |
| `bool` | `Boolean` |
| `decimal` / `decimal?` | `BigDecimal` (Mongo) / `Double` (Neo4j — no decimal type). **Never** `double` for money |
| `DateTime` / `DateTime?` | `LocalDateTime` (date-only intent → `LocalDate`) |
| `string` | `String` |
| `Guid` | `String` (or `UUID`) |
| `List<T>` navigation | embedded `List<T>` / `@DocumentReference` / `@Relationship` |

Keep the **source `[Key]` integer as a normal field on the target**; the store id (`@Id` String on
Mongo, `@Id @GeneratedValue` on Neo4j) is a separate, store-generated identity.
