"""EFCore (LINQ) source inputs for the UOM eval dataset (schema + idiomatic query bodies).

Queries are ported 1:1 from `benchmarks/EFCorePerformance/EFCoreBenchmarks.cs` (the canonical .NET
ORM benchmark suite), restricted to entities with data in BOTH eval stores (SQL WWI subset ↔ Mongo
`uom` collections: orders, orderLines, people, suppliers — Sales.Customers is EMPTY in the eval SQL
DB and Mongo has no customers/purchaseOrders collections, so the A/D2/D3/E-on-PurchaseOrder/H
categories are excluded or re-targeted):

  Query1-6   = B1-B6  (selection: indexed, non-indexed, range, IN, text search, paging)
  Query7-9   = C1-C3  (aggregation: group-count, max, sum)
  Query10    = D1     (one-to-many relationship fetch)
  Query11    = E1     (column sorting + take; benchmark uses PurchaseOrders — re-targeted to Orders
                       which carry the same ExpectedDeliveryDate column)
  Query12    = E2     (distinct projection; re-targeted from PurchaseOrders.SupplierReference to
                       Orders.CustomerPurchaseOrderNumber, same nullable-string shape)
  Query13-14 = F1-F2  (JSON object / JSON array queries over Application.People)
  Query15-16 = G1-G2  (set operations: union / intersection over Purchasing.Suppliers)

Entities mirror `benchmarks/EFCoreEntities/*` (OrderLine/Order/Person verbatim; Supplier trimmed to
the fields the G queries touch to keep the prompt lean — the queries only project SupplierID)."""

SCHEMA = '''\
[Table("OrderLines", Schema = "Sales")]
public class OrderLine
{
  [Key]
  public int OrderLineID { get; set; }
  [ForeignKey(nameof(Order))]
  public int OrderID { get; set; }
  public int StockItemID { get; set; }
  public required string Description { get; set; }
  public int PackageTypeID { get; set; }
  public int Quantity { get; set; }
  public decimal? UnitPrice { get; set; }
  public decimal TaxRate { get; set; }
  public int PickedQuantity { get; set; }
  public DateTime? PickingCompletedWhen { get; set; }
  public int LastEditedBy { get; set; }
  public DateTime LastEditedWhen { get; set; }
}

[Table("Orders", Schema = "Sales")]
public class Order
{
  [Key]
  public int OrderID { get; set; }
  public int CustomerID { get; set; }
  public int SalespersonPersonID { get; set; }
  public int? PickedByPersonID { get; set; }
  public int ContactPersonID { get; set; }
  public int? BackorderOrderID { get; set; }
  public DateTime OrderDate { get; set; }
  public DateTime ExpectedDeliveryDate { get; set; }
  public string? CustomerPurchaseOrderNumber { get; set; }
  public bool IsUndersupplyBackordered { get; set; }
  public string? Comments { get; set; }
  public string? DeliveryInstructions { get; set; }
  public string? InternalComments { get; set; }
  public DateTime? PickingCompletedWhen { get; set; }
  public int LastEditedBy { get; set; }
  public DateTime LastEditedWhen { get; set; }
  public List<OrderLine> OrderLines { get; set; } = [];
}

[Table("People", Schema = "Application")]
public class Person
{
  [Key]
  public int PersonID { get; set; }
  public required string FullName { get; set; }
  public required string PreferredName { get; set; }
  public string? EmailAddress { get; set; }
  public CustomFields? CustomFields { get; set; }
  public List<string>? OtherLanguages { get; set; }
}

public class CustomFields
{
  public List<string>? OtherLanguages { get; set; }
  public DateTime? HireDate { get; set; }
  public string? Title { get; set; }
}

[Table("Suppliers", Schema = "Purchasing")]
public class Supplier
{
  [Key]
  public int SupplierID { get; set; }
  public required string SupplierName { get; set; }
  public string? SupplierReference { get; set; }
  public int PaymentDays { get; set; }
}

public class SandboxDbContext(DbContextOptions<SandboxDbContext> options) : DbContext(options)
{
  public DbSet<Order> Orders => Set<Order>();
  public DbSet<OrderLine> OrderLines => Set<OrderLine>();
  public DbSet<Person> People => Set<Person>();
  public DbSet<Supplier> Suppliers => Set<Supplier>();

  protected override void OnModelCreating(ModelBuilder modelBuilder)
  {
    modelBuilder.Entity<Person>().OwnsOne(p => p.CustomFields, cb => { cb.ToJson(); });
    base.OnModelCreating(modelBuilder);
  }
}'''

