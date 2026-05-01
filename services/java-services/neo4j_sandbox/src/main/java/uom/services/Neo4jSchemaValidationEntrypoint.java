package uom.services;

import java.math.*;
import java.time.*;
import java.time.format.*;
import java.time.temporal.*;
import java.util.*;
import java.util.Set;

import org.neo4j.cypherdsl.core.*;
import org.neo4j.driver.*;
import org.slf4j.*;
import org.springframework.data.neo4j.core.*;
import org.springframework.data.neo4j.core.mapping.*;
import org.springframework.data.neo4j.core.schema.*;
import org.springframework.data.neo4j.core.schema.Node;
import org.springframework.data.neo4j.core.schema.Property;
import org.springframework.data.neo4j.core.schema.Relationship;
import org.springframework.data.neo4j.core.transaction.*;

import com.fasterxml.jackson.annotation.JsonInclude.*;

import ch.qos.logback.classic.*;
import tools.jackson.core.*;
import tools.jackson.databind.*;
import tools.jackson.databind.cfg.*;
import tools.jackson.databind.json.*;
import tools.jackson.databind.module.*;
import tools.jackson.databind.ser.std.*;

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
    private static final String DEFAULT_NEO4J_URI = "neo4j://neo4j:7687";
    private static final String DEFAULT_NEO4J_USER = "neo4j";
    private static final String DEFAULT_NEO4J_PASS = "password";

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

    static void configureLogger() {
        var loggerContext = (LoggerContext) LoggerFactory.getILoggerFactory();
        var mongoLogger = loggerContext.getLogger("org.springframework.data.neo4j.cypher");
        mongoLogger.setLevel(ch.qos.logback.classic.Level.DEBUG);
    }

    static String getNeo4jUri() {
        String uri = System.getenv("NEO4J_URI");
        return uri != null ? uri : DEFAULT_NEO4J_URI;
    }

    static String getNeo4jUsername() {
        String user = System.getenv("NEO4J_USERNAME");
        return user != null ? user : DEFAULT_NEO4J_USER;
    }

    static String getNeo4jPassword() {
        String pass = System.getenv("NEO4J_PASSWORD");
        return pass != null ? pass : DEFAULT_NEO4J_PASS;
    }
}

// --- Schema and Related Settings ---

@Node("Order")
class Order {

    @Id @GeneratedValue
    private String id;

    @Property("orderId")
    private Integer orderId;

    @Relationship(type = "CUSTOMERS", direction = Relationship.Direction.OUTGOING)
    private Customer customer;

    @Relationship(type = "ORDERS", direction = Relationship.Direction.INCOMING)
    private List<OrderLine> orderLines;

    public Order() {
    }

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    public Integer getOrderId() { return orderId; }
    public void setOrderId(Integer orderId) { this.orderId = orderId; }
    public Customer getCustomer() { return customer; }
    public void setCustomer(Customer customer) { this.customer = customer; }
    public List<OrderLine> getOrderLines() { return orderLines; }
    public void setOrderLines(List<OrderLine> orderLines) { this.orderLines = orderLines; }
}

@Node("Customer")
class Customer {

    @Id @GeneratedValue
    private String id;

    @Property("customerId")
    private Integer customerId;

    @Property("customerName")
    private String customerName;

    @Property("accountOpenedDate")
    private LocalDate accountOpenedDate;

    @Property("creditLimit")
    private Double creditLimit;

    @Relationship(type = "CUSTOMERS", direction = Relationship.Direction.INCOMING)
    private List<CustomerTransaction> customerTransactions;

    public Customer() {
    }

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    public Integer getCustomerId() { return customerId; }
    public void setCustomerId(Integer customerId) { this.customerId = customerId; }
    public String getCustomerName() { return customerName; }
    public void setCustomerName(String customerName) { this.customerName = customerName; }
    public LocalDate getAccountOpenedDate() { return accountOpenedDate; }
    public void setAccountOpenedDate(LocalDate accountOpenedDate) { this.accountOpenedDate = accountOpenedDate; }
    public Double getCreditLimit() { return creditLimit; }
    public void setCreditLimit(Double creditLimit) { this.creditLimit = creditLimit; }
    public List<CustomerTransaction> getCustomerTransactions() { return customerTransactions; }
    public void setCustomerTransactions(List<CustomerTransaction> customerTransactions) { this.customerTransactions = customerTransactions; }
}

@Node("CustomerTransaction")
class CustomerTransaction {

    @Id @GeneratedValue
    private String id;

    @Property("customerTransactionId")
    private Integer customerTransactionId;

    @Property("transactionDate")
    private LocalDate transactionDate;

    @Property("transactionAmount")
    private Double transactionAmount;

