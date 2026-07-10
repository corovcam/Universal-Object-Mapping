"""NHibernate (LINQ over ISession) source inputs for the UOM eval dataset (schema + query bodies).

Queries are ported 1:1 from `benchmarks/NHibernatePerformance/NHibernateBenchmarks.cs` (1-16) and
extended (17-40) to cover every answerable benchmark FEATURE category — see eval_inputs/efcore.py
for the full category map, the data-availability rationale, the A4/H1/Sales.Customers exclusions,
and the entity-design rule (only columns representable in ALL THREE eval stores; PackageTypeID and
the Order person-role FKs are dropped, ValidFrom/ValidTo avoided).

NHibernate-specific idioms preserved from `benchmarks/NHibernateFeatures/FeatureTests.cs`:
`session.Get<T>(id)` for the PK fetch (A1), LINQ projection into DTOs (A2/A3), and
`CreateSQLQuery` + `AliasToBean` for the JSON queries (F1-F3 — NHibernate LINQ cannot express
JSON_VALUE). Entities use mapping-by-code `ClassMapping<T>`; DTOs are unmapped POCOs."""

SCHEMA = '''\
public class OrderLine
{
    public virtual int OrderLineID { get; set; }
    public virtual int OrderID { get; set; }
    public virtual int StockItemID { get; set; }
    public virtual required string Description { get; set; }
    public virtual int Quantity { get; set; }
    public virtual decimal? UnitPrice { get; set; }
    public virtual decimal TaxRate { get; set; }
    public virtual int PickedQuantity { get; set; }
    public virtual DateTime? PickingCompletedWhen { get; set; }
    public virtual int LastEditedBy { get; set; }
    public virtual DateTime LastEditedWhen { get; set; }
}
public class Order
{
    public virtual int OrderID { get; set; }
    public virtual int CustomerID { get; set; }
    public virtual int? BackorderOrderID { get; set; }
    public virtual DateTime OrderDate { get; set; }
    public virtual DateTime ExpectedDeliveryDate { get; set; }
    public virtual string? CustomerPurchaseOrderNumber { get; set; }
    public virtual bool IsUndersupplyBackordered { get; set; }
    public virtual string? Comments { get; set; }
    public virtual string? DeliveryInstructions { get; set; }
    public virtual string? InternalComments { get; set; }
    public virtual DateTime? PickingCompletedWhen { get; set; }
    public virtual DateTime LastEditedWhen { get; set; }
    public virtual IList<OrderLine> OrderLines { get; set; } = [];
}
public class Person
{
    public virtual int PersonID { get; set; }
    public virtual required string FullName { get; set; }
    public virtual required string PreferredName { get; set; }
    public virtual string? EmailAddress { get; set; }
    public virtual string? CustomFields { get; set; }
    public virtual string? OtherLanguages { get; set; }
}
public class Supplier
{
    public virtual int SupplierID { get; set; }
    public virtual required string SupplierName { get; set; }
    public virtual string? SupplierReference { get; set; }
    public virtual int PaymentDays { get; set; }
    public virtual string? PhoneNumber { get; set; }
    public virtual string? FaxNumber { get; set; }
    public virtual string? WebsiteURL { get; set; }
    public virtual string? BankAccountName { get; set; }
    public virtual string? BankAccountBranch { get; set; }
    public virtual string? BankAccountCode { get; set; }
    public virtual string? BankAccountNumber { get; set; }
    public virtual string? BankInternationalCode { get; set; }
}
public class CustomerTransaction
{
    public virtual int CustomerTransactionID { get; set; }
    public virtual int CustomerID { get; set; }
    public virtual DateTime TransactionDate { get; set; }
    public virtual decimal TransactionAmount { get; set; }
    public virtual decimal OutstandingBalance { get; set; }
    public virtual bool IsFinalized { get; set; }
}
public class PurchaseOrder
{
    public virtual int PurchaseOrderID { get; set; }
    public virtual int SupplierID { get; set; }
    public virtual DateTime OrderDate { get; set; }
    public virtual DateTime ExpectedDeliveryDate { get; set; }
    public virtual string? SupplierReference { get; set; }
    public virtual bool IsOrderFinalized { get; set; }
}
public class StockItem
{
    public virtual int StockItemID { get; set; }
    public virtual required string StockItemName { get; set; }
    public virtual int SupplierID { get; set; }
    public virtual int QuantityPerOuter { get; set; }
    public virtual int LeadTimeDays { get; set; }
    public virtual bool IsChillerStock { get; set; }
    public virtual decimal? UnitPrice { get; set; }
    public virtual decimal RecommendedRetailPrice { get; set; }
}
public class StockItemStockGroup
{
    public virtual int StockItemStockGroupID { get; set; }
    public virtual int StockItemID { get; set; }
    public virtual int StockGroupID { get; set; }
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
public class OrderLineMap : ClassMapping<OrderLine> {
    public OrderLineMap() {
        Table("OrderLines"); Schema("Sales");
        Id(x => x.OrderLineID, m => m.Generator(Generators.Identity));
        Property(x => x.OrderID, m => { m.Insert(false); m.Update(false); });
        Property(x => x.StockItemID);
        Property(x => x.Description);
        Property(x => x.Quantity);
        Property(x => x.UnitPrice);
        Property(x => x.TaxRate);
        Property(x => x.PickedQuantity);
        Property(x => x.PickingCompletedWhen);
        Property(x => x.LastEditedBy);
        Property(x => x.LastEditedWhen);
    }
}
public class OrderMap : ClassMapping<Order> {
    public OrderMap() {
        Table("Orders"); Schema("Sales");
        Id(x => x.OrderID, m => m.Generator(Generators.Identity));
        Property(x => x.CustomerID);
        Property(x => x.BackorderOrderID);
        Property(x => x.OrderDate);
        Property(x => x.ExpectedDeliveryDate);
        Property(x => x.CustomerPurchaseOrderNumber);
        Property(x => x.IsUndersupplyBackordered);
        Property(x => x.Comments);
        Property(x => x.DeliveryInstructions);
        Property(x => x.InternalComments);
        Property(x => x.PickingCompletedWhen);
        Property(x => x.LastEditedWhen);
        Bag(x => x.OrderLines, map => { map.Key(k => k.Column("OrderID")); map.Inverse(true); }, rel => rel.OneToMany());
    }
}
public class PersonMap : ClassMapping<Person> {
    public PersonMap() {
        Table("People"); Schema("Application");
        Id(x => x.PersonID, m => m.Generator(Generators.Identity));
        Property(x => x.FullName);
        Property(x => x.PreferredName);
        Property(x => x.EmailAddress);
        Property(x => x.CustomFields);
        Property(x => x.OtherLanguages);
    }
}
public class SupplierMap : ClassMapping<Supplier> {
    public SupplierMap() {
        Table("Suppliers"); Schema("Purchasing");
        Id(x => x.SupplierID, m => m.Generator(Generators.Identity));
        Property(x => x.SupplierName);
        Property(x => x.SupplierReference);
        Property(x => x.PaymentDays);
        Property(x => x.PhoneNumber);
        Property(x => x.FaxNumber);
        Property(x => x.WebsiteURL);
        Property(x => x.BankAccountName);
        Property(x => x.BankAccountBranch);
        Property(x => x.BankAccountCode);
        Property(x => x.BankAccountNumber);
        Property(x => x.BankInternationalCode);
    }
}
public class CustomerTransactionMap : ClassMapping<CustomerTransaction> {
    public CustomerTransactionMap() {
        Table("CustomerTransactions"); Schema("Sales");
        Id(x => x.CustomerTransactionID, m => m.Generator(Generators.Identity));
        Property(x => x.CustomerID);
        Property(x => x.TransactionDate);
        Property(x => x.TransactionAmount);
        Property(x => x.OutstandingBalance);
        Property(x => x.IsFinalized);
    }
}
public class PurchaseOrderMap : ClassMapping<PurchaseOrder> {
    public PurchaseOrderMap() {
        Table("PurchaseOrders"); Schema("Purchasing");
        Id(x => x.PurchaseOrderID, m => m.Generator(Generators.Identity));
        Property(x => x.SupplierID);
        Property(x => x.OrderDate);
        Property(x => x.ExpectedDeliveryDate);
        Property(x => x.SupplierReference);
        Property(x => x.IsOrderFinalized);
    }
}
public class StockItemMap : ClassMapping<StockItem> {
    public StockItemMap() {
        Table("StockItems"); Schema("Warehouse");
        Id(x => x.StockItemID, m => m.Generator(Generators.Identity));
        Property(x => x.StockItemName);
        Property(x => x.SupplierID);
        Property(x => x.QuantityPerOuter);
        Property(x => x.LeadTimeDays);
        Property(x => x.IsChillerStock);
        Property(x => x.UnitPrice);
        Property(x => x.RecommendedRetailPrice);
    }
}
public class StockItemStockGroupMap : ClassMapping<StockItemStockGroup> {
    public StockItemStockGroupMap() {
        Table("StockItemStockGroups"); Schema("Warehouse");
        Id(x => x.StockItemStockGroupID, m => m.Generator(Generators.Identity));
        Property(x => x.StockItemID);
        Property(x => x.StockGroupID);
    }
}
public record TaxRateCount { public decimal TaxRate { get; set; } public long Count { get; set; } }'''

