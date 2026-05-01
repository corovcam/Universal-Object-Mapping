using System;
using System.Linq;
using Microsoft.EntityFrameworkCore;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;
using System.Collections.Generic;
using Microsoft.Extensions.Logging;
using Microsoft.EntityFrameworkCore.Diagnostics;

namespace efcore_sandbox;

[Table("Customers", Schema = "Sales")]
public class Customer
{
    [Key]
    public required int CustomerID { get; set; }
    [MaxLength(200)]
    public required string CustomerName { get; set; }
    [Column(TypeName="datetime2")]
    [Precision(7)]
    public required DateTime AccountOpenedDate { get; set; }
    [Column(TypeName="decimal")]
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
    [ForeignKey(nameof(Customer))]
    public int CustomerID { get; set; }
    public Customer Customer { get; set; } = null!;
    public List<OrderLine> OrderLines { get; set; } = [];
}

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

public class SandboxDbContext(DbContextOptions<SandboxDbContext> options) : DbContext(options)
{
    public DbSet<Customer> Customers => Set<Customer>();
    public DbSet<Order> Orders => Set<Order>();
    public DbSet<CustomerTransaction> CustomerTransactions => Set<CustomerTransaction>();
    public DbSet<OrderLine> OrderLines => Set<OrderLine>();
}

public static class EFCoreSchemaValidationEntrypoint
{
    public static void ValidateEntity<T>(SandboxDbContext ctx) where T : class
    {
        Console.WriteLine($"Validating EF Core entity: {typeof(T).Name}");
        var entity = ctx.Set<T>().FirstOrDefault();
        Console.WriteLine($"Successfully validated EF Core entity: {typeof(T).Name}");
    }

    public static void Main(string[] args)
    {
        using var context = new SandboxDbContext(
            new DbContextOptionsBuilder<SandboxDbContext>()
                .UseSqlServer(
                    args.ElementAtOrDefault(0) ?? Environment.GetEnvironmentVariable("CONNECTION_STRING") 
                        ?? "Server=localhost,1444;Database=WideWorldImporters;User Id=sa;Password=Testingorms123;TrustServerCertificate=True"
                )
                .UseQueryTrackingBehavior(QueryTrackingBehavior.NoTracking)
                .EnableSensitiveDataLogging()
                .LogTo(Console.WriteLine, [DbLoggerCategory.Database.Command.Name], minimumLevel: LogLevel.Information, options: DbContextLoggerOptions.SingleLine).Options
        );
        
        var queries = new Action[] {
            () => ValidateEntity<Customer>(context),
            () => ValidateEntity<CustomerTransaction>(context),
            () => ValidateEntity<Order>(context),
            () => ValidateEntity<OrderLine>(context)
        };

        foreach (var query in queries) {
            try {
                query();
            } catch (Exception ex) {
                Console.WriteLine($"Error occurred while validating entity: {ex}");
            }
        }
    }
}