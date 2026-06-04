using System;
using System.Linq;
using System.Text.Json.Serialization;
using System.Text.Json;
using System.Text.Encodings.Web;
using System.Globalization;
using System.Text.Json.Serialization.Metadata;
using System.Collections.Generic;
using NHibernate.Cfg;
using NHibernate.Mapping.ByCode;
using NHibernate.Mapping.ByCode.Conformist;

namespace nhibernate_sandbox;

// --- Harness and Utilities ---

public static class CustomJsonSerializer
{
    public class StrictIsoDateTimeConverter : JsonConverter<DateTime>
    {
        public override DateTime Read(ref Utf8JsonReader reader, Type typeToConvert, JsonSerializerOptions options)
        {
            return DateTime.Parse(
                reader.GetString()!,
                CultureInfo.InvariantCulture,
                DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal);
        }

        public override void Write(Utf8JsonWriter writer, DateTime value, JsonSerializerOptions options)
        {
            writer.WriteStringValue(value.ToString("yyyy-MM-dd'T'HH:mm:ss.fff'Z'", CultureInfo.InvariantCulture));
        }
    }

    public class StrictIsoDateTimeOffsetConverter : JsonConverter<DateTimeOffset>
    {
        public override DateTimeOffset Read(ref Utf8JsonReader reader, Type typeToConvert, JsonSerializerOptions options)
        {
            return DateTimeOffset.Parse(reader.GetString()!, CultureInfo.InvariantCulture);
        }

        public override void Write(Utf8JsonWriter writer, DateTimeOffset value, JsonSerializerOptions options)
        {
            writer.WriteStringValue(
                value.ToUniversalTime().ToString("yyyy-MM-dd'T'HH:mm:ss.fff'Z'", CultureInfo.InvariantCulture));
        }
    }

    public class FixedDecimalConverter : JsonConverter<decimal>
    {
        public override decimal Read(ref Utf8JsonReader reader, Type typeToConvert, JsonSerializerOptions options)
        {
            return reader.GetDecimal();
        }

        public override void Write(Utf8JsonWriter writer, decimal value, JsonSerializerOptions options)
        {
            writer.WriteRawValue(value.ToString("0.000", CultureInfo.InvariantCulture));
        }
    }

    public class FixedDoubleConverter : JsonConverter<double>
    {
        public override double Read(ref Utf8JsonReader reader, Type typeToConvert, JsonSerializerOptions options)
        {
            return reader.GetDouble();
        }

        public override void Write(Utf8JsonWriter writer, double value, JsonSerializerOptions options)
        {
            writer.WriteRawValue(value.ToString("0.000", CultureInfo.InvariantCulture));
        }
    }

    public class CustomCamelCaseNamingPolicy : JsonNamingPolicy
    {
        public override string ConvertName(string name)
        {
            if (string.IsNullOrEmpty(name)) return name;
            string camelCased = CamelCase.ConvertName(name);
            if (camelCased.EndsWith("ID"))
            {
                return camelCased[..^2] + "Id";
            } else if (camelCased.EndsWith("URL"))
            {
                return camelCased[..^3] + "Url";
            }
            return camelCased;
        }
    }

    public static Action<JsonTypeInfo> AlphabetizeProperties()
    {
        return static typeInfo =>
        {
            if (typeInfo.Kind!= JsonTypeInfoKind.Object) return;
            var properties = typeInfo.Properties.OrderBy(p => p.Name, StringComparer.Ordinal).ToList();
            typeInfo.Properties.Clear();
            for (int i = 0; i < properties.Count; i++)
            {
                properties[i].Order = i;
                typeInfo.Properties.Add(properties[i]);
            }
        };
    }

    public static readonly JsonSerializerOptions Options = new()
    {
        PropertyNamingPolicy = new CustomCamelCaseNamingPolicy(),
        DictionaryKeyPolicy = new CustomCamelCaseNamingPolicy(),
        DefaultIgnoreCondition = JsonIgnoreCondition.Never,
        Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping,
        ReferenceHandler = ReferenceHandler.IgnoreCycles,
        TypeInfoResolver = new DefaultJsonTypeInfoResolver
        {
            Modifiers = { AlphabetizeProperties() }
        },
        Converters = { 
            new StrictIsoDateTimeConverter(), 
            new StrictIsoDateTimeOffsetConverter(),
            new FixedDecimalConverter(),
            new FixedDoubleConverter(),
            new JsonStringEnumConverter(new CustomCamelCaseNamingPolicy()) 
        }
    };

    public static string Serialize(object? entity)
    {
        return JsonSerializer.Serialize(entity, Options);
    }
}

// --- Schema and Related Settings ---

public class Customer
{
    [JsonPropertyName("customerId")]
    public virtual int CustomerID { get; set; }
    public virtual required string CustomerName { get; set; }
    public virtual DateTime AccountOpenedDate { get; set; }
    public virtual decimal? CreditLimit { get; set; }
    [JsonIgnore] // Don't serialize this, cause it's large
    public virtual IList<CustomerTransaction> CustomerTransactions { get; set; } = [];
}

public class CustomerTransaction
{
    [JsonPropertyName("customerTransactionId")]
    public virtual int CustomerTransactionID { get; set; }
    [JsonPropertyName("customerId")]
    public virtual int CustomerID { get; set; }
    public virtual DateTime TransactionDate { get; set; }
    public virtual decimal TransactionAmount { get; set; }
}

public class Order
{
    [JsonPropertyName("orderId")]
    public virtual int OrderID { get; set; }
    [JsonPropertyName("customerId")]
    public virtual int CustomerID { get; set; }
    public virtual Customer Customer { get; set; } = null!;
    [JsonIgnore] // Don't serialize this, cause it's large
    public virtual IList<OrderLine> OrderLines { get; set; } = [];
}

public class OrderLine
{
    [JsonPropertyName("orderLineId")]
    public virtual int OrderLineID { get; set; }
    [JsonPropertyName("orderId")]
    public virtual int OrderID { get; set; }
    [JsonPropertyName("stockItemId")]
    public virtual int StockItemID { get; set; }
    public virtual required string Description { get; set; }
    [JsonPropertyName("packageTypeId")]
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
        ManyToOne(x => x.Customer, m => m.Column("CustomerID"));
        Bag(x => x.OrderLines, map => { map.Key(k => k.Column("OrderID")); map.Inverse(true); }, rel => rel.OneToMany());
    }
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

// --- Schema Validation Entrypoint ---

public static class NHibernateSchemaValidationEntrypoint
{
    public static void ValidateEntity<T>(NHibernate.ISession session) where T : class
    {
        Console.WriteLine($"Validating NHibernate entity: {typeof(T).Name}");
        Console.WriteLine(CustomJsonSerializer.Serialize(session.Query<T>().FirstOrDefault()));
        Console.WriteLine($"Successfully validated NHibernate entity: {typeof(T).Name}");
    }

    public static void Main(string[] args)
    {
        var connectionString = args.ElementAtOrDefault(0) ??
                               System.Environment.GetEnvironmentVariable("CONNECTION_STRING")
                               ??
                               "Server=localhost,1333;Database=WideWorldImporters;User Id=sa;Password=Testingorms123;TrustServerCertificate=True";

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
                Console.Error.WriteLine($"Error occurred while validating entity: {ex}");
            }
        }
    }
}