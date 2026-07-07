"""NHibernate (LINQ over ISession) source inputs for the UOM eval dataset (schema + query bodies).

Queries are ported 1:1 from `benchmarks/NHibernatePerformance/NHibernateBenchmarks.cs`, restricted
to entities with data in BOTH eval stores (see eval_inputs/efcore.py for the category map and the
data-availability rationale — Query1-6=B1-B6, 7-9=C1-C3, 10=D1, 11-12=E1-E2 re-targeted to Orders,
13-14=F1-F2 on People, 15-16=G1-G2 on Suppliers).

Entities mirror `benchmarks/NHibernateEntities/*` (mapping-by-code `ClassMapping<T>` instead of the
benchmark's hbm.xml — the eval harness bootstrap discovers `<Entity>Map` classes by name suffix).
Person keeps the raw string JSON columns exactly as the benchmark does."""

SCHEMA = '''\
public class OrderLine
{
    public virtual int OrderLineID { get; set; }
    public virtual int OrderID { get; set; }
    public virtual int StockItemID { get; set; }
    public virtual required string Description { get; set; }
    public virtual int PackageTypeID { get; set; }
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
    public virtual int SalespersonPersonID { get; set; }
    public virtual int? PickedByPersonID { get; set; }
    public virtual int ContactPersonID { get; set; }
    public virtual int? BackorderOrderID { get; set; }
    public virtual DateTime OrderDate { get; set; }
    public virtual DateTime ExpectedDeliveryDate { get; set; }
    public virtual string? CustomerPurchaseOrderNumber { get; set; }
    public virtual bool IsUndersupplyBackordered { get; set; }
    public virtual string? Comments { get; set; }
    public virtual string? DeliveryInstructions { get; set; }
    public virtual string? InternalComments { get; set; }
    public virtual DateTime? PickingCompletedWhen { get; set; }
    public virtual int LastEditedBy { get; set; }
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
}
public class OrderLineMap : ClassMapping<OrderLine> {
    public OrderLineMap() {
        Table("OrderLines"); Schema("Sales");
        Id(x => x.OrderLineID, m => m.Generator(Generators.Identity));
        Property(x => x.OrderID, m => { m.Insert(false); m.Update(false); });
        Property(x => x.StockItemID);
        Property(x => x.Description);
        Property(x => x.PackageTypeID);
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
        Property(x => x.SalespersonPersonID);
        Property(x => x.PickedByPersonID);
        Property(x => x.ContactPersonID);
        Property(x => x.BackorderOrderID);
        Property(x => x.OrderDate);
        Property(x => x.ExpectedDeliveryDate);
        Property(x => x.CustomerPurchaseOrderNumber);
        Property(x => x.IsUndersupplyBackordered);
        Property(x => x.Comments);
        Property(x => x.DeliveryInstructions);
        Property(x => x.InternalComments);
        Property(x => x.PickingCompletedWhen);
        Property(x => x.LastEditedBy);
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
    # B4_InQuery
    '''\
public static IQueryable<OrderLine> Query4(NHibernate.ISession session)
{
    var orderIds = new[] { 1, 10, 100, 1000, 10000 };
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
]
