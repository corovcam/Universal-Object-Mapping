"""EFCore (LINQ) source inputs for the UOM eval dataset (schema + idiomatic query bodies).

Queries 1-16 are ported 1:1 from `benchmarks/EFCorePerformance/EFCoreBenchmarks.cs`; queries 17-40
extend coverage to EVERY benchmark FEATURE category (`benchmarks/EFCoreFeatures/FeatureTests.cs`)
that is answerable in ALL THREE eval stores (SQL WWI <-> Mongo `uom` <-> Neo4j graph):

  Query1-6   = B1-B6  (selection: indexed, non-indexed, range, IN, text search, paging)
  Query7-9   = C1-C3  (aggregation: group-count, max, sum)
  Query10    = D1     (one-to-many relationship fetch)
  Query11-12 = E1-E2  (column sorting + take; distinct projection — re-targeted to Orders)
  Query13-14 = F1-F2  (JSON object / JSON array queries over Application.People)
  Query15-16 = G1-G2  (set operations: union / intersection over Purchasing.Suppliers)
  Query17-19 = A1-A3  (PK entity fetch; limited-entity projection; TWO entities from ONE row)
  Query20    = G3     (set difference / EXCEPT)
  Query21-22 = D2     (many-to-many via the StockItemStockGroups junction: per-item groups;
                       per-group item counts)
  Query23    = D4     (explicit two-entity JOIN projection: purchase order + supplier name)
  Query24    = C4     (aggregation: min)
  Query25    = D6     (EXISTS / Any subquery: orders having a line with quantity >= 200)
  Query26    = D3     (OPTIONAL self-reference: orders <= 1000 incl. NULL backorderOrderId)
  Query27-30 = B7-B10 (compound AND; OR + IS NULL; StartsWith; date equality)
  Query31    = C8     (GROUP BY date part: orders per year)
  Query32-33 = C5-C6  (average; count-distinct)
  Query34    = C7     (GROUP BY + HAVING: customers with > 200 transactions)
  Query35    = C9     (top-N by grouped aggregate: 10 highest-revenue stock items)
  Query36-37 = E3-E4  (multi-column sort; computed-expression sort)
  Query38    = F3     (JSON nested DATE equality: CustomFields.HireDate)
  Query39    = B11    (IN over a string column)
  Query40    = E5     (distinct + sort over an int column: QuantityPerOuter)

EXCLUDED with rationale (documented in out/query-workload-design.md):
  A4 (stored procedure)  — the eval SQL login `uom_readonly` exposes/executes no stored procedures;
  H1 (metadata query)    — INFORMATION_SCHEMA has no semantic analogue in document/graph stores;
  Sales.Customers        — WWI row-level security filters the table to 0 rows for `uom_readonly`,
                           so no source query may touch Customers (CustomerTransactions is open).

ENTITY-DESIGN RULE (2026-07-10): entities expose ONLY columns representable in every eval store.
Dropped: OrderLine.PackageTypeID (no PackageType label/property in the graph, nothing in Mongo);
Order.{SalespersonPersonID, PickedByPersonID, ContactPersonID, LastEditedBy} (the graph's untyped
Order-[:PEOPLE]->Person edges mix all four roles — irrecoverable). OrderLine.{OrderID, StockItemID,
LastEditedBy} STAY: the graph recovers them via its complete (231,412/231,412) ORDERS /
STOCK_ITEMS / PEOPLE relationships. Suppliers.ValidFrom/ValidTo are AVOIDED everywhere (the
Mongo/Neo4j ETL corrupted the sentinel 9999-12-31 into 1816-03-30)."""

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
  public int? BackorderOrderID { get; set; }
  public DateTime OrderDate { get; set; }
  public DateTime ExpectedDeliveryDate { get; set; }
  public string? CustomerPurchaseOrderNumber { get; set; }
  public bool IsUndersupplyBackordered { get; set; }
  public string? Comments { get; set; }
  public string? DeliveryInstructions { get; set; }
  public string? InternalComments { get; set; }
  public DateTime? PickingCompletedWhen { get; set; }
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
  public string? PhoneNumber { get; set; }
  public string? FaxNumber { get; set; }
  public string? WebsiteURL { get; set; }
  public string? BankAccountName { get; set; }
  public string? BankAccountBranch { get; set; }
  public string? BankAccountCode { get; set; }
  public string? BankAccountNumber { get; set; }
  public string? BankInternationalCode { get; set; }
}

