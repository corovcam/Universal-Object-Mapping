package uom.services.benchmarks;

import java.math.BigDecimal;
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
import java.util.List;
import java.util.Map;

import org.springframework.data.annotation.Id;
import org.springframework.data.domain.Sort;
import org.springframework.data.mongodb.MongoDatabaseFactory;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.mongodb.core.SimpleMongoClientDatabaseFactory;
import org.springframework.data.mongodb.core.convert.DefaultDbRefResolver;
import org.springframework.data.mongodb.core.convert.DefaultMongoTypeMapper;
import org.springframework.data.mongodb.core.convert.MappingMongoConverter;
import org.springframework.data.mongodb.core.convert.MongoCustomConversions;
import org.springframework.data.mongodb.core.mapping.Document;
import org.springframework.data.mongodb.core.mapping.Field;
import org.springframework.data.mongodb.core.mapping.MongoMappingContext;
import org.springframework.data.mongodb.core.query.Criteria;
import org.springframework.data.mongodb.core.query.Query;

import com.fasterxml.jackson.annotation.JsonInclude.Include;
import com.mongodb.client.MongoClients;

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

    private static final DateTimeFormatter DATE_FORMATTER = 
        DateTimeFormatter.ofPattern("yyyy-MM-dd");

    public CustomJsonSerializer() {
        super(Object.class);
    }

    @Override
    public void serialize(Object value, JsonGenerator gen, SerializationContext ctx) {
        if (value == null) {
            gen.writeNull();
        } else if (value instanceof BigDecimal) {
            gen.writeNumber(((BigDecimal) value).stripTrailingZeros().toPlainString());
        } else if (value instanceof LocalDate) {
            gen.writeString(DATE_FORMATTER.format((LocalDate) value));
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
    private static final String DEFAULT_MONGO_URI = "mongodb://uom_readonly:uom_readonly@localhost:27027/uom";
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

    static String defaultMongoUri() {
        return DEFAULT_MONGO_URI;
    }

    static String defaultMongoDatabase() {
        return DEFAULT_MONGO_DATABASE;
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
 * Maps to the 'orders' collection in MongoDB.
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

    @Field("orderDate")
    private LocalDateTime orderDate;

    @Field("expectedDeliveryDate")
    private LocalDate expectedDeliveryDate;

    // Embedded Customer document (denormalized from Sales.Customers table)
    private Customer customer;

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

    public LocalDateTime getOrderDate() { return orderDate; }
    public void setOrderDate(LocalDateTime orderDate) { this.orderDate = orderDate; }

    public LocalDate getExpectedDeliveryDate() { return expectedDeliveryDate; }
    public void setExpectedDeliveryDate(LocalDate expectedDeliveryDate) { this.expectedDeliveryDate = expectedDeliveryDate; }

    public Customer getCustomer() { return customer; }
    public void setCustomer(Customer customer) { this.customer = customer; }
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

    // Additional transaction fields from Sales.CustomerTransactions
    private BigDecimal amountExcludingTax;
    private BigDecimal taxAmount;
    private BigDecimal outstandingBalance;
    private Boolean isFinalized;

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

    public BigDecimal getAmountExcludingTax() { return amountExcludingTax; }
    public void setAmountExcludingTax(BigDecimal amountExcludingTax) { this.amountExcludingTax = amountExcludingTax; }

    public BigDecimal getTaxAmount() { return taxAmount; }
    public void setTaxAmount(BigDecimal taxAmount) { this.taxAmount = taxAmount; }

    public BigDecimal getOutstandingBalance() { return outstandingBalance; }
    public void setOutstandingBalance(BigDecimal outstandingBalance) { this.outstandingBalance = outstandingBalance; }

    public Boolean getIsFinalized() { return isFinalized; }
    public void setIsFinalized(Boolean isFinalized) { this.isFinalized = isFinalized; }
}

/**
 * OrderLine document with embedded StockItem.
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

    // Embedded StockItem document (denormalized reference data)
    private StockItem stockItem;

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

    public StockItem getStockItem() { return stockItem; }
    public void setStockItem(StockItem stockItem) { this.stockItem = stockItem; }
}

/**
 * Embedded StockItem document within OrderLine.
 * Represents denormalized stock item reference data.
 * 
 * NOTE: No @Document annotation - this is a value object embedded in OrderLine
 */
class StockItem {

    private Integer stockItemId;

    // Getters and Setters
    public Integer getStockItemId() { return stockItemId; }
    public void setStockItemId(Integer stockItemId) { this.stockItemId = stockItemId; }
}

// --- Query Entrypoint ---

public class MongoQueryEntrypoint {

    public static Query query() {
        LocalDate from = LocalDate.of(2014, 12, 20);
        LocalDate to = LocalDate.of(2014, 12, 31);

        Criteria criteria = Criteria.where("pickingCompletedWhen").gte(from).lte(to);
        Query query = new Query(criteria);
        
        return query;
    }

    public static void main(String[] args) throws Exception {
        String mongoUri = args.length > 0 ? args[0] : QueryRuntimeSupport.defaultMongoUri();
        String mongoDatabase = args.length > 1 ? args[1] : QueryRuntimeSupport.defaultMongoDatabase();

        MongoTemplate mongoTemplate = QueryRuntimeSupport.createMongoTemplate(mongoUri, mongoDatabase);

        // Deterministic sorting
        Query ascQuery = query().with(Sort.by(Sort.Direction.ASC, "orderLineId")).limit(1);
        Query descQuery = query().with(Sort.by(Sort.Direction.DESC, "orderLineId")).limit(1);

        OrderLine firstSample = mongoTemplate.findOne(ascQuery, OrderLine.class);
        OrderLine lastSample = mongoTemplate.findOne(descQuery, OrderLine.class);

        var query = query();
        var mongoQuery = Map.of(
            "collection", mongoTemplate.getCollectionName(OrderLine.class),
            "filter", query.getQueryObject(),
            "fields", query.getFieldsObject(),
            "sort", query.getSortObject()
        );
        var result = Map.of(
            "mongoQuery", mongoQuery,
            "estimatedRowCount", mongoTemplate.count(query, OrderLine.class),
            "firstSample", firstSample,
            "lastSample", lastSample
        );

        System.out.println(QueryRuntimeSupport.createJsonMapper().writeValueAsString(result));
    }
}
