"""Dapper (raw SQL) source inputs for the UOM eval dataset (schema + idiomatic query bodies).

Queries are ported 1:1 from `benchmarks/DapperPerformance/DapperBenchmark.cs` (1-16) and extended
(17-40) to cover every answerable benchmark FEATURE category — see eval_inputs/efcore.py for the
full category map, the data-availability rationale, the A4/H1/Sales.Customers exclusions, and the
entity-design rule (only columns representable in ALL THREE eval stores; PackageTypeID and the
Order person-role FKs are dropped, ValidFrom/ValidTo avoided).

Dapper-specific idioms preserved from `benchmarks/DapperFeatures/FeatureTests.cs`: `SELECT *`
mapping for full entities (A1), explicit column-list projection into a DTO (A2), and MULTI-MAPPING
two DTOs from one row via `splitOn:` (A3). Aggregations use `ExecuteScalar`, grouped results use
value-tuple mapping (matching the benchmark's C1 shape)."""

SCHEMA = '''\
public class OrderLine
{
    public int OrderLineID { get; set; }
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
public class Order
{
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
    public string? PhoneNumber { get; set; }
    public string? FaxNumber { get; set; }
    public string? WebsiteURL { get; set; }
    public string? BankAccountName { get; set; }
    public string? BankAccountBranch { get; set; }
    public string? BankAccountCode { get; set; }
    public string? BankAccountNumber { get; set; }
    public string? BankInternationalCode { get; set; }
}
public class CustomerTransaction
{
    public int CustomerTransactionID { get; set; }
    public int CustomerID { get; set; }
    public DateTime TransactionDate { get; set; }
    public decimal TransactionAmount { get; set; }
    public decimal OutstandingBalance { get; set; }
    public bool IsFinalized { get; set; }
}
public class PurchaseOrder
{
    public int PurchaseOrderID { get; set; }
    public int SupplierID { get; set; }
    public DateTime OrderDate { get; set; }
    public DateTime ExpectedDeliveryDate { get; set; }
    public string? SupplierReference { get; set; }
    public bool IsOrderFinalized { get; set; }
}
public class StockItem
{
    public int StockItemID { get; set; }
    public required string StockItemName { get; set; }
    public int SupplierID { get; set; }
    public int QuantityPerOuter { get; set; }
    public int LeadTimeDays { get; set; }
    public bool IsChillerStock { get; set; }
    public decimal? UnitPrice { get; set; }
    public decimal RecommendedRetailPrice { get; set; }
}
public class StockItemStockGroup
{
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
    # A1_EntityIdenticalToTable (PK fetch, full entity)
    '''\
public static Supplier? Query17(SqlConnection conn)
{
    string sql = @"SELECT * FROM Purchasing.Suppliers WHERE SupplierID = @SupplierID";
    return conn.QuerySingleOrDefault<Supplier>(sql, new { SupplierID = 10 });
}''',
    # A2_LimitedEntity (explicit column-list projection into a DTO)
    '''\
public static SupplierContactInfo? Query18(SqlConnection conn)
{
    string sql = @"
        SELECT SupplierID, SupplierName, PhoneNumber, FaxNumber, WebsiteURL
        FROM Purchasing.Suppliers WHERE SupplierID = @SupplierID";
    return conn.QuerySingleOrDefault<SupplierContactInfo>(sql, new { SupplierID = 10 });
}''',
    # A3_MultipleEntitiesFromOneResult (multi-mapping two DTOs from ONE row via splitOn)
    '''\
public static SupplierAccounts? Query19(SqlConnection conn)
{
    string sql = @"
        SELECT
            SupplierID, SupplierName, PhoneNumber, FaxNumber, WebsiteURL,
            SupplierID, BankAccountName, BankAccountBranch, BankAccountCode, BankAccountNumber, BankInternationalCode
        FROM Purchasing.Suppliers WHERE SupplierID = @SupplierID";
    return conn.Query<SupplierContactInfo, SupplierBankAccount, SupplierAccounts>(
        sql,
        (contactInfo, bankAccount) => new SupplierAccounts { ContactInfo = contactInfo, BankAccount = bankAccount },
        new { SupplierID = 10 },
        splitOn: "SupplierID"
    ).SingleOrDefault();
}''',
    # G3_Difference (EXCEPT)
    '''\
