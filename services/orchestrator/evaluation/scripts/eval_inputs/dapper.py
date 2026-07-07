"""Dapper (raw SQL) source inputs for the UOM eval dataset (schema + idiomatic query bodies).

Queries are ported 1:1 from `benchmarks/DapperPerformance/DapperBenchmark.cs`, restricted to
entities with data in BOTH eval stores (see eval_inputs/efcore.py for the category map and the
data-availability rationale — Query1-6=B1-B6, 7-9=C1-C3, 10=D1, 11-12=E1-E2 re-targeted to Orders,
13-14=F1-F2 on People, 15-16=G1-G2 on Suppliers).

Entities mirror `benchmarks/DapperEntities/*` (OrderLine/Order/Person verbatim; Supplier trimmed to
the fields the G queries touch)."""

SCHEMA = '''\
public class OrderLine
{
    public int OrderLineID { get; set; }
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
public class Order
{
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
public class Person
{
    public int PersonID { get; set; }
    public required string FullName { get; set; }
    public required string PreferredName { get; set; }
    public string? EmailAddress { get; set; }
    public string? CustomFields { get; set; }
    public string? OtherLanguages { get; set; }
}
public class Supplier
{
    public int SupplierID { get; set; }
    public required string SupplierName { get; set; }
    public string? SupplierReference { get; set; }
    public int PaymentDays { get; set; }
}'''

