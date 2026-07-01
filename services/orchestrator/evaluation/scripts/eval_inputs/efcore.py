"""EFCore (LINQ) source inputs for the UOM eval dataset (schema + idiomatic query bodies).

Extracted from build_eval_dataset.py so the bulky C# inputs live in their own files; the builder
imports SCHEMA/QUERIES from here. Schema is verbatim from tests/fixtures/input-*.txt; queries span
the .NET ORM benchmark categories in this framework's native idiom."""

SCHEMA = '''\
[Table("Customers", Schema = "Sales")]
public class Customer
{
  [Key]
  public required int CustomerID { get; set; }
  [MaxLength(200)]
  public required string CustomerName { get; set; }
  [Column(TypeName = "datetime2")]
  [Precision(7)]
  public required DateTime AccountOpenedDate { get; set; }
  [Column(TypeName = "decimal")]
  [Precision(18, 2)]
  public decimal? CreditLimit { get; set; }
  public List<CustomerTransaction> CustomerTransactions { get; set; } = [];
}

[Table("CustomerTransactions", Schema = "Sales")]
public class CustomerTransaction
{
  [Key]
  public int CustomerTransactionID { get; set; }
  [ForeignKey(nameof(Customer))]
  public int CustomerID { get; set; }
  public DateTime TransactionDate { get; set; }
  public decimal TransactionAmount { get; set; }
}

[Table("Orders", Schema = "Sales")]
public class Order
{
  [Key]
  public int OrderID { get; set; }
  public int CustomerID { get; set; }
  public List<OrderLine> OrderLines { get; set; } = [];
}

[Table("OrderLines", Schema = "Sales")]
public class OrderLine
{
  [Key]
  public int OrderLineID { get; set; }
  [ForeignKey(nameof(Order))]
  public int OrderID { get; set; }
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

public class SandboxDbContext(DbContextOptions<SandboxDbContext> options) : DbContext(options)
{
  public DbSet<Customer> Customers => Set<Customer>();
  public DbSet<Order> Orders => Set<Order>();
  public DbSet<CustomerTransaction> CustomerTransactions => Set<CustomerTransaction>();
  public DbSet<OrderLine> OrderLines => Set<OrderLine>();
}'''

QUERIES = [
    '''\
public static IQueryable<OrderLine> Query1(SandboxDbContext ctx)
{
  var from = new DateTime(2014, 12, 20);
  var to = new DateTime(2014, 12, 31);
  return ctx.OrderLines.Where(ol => ol.PickingCompletedWhen >= from && ol.PickingCompletedWhen <= to);
}''',
    '''\
public static IQueryable<OrderLine> Query2(SandboxDbContext ctx)
{
  return ctx.OrderLines.Where(ol => ol.OrderID == 26866);
}''',
    '''\
public static IQueryable<OrderLine> Query3(SandboxDbContext ctx)
{
  return ctx.OrderLines.Where(ol => ol.UnitPrice == 25m);
}''',
    '''\
public static IQueryable<OrderLine> Query4(SandboxDbContext ctx)
{
  var ids = new[] { 1, 10, 100, 1000, 10000 };
  return ctx.OrderLines.Where(ol => ids.Contains(ol.OrderID));
}''',
    '''\
public static IQueryable<OrderLine> Query5(SandboxDbContext ctx)
{
  return ctx.OrderLines.Where(ol => ol.Description.Contains("C++"));
}''',
    '''\
public static IQueryable<OrderLine> Query6(SandboxDbContext ctx)
{
  return ctx.OrderLines.OrderBy(ol => ol.OrderLineID).Skip(1000).Take(50);
}''',
    '''\
public static IQueryable<dynamic> Query7(SandboxDbContext ctx)
{
  return ctx.OrderLines.GroupBy(ol => ol.TaxRate)
    .Select(g => new { TaxRate = g.Key, Count = g.Count() })
    .OrderByDescending(x => x.Count);
}''',
    '''\
public static IQueryable<dynamic> Query8(SandboxDbContext ctx)
{
  return ctx.OrderLines.GroupBy(ol => ol.PackageTypeID)
    .Select(g => new { PackageTypeID = g.Key, TotalQuantity = g.Sum(ol => ol.Quantity) });
}''',
    '''\
public static IQueryable<Order> Query9(SandboxDbContext ctx)
{
  return ctx.Orders.Include(o => o.OrderLines).Where(o => o.OrderID == 530);
}''',
    '''\
public static IQueryable<Customer> Query10(SandboxDbContext ctx)
{
  return ctx.Customers.Include(c => c.CustomerTransactions).OrderBy(c => c.CustomerID);
}''',
    '''\
public static IQueryable<OrderLine> Query11(SandboxDbContext ctx)
{
  return ctx.OrderLines.OrderByDescending(ol => ol.Quantity).Take(50);
}''',
    '''\
public static IQueryable<string> Query12(SandboxDbContext ctx)
{
  return ctx.OrderLines.Select(ol => ol.Description).Distinct();
}''',
    '''\
public static IQueryable<dynamic> Query13(SandboxDbContext ctx)
{
  return ctx.OrderLines.Select(ol => new { ol.OrderLineID, ol.Quantity });
}''',
    '''\
public static IQueryable<Customer> Query14(SandboxDbContext ctx)
{
  return ctx.Customers.Where(c => c.CreditLimit > 1000m).OrderByDescending(c => c.CreditLimit);
}''',
    '''\
public static IQueryable<OrderLine> Query15(SandboxDbContext ctx)
{
  return ctx.OrderLines.Where(ol => ol.Quantity > 10 && ol.TaxRate == 15m);
}''',
]