public static IEnumerable<int> Query20(SqlConnection conn)
{
    string sql = @"
        SELECT SupplierID FROM Purchasing.Suppliers WHERE SupplierID < 10
        EXCEPT
        SELECT SupplierID FROM Purchasing.Suppliers WHERE SupplierID BETWEEN 5 AND 15
        ORDER BY SupplierID";
    return conn.Query<int>(sql);
}''',
    # D2a_ManyToMany (junction fetch: the stock groups of one item)
    '''\
public static IEnumerable<int> Query21(SqlConnection conn)
{
    string sql = @"
        SELECT StockGroupID FROM Warehouse.StockItemStockGroups
        WHERE StockItemID = @StockItemID
        ORDER BY StockGroupID";
    return conn.Query<int>(sql, new { StockItemID = 1 });
}''',
    # D2b_ManyToMany (junction aggregation: item count per stock group)
    '''\
public static IEnumerable<(int StockGroupID, int Count)> Query22(SqlConnection conn)
{
    string sql = @"
        SELECT StockGroupID, COUNT(*) AS Count
        FROM Warehouse.StockItemStockGroups
        GROUP BY StockGroupID
        ORDER BY StockGroupID";
    return conn.Query<(int StockGroupID, int Count)>(sql);
}''',
    # D4_JoinProjection (explicit two-entity join into a DTO)
    '''\
public static PurchaseOrderInfo? Query23(SqlConnection conn)
{
    string sql = @"
        SELECT po.PurchaseOrderID, s.SupplierName, po.OrderDate
        FROM Purchasing.PurchaseOrders po
        JOIN Purchasing.Suppliers s ON s.SupplierID = po.SupplierID
        WHERE po.PurchaseOrderID = @PurchaseOrderID";
    return conn.QuerySingleOrDefault<PurchaseOrderInfo>(sql, new { PurchaseOrderID = 25 });
}''',
    # C4_AggregationMin
    '''\
public static decimal? Query24(SqlConnection conn)
{
    string sql = @"SELECT MIN(UnitPrice) FROM Sales.OrderLines";
    return conn.ExecuteScalar<decimal?>(sql);
}''',
    # D6_ExistsSubquery (orders having at least one big line)
    '''\
public static IEnumerable<int> Query25(SqlConnection conn)
{
    string sql = @"
        SELECT o.OrderID FROM Sales.Orders o
        WHERE EXISTS (
            SELECT 1 FROM Sales.OrderLines ol
            WHERE ol.OrderID = o.OrderID AND ol.Quantity >= @MinQuantity
        )
        ORDER BY o.OrderID";
    return conn.Query<int>(sql, new { MinQuantity = 200 });
}''',
    # D3_OptionalSelfReference (nullable BackorderOrderID must survive as NULL)
    '''\
public static IEnumerable<Order> Query26(SqlConnection conn)
{
    string sql = @"SELECT * FROM Sales.Orders WHERE OrderID <= @MaxOrderID ORDER BY OrderID";
    return conn.Query<Order>(sql, new { MaxOrderID = 1000 });
}''',
    # B7_CompoundPredicate (AND over two columns)
    '''\
public static IEnumerable<OrderLine> Query27(SqlConnection conn)
{
    string sql = @"
        SELECT * FROM Sales.OrderLines
        WHERE TaxRate = @TaxRate AND Quantity > @MinQuantity
        ORDER BY OrderLineID";
    return conn.Query<OrderLine>(sql, new { TaxRate = 10m, MinQuantity = 25 });
}''',
    # B8_OrWithNullCheck (IS NULL branch + date branch)
    '''\
public static IEnumerable<Order> Query28(SqlConnection conn)
{
    string sql = @"
        SELECT * FROM Sales.Orders
        WHERE PickingCompletedWhen IS NULL OR OrderDate >= @Cutoff
        ORDER BY OrderID";
    return conn.Query<Order>(sql, new { Cutoff = new DateTime(2016, 5, 1) });
}''',
    # B9_StartsWith (anchored prefix search)
    '''\
public static IEnumerable<OrderLine> Query29(SqlConnection conn)
{
    string sql = @"SELECT * FROM Sales.OrderLines WHERE Description LIKE @Pattern ORDER BY OrderLineID";
    return conn.Query<OrderLine>(sql, new { Pattern = "USB%" });
}''',
    # B10_DateEquality (whole-day match on a date column)
    '''\
