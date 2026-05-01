package uom.services;

import java.math.*;
import java.time.*;
import java.util.*;

import org.slf4j.*;
import org.springframework.data.annotation.*;
import org.springframework.data.mongodb.*;
import org.springframework.data.mongodb.core.*;
import org.springframework.data.mongodb.core.convert.*;
import org.springframework.data.mongodb.core.mapping.*;
import org.springframework.data.mongodb.core.mapping.Field;
import org.springframework.data.mongodb.core.query.*;

import com.mongodb.client.*;

import ch.qos.logback.classic.*;

// --- Harness and Utilities ---

final class QueryRuntimeSupport {
    private static final String DEFAULT_MONGO_URI = "mongodb://uom_readonly:uom_readonly@mongodb:27017/uom";
    private static final String DEFAULT_MONGO_DATABASE = "uom";

    private QueryRuntimeSupport() {
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
 * Instead, Customer and its transactions are embedded within Order.
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
    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public Integer getOrderId() {
        return orderId;
    }

    public void setOrderId(Integer orderId) {
        this.orderId = orderId;
    }

    public Integer getCustomerId() {
        return customerId;
    }

    public void setCustomerId(Integer customerId) {
        this.customerId = customerId;
    }

    public Customer getCustomer() {
        return customer;
    }

    public void setCustomer(Customer customer) {
        this.customer = customer;
    }

    public List<OrderLine> getOrderLines() {
        return orderLines;
    }

    public void setOrderLines(List<OrderLine> orderLines) {
        this.orderLines = orderLines;
    }
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

    // Embedded CustomerTransactions array (denormalized from
    // Sales.CustomerTransactions table)
    private List<CustomerTransaction> customerTransactions = new ArrayList<>();

    // Constructors
    public Customer() {
    }

    // Getters and Setters
    public Integer getCustomerId() {
        return customerId;
    }

    public void setCustomerId(Integer customerId) {
        this.customerId = customerId;
    }

    public String getCustomerName() {
        return customerName;
    }

    public void setCustomerName(String customerName) {
        this.customerName = customerName;
    }

    public LocalDate getAccountOpenedDate() {
        return accountOpenedDate;
    }

    public void setAccountOpenedDate(LocalDate accountOpenedDate) {
        this.accountOpenedDate = accountOpenedDate;
    }

    public BigDecimal getCreditLimit() {
        return creditLimit;
    }

    public void setCreditLimit(BigDecimal creditLimit) {
        this.creditLimit = creditLimit;
    }

    public List<CustomerTransaction> getCustomerTransactions() {
        return customerTransactions;
    }

    public void setCustomerTransactions(List<CustomerTransaction> customerTransactions) {
        this.customerTransactions = customerTransactions;
    }
}

/**
 * Embedded CustomerTransaction document within Customer.customerTransactions
 * array.
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
    public Integer getCustomerTransactionId() {
        return customerTransactionId;
    }

    public void setCustomerTransactionId(Integer customerTransactionId) {
        this.customerTransactionId = customerTransactionId;
    }

    public Integer getCustomerId() {
        return customerId;
    }

    public void setCustomerId(Integer customerId) {
        this.customerId = customerId;
    }

    public LocalDate getTransactionDate() {
        return transactionDate;
    }

    public void setTransactionDate(LocalDate transactionDate) {
        this.transactionDate = transactionDate;
    }

    public BigDecimal getTransactionAmount() {
        return transactionAmount;
    }

    public void setTransactionAmount(BigDecimal transactionAmount) {
        this.transactionAmount = transactionAmount;
    }
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
    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public Integer getOrderLineId() {
        return orderLineId;
    }

    public void setOrderLineId(Integer orderLineId) {
        this.orderLineId = orderLineId;
    }

    public Integer getOrderId() {
        return orderId;
    }

    public void setOrderId(Integer orderId) {
        this.orderId = orderId;
    }

    public Integer getStockItemId() {
        return stockItemId;
    }

    public void setStockItemId(Integer stockItemId) {
        this.stockItemId = stockItemId;
    }

    public String getDescription() {
        return description;
    }

    public void setDescription(String description) {
        this.description = description;
    }

    public Integer getPackageTypeId() {
        return packageTypeId;
    }

    public void setPackageTypeId(Integer packageTypeId) {
        this.packageTypeId = packageTypeId;
    }

    public Integer getQuantity() {
        return quantity;
    }

    public void setQuantity(Integer quantity) {
        this.quantity = quantity;
    }

    public BigDecimal getUnitPrice() {
        return unitPrice;
    }

    public void setUnitPrice(BigDecimal unitPrice) {
        this.unitPrice = unitPrice;
    }

    public BigDecimal getTaxRate() {
        return taxRate;
    }

    public void setTaxRate(BigDecimal taxRate) {
        this.taxRate = taxRate;
    }

    public Integer getPickedQuantity() {
        return pickedQuantity;
    }

    public void setPickedQuantity(Integer pickedQuantity) {
        this.pickedQuantity = pickedQuantity;
    }

    public LocalDateTime getPickingCompletedWhen() {
        return pickingCompletedWhen;
    }

    public void setPickingCompletedWhen(LocalDateTime pickingCompletedWhen) {
        this.pickingCompletedWhen = pickingCompletedWhen;
    }

    public Integer getLastEditedBy() {
        return lastEditedBy;
    }

    public void setLastEditedBy(Integer lastEditedBy) {
        this.lastEditedBy = lastEditedBy;
    }

    public LocalDateTime getLastEditedWhen() {
        return lastEditedWhen;
    }

    public void setLastEditedWhen(LocalDateTime lastEditedWhen) {
        this.lastEditedWhen = lastEditedWhen;
    }
}

// --- Schema Validation Entrypoint ---

public class MongoSchemaValidationEntrypoint {
    /**
     * Validates a MongoDB entity by running
     * {@code mongoTemplate.findOne(query, entityClass)}
     * with a limit of 1. If the mapping is invalid, Spring Data MongoDB will throw.
     */
    public static void validateMongoEntity(Class<?> entityClass, MongoTemplate mongoTemplate) {
        System.out.println("Validating MongoDB entity: " + entityClass.getSimpleName());
        Query query = new Query().limit(1);
        // This will throw MappingException or similar if the entity mapping is invalid
        // or if the collection doesn't exist / has incompatible data
        mongoTemplate.findOne(query, entityClass);
        System.out.println("Successfully validated MongoDB entity: " + entityClass.getSimpleName());
    }

    public static void main(String[] args) throws Exception {
        String mongoUri = args.length > 0 ? args[0] : QueryRuntimeSupport.defaultMongoUri();
        String mongoDatabase = args.length > 1 ? args[1] : QueryRuntimeSupport.defaultMongoDatabase();
        QueryRuntimeSupport.configureLogger();
        MongoTemplate template = QueryRuntimeSupport.createMongoTemplate(mongoUri, mongoDatabase);
        // Only validate @Document aggregate roots - Order and OrderLine. Customer and CustomerTransaction are embedded value objects.
        List<Runnable> queries = List.of(
                () -> validateMongoEntity(Order.class, template),
                () -> validateMongoEntity(OrderLine.class, template));
        for (var query : queries) {
            try {
                query.run();
            } catch (Exception e) {
                System.err.println("Error occurred while validating entity");
                e.printStackTrace();
            }
        }
    }
}