QUERIES = [
    # B1_SelectionOverIndexedColumn
    '''\
public static IEnumerable<OrderLine> Query1(SqlConnection conn)
{
    string sql = @"SELECT * FROM Sales.OrderLines WHERE OrderID = @OrderID";
    return conn.Query<OrderLine>(sql, new { OrderID = 26866 });
}''',
    # B2_SelectionOverNonIndexedColumn
    '''\
public static IEnumerable<OrderLine> Query2(SqlConnection conn)
{
    string sql = @"SELECT * FROM Sales.OrderLines WHERE UnitPrice = @UnitPrice";
    return conn.Query<OrderLine>(sql, new { UnitPrice = 25m });
}''',
    # B3_RangeQuery
    '''\
public static IEnumerable<OrderLine> Query3(SqlConnection conn)
{
    var from = new DateTime(2014, 12, 20);
    var to = new DateTime(2014, 12, 31);
    string sql = @"SELECT * FROM Sales.OrderLines WHERE PickingCompletedWhen >= @From AND PickingCompletedWhen <= @To";
    return conn.Query<OrderLine>(sql, new { From = from, To = to });
}''',
    # B4_InQuery
    '''\
public static IEnumerable<OrderLine> Query4(SqlConnection conn)
{
    var orderIds = new[] { 1, 10, 100, 1000, 10000 };
    string sql = @"SELECT * FROM Sales.OrderLines WHERE OrderID IN @Ids";
    return conn.Query<OrderLine>(sql, new { Ids = orderIds });
}''',
    # B5_TextSearch
    '''\
public static IEnumerable<OrderLine> Query5(SqlConnection conn)
{
    string sql = @"SELECT * FROM Sales.OrderLines WHERE Description LIKE @Pattern";
    return conn.Query<OrderLine>(sql, new { Pattern = "%C++%" });
}''',
    # B6_PagingQuery
    '''\
public static IEnumerable<OrderLine> Query6(SqlConnection conn)
{
    string sql = @"SELECT * FROM Sales.OrderLines ORDER BY OrderLineID OFFSET @Skip ROWS FETCH NEXT @Take ROWS ONLY";
    return conn.Query<OrderLine>(sql, new { Skip = 1000, Take = 50 });
}''',
    # C1_AggregationCount
    '''\
public static IEnumerable<(decimal TaxRate, int Count)> Query7(SqlConnection conn)
{
    string sql = @"SELECT TaxRate, COUNT(*) AS Count FROM Sales.OrderLines GROUP BY TaxRate ORDER BY Count DESC";
    return conn.Query<(decimal TaxRate, int Count)>(sql);
}''',
    # C2_AggregationMax
    '''\
public static decimal? Query8(SqlConnection conn)
{
    string sql = @"SELECT MAX(UnitPrice) FROM Sales.OrderLines";
    return conn.ExecuteScalar<decimal?>(sql);
}''',
    # C3_AggregationSum
    '''\
public static decimal? Query9(SqlConnection conn)
{
    string sql = @"SELECT SUM(Quantity * UnitPrice) FROM Sales.OrderLines";
    return conn.ExecuteScalar<decimal?>(sql);
}''',
    # D1_OneToManyRelationship
    '''\
static Order Query10mapRow(Order o, OrderLine ol)
{
    if (ol != null) o.OrderLines.Add(ol);
    return o;
}
public static Order? Query10(SqlConnection conn)
{
    string sql = @"
        SELECT o.*, ol.*
        FROM Sales.Orders o
        LEFT JOIN Sales.OrderLines ol ON o.OrderID = ol.OrderID
        WHERE o.OrderID = 530";
    var rows = conn.Query<Order, OrderLine, Order>(sql, Query10mapRow, splitOn: "OrderLineID");
    return rows.GroupBy(o => o.OrderID).Select(g => {
        var order = g.First();
        order.OrderLines = g.SelectMany(o => o.OrderLines).ToList();
        return order;
    }).SingleOrDefault();
}''',
    # E1_ColumnSorting (benchmark shape on Orders)
    '''\
public static IEnumerable<Order> Query11(SqlConnection conn)
{
    string sql = @"SELECT TOP 1000 * FROM Sales.Orders ORDER BY ExpectedDeliveryDate";
    return conn.Query<Order>(sql);
}''',
    # E2_Distinct (benchmark shape on Orders)
    '''\
public static IEnumerable<string?> Query12(SqlConnection conn)
{
    string sql = @"SELECT DISTINCT CustomerPurchaseOrderNumber FROM Sales.Orders";
    return conn.Query<string?>(sql);
}''',
    # F1_JSONObjectQuery
    '''\
public static IEnumerable<Person> Query13(SqlConnection conn)
{
    string sql = @"
        SELECT PersonID, FullName, PreferredName, EmailAddress, CustomFields, OtherLanguages
        FROM Application.People
        WHERE JSON_VALUE(CustomFields, '$.Title') = @Title
        ORDER BY PersonID";
    return conn.Query<Person>(sql, new { Title = "Team Member" });
}''',
    # F2_JSONArrayQuery
    '''\
public static IEnumerable<Person> Query14(SqlConnection conn)
{
    string sql = @"
        SELECT PersonID, FullName, PreferredName, EmailAddress, CustomFields, OtherLanguages
        FROM Application.People
        WHERE EXISTS (
            SELECT 1 FROM OPENJSON(OtherLanguages)
            WHERE value = @Language
        )
        ORDER BY PersonID";
    return conn.Query<Person>(sql, new { Language = "Slovak" });
}''',
    # G1_Union
    '''\
public static IEnumerable<int> Query15(SqlConnection conn)
{
    string sql = @"
        SELECT SupplierID FROM Purchasing.Suppliers WHERE SupplierID < 5
        UNION
        SELECT SupplierID FROM Purchasing.Suppliers WHERE SupplierID BETWEEN 5 AND 10
        ORDER BY SupplierID";
    return conn.Query<int>(sql);
}''',
    # G2_Intersection
    '''\
public static IEnumerable<int> Query16(SqlConnection conn)
{
    string sql = @"
        SELECT SupplierID FROM Purchasing.Suppliers WHERE SupplierID < 10
        INTERSECT
        SELECT SupplierID FROM Purchasing.Suppliers WHERE SupplierID BETWEEN 5 AND 15
        ORDER BY SupplierID";
    return conn.Query<int>(sql);
}''',
]
