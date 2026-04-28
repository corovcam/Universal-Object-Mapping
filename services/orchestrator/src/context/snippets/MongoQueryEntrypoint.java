package uom.services;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.Instant;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.time.ZonedDateTime;
import java.time.format.DateTimeFormatter;
import java.time.temporal.TemporalAccessor;
import java.util.ArrayList;
import java.util.Date;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.function.Supplier;

import org.slf4j.LoggerFactory;
import org.springframework.data.annotation.Id;
import org.springframework.data.annotation.ReadOnlyProperty;
import org.springframework.data.domain.Sort;
import org.springframework.data.mongodb.MongoDatabaseFactory;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.mongodb.core.SimpleMongoClientDatabaseFactory;
import org.springframework.data.mongodb.core.aggregation.Aggregation;
import org.springframework.data.mongodb.core.aggregation.TypedAggregation;
import org.springframework.data.mongodb.core.convert.DefaultDbRefResolver;
import org.springframework.data.mongodb.core.convert.DefaultMongoTypeMapper;
import org.springframework.data.mongodb.core.convert.MappingMongoConverter;
import org.springframework.data.mongodb.core.convert.MongoCustomConversions;
import org.springframework.data.mongodb.core.mapping.Document;
import org.springframework.data.mongodb.core.mapping.DocumentReference;
import org.springframework.data.mongodb.core.mapping.Field;
import org.springframework.data.mongodb.core.mapping.MongoMappingContext;
import org.springframework.data.mongodb.core.query.Criteria;
import org.springframework.data.mongodb.core.query.Query;

import com.fasterxml.jackson.annotation.JsonInclude.Include;
import com.mongodb.client.MongoClients;

import ch.qos.logback.classic.LoggerContext;
import tools.jackson.core.JsonGenerator;
import tools.jackson.core.StreamWriteFeature;
import tools.jackson.databind.MapperFeature;
import tools.jackson.databind.SerializationContext;
import tools.jackson.databind.SerializationFeature;
import tools.jackson.databind.cfg.DateTimeFeature;
import tools.jackson.databind.json.JsonMapper;
import tools.jackson.databind.module.SimpleModule;
import tools.jackson.databind.ser.std.StdSerializer;


// --- Harness and Utilities ---

class CustomJsonSerializer extends StdSerializer<Object> {
    
    private static final DateTimeFormatter DATETIME_FORMATTER = 
        DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'").withZone(ZoneOffset.UTC);

    public CustomJsonSerializer() {
        super(Object.class);
    }

    @Override
    public void serialize(Object value, JsonGenerator gen, SerializationContext ctx) {
        if (value == null) {
            gen.writeNull();
        } else if (value instanceof BigDecimal) {
            gen.writeNumber(((BigDecimal) value).setScale(3, RoundingMode.HALF_UP).toPlainString());
        } else if (value instanceof Double) {
            gen.writeNumber(BigDecimal.valueOf((Double) value).setScale(3, RoundingMode.HALF_UP).toPlainString());
        } else if (value instanceof Float) {
            gen.writeNumber(BigDecimal.valueOf((Float) value).setScale(3, RoundingMode.HALF_UP).toPlainString());
        } else if (value instanceof LocalDate) {
            gen.writeString(DATETIME_FORMATTER.format(((LocalDate) value).atStartOfDay()));
        } else if (value instanceof LocalDateTime) {
            gen.writeString(DATETIME_FORMATTER.format((LocalDateTime) value));
        } else if (value instanceof Date) {
            gen.writeString(DATETIME_FORMATTER.format(((Date) value).toInstant()));
        } else if (value instanceof TemporalAccessor) {
            gen.writeString(DATETIME_FORMATTER.format((TemporalAccessor) value));
        } else {
            gen.writeString(value.toString());
        }
    }
}

final class QueryRuntimeSupport {
    private static final String DEFAULT_MONGO_URI = "mongodb://uom_readonly:uom_readonly@mongodb:27017/uom";
    private static final String DEFAULT_MONGO_DATABASE = "uom";

    private QueryRuntimeSupport() {
    }

