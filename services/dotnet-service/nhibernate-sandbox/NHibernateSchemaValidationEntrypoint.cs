using System;
using System.Linq;
using System.Collections.Generic;
using NHibernate;
using NHibernate.Cfg;
using NHibernate.Mapping.ByCode;
using NHibernate.Mapping.ByCode.Conformist;

namespace nhibernate_sandbox;

public class Customer
{
    public virtual int CustomerID { get; set; }
    public virtual string CustomerName { get; set; } = string.Empty;
    public virtual DateTime AccountOpenedDate { get; set; }
    public virtual decimal? CreditLimit { get; set; }
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
}

public class OrderLine
{
    public virtual int OrderLineID { get; set; }
    public virtual int OrderID { get; set; }
    public virtual int StockItemID { get; set; }
    public virtual string Description { get; set; } = string.Empty;
    public virtual int PackageTypeID { get; set; }
    public virtual int Quantity { get; set; }
    public virtual decimal? UnitPrice { get; set; }
    public virtual decimal TaxRate { get; set; }
    public virtual int PickedQuantity { get; set; }
    public virtual DateTime? PickingCompletedWhen { get; set; }
    public virtual int LastEditedBy { get; set; }
    public virtual DateTime LastEditedWhen { get; set; }
}

public class CustomerMap : ClassMapping<Customer>
{
    public CustomerMap()
    {
        Schema("Sales");
        Table("Customers");
        Id(x => x.CustomerID, m => m.Column("CustomerID"));
        Property(x => x.CustomerName);
        Property(x => x.AccountOpenedDate);
        Property(x => x.CreditLimit);
    }
}

public class CustomerTransactionMap : ClassMapping<CustomerTransaction>
{
    public CustomerTransactionMap()
    {
        Schema("Sales");
        Table("CustomerTransactions");
        Id(x => x.CustomerTransactionID, m => m.Column("CustomerTransactionID"));
        Property(x => x.CustomerID);
        Property(x => x.TransactionDate);
        Property(x => x.TransactionAmount);
    }
}

public class OrderMap : ClassMapping<Order>
{
    public OrderMap()
    {
        Schema("Sales");
        Table("Orders");
        Id(x => x.OrderID, m => m.Column("OrderID"));
        Property(x => x.CustomerID);
    }
}

public class OrderLineMap : ClassMapping<OrderLine>
{
    public OrderLineMap()
    {
        Schema("Sales");
        Table("OrderLines");
        Id(x => x.OrderLineID, m => m.Column("OrderLineID"));
        Property(x => x.OrderID);
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

public static class NHibernateSchemaValidationEntrypoint
{
    public static void ValidateEntity<T>(ISession session) where T : class
    {
        Console.WriteLine($"Validating NHibernate entity: {typeof(T).Name}");
        session.Query<T>().FirstOrDefault();
        Console.WriteLine($"Successfully validated NHibernate entity: {typeof(T).Name}");
    }

    public static void Main(string[] args)
    {
        var connectionString = args.ElementAtOrDefault(0) ??
                               System.Environment.GetEnvironmentVariable("CONNECTION_STRING")
                               ??
                               "Server=localhost,1444;Database=WideWorldImporters;User Id=sa;Password=Testingorms123;TrustServerCertificate=True";

        var configuration = new Configuration();
        configuration.DataBaseIntegration(c =>
        {
            c.Driver<NHibernate.Driver.MicrosoftDataSqlClientDriver>();
            c.Dialect<NHibernate.Dialect.MsSql2012Dialect>();
            c.ConnectionString = connectionString;
            c.LogSqlInConsole = true;
        });

        var mapper = new ModelMapper();
        mapper.AddMappings(new[]
        {
            typeof(CustomerMap), 
            typeof(CustomerTransactionMap), 
            typeof(OrderMap), 
            typeof(OrderLineMap)
        });

        configuration.AddMapping(mapper.CompileMappingForAllExplicitlyAddedEntities());

        var sessionFactory = configuration.BuildSessionFactory();
        using var session = sessionFactory.OpenSession();

        var queries = new Action[]
        {
            () => ValidateEntity<Customer>(session),
            () => ValidateEntity<CustomerTransaction>(session),
            () => ValidateEntity<Order>(session),
            () => ValidateEntity<OrderLine>(session)
        };

        foreach (var query in queries)
        {
            try
            {
                query();
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error occurred while validating entity: {ex}");
            }
        }
    }
}