[Table("CustomerTransactions", Schema = "Sales")]
public class CustomerTransaction
{
  [Key]
  public int CustomerTransactionID { get; set; }
  public int CustomerID { get; set; }
  public DateTime TransactionDate { get; set; }
  public decimal TransactionAmount { get; set; }
  public decimal OutstandingBalance { get; set; }
  public bool IsFinalized { get; set; }
}

[Table("PurchaseOrders", Schema = "Purchasing")]
public class PurchaseOrder
{
  [Key]
  public int PurchaseOrderID { get; set; }
  public int SupplierID { get; set; }
  public DateTime OrderDate { get; set; }
  public DateTime ExpectedDeliveryDate { get; set; }
  public string? SupplierReference { get; set; }
  public bool IsOrderFinalized { get; set; }
}

[Table("StockItems", Schema = "Warehouse")]
public class StockItem
{
  [Key]
  public int StockItemID { get; set; }
  public required string StockItemName { get; set; }
  public int SupplierID { get; set; }
  public int QuantityPerOuter { get; set; }
  public int LeadTimeDays { get; set; }
  public bool IsChillerStock { get; set; }
  public decimal? UnitPrice { get; set; }
  public decimal RecommendedRetailPrice { get; set; }
}

[Table("StockItemStockGroups", Schema = "Warehouse")]
public class StockItemStockGroup
{
  [Key]
  public int StockItemStockGroupID { get; set; }
  public int StockItemID { get; set; }
  public int StockGroupID { get; set; }
}

public class SupplierContactInfo
{
  public int SupplierID { get; set; }
  public string? SupplierName { get; set; }
  public string? PhoneNumber { get; set; }
  public string? FaxNumber { get; set; }
  public string? WebsiteURL { get; set; }
}

public class SupplierBankAccount
{
  public int SupplierID { get; set; }
  public string? BankAccountName { get; set; }
  public string? BankAccountBranch { get; set; }
  public string? BankAccountCode { get; set; }
  public string? BankAccountNumber { get; set; }
  public string? BankInternationalCode { get; set; }
}

public class SupplierAccounts
{
  public SupplierContactInfo? ContactInfo { get; set; }
  public SupplierBankAccount? BankAccount { get; set; }
}

public class PurchaseOrderInfo
{
  public int PurchaseOrderID { get; set; }
  public string? SupplierName { get; set; }
  public DateTime OrderDate { get; set; }
}

