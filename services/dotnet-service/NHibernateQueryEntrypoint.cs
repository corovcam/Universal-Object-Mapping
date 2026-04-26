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

namespace NHibernateSandbox;

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

    public static Action<JsonTypeInfo> AlphabetizeProperties()
    {
        return static typeInfo =>
        {
            if (typeInfo.Kind != JsonTypeInfoKind.Object) return;
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
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        DictionaryKeyPolicy = JsonNamingPolicy.CamelCase,
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
            new JsonStringEnumConverter(JsonNamingPolicy.CamelCase) 
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
    public virtual int CustomerID { get; set; }

    public virtual required string CustomerName { get; set; }

    public virtual DateTime AccountOpenedDate { get; set; }

    public virtual decimal? CreditLimit { get; set; }

    public virtual IList<CustomerTransaction> Transactions { get; set; } = [];
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

public class OrderLineMap : ClassMapping<OrderLine>
{
    public OrderLineMap()
    {
        Table("OrderLines");
        Schema("Sales");
        Id(x => x.OrderLineID, m => m.Generator(Generators.Identity));
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

// --- Query Entrypoint ---

public static class NHibernateQueryEntrypoint
{
    public static IEnumerable<OrderLine> Query1(NHibernate.ISession session)
    {
        var from = new DateTime(2014, 12, 20);
        var to = new DateTime(2014, 12, 31);

        return session.Query<OrderLine>().Where(ol => ol.PickingCompletedWhen >= from && ol.PickingCompletedWhen <= to);
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
        mapper.AddMapping<OrderLineMap>();
        configuration.AddMapping(mapper.CompileMappingForAllExplicitlyAddedEntities());

        using var sessionFactory = configuration.BuildSessionFactory();
        using var session = sessionFactory.OpenSession();

        var query = Query1(session);

        var firstSample = query.OrderBy(ol => ol.OrderLineID).FirstOrDefault();
        var lastSample = query.OrderByDescending(ol => ol.OrderLineID).FirstOrDefault();

        var resultDictionary = new SortedDictionary<string, object?>()
        {
            { "estimatedRowCount", query.Count() },
            { "firstSample", firstSample },
            { "lastSample", lastSample }
        };
        Console.WriteLine(CustomJsonSerializer.Serialize(resultDictionary));
    }
}