    static JsonMapper createJsonMapper() {
        SimpleModule customModule = new SimpleModule();
        CustomJsonSerializer customJsonSerializer = new CustomJsonSerializer();
        customModule.addSerializer(LocalDate.class, customJsonSerializer);
        customModule.addSerializer(LocalDateTime.class, customJsonSerializer);
        customModule.addSerializer(ZonedDateTime.class, customJsonSerializer);
        customModule.addSerializer(OffsetDateTime.class, customJsonSerializer);
        customModule.addSerializer(Instant.class, customJsonSerializer);
        customModule.addSerializer(Date.class, customJsonSerializer);
        customModule.addSerializer(BigDecimal.class, customJsonSerializer);
        customModule.addSerializer(Double.class, customJsonSerializer);
        customModule.addSerializer(Float.class, customJsonSerializer);
        return JsonMapper.builder()
                .changeDefaultPropertyInclusion(incl -> incl.withValueInclusion(Include.ALWAYS))
                .disable(DateTimeFeature.WRITE_DATES_AS_TIMESTAMPS)
                .enable(StreamWriteFeature.WRITE_BIGDECIMAL_AS_PLAIN)
                .enable(MapperFeature.SORT_PROPERTIES_ALPHABETICALLY)
                .enable(SerializationFeature.ORDER_MAP_ENTRIES_BY_KEYS)
                .addModule(customModule)
                .build();
    }

    static MongoTemplate createMongoTemplate(String mongoUri, String mongoDatabase) {
        return MongoTemplateFactory.create(mongoUri, mongoDatabase);
    }

    static void configureLogger() {
        var loggerContext = (LoggerContext) LoggerFactory.getILoggerFactory();
        var mongoLogger = loggerContext.getLogger("org.springframework.data.mongodb.core.MongoTemplate");
        mongoLogger.setLevel(ch.qos.logback.classic.Level.DEBUG);
    }

    static String defaultMongoUri() {
        return System.getenv("MONGODB_URI") != null ? System.getenv("MONGODB_URI") : DEFAULT_MONGO_URI;
    }

    static String defaultMongoDatabase() {
        return System.getenv("MONGODB_DATABASE") != null ? System.getenv("MONGODB_DATABASE") : DEFAULT_MONGO_DATABASE;
    }
}

final class MongoTemplateFactory {
    private MongoTemplateFactory() {
    }

    static MongoTemplate create(String mongoUri, String mongoDatabase) {
        MongoDatabaseFactory databaseFactory = new SimpleMongoClientDatabaseFactory(
                MongoClients.create(mongoUri),
                mongoDatabase);
        MongoCustomConversions customConversions = MongoCustomConversions.create(configuration -> {
        });
        MongoMappingContext mappingContext = new MongoMappingContext();
        mappingContext.setSimpleTypeHolder(customConversions.getSimpleTypeHolder());
        mappingContext.afterPropertiesSet();

        MappingMongoConverter converter = new MappingMongoConverter(
                new DefaultDbRefResolver(databaseFactory),
                mappingContext);
        converter.setCustomConversions(customConversions);
        converter.setTypeMapper(new DefaultMongoTypeMapper(null));
        converter.afterPropertiesSet();

        return new MongoTemplate(databaseFactory, converter);
    }
}

// --- Schema and Related Settings ---

/**
 * Order document with embedded Customer and CustomerTransactions.
 * 
 * TRANSLATED FROM: C# EFCore Customer, CustomerTransaction entities
 * ARCHITECTURAL SHIFT: Denormalized - Customers no longer a root collection.
 *                      Instead, Customer and its transactions are embedded within Order.
 */
@Document(collection = "orders")
class Order {

    @Id
    private String id;

    @Field("orderId")
    private Integer orderId;

    @Field("customerId")
    private Integer customerId;

    // Embedded Customer document (denormalized from Sales.Customers table)
    private Customer customer;

    @ReadOnlyProperty
    @DocumentReference(lazy = true, lookup = "{ 'orderId': ?#{#self.orderId} }", sort = "{ 'orderLineId': 1 }")
    private List<OrderLine> orderLines;

    // Constructors
    public Order() {
    }

    // Getters and Setters
    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    public Integer getOrderId() { return orderId; }
    public void setOrderId(Integer orderId) { this.orderId = orderId; }
    public Integer getCustomerId() { return customerId; }
    public void setCustomerId(Integer customerId) { this.customerId = customerId; }
    public Customer getCustomer() { return customer; }
    public void setCustomer(Customer customer) { this.customer = customer; }
    public List<OrderLine> getOrderLines() { return orderLines; }
    public void setOrderLines(List<OrderLine> orderLines) { this.orderLines = orderLines; }
}

/**
 * Embedded Customer document within Order.
 * Represents the denormalized Sales.Customers table data.
 * 
 * TRANSLATED FROM: C# Customer entity (no longer a @Document root)
 * NOTE: No @Document annotation - this is a value object embedded in Order
 */
class Customer {

    private Integer customerId;
    private String customerName;
    private LocalDate accountOpenedDate;
    private BigDecimal creditLimit;

    // Embedded CustomerTransactions array (denormalized from Sales.CustomerTransactions table)
    private List<CustomerTransaction> customerTransactions = new ArrayList<>();

    // Constructors
    public Customer() {
    }

    // Getters and Setters
    public Integer getCustomerId() { return customerId; }
    public void setCustomerId(Integer customerId) { this.customerId = customerId; }
    public String getCustomerName() { return customerName; }
    public void setCustomerName(String customerName) { this.customerName = customerName; }
    public LocalDate getAccountOpenedDate() { return accountOpenedDate; }
    public void setAccountOpenedDate(LocalDate accountOpenedDate) { this.accountOpenedDate = accountOpenedDate; }
    public BigDecimal getCreditLimit() { return creditLimit; }
    public void setCreditLimit(BigDecimal creditLimit) { this.creditLimit = creditLimit; }
    public List<CustomerTransaction> getCustomerTransactions() { return customerTransactions; }
    public void setCustomerTransactions(List<CustomerTransaction> customerTransactions) { this.customerTransactions = customerTransactions; }
}

/**
 * Embedded CustomerTransaction document within Customer.customerTransactions array.
 * Represents the denormalized Sales.CustomerTransactions table data.
 * 
 * TRANSLATED FROM: C# CustomerTransaction entity
 * NOTE: No @Document annotation - this is a value object embedded in Customer
 */
class CustomerTransaction {

    private Integer customerTransactionId;
    private Integer customerId;
    private LocalDate transactionDate;
    private BigDecimal transactionAmount;

    // Constructors
    public CustomerTransaction() {
    }

    // Getters and Setters
    public Integer getCustomerTransactionId() { return customerTransactionId; }
    public void setCustomerTransactionId(Integer customerTransactionId) { this.customerTransactionId = customerTransactionId; }
    public Integer getCustomerId() { return customerId; }
    public void setCustomerId(Integer customerId) { this.customerId = customerId; }
    public LocalDate getTransactionDate() { return transactionDate; }
    public void setTransactionDate(LocalDate transactionDate) { this.transactionDate = transactionDate; }
    public BigDecimal getTransactionAmount() { return transactionAmount; }
    public void setTransactionAmount(BigDecimal transactionAmount) { this.transactionAmount = transactionAmount; }
}

/**
 * OrderLine document.
 * Maps to the 'orderLines' collection in MongoDB.
 * 
 * TRANSLATED FROM: C# OrderLine entity
 */
@Document(collection = "orderLines")
class OrderLine {

    @Id
    private String id;

    @Field("orderLineId")
    private Integer orderLineId;

    @Field("orderId")
    private Integer orderId;

    @Field("stockItemId")
    private Integer stockItemId;

    private String description;

    @Field("packageTypeId")
    private Integer packageTypeId;

    private Integer quantity;

    private BigDecimal unitPrice;

    @Field("taxRate")
    private BigDecimal taxRate;

    @Field("pickedQuantity")
    private Integer pickedQuantity;

    @Field("pickingCompletedWhen")
    private LocalDateTime pickingCompletedWhen;

    @Field("lastEditedBy")
    private Integer lastEditedBy;

    @Field("lastEditedWhen")
    private LocalDateTime lastEditedWhen;

    // Constructors
    public OrderLine() {
    }

