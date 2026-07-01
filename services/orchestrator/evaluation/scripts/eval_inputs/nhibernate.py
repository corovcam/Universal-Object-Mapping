"""NHibernate (LINQ over ISession) source inputs for the UOM eval dataset (schema + idiomatic query bodies).

Extracted from build_eval_dataset.py so the bulky C# inputs live in their own files; the builder
imports SCHEMA/QUERIES from here. Schema is verbatim from tests/fixtures/input-*.txt; queries span
the .NET ORM benchmark categories in this framework's native idiom."""

SCHEMA = '''\
public class Customer
{
    public virtual int CustomerID { get; set; }
    public virtual required string CustomerName { get; set; }
    public virtual DateTime AccountOpenedDate { get; set; }
    public virtual decimal? CreditLimit { get; set; }
    public virtual IList<CustomerTransaction> CustomerTransactions { get; set; } = [];
}
public class CustomerTransaction
{
    public virtual int CustomerTransactionID { get; set; }
    public virtual int CustomerID { get; set; }
    public virtual DateTime TransactionDate { get; set; }
    public virtual decimal TransactionAmount { get; set; }
}
public class Order
{
    public virtual int OrderID { get; set; }
    public virtual int CustomerID { get; set; }
    public virtual IList<OrderLine> OrderLines { get; set; } = [];
}
public class OrderLine
{
    public virtual int OrderLineID { get; set; }
    public virtual int OrderID { get; set; }
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
public class CustomerMap : ClassMapping<Customer> {
    public CustomerMap() {
        Table("Customers"); Schema("Sales");
        Id(x => x.CustomerID, m => m.Generator(Generators.Identity));
        Property(x => x.CustomerName);
        Property(x => x.AccountOpenedDate);
        Property(x => x.CreditLimit);
        Bag(x => x.CustomerTransactions, map => { map.Key(k => k.Column("CustomerID")); map.Inverse(true); }, rel => rel.OneToMany());
    }
}
public class CustomerTransactionMap : ClassMapping<CustomerTransaction> {
    public CustomerTransactionMap() {
        Table("CustomerTransactions"); Schema("Sales");
        Id(x => x.CustomerTransactionID, m => m.Generator(Generators.Identity));
        Property(x => x.CustomerID, m => { m.Insert(false); m.Update(false); });
        Property(x => x.TransactionDate);
        Property(x => x.TransactionAmount);
    }
}
public class OrderMap : ClassMapping<Order> {
    public OrderMap() {
        Table("Orders"); Schema("Sales");
        Id(x => x.OrderID, m => m.Generator(Generators.Identity));
        Property(x => x.CustomerID, m => { m.Insert(false); m.Update(false); });
        Bag(x => x.OrderLines, map => { map.Key(k => k.Column("OrderID")); map.Inverse(true); }, rel => rel.OneToMany());
    }
}
public class OrderLineMap : ClassMapping<OrderLine> {
    public OrderLineMap() {
        Table("OrderLines"); Schema("Sales");
        Id(x => x.OrderLineID, m => m.Generator(Generators.Identity));
        Property(x => x.OrderID, m => { m.Insert(false); m.Update(false); });
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
public record TaxRateCount { public decimal TaxRate { get; set; } public long Count { get; set; } }
public record PackageQtySum { public int PackageTypeID { get; set; } public int TotalQuantity { get; set; } }
public record LineQtyProjection { public int OrderLineID { get; set; } public int Quantity { get; set; } }'''

QUERIES = [
    '''\
public static IQueryable<OrderLine> Query1(NHibernate.ISession session)
{
    var from = new DateTime(2014, 12, 20);
    var to = new DateTime(2014, 12, 31);
    return session.Query<OrderLine>().Where(ol => ol.PickingCompletedWhen >= from && ol.PickingCompletedWhen <= to);
}''',
    '''\
public static IQueryable<OrderLine> Query2(NHibernate.ISession session)
{
    return session.Query<OrderLine>().Where(ol => ol.OrderID == 26866);
}''',
    '''\
public static IQueryable<OrderLine> Query3(NHibernate.ISession session)
{
    return session.Query<OrderLine>().Where(ol => ol.UnitPrice == 25m);
}''',
    '''\
public static IQueryable<OrderLine> Query4(NHibernate.ISession session)
{
    var ids = new[] { 1, 10, 100, 1000, 10000 };
    return session.Query<OrderLine>().Where(ol => ids.Contains(ol.OrderID));
}''',
    '''\
public static IQueryable<OrderLine> Query5(NHibernate.ISession session)
{
    return session.Query<OrderLine>().Where(ol => ol.Description.Contains("C++"));
}''',
    '''\
public static IQueryable<OrderLine> Query6(NHibernate.ISession session)
{
    return session.Query<OrderLine>().OrderBy(ol => ol.OrderLineID).Skip(1000).Take(50);
}''',
    '''\
public static IQueryable<TaxRateCount> Query7(NHibernate.ISession session)
{
    return session.Query<OrderLine>().GroupBy(ol => ol.TaxRate)
        .Select(g => new TaxRateCount { TaxRate = g.Key, Count = g.Count() })
        .OrderByDescending(x => x.Count);
}''',
    '''\
public static IQueryable<PackageQtySum> Query8(NHibernate.ISession session)
{
    return session.Query<OrderLine>().GroupBy(ol => ol.PackageTypeID)
        .Select(g => new PackageQtySum { PackageTypeID = g.Key, TotalQuantity = g.Sum(ol => ol.Quantity) });
}''',
    '''\
public static IQueryable<Order> Query9(NHibernate.ISession session)
{
    return session.Query<Order>().Where(o => o.OrderID == 530).Fetch(o => o.OrderLines);
}''',
    '''\
public static IQueryable<Customer> Query10(NHibernate.ISession session)
{
    return session.Query<Customer>().FetchMany(c => c.CustomerTransactions).OrderBy(c => c.CustomerID);
}''',
    '''\
public static IQueryable<OrderLine> Query11(NHibernate.ISession session)
{
    return session.Query<OrderLine>().OrderByDescending(ol => ol.Quantity).Take(50);
}''',
    '''\
public static IQueryable<string> Query12(NHibernate.ISession session)
{
    return session.Query<OrderLine>().Select(ol => ol.Description).Distinct();
}''',
    '''\
public static IQueryable<LineQtyProjection> Query13(NHibernate.ISession session)
{
    return session.Query<OrderLine>().Select(ol => new LineQtyProjection { OrderLineID = ol.OrderLineID, Quantity = ol.Quantity });
}''',
    '''\
public static IQueryable<Customer> Query14(NHibernate.ISession session)
{
    return session.Query<Customer>().Where(c => c.CreditLimit > 1000m).OrderByDescending(c => c.CreditLimit);
}''',
    '''\
public static IQueryable<OrderLine> Query15(NHibernate.ISession session)
{
    return session.Query<OrderLine>().Where(ol => ol.Quantity > 10 && ol.TaxRate == 15m);
}''',
]