    public CustomerTransaction() {
    }

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    public Integer getCustomerTransactionId() { return customerTransactionId; }
    public void setCustomerTransactionId(Integer customerTransactionId) { this.customerTransactionId = customerTransactionId; }
    public LocalDate getTransactionDate() { return transactionDate; }
    public void setTransactionDate(LocalDate transactionDate) { this.transactionDate = transactionDate; }
    public Double getTransactionAmount() { return transactionAmount; }
    public void setTransactionAmount(Double transactionAmount) { this.transactionAmount = transactionAmount; }
}

@Node("OrderLine")
class OrderLine {

    @Id @GeneratedValue
    private String id;

    @Property("orderLineId")
    private Integer orderLineId;

    @Property("description")
    private String description;

    @Property("quantity")
    private Integer quantity;

    @Property("unitPrice")
    private Double unitPrice;

    @Property("taxRate")
    private Double taxRate;

    @Property("pickedQuantity")
    private Integer pickedQuantity;

    @Property("pickingCompletedWhen")
    private ZonedDateTime pickingCompletedWhen;

    @Property("lastEditedWhen")
    private ZonedDateTime lastEditedWhen;

    public OrderLine() {
    }

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    public Integer getOrderLineId() { return orderLineId; }
    public void setOrderLineId(Integer orderLineId) { this.orderLineId = orderLineId; }
    public String getDescription() { return description; }
    public void setDescription(String description) { this.description = description; }
    public Integer getQuantity() { return quantity; }
    public void setQuantity(Integer quantity) { this.quantity = quantity; }
    public Double getUnitPrice() { return unitPrice; }
    public void setUnitPrice(Double unitPrice) { this.unitPrice = unitPrice; }
    public Double getTaxRate() { return taxRate; }
    public void setTaxRate(Double taxRate) { this.taxRate = taxRate; }
    public Integer getPickedQuantity() { return pickedQuantity; }
    public void setPickedQuantity(Integer pickedQuantity) { this.pickedQuantity = pickedQuantity; }
    public ZonedDateTime getPickingCompletedWhen() { return pickingCompletedWhen; }
    public void setPickingCompletedWhen(ZonedDateTime pickingCompletedWhen) { this.pickingCompletedWhen = pickingCompletedWhen; }
    public ZonedDateTime getLastEditedWhen() { return lastEditedWhen; }
    public void setLastEditedWhen(ZonedDateTime lastEditedWhen) { this.lastEditedWhen = lastEditedWhen; }
}

final class Neo4jTemplateFactory {
    private Neo4jTemplateFactory() {
    }

    static Neo4jTemplate create(Driver driver) {
        Neo4jClient client = Neo4jClient.create(driver);
        var mappingContext = new Neo4jMappingContext();
        mappingContext.setInitialEntitySet(Set.of(Order.class, Customer.class, CustomerTransaction.class, OrderLine.class));
        mappingContext.afterPropertiesSet();
    
        Neo4jTransactionManager transactionManager = new Neo4jTransactionManager(driver);
        return new Neo4jTemplate(client, mappingContext, transactionManager);
    }
}

// --- Query Entrypoint ---

public class Neo4jSchemaValidationEntrypoint {
    /**
     * Validates a Neo4j entity by running
     * {@code neo4jTemplate.findAll(entityClass)}
     * which translates to a MATCH query. If the mapping is invalid, Spring Data
     * Neo4j
     * will throw a MappingException.
     */
    public static void validateNeo4jEntity(Class<?> entityClass, Neo4jTemplate neo4jTemplate, JsonMapper jsonMapper) {
        System.out.println("Validating Neo4j entity: " + entityClass.getSimpleName());
        var node = Cypher.node(entityClass.getSimpleName());
        System.out.println(jsonMapper.writeValueAsString(neo4jTemplate.findOne(Cypher.match(node).returning(node).limit(1).build(), Map.of(), entityClass)));
        System.out.println("Successfully validated Neo4j entity: " + entityClass.getSimpleName());
    }

    public static void main(String[] args) throws Exception {
        String uri = args.length > 0 ? args[0] : QueryRuntimeSupport.getNeo4jUri();
        String user = args.length > 1 ? args[1] : QueryRuntimeSupport.getNeo4jUsername();
        String pass = args.length > 2 ? args[2] : QueryRuntimeSupport.getNeo4jPassword();
        QueryRuntimeSupport.configureLogger();

        try (Driver driver = GraphDatabase.driver(uri, AuthTokens.basic(user, pass))) {
            Neo4jTemplate template = Neo4jTemplateFactory.create(driver);
            var jsonMapper = QueryRuntimeSupport.createJsonMapper();
            List<Runnable> queries = List.of(
                    () -> validateNeo4jEntity(Order.class, template, jsonMapper),
                    () -> validateNeo4jEntity(Customer.class, template, jsonMapper),
                    () -> validateNeo4jEntity(CustomerTransaction.class, template, jsonMapper),
                    () -> validateNeo4jEntity(OrderLine.class, template, jsonMapper));
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
}