    // Getters and Setters
    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    public Integer getOrderLineId() { return orderLineId; }
    public void setOrderLineId(Integer orderLineId) { this.orderLineId = orderLineId; }
    public Integer getOrderId() { return orderId; }
    public void setOrderId(Integer orderId) { this.orderId = orderId; }
    public Integer getStockItemId() { return stockItemId; }
    public void setStockItemId(Integer stockItemId) { this.stockItemId = stockItemId; }
    public String getDescription() { return description; }
    public void setDescription(String description) { this.description = description; }
    public Integer getPackageTypeId() { return packageTypeId; }
    public void setPackageTypeId(Integer packageTypeId) { this.packageTypeId = packageTypeId; }
    public Integer getQuantity() { return quantity; }
    public void setQuantity(Integer quantity) { this.quantity = quantity; }
    public BigDecimal getUnitPrice() { return unitPrice; }
    public void setUnitPrice(BigDecimal unitPrice) { this.unitPrice = unitPrice; }
    public BigDecimal getTaxRate() { return taxRate; }
    public void setTaxRate(BigDecimal taxRate) { this.taxRate = taxRate; }
    public Integer getPickedQuantity() { return pickedQuantity; }
    public void setPickedQuantity(Integer pickedQuantity) { this.pickedQuantity = pickedQuantity; }
    public LocalDateTime getPickingCompletedWhen() { return pickingCompletedWhen; }
    public void setPickingCompletedWhen(LocalDateTime pickingCompletedWhen) { this.pickingCompletedWhen = pickingCompletedWhen; }
    public Integer getLastEditedBy() { return lastEditedBy; }
    public void setLastEditedBy(Integer lastEditedBy) { this.lastEditedBy = lastEditedBy; }
    public LocalDateTime getLastEditedWhen() { return lastEditedWhen; }
    public void setLastEditedWhen(LocalDateTime lastEditedWhen) { this.lastEditedWhen = lastEditedWhen; }
}

record CountProjection(Long count) {
}

interface Query5Projection {
    Integer getOrderLineId();
    Integer getQuantity();
}

// --- Query Entrypoint ---

final class Query1 {
    public static Query query() {
        LocalDate from = LocalDate.of(2014, 12, 20);
        LocalDate to = LocalDate.of(2014, 12, 31);
        return new Query(Criteria.where("pickingCompletedWhen").gte(from).lte(to));
    }

    public static Map<String, Object> harness(MongoTemplate template) {
        Query q = query();
        long count = template.count(q, OrderLine.class);
        Object first = null;
        if (count > 0) {
            first = template.findOne(query().with(Sort.by(Sort.Direction.ASC, "orderLineId")).limit(1), OrderLine.class);
        }
        Object last = null;
        if (count > 1) {
            last = template.findOne(query().with(Sort.by(Sort.Direction.DESC, "orderLineId")).limit(1), OrderLine.class);
        }
        return Map.of("mongoQuery", Map.of("collection", template.getCollectionName(OrderLine.class), "filter", q.getQueryObject()), "count", count, "firstSample", first, "lastSample", last);
    }
}

final class Query2 {
    public static Query query() {
        return new Query(Criteria.where("customerId").is(1));
    }

    public static Map<String, Object> harness(MongoTemplate template) {
        Query q = query();
        long count = template.count(q, Order.class);
        Object first = null;
        if (count > 0) {
            first = template.findOne(query().with(Sort.by(Sort.Direction.ASC, "orderId")).limit(1), Order.class);
        }
        Object last = null;
        if (count > 1) {
            last = template.findOne(query().with(Sort.by(Sort.Direction.DESC, "orderId")).limit(1), Order.class);
        }
        return Map.of("mongoQuery", Map.of("collection", template.getCollectionName(Order.class), "filter", q.getQueryObject()), "count", count, "firstSample", first, "lastSample", last);
    }
}

final class Query3 {
    public static TypedAggregation<OrderLine> query() {
        return Aggregation.newAggregation(
            OrderLine.class,
            Aggregation.group("taxRate").count().as("count"),
            Aggregation.project("count").and("taxRate").previousOperation(),
            Aggregation.sort(Sort.Direction.DESC, "count")
        );
    }