QUERIES = [
    # B1_SelectionOverIndexedColumn
    '''\
public static IQueryable<OrderLine> Query1(SandboxDbContext ctx)
{
  int orderId = 26866;
  return ctx.OrderLines.Where(ol => ol.OrderID == orderId);
}''',
    # B2_SelectionOverNonIndexedColumn
    '''\
public static IQueryable<OrderLine> Query2(SandboxDbContext ctx)
{
  decimal unitPrice = 25m;
  return ctx.OrderLines.Where(ol => ol.UnitPrice == unitPrice);
}''',
    # B3_RangeQuery
    '''\
public static IQueryable<OrderLine> Query3(SandboxDbContext ctx)
{
  var from = new DateTime(2014, 12, 20);
  var to = new DateTime(2014, 12, 31);
  return ctx.OrderLines.Where(ol => ol.PickingCompletedWhen >= from && ol.PickingCompletedWhen <= to);
}''',
    # B4_InQuery
    '''\
public static IQueryable<OrderLine> Query4(SandboxDbContext ctx)
{
  var orderIds = new[] { 1, 10, 100, 1000, 10000 };
  return ctx.OrderLines.Where(ol => orderIds.Contains(ol.OrderID));
}''',
    # B5_TextSearch
    '''\
public static IQueryable<OrderLine> Query5(SandboxDbContext ctx)
{
  string text = "C++";
  return ctx.OrderLines.Where(ol => ol.Description.Contains(text));
}''',
    # B6_PagingQuery
    '''\
public static IQueryable<OrderLine> Query6(SandboxDbContext ctx)
{
  int skip = 1000;
  int take = 50;
  return ctx.OrderLines.OrderBy(ol => ol.OrderLineID).Skip(skip).Take(take);
}''',
    # C1_AggregationCount
    '''\
public static Dictionary<decimal, int> Query7(SandboxDbContext ctx)
{
  return ctx.OrderLines
    .GroupBy(ol => ol.TaxRate)
    .Select(g => new { TaxRate = g.Key, Count = g.Count() })
    .OrderByDescending(x => x.Count)
    .ToDictionary(x => x.TaxRate, x => x.Count);
}''',
    # C2_AggregationMax
    '''\
public static decimal? Query8(SandboxDbContext ctx)
{
  return ctx.OrderLines.Max(ol => ol.UnitPrice);
}''',
    # C3_AggregationSum
    '''\
public static decimal? Query9(SandboxDbContext ctx)
{
  return ctx.OrderLines.Sum(ol => ol.Quantity * ol.UnitPrice);
}''',
    # D1_OneToManyRelationship
    '''\
public static Order? Query10(SandboxDbContext ctx)
{
  return ctx.Orders.Include(o => o.OrderLines).SingleOrDefault(o => o.OrderID == 530);
}''',
    # E1_ColumnSorting (benchmark shape on Orders)
    '''\
public static IQueryable<Order> Query11(SandboxDbContext ctx)
{
  return ctx.Orders.OrderBy(o => o.ExpectedDeliveryDate).Take(1000);
}''',
    # E2_Distinct (benchmark shape on Orders)
    '''\
public static IQueryable<string?> Query12(SandboxDbContext ctx)
{
  return ctx.Orders.Select(o => o.CustomerPurchaseOrderNumber).Distinct();
}''',
    # F1_JSONObjectQuery
    '''\
public static IQueryable<Person> Query13(SandboxDbContext ctx)
{
  return ctx.People.Where(p => p.CustomFields!.Title == "Team Member").OrderBy(p => p.PersonID);
}''',
    # F2_JSONArrayQuery
    '''\
public static IQueryable<Person> Query14(SandboxDbContext ctx)
{
  return ctx.People.Where(p => p.OtherLanguages!.Contains("Slovak")).OrderBy(p => p.PersonID);
}''',
    # G1_Union
    '''\
public static List<int> Query15(SandboxDbContext ctx)
{
  var first = ctx.Suppliers.Where(s => s.SupplierID < 5).Select(s => s.SupplierID).ToList();
  var last = ctx.Suppliers.Where(s => s.SupplierID >= 5 && s.SupplierID <= 10).Select(s => s.SupplierID).ToList();
  return first.Union(last).OrderBy(s => s).ToList();
}''',
    # G2_Intersection
    '''\
public static List<int> Query16(SandboxDbContext ctx)
{
  var first = ctx.Suppliers.Where(s => s.SupplierID < 10).Select(s => s.SupplierID).ToList();
  var last = ctx.Suppliers.Where(s => s.SupplierID >= 5 && s.SupplierID <= 15).Select(s => s.SupplierID).ToList();
  return first.Intersect(last).OrderBy(s => s).ToList();
}''',
]
