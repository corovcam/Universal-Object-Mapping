using NHibernate.Linq;
using System;
using System.Linq;
using System.Text.Json.Serialization;
using System.Text.Json;
using System.Text.Encodings.Web;
using System.Globalization;
using System.Text.Json.Serialization.Metadata;
using System.Collections.Generic;
using NHibernate.Cfg;
using NHibernate.Driver;
using NHibernate.Mapping.ByCode;
using NHibernate.Mapping.ByCode.Conformist;
using NHibernate.Dialect;

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

    public static string Serialize(object entity)
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

public record Query3Projection
{
    public decimal TaxRate { get; set; }
    public long Count { get; set; }
}

public record Query5Projection
{
    public int OrderLineID { get; set; }
    public int Quantity { get; set; }
}

// --- Query Entrypoint ---

public static class NHibernateQueryEntrypoint
{
    public static IQueryable<OrderLine> Query1(NHibernate.ISession session)
    {
        var from = new DateTime(2014, 12, 20);
        var to = new DateTime(2014, 12, 31);
        return session.Query<OrderLine>().Where(ol => ol.PickingCompletedWhen >= from && ol.PickingCompletedWhen <= to);
    }

    public static IEnumerable<Order> Query2(NHibernate.ISession session)
    {
        // Cartesian product cannot be done NHibernate
        var q = session.Query<Order>()
            .Where(o => o.CustomerID == 1);

        q.Fetch(o => o.Customer)
            .ThenFetchMany(c => c.CustomerTransactions)
            .ToFuture();

        return q.FetchMany(o => o.OrderLines)
            .Distinct()
            .ToFuture();
    }

    public static IQueryable<Query3Projection> Query3(NHibernate.ISession session)
    {
        return session.Query<OrderLine>().GroupBy(ol => ol.TaxRate).Select(g => new Query3Projection { TaxRate = g.Key, Count = g.Count() }).OrderByDescending(x => x.Count);
    }

    public static IQueryable<OrderLine> Query4(NHibernate.ISession session)
    {
        return session.Query<OrderLine>().OrderByDescending(ol => ol.Quantity).Take(50);
    }

    public static IQueryable<Query5Projection> Query5(NHibernate.ISession session)
    {
        return session.Query<OrderLine>().Select(ol => new Query5Projection { OrderLineID = ol.OrderLineID, Quantity = ol.Quantity });
    }

    private static object RunQuery<T>(Func<IEnumerable<T>> q, Func<T, object>? orderBySelector = null)
    {
        var query = q();
        var count = query.Count();
        return new { sqlString = "logged in console", count, 
            firstSample = count > 0 ? (orderBySelector != null ? query.OrderBy(orderBySelector).FirstOrDefault() : query.FirstOrDefault()) : default, 
            lastSample = count > 1 ? (orderBySelector != null ? query.OrderByDescending(orderBySelector).FirstOrDefault() : query.LastOrDefault()) : default };
    }

    public static void Main(string[] args)
    {
        string connectionString = args.ElementAtOrDefault(0) 
            ?? System.Environment.GetEnvironmentVariable("CONNECTION_STRING") 
            ?? "Server=localhost,1444;Database=WideWorldImporters;User Id=sa;Password=Testingorms123;TrustServerCertificate=True";

        var configuration = new Configuration()
            .DataBaseIntegration(db =>
            {
                db.ConnectionString = connectionString;
                db.Dialect<MsSql2012Dialect>();
                db.Driver<MicrosoftDataSqlClientDriver>();
                db.LogSqlInConsole = true;
            });

        var mapper = new ModelMapper();
        mapper.AddMapping<CustomerMap>();
        mapper.AddMapping<CustomerTransactionMap>();
        mapper.AddMapping<OrderMap>();
        mapper.AddMapping<OrderLineMap>();
        configuration.AddMapping(mapper.CompileMappingForAllExplicitlyAddedEntities());

        using var sessionFactory = configuration.BuildSessionFactory();
        using var session = sessionFactory.OpenSession();

        var results = new Dictionary<string, object?>();
        var harnesses = new Func<object>[] {
            () => RunQuery(() => Query1(session), ol => ol.OrderLineID),
            () => RunQuery(() => Query2(session), o => o.OrderID),
            () => RunQuery(() => Query3(session), x => x.TaxRate),
            () => RunQuery(() => Query4(session)),
            () => RunQuery(() => Query5(session), ol => ol.OrderLineID)
        };

        for (int i = 0; i < harnesses.Length; i++) {
            var qid = i+1;
            Console.WriteLine($"Running Query {qid}...");
            try {
                results[$"query{qid}"] = harnesses[i]();
            } catch (Exception ex) {
                results[$"query{qid}"] = new { error = ex.Message };
                Console.WriteLine($"Error occurred while running Query{qid}: {ex}");
            }
        }
        File.WriteAllText($"{System.Environment.GetEnvironmentVariable("NHIBERNATE_RESULTS_PATH")}/nhibernate_results_{DateTime.Now:yyyyMMdd_HHmmss}.json", CustomJsonSerializer.Serialize(results));
    }
}