public class SandboxDbContext(DbContextOptions<SandboxDbContext> options) : DbContext(options)
{
  public DbSet<Order> Orders => Set<Order>();
  public DbSet<OrderLine> OrderLines => Set<OrderLine>();
  public DbSet<Person> People => Set<Person>();
  public DbSet<Supplier> Suppliers => Set<Supplier>();
  public DbSet<CustomerTransaction> CustomerTransactions => Set<CustomerTransaction>();
  public DbSet<PurchaseOrder> PurchaseOrders => Set<PurchaseOrder>();
  public DbSet<StockItem> StockItems => Set<StockItem>();
  public DbSet<StockItemStockGroup> StockItemStockGroups => Set<StockItemStockGroup>();

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
    # A1_EntityIdenticalToTable (PK fetch, full entity)
    '''\
public static Supplier? Query17(SandboxDbContext ctx)
{
  return ctx.Suppliers.SingleOrDefault(s => s.SupplierID == 10);
}''',
    # A2_LimitedEntity (projection to a narrower DTO)
    '''\
public static SupplierContactInfo? Query18(SandboxDbContext ctx)
{
  return ctx.Suppliers
    .Where(s => s.SupplierID == 10)
    .Select(s => new SupplierContactInfo
    {
      SupplierID = s.SupplierID,
      SupplierName = s.SupplierName,
      PhoneNumber = s.PhoneNumber,
      FaxNumber = s.FaxNumber,
      WebsiteURL = s.WebsiteURL
    })
    .SingleOrDefault();
}''',
    # A3_MultipleEntitiesFromOneResult (two DTOs materialized from ONE row)
    '''\
public static SupplierAccounts? Query19(SandboxDbContext ctx)
{
  return ctx.Suppliers
    .Where(s => s.SupplierID == 10)
    .Select(s => new SupplierAccounts
    {
      ContactInfo = new SupplierContactInfo
      {
        SupplierID = s.SupplierID,
        SupplierName = s.SupplierName,
        PhoneNumber = s.PhoneNumber,
        FaxNumber = s.FaxNumber,
        WebsiteURL = s.WebsiteURL
      },
      BankAccount = new SupplierBankAccount
      {
        SupplierID = s.SupplierID,
        BankAccountName = s.BankAccountName,
        BankAccountBranch = s.BankAccountBranch,
        BankAccountCode = s.BankAccountCode,
        BankAccountNumber = s.BankAccountNumber,
        BankInternationalCode = s.BankInternationalCode
      }
    })
    .SingleOrDefault();
}''',
    # G3_Difference (EXCEPT)
    '''\
public static List<int> Query20(SandboxDbContext ctx)
{
  var first = ctx.Suppliers.Where(s => s.SupplierID < 10).Select(s => s.SupplierID).ToList();
  var last = ctx.Suppliers.Where(s => s.SupplierID >= 5 && s.SupplierID <= 15).Select(s => s.SupplierID).ToList();
  return first.Except(last).OrderBy(s => s).ToList();
}''',
    # D2a_ManyToMany (junction fetch: the stock groups of one item)
    '''\
public static IQueryable<int> Query21(SandboxDbContext ctx)
{
  return ctx.StockItemStockGroups
    .Where(j => j.StockItemID == 1)
    .OrderBy(j => j.StockGroupID)
    .Select(j => j.StockGroupID);
}''',
    # D2b_ManyToMany (junction aggregation: item count per stock group)
    '''\
public static Dictionary<int, int> Query22(SandboxDbContext ctx)
{
  return ctx.StockItemStockGroups
    .GroupBy(j => j.StockGroupID)
    .Select(g => new { StockGroupID = g.Key, Count = g.Count() })
    .OrderBy(x => x.StockGroupID)
    .ToDictionary(x => x.StockGroupID, x => x.Count);
}''',
    # D4_JoinProjection (explicit two-entity join into a DTO)
    '''\
public static PurchaseOrderInfo? Query23(SandboxDbContext ctx)
{
  return ctx.PurchaseOrders
    .Where(po => po.PurchaseOrderID == 25)
    .Join(ctx.Suppliers,
          po => po.SupplierID,
          s => s.SupplierID,
          (po, s) => new PurchaseOrderInfo
          {
            PurchaseOrderID = po.PurchaseOrderID,
            SupplierName = s.SupplierName,
            OrderDate = po.OrderDate
          })
    .SingleOrDefault();
}''',
    # C4_AggregationMin
    '''\
public static decimal? Query24(SandboxDbContext ctx)
{
  return ctx.OrderLines.Min(ol => ol.UnitPrice);
}''',
    # D6_ExistsSubquery (orders having at least one big line)
    '''\
public static IQueryable<int> Query25(SandboxDbContext ctx)
{
  return ctx.Orders
    .Where(o => o.OrderLines.Any(ol => ol.Quantity >= 200))
    .OrderBy(o => o.OrderID)
    .Select(o => o.OrderID);
}''',
    # D3_OptionalSelfReference (nullable BackorderOrderID must survive as NULL)
    '''\
public static IQueryable<Order> Query26(SandboxDbContext ctx)
{
  return ctx.Orders.Where(o => o.OrderID <= 1000).OrderBy(o => o.OrderID);
}''',
    # B7_CompoundPredicate (AND over two columns)
    '''\
public static IQueryable<OrderLine> Query27(SandboxDbContext ctx)
{
  return ctx.OrderLines
    .Where(ol => ol.TaxRate == 10m && ol.Quantity > 25)
    .OrderBy(ol => ol.OrderLineID);
}''',
    # B8_OrWithNullCheck (IS NULL branch + date branch)
    '''\
public static IQueryable<Order> Query28(SandboxDbContext ctx)
{
  var cutoff = new DateTime(2016, 5, 1);
  return ctx.Orders
    .Where(o => o.PickingCompletedWhen == null || o.OrderDate >= cutoff)
    .OrderBy(o => o.OrderID);
}''',
    # B9_StartsWith (anchored prefix search)
    '''\
public static IQueryable<OrderLine> Query29(SandboxDbContext ctx)
{
  return ctx.OrderLines
    .Where(ol => ol.Description.StartsWith("USB"))
    .OrderBy(ol => ol.OrderLineID);
}''',
    # B10_DateEquality (whole-day match on a date column)
    '''\
public static IQueryable<Order> Query30(SandboxDbContext ctx)
{
  var day = new DateTime(2014, 6, 2);
  return ctx.Orders.Where(o => o.OrderDate == day).OrderBy(o => o.OrderID);
}''',
    # C8_GroupByDatePart (orders per calendar year)
    '''\
public static Dictionary<int, int> Query31(SandboxDbContext ctx)
{
  return ctx.Orders
    .GroupBy(o => o.OrderDate.Year)
    .Select(g => new { Year = g.Key, Count = g.Count() })
    .OrderBy(x => x.Year)
    .ToDictionary(x => x.Year, x => x.Count);
}''',
    # C5_AggregationAverage
    '''\
public static double Query32(SandboxDbContext ctx)
{
  return ctx.OrderLines.Average(ol => (double)ol.Quantity);
}''',
    # C6_CountDistinct
    '''\
public static int Query33(SandboxDbContext ctx)
{
  return ctx.OrderLines.Select(ol => ol.StockItemID).Distinct().Count();
}''',
    # C7_GroupByHaving (customers with more than 200 transactions)
    '''\
public static Dictionary<int, int> Query34(SandboxDbContext ctx)
{
  return ctx.CustomerTransactions
    .GroupBy(t => t.CustomerID)
    .Where(g => g.Count() > 200)
    .Select(g => new { CustomerID = g.Key, Count = g.Count() })
    .OrderBy(x => x.CustomerID)
    .ToDictionary(x => x.CustomerID, x => x.Count);
}''',
    # C9_TopNByGroupedAggregate (10 highest-revenue stock items)
    '''\
public static Dictionary<int, decimal?> Query35(SandboxDbContext ctx)
{
  return ctx.OrderLines
    .GroupBy(ol => ol.StockItemID)
    .Select(g => new { StockItemID = g.Key, Revenue = g.Sum(ol => ol.Quantity * ol.UnitPrice) })
    .OrderByDescending(x => x.Revenue)
    .ThenBy(x => x.StockItemID)
    .Take(10)
    .ToDictionary(x => x.StockItemID, x => x.Revenue);
}''',
    # E3_MultiColumnSort
    '''\
public static IQueryable<OrderLine> Query36(SandboxDbContext ctx)
{
  return ctx.OrderLines
    .OrderByDescending(ol => ol.TaxRate)
    .ThenBy(ol => ol.OrderLineID)
    .Take(100);
}''',
    # E4_ComputedExpressionSort (top 50 line totals)
    '''\
public static Dictionary<int, decimal?> Query37(SandboxDbContext ctx)
{
  return ctx.OrderLines
    .OrderByDescending(ol => ol.Quantity * ol.UnitPrice)
    .ThenBy(ol => ol.OrderLineID)
    .Take(50)
    .Select(ol => new { ol.OrderLineID, Total = ol.Quantity * ol.UnitPrice })
    .ToDictionary(x => x.OrderLineID, x => x.Total);
}''',
    # F3_JSONNestedDateEquality
    '''\
public static IQueryable<Person> Query38(SandboxDbContext ctx)
{
  var hired = new DateTime(2008, 4, 19);
  return ctx.People.Where(p => p.CustomFields!.HireDate == hired).OrderBy(p => p.PersonID);
}''',
    # B11_InQueryOverStrings
    '''\
public static IQueryable<Order> Query39(SandboxDbContext ctx)
{
  var purchaseOrderNumbers = new[] { "12126", "19446", "10203" };
  return ctx.Orders
    .Where(o => purchaseOrderNumbers.Contains(o.CustomerPurchaseOrderNumber))
    .OrderBy(o => o.OrderID);
}''',
    # E5_DistinctSortedIntColumn
    '''\
public static List<int> Query40(SandboxDbContext ctx)
{
  return ctx.StockItems
    .Select(si => si.QuantityPerOuter)
    .Distinct()
    .OrderBy(q => q)
    .ToList();
}''',
]