QUERIES = [
    # B1_SelectionOverIndexedColumn
    '''\
public static IQueryable<OrderLine> Query1(NHibernate.ISession session)
{
    int orderId = 26866;
    return session.Query<OrderLine>().Where(ol => ol.OrderID == orderId);
}''',
    # B2_SelectionOverNonIndexedColumn
    '''\
public static IQueryable<OrderLine> Query2(NHibernate.ISession session)
{
    decimal unitPrice = 25m;
    return session.Query<OrderLine>().Where(ol => ol.UnitPrice == unitPrice);
}''',
    # B3_RangeQuery
    '''\
public static IQueryable<OrderLine> Query3(NHibernate.ISession session)
{
    var from = new DateTime(2014, 12, 20);
    var to = new DateTime(2014, 12, 31);
    return session.Query<OrderLine>().Where(ol => ol.PickingCompletedWhen >= from && ol.PickingCompletedWhen <= to);
}''',
    # B4_InQuery (List<int> instead of the benchmark's array: NHibernate 5.5 LINQ throws
    # NotSupportedException on array.Contains — container-verified 2026-07-10)
    '''\
public static IQueryable<OrderLine> Query4(NHibernate.ISession session)
{
    var orderIds = new List<int> { 1, 10, 100, 1000, 10000 };
    return session.Query<OrderLine>().Where(ol => orderIds.Contains(ol.OrderID));
}''',
    # B5_TextSearch
    '''\
public static IQueryable<OrderLine> Query5(NHibernate.ISession session)
{
    string text = "C++";
    return session.Query<OrderLine>().Where(ol => ol.Description.Contains(text));
}''',
    # B6_PagingQuery
    '''\
public static IQueryable<OrderLine> Query6(NHibernate.ISession session)
{
    int skip = 1000;
    int take = 50;
    return session.Query<OrderLine>().OrderBy(ol => ol.OrderLineID).Skip(skip).Take(take);
}''',
    # C1_AggregationCount
    '''\
public static Dictionary<decimal, int> Query7(NHibernate.ISession session)
{
    return session.Query<OrderLine>()
        .GroupBy(ol => ol.TaxRate)
        .Select(g => new { TaxRate = g.Key, Count = g.Count() })
        .OrderByDescending(x => x.Count)
        .ToDictionary(x => x.TaxRate, x => x.Count);
}''',
    # C2_AggregationMax
    '''\
public static decimal? Query8(NHibernate.ISession session)
{
    return session.Query<OrderLine>().Max(ol => ol.UnitPrice);
}''',
    # C3_AggregationSum
    '''\
public static decimal? Query9(NHibernate.ISession session)
{
    return session.Query<OrderLine>().Sum(ol => ol.Quantity * ol.UnitPrice);
}''',
    # D1_OneToManyRelationship
    '''\
public static Order Query10(NHibernate.ISession session)
{
    return session.Query<Order>().Fetch(o => o.OrderLines).Single(o => o.OrderID == 530);
}''',
    # E1_ColumnSorting (benchmark shape on Orders)
    '''\
public static IQueryable<Order> Query11(NHibernate.ISession session)
{
    return session.Query<Order>().OrderBy(o => o.ExpectedDeliveryDate).Take(1000);
}''',
    # E2_Distinct (benchmark shape on Orders)
    '''\
public static IQueryable<string?> Query12(NHibernate.ISession session)
{
    return session.Query<Order>().Select(o => o.CustomerPurchaseOrderNumber).Distinct();
}''',
    # F1_JSONObjectQuery
    '''\
public static IList<Person> Query13(NHibernate.ISession session)
{
    var sql = """
                  SELECT PersonID, FullName, PreferredName, EmailAddress, CustomFields, OtherLanguages
                  FROM Application.People
                  WHERE JSON_VALUE(CustomFields, '$.Title') = :title
                  ORDER BY PersonID
              """;
    return session.CreateSQLQuery(sql)
        .SetParameter("title", "Team Member")
        .SetResultTransformer(Transformers.AliasToBean<Person>())
        .List<Person>();
}''',
    # F2_JSONArrayQuery
    '''\
public static IList<Person> Query14(NHibernate.ISession session)
{
    var sql = """
                  SELECT PersonID, FullName, PreferredName, EmailAddress, CustomFields, OtherLanguages
                  FROM Application.People
                  WHERE EXISTS (
                      SELECT 1 FROM OPENJSON(OtherLanguages)
                      WHERE value = :lang
                  )
                  ORDER BY PersonID
              """;
    return session.CreateSQLQuery(sql)
        .SetParameter("lang", "Slovak")
        .SetResultTransformer(Transformers.AliasToBean<Person>())
        .List<Person>();
}''',
    # G1_Union
    '''\
public static List<int> Query15(NHibernate.ISession session)
{
    var first = session.Query<Supplier>()
        .Where(s => s.SupplierID < 5)
        .Select(s => s.SupplierID)
        .ToList();
    var last = session.Query<Supplier>()
        .Where(s => s.SupplierID >= 5 && s.SupplierID <= 10)
        .Select(s => s.SupplierID)
        .ToList();
    return first.Union(last).OrderBy(s => s).ToList();
}''',
    # G2_Intersection
    '''\
public static List<int> Query16(NHibernate.ISession session)
{
    var first = session.Query<Supplier>()
        .Where(s => s.SupplierID < 10)
        .Select(s => s.SupplierID)
        .ToList();
    var last = session.Query<Supplier>()
        .Where(s => s.SupplierID >= 5 && s.SupplierID <= 15)
        .Select(s => s.SupplierID)
        .ToList();
    return first.Intersect(last).OrderBy(s => s).ToList();
}''',
    # A1_EntityIdenticalToTable (session.Get PK fetch, full entity)
    '''\
public static Supplier? Query17(NHibernate.ISession session)
{
    return session.Get<Supplier>(10);
}''',
    # A2_LimitedEntity (LINQ projection to a narrower DTO)
    '''\
public static SupplierContactInfo? Query18(NHibernate.ISession session)
{
    return session.Query<Supplier>()
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
public static SupplierAccounts? Query19(NHibernate.ISession session)
{
    return session.Query<Supplier>()
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
public static List<int> Query20(NHibernate.ISession session)
{
    var first = session.Query<Supplier>()
        .Where(s => s.SupplierID < 10)
        .Select(s => s.SupplierID)
        .ToList();
    var last = session.Query<Supplier>()
        .Where(s => s.SupplierID >= 5 && s.SupplierID <= 15)
        .Select(s => s.SupplierID)
        .ToList();
    return first.Except(last).OrderBy(s => s).ToList();
}''',
    # D2a_ManyToMany (junction fetch: the stock groups of one item)
    '''\
public static IQueryable<int> Query21(NHibernate.ISession session)
{
    return session.Query<StockItemStockGroup>()
        .Where(j => j.StockItemID == 1)
        .OrderBy(j => j.StockGroupID)
        .Select(j => j.StockGroupID);
}''',
    # D2b_ManyToMany (junction aggregation: item count per stock group)
    '''\
public static Dictionary<int, int> Query22(NHibernate.ISession session)
{
    return session.Query<StockItemStockGroup>()
        .GroupBy(j => j.StockGroupID)
        .Select(g => new { StockGroupID = g.Key, Count = g.Count() })
        .OrderBy(x => x.StockGroupID)
        .ToDictionary(x => x.StockGroupID, x => x.Count);
}''',
    # D4_JoinProjection (explicit two-entity join into a DTO)
    '''\
public static PurchaseOrderInfo? Query23(NHibernate.ISession session)
{
    return session.Query<PurchaseOrder>()
        .Where(po => po.PurchaseOrderID == 25)
        .Join(session.Query<Supplier>(),
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
public static decimal? Query24(NHibernate.ISession session)
{
    return session.Query<OrderLine>().Min(ol => ol.UnitPrice);
}''',
    # D6_ExistsSubquery (orders having at least one big line)
    '''\
public static IQueryable<int> Query25(NHibernate.ISession session)
{
    return session.Query<Order>()
        .Where(o => o.OrderLines.Any(ol => ol.Quantity >= 200))
        .OrderBy(o => o.OrderID)
        .Select(o => o.OrderID);
}''',
    # D3_OptionalSelfReference (nullable BackorderOrderID must survive as NULL)
    '''\
public static IQueryable<Order> Query26(NHibernate.ISession session)
{
    return session.Query<Order>().Where(o => o.OrderID <= 1000).OrderBy(o => o.OrderID);
}''',
    # B7_CompoundPredicate (AND over two columns)
    '''\
public static IQueryable<OrderLine> Query27(NHibernate.ISession session)
{
    return session.Query<OrderLine>()
        .Where(ol => ol.TaxRate == 10m && ol.Quantity > 25)
        .OrderBy(ol => ol.OrderLineID);
}''',
    # B8_OrWithNullCheck (IS NULL branch + date branch)
    '''\
public static IQueryable<Order> Query28(NHibernate.ISession session)
{
    var cutoff = new DateTime(2016, 5, 1);
    return session.Query<Order>()
        .Where(o => o.PickingCompletedWhen == null || o.OrderDate >= cutoff)
        .OrderBy(o => o.OrderID);
}''',
    # B9_StartsWith (anchored prefix search)
    '''\
public static IQueryable<OrderLine> Query29(NHibernate.ISession session)
{
    return session.Query<OrderLine>()
        .Where(ol => ol.Description.StartsWith("USB"))
        .OrderBy(ol => ol.OrderLineID);
}''',
    # B10_DateEquality (whole-day match on a date column)
    '''\
public static IQueryable<Order> Query30(NHibernate.ISession session)
{
    var day = new DateTime(2014, 6, 2);
    return session.Query<Order>().Where(o => o.OrderDate == day).OrderBy(o => o.OrderID);
}''',
    # C8_GroupByDatePart (orders per calendar year)
    '''\
public static Dictionary<int, int> Query31(NHibernate.ISession session)
{
    return session.Query<Order>()
        .GroupBy(o => o.OrderDate.Year)
        .Select(g => new { Year = g.Key, Count = g.Count() })
        .OrderBy(x => x.Year)
        .ToDictionary(x => x.Year, x => x.Count);
}''',
    # C5_AggregationAverage
    '''\
public static double Query32(NHibernate.ISession session)
{
    return session.Query<OrderLine>().Average(ol => (double)ol.Quantity);
}''',
    # C6_CountDistinct
    '''\
public static int Query33(NHibernate.ISession session)
{
    return session.Query<OrderLine>().Select(ol => ol.StockItemID).Distinct().Count();
}''',
    # C7_GroupByHaving (customers with more than 200 transactions)
    '''\
public static Dictionary<int, int> Query34(NHibernate.ISession session)
{
    return session.Query<CustomerTransaction>()
        .GroupBy(t => t.CustomerID)
        .Where(g => g.Count() > 200)
        .Select(g => new { CustomerID = g.Key, Count = g.Count() })
        .OrderBy(x => x.CustomerID)
        .ToDictionary(x => x.CustomerID, x => x.Count);
}''',
    # C9_TopNByGroupedAggregate (10 highest-revenue stock items)
    '''\
public static Dictionary<int, decimal?> Query35(NHibernate.ISession session)
{
    return session.Query<OrderLine>()
        .GroupBy(ol => ol.StockItemID)
        .Select(g => new { StockItemID = g.Key, Revenue = g.Sum(ol => ol.Quantity * ol.UnitPrice) })
        .OrderByDescending(x => x.Revenue)
        .ThenBy(x => x.StockItemID)
        .Take(10)
        .ToDictionary(x => x.StockItemID, x => x.Revenue);
}''',
    # E3_MultiColumnSort
    '''\
public static IQueryable<OrderLine> Query36(NHibernate.ISession session)
{
    return session.Query<OrderLine>()
        .OrderByDescending(ol => ol.TaxRate)
        .ThenBy(ol => ol.OrderLineID)
        .Take(100);
}''',
    # E4_ComputedExpressionSort (top 50 line totals)
    '''\
public static Dictionary<int, decimal?> Query37(NHibernate.ISession session)
{
    return session.Query<OrderLine>()
        .OrderByDescending(ol => ol.Quantity * ol.UnitPrice)
        .ThenBy(ol => ol.OrderLineID)
        .Take(50)
        .Select(ol => new { ol.OrderLineID, Total = ol.Quantity * ol.UnitPrice })
        .ToDictionary(x => x.OrderLineID, x => x.Total);
}''',
    # F3_JSONNestedDateEquality
    '''\
public static IList<Person> Query38(NHibernate.ISession session)
{
    var sql = """
                  SELECT PersonID, FullName, PreferredName, EmailAddress, CustomFields, OtherLanguages
                  FROM Application.People
                  WHERE JSON_VALUE(CustomFields, '$.HireDate') = :hireDate
                  ORDER BY PersonID
              """;
    return session.CreateSQLQuery(sql)
        .SetParameter("hireDate", "2008-04-19T00:00:00")
        .SetResultTransformer(Transformers.AliasToBean<Person>())
        .List<Person>();
}''',
    # B11_InQueryOverStrings (List<string>: NHibernate 5.5 LINQ does not translate array.Contains)
    '''\
public static IQueryable<Order> Query39(NHibernate.ISession session)
{
    var purchaseOrderNumbers = new List<string> { "12126", "19446", "10203" };
    return session.Query<Order>()
        .Where(o => purchaseOrderNumbers.Contains(o.CustomerPurchaseOrderNumber))
        .OrderBy(o => o.OrderID);
}''',
    # E5_DistinctSortedIntColumn (DISTINCT server-side, sort client-side: NHibernate 5.5 LINQ
    # cannot compose OrderBy after Distinct on a scalar projection)
    '''\
public static List<int> Query40(NHibernate.ISession session)
{
    var quantities = session.Query<StockItem>()
        .Select(si => si.QuantityPerOuter)
        .Distinct()
        .ToList();
    return quantities.OrderBy(q => q).ToList();
}''',
]
