"""Dapper (raw SQL) source inputs for the UOM eval dataset (schema + idiomatic query bodies).

Extracted from build_eval_dataset.py so the bulky C# inputs live in their own files; the builder
imports SCHEMA/QUERIES from here. Schema is verbatim from tests/fixtures/input-*.txt; queries span
the .NET ORM benchmark categories in this framework's native idiom."""

SCHEMA = '''\
public class Customer
{
    public required int CustomerID { get; set; }
    public required string CustomerName { get; set; }
    public required DateTime AccountOpenedDate { get; set; }
    public decimal? CreditLimit { get; set; }
    public List<CustomerTransaction> CustomerTransactions { get; set; } = [];
}
public class CustomerTransaction
{
    public int CustomerTransactionID { get; set; }
    public int CustomerID { get; set; }
    public DateTime TransactionDate { get; set; }
    public decimal TransactionAmount { get; set; }
}
public class Order
{
    public int OrderID { get; set; }
    public int CustomerID { get; set; }
    public List<OrderLine> OrderLines { get; set; } = [];
}
public class OrderLine
{
    public int OrderLineID { get; set; }
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
}'''

QUERIES = [
    '''\
public static IEnumerable<OrderLine> Query1(SqlConnection conn)
{
    var from = new DateTime(2014, 12, 20);
    var to = new DateTime(2014, 12, 31);
    string sql = @"SELECT * FROM Sales.OrderLines WHERE PickingCompletedWhen >= @From AND PickingCompletedWhen <= @To";
    return conn.Query<OrderLine>(sql, new { From = from, To = to });
}''',
    '''\
public static IEnumerable<OrderLine> Query2(SqlConnection conn)
{
    string sql = @"SELECT * FROM Sales.OrderLines WHERE OrderID = @OrderID";
    return conn.Query<OrderLine>(sql, new { OrderID = 26866 });
}''',
    '''\
public static IEnumerable<OrderLine> Query3(SqlConnection conn)
{
    string sql = @"SELECT * FROM Sales.OrderLines WHERE UnitPrice = @UnitPrice";
    return conn.Query<OrderLine>(sql, new { UnitPrice = 25m });
}''',
    '''\
public static IEnumerable<OrderLine> Query4(SqlConnection conn)
{
    var ids = new[] { 1, 10, 100, 1000, 10000 };
    string sql = @"SELECT * FROM Sales.OrderLines WHERE OrderID IN @Ids";
    return conn.Query<OrderLine>(sql, new { Ids = ids });
}''',
    '''\
public static IEnumerable<OrderLine> Query5(SqlConnection conn)
{
    string sql = @"SELECT * FROM Sales.OrderLines WHERE Description LIKE @Pattern";
    return conn.Query<OrderLine>(sql, new { Pattern = "%C++%" });
}''',
    '''\
public static IEnumerable<OrderLine> Query6(SqlConnection conn)
{
    string sql = @"SELECT * FROM Sales.OrderLines ORDER BY OrderLineID OFFSET 1000 ROWS FETCH NEXT 50 ROWS ONLY";
    return conn.Query<OrderLine>(sql);
}''',
    '''\
public static IEnumerable<(decimal TaxRate, int Count)> Query7(SqlConnection conn)
{
    string sql = @"SELECT TaxRate, COUNT(*) AS Count FROM Sales.OrderLines GROUP BY TaxRate ORDER BY Count DESC";
    return conn.Query<(decimal TaxRate, int Count)>(sql);
}''',
    '''\
public static IEnumerable<(int PackageTypeID, int TotalQuantity)> Query8(SqlConnection conn)
{
    string sql = @"SELECT PackageTypeID, SUM(Quantity) AS TotalQuantity FROM Sales.OrderLines GROUP BY PackageTypeID";
    return conn.Query<(int PackageTypeID, int TotalQuantity)>(sql);
}''',
    '''\
static Order Query9mapRow(Order o, OrderLine ol)
{
    o.OrderLines.Add(ol);
    return o;
}
public static IEnumerable<Order> Query9(SqlConnection conn)
{
    string sql = @"
        SELECT o.*, ol.*
        FROM Sales.Orders o
        LEFT JOIN Sales.OrderLines ol ON o.OrderID = ol.OrderID
        WHERE o.OrderID = 530";
    var rows = conn.Query<Order, OrderLine, Order>(sql, Query9mapRow, splitOn: "OrderLineID");
    return rows.GroupBy(o => o.OrderID).Select(g => {
        var order = g.First();
        order.OrderLines = g.SelectMany(o => o.OrderLines).Where(ol => ol != null).ToList();
        return order;
    });
}''',
    '''\
static Customer Query10mapRow(Customer c, CustomerTransaction t)
{
    if (t != null) c.CustomerTransactions.Add(t);
    return c;
}
public static IEnumerable<Customer> Query10(SqlConnection conn)
{
    string sql = @"
        SELECT c.*, t.*
        FROM Sales.Customers c
        LEFT JOIN Sales.CustomerTransactions t ON c.CustomerID = t.CustomerID
        ORDER BY c.CustomerID";
    var rows = conn.Query<Customer, CustomerTransaction, Customer>(sql, Query10mapRow, splitOn: "CustomerTransactionID");
    return rows.GroupBy(c => c.CustomerID).Select(g => {
        var customer = g.First();
        customer.CustomerTransactions = g.SelectMany(c => c.CustomerTransactions).Where(t => t != null).ToList();
        return customer;
    });
}''',
    '''\
public static IEnumerable<OrderLine> Query11(SqlConnection conn)
{
    string sql = @"SELECT TOP 50 * FROM Sales.OrderLines ORDER BY Quantity DESC";
    return conn.Query<OrderLine>(sql);
}''',
    '''\
public static IEnumerable<string> Query12(SqlConnection conn)
{
    string sql = @"SELECT DISTINCT Description FROM Sales.OrderLines";
    return conn.Query<string>(sql);
}''',
    '''\
public static IEnumerable<(int OrderLineID, int Quantity)> Query13(SqlConnection conn)
{
    string sql = @"SELECT OrderLineID, Quantity FROM Sales.OrderLines";
    return conn.Query<(int OrderLineID, int Quantity)>(sql);
}''',
    '''\
public static IEnumerable<Customer> Query14(SqlConnection conn)
{
    string sql = @"SELECT * FROM Sales.Customers WHERE CreditLimit > @Limit ORDER BY CreditLimit DESC";
    return conn.Query<Customer>(sql, new { Limit = 1000m });
}''',
    '''\
public static IEnumerable<OrderLine> Query15(SqlConnection conn)
{
    string sql = @"SELECT * FROM Sales.OrderLines WHERE Quantity > @Qty AND TaxRate = @Tax";
    return conn.Query<OrderLine>(sql, new { Qty = 10, Tax = 15m });
}''',
]