public static IEnumerable<Order> Query30(SqlConnection conn)
{
    string sql = @"SELECT * FROM Sales.Orders WHERE OrderDate = @Day ORDER BY OrderID";
    return conn.Query<Order>(sql, new { Day = new DateTime(2014, 6, 2) });
}''',
    # C8_GroupByDatePart (orders per calendar year)
    '''\
public static IEnumerable<(int Year, int Count)> Query31(SqlConnection conn)
{
    string sql = @"
        SELECT YEAR(OrderDate) AS Year, COUNT(*) AS Count
        FROM Sales.Orders
        GROUP BY YEAR(OrderDate)
        ORDER BY Year";
    return conn.Query<(int Year, int Count)>(sql);
}''',
    # C5_AggregationAverage
    '''\
public static double? Query32(SqlConnection conn)
{
    string sql = @"SELECT AVG(CAST(Quantity AS float)) FROM Sales.OrderLines";
    return conn.ExecuteScalar<double?>(sql);
}''',
    # C6_CountDistinct
    '''\
public static int Query33(SqlConnection conn)
{
    string sql = @"SELECT COUNT(DISTINCT StockItemID) FROM Sales.OrderLines";
    return conn.ExecuteScalar<int>(sql);
}''',
    # C7_GroupByHaving (customers with more than 200 transactions)
    '''\
public static IEnumerable<(int CustomerID, int Count)> Query34(SqlConnection conn)
{
    string sql = @"
        SELECT CustomerID, COUNT(*) AS Count
        FROM Sales.CustomerTransactions
        GROUP BY CustomerID
        HAVING COUNT(*) > @MinTransactions
        ORDER BY CustomerID";
    return conn.Query<(int CustomerID, int Count)>(sql, new { MinTransactions = 200 });
}''',
    # C9_TopNByGroupedAggregate (10 highest-revenue stock items)
    '''\
public static IEnumerable<(int StockItemID, decimal Revenue)> Query35(SqlConnection conn)
{
    string sql = @"
        SELECT TOP 10 StockItemID, SUM(Quantity * UnitPrice) AS Revenue
        FROM Sales.OrderLines
        GROUP BY StockItemID
        ORDER BY Revenue DESC, StockItemID";
    return conn.Query<(int StockItemID, decimal Revenue)>(sql);
}''',
    # E3_MultiColumnSort
    '''\
public static IEnumerable<OrderLine> Query36(SqlConnection conn)
{
    string sql = @"SELECT TOP 100 * FROM Sales.OrderLines ORDER BY TaxRate DESC, OrderLineID";
    return conn.Query<OrderLine>(sql);
}''',
    # E4_ComputedExpressionSort (top 50 line totals)
    '''\
public static IEnumerable<(int OrderLineID, decimal Total)> Query37(SqlConnection conn)
{
    string sql = @"
        SELECT TOP 50 OrderLineID, Quantity * UnitPrice AS Total
        FROM Sales.OrderLines
        ORDER BY Total DESC, OrderLineID";
    return conn.Query<(int OrderLineID, decimal Total)>(sql);
}''',
    # F3_JSONNestedDateEquality
    '''\
public static IEnumerable<Person> Query38(SqlConnection conn)
{
    string sql = @"
        SELECT PersonID, FullName, PreferredName, EmailAddress, CustomFields, OtherLanguages
        FROM Application.People
        WHERE JSON_VALUE(CustomFields, '$.HireDate') = @HireDate
        ORDER BY PersonID";
    return conn.Query<Person>(sql, new { HireDate = "2008-04-19T00:00:00" });
}''',
    # B11_InQueryOverStrings
    '''\
public static IEnumerable<Order> Query39(SqlConnection conn)
{
    var purchaseOrderNumbers = new[] { "12126", "19446", "10203" };
    string sql = @"
        SELECT * FROM Sales.Orders
        WHERE CustomerPurchaseOrderNumber IN @Numbers
        ORDER BY OrderID";
    return conn.Query<Order>(sql, new { Numbers = purchaseOrderNumbers });
}''',
    # E5_DistinctSortedIntColumn
    '''\
public static IEnumerable<int> Query40(SqlConnection conn)
{
    string sql = @"SELECT DISTINCT QuantityPerOuter FROM Warehouse.StockItems ORDER BY QuantityPerOuter";
    return conn.Query<int>(sql);
}''',
]