    public static Map<String, Object> harness(MongoTemplate template) {
        var baseAgg = query();
        
        var countOps = new ArrayList<>(baseAgg.getPipeline().getOperations());
        countOps.add(Aggregation.count().as("count"));
        var countAgg = Aggregation.newAggregation(OrderLine.class, countOps);
        var countResult = template.aggregate(countAgg, OrderLine.class, CountProjection.class).getUniqueMappedResult();
        var count = countResult != null ? countResult.count() : 0L;
        
        Object first = null;
        if (count > 0) {
            var agg = Aggregation.newAggregation(query().getPipeline().add(Aggregation.sort(Sort.Direction.ASC, "taxRate")).add(Aggregation.limit(1)).getOperations());
            first = template.aggregate(agg, template.getCollectionName(OrderLine.class), Object.class).getUniqueMappedResult();
        }
        Object last = null;
        if (count > 1) {
            var desc = Aggregation.newAggregation(query().getPipeline().add(Aggregation.sort(Sort.Direction.DESC, "taxRate")).add(Aggregation.limit(1)).getOperations());
            last = template.aggregate(desc, template.getCollectionName(OrderLine.class), Object.class).getUniqueMappedResult();
        }
        return Map.of("mongoAggregation", Map.of("collection", template.getCollectionName(OrderLine.class), "pipeline", baseAgg.toString()), "count", count, "firstSample", first, "lastSample", last);
    }
}

final class Query4 {
    public static Query query() {
        return new Query().with(Sort.by(Sort.Direction.DESC, "quantity")).limit(50);
    }

    public static Map<String, Object> harness(MongoTemplate template) {
        Query q = query();
        long count = template.count(q, OrderLine.class);

        Object first = null;
        if (count > 0) {
            Query firstQ = q.with(Sort.by(Sort.Direction.ASC, "orderLineId")).limit(1);
            first = template.findOne(firstQ, OrderLine.class);
        }
        Object last = null;
        if (count > 1) {
            Query lastQ = q.with(Sort.by(Sort.Direction.ASC, "orderLineId")).skip(count - 1).limit(1);
            last = template.findOne(lastQ, OrderLine.class);
        }
        return Map.of("mongoQuery", Map.of("collection", template.getCollectionName(OrderLine.class), "filter", q.getQueryObject(), "sort", q.getSortObject()), "count", count, "firstSample", first, "lastSample", last);
    }
}

final class Query5 {
    public static Query query() {
        Query q = new Query();
        q.fields().include("orderLineId", "quantity");
        return q;
    }

    public static Map<String, Object> harness(MongoTemplate template) {
        Query q = query();
        long count = template.count(q, OrderLine.class);
        
        Object first = null;
        if (count > 0) {
            Query asc = query().with(Sort.by(Sort.Direction.ASC, "orderLineId")).limit(1);
            first = template.query(OrderLine.class).as(Query5Projection.class).matching(asc).firstValue();
        }
        Object last = null;
        if (count > 1) {
            Query desc = query().with(Sort.by(Sort.Direction.DESC, "orderLineId")).limit(1);
            last = template.query(OrderLine.class).as(Query5Projection.class).matching(desc).firstValue();
        }
        return Map.of("mongoQuery", Map.of("collection", template.getCollectionName(OrderLine.class), "filter", q.getQueryObject(), "fields", q.getFieldsObject()), "count", count, "firstSample", first, "lastSample", last);
    }
}

public class MongoQueryEntrypoint {

    public static void main(String[] args) throws Exception {
        String mongoUri = args.length > 0 ? args[0] : QueryRuntimeSupport.defaultMongoUri();
        String mongoDatabase = args.length > 1 ? args[1] : QueryRuntimeSupport.defaultMongoDatabase();
        QueryRuntimeSupport.configureLogger();
        MongoTemplate template = QueryRuntimeSupport.createMongoTemplate(mongoUri, mongoDatabase);

        var results = new LinkedHashMap<String, Object>();
        List<Supplier<Map<String, Object>>> harnesses = List.of(
            () -> Query1.harness(template),
            () -> Query2.harness(template),
            () -> Query3.harness(template),
            () -> Query4.harness(template),
            () -> Query5.harness(template)
        );

        int idx = 0;
        for (var harness : harnesses) {
            idx += 1;
            System.out.println("Executing query" + idx + "...");
            try {
                results.put("query" + idx, harness.get());
            } catch (Exception e) {
                System.err.println("Error occurred while executing query" + idx);
                e.printStackTrace();
                results.put("query" + idx, Map.of("error", e.toString()));
            }
        }
        QueryRuntimeSupport.createJsonMapper().writeValue(new java.io.File(System.getenv("MONGO_RESULTS_PATH") + "/mongo_results_" + System.currentTimeMillis() + ".json"), results);
    }
}
