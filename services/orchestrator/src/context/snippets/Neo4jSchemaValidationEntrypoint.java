package uom.services;

import java.time.LocalDate;
import java.time.ZonedDateTime;
import java.util.List;
import java.util.Map;
import java.util.Set;

import org.neo4j.cypherdsl.core.Cypher;
import org.neo4j.driver.AuthTokens;
import org.neo4j.driver.Driver;
import org.neo4j.driver.GraphDatabase;
import org.slf4j.LoggerFactory;
import org.springframework.data.neo4j.core.Neo4jClient;
import org.springframework.data.neo4j.core.Neo4jTemplate;
import org.springframework.data.neo4j.core.mapping.Neo4jMappingContext;
import org.springframework.data.neo4j.core.schema.GeneratedValue;
import org.springframework.data.neo4j.core.schema.Id;
import org.springframework.data.neo4j.core.schema.Node;
import org.springframework.data.neo4j.core.schema.Property;
import org.springframework.data.neo4j.core.schema.Relationship;
import org.springframework.data.neo4j.core.transaction.Neo4jTransactionManager;

import ch.qos.logback.classic.LoggerContext;

// --- Harness and Utilities ---

final class QueryRuntimeSupport {
    private static final String DEFAULT_NEO4J_URI = "neo4j://neo4j:7687";
    private static final String DEFAULT_NEO4J_USER = "neo4j";
    private static final String DEFAULT_NEO4J_PASS = "password";

    private QueryRuntimeSupport() {
    }

    static Neo4jTemplate createNeo4jTemplate(Driver driver) {
        Neo4jClient client = Neo4jClient.create(driver);
        var mappingContext = new Neo4jMappingContext();
        mappingContext
                .setInitialEntitySet(Set.of(Order.class, Customer.class, CustomerTransaction.class, OrderLine.class));
        mappingContext.afterPropertiesSet();

        Neo4jTransactionManager transactionManager = new Neo4jTransactionManager(driver);
        return new Neo4jTemplate(client, mappingContext, transactionManager);
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

    @Id
    @GeneratedValue
    private String id;

    @Property("orderId")
    private Integer orderId;

    @Relationship(type = "CUSTOMERS", direction = Relationship.Direction.OUTGOING)
    private Customer customer;

    @Relationship(type = "ORDERS", direction = Relationship.Direction.INCOMING)
    private List<OrderLine> orderLines;

    public Order() {
    }

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

@Node("Customer")
class Customer {

    @Id
    @GeneratedValue
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

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

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

    public Double getCreditLimit() {
        return creditLimit;
    }

    public void setCreditLimit(Double creditLimit) {
        this.creditLimit = creditLimit;
    }

    public List<CustomerTransaction> getCustomerTransactions() {
        return customerTransactions;
    }

    public void setCustomerTransactions(List<CustomerTransaction> customerTransactions) {
        this.customerTransactions = customerTransactions;
    }
}

@Node("CustomerTransaction")
class CustomerTransaction {

    @Id
    @GeneratedValue
    private String id;

    @Property("customerTransactionId")
    private Integer customerTransactionId;

    @Property("transactionDate")
    private LocalDate transactionDate;

    @Property("transactionAmount")
    private Double transactionAmount;

    public CustomerTransaction() {
    }

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public Integer getCustomerTransactionId() {
        return customerTransactionId;
    }

    public void setCustomerTransactionId(Integer customerTransactionId) {
        this.customerTransactionId = customerTransactionId;
    }

    public LocalDate getTransactionDate() {
        return transactionDate;
    }

    public void setTransactionDate(LocalDate transactionDate) {
        this.transactionDate = transactionDate;
    }

    public Double getTransactionAmount() {
        return transactionAmount;
    }

    public void setTransactionAmount(Double transactionAmount) {
        this.transactionAmount = transactionAmount;
    }
}

@Node("OrderLine")
class OrderLine {

    @Id
    @GeneratedValue
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

    public String getDescription() {
        return description;
    }

    public void setDescription(String description) {
        this.description = description;
    }

    public Integer getQuantity() {
        return quantity;
    }

    public void setQuantity(Integer quantity) {
        this.quantity = quantity;
    }

    public Double getUnitPrice() {
        return unitPrice;
    }

    public void setUnitPrice(Double unitPrice) {
        this.unitPrice = unitPrice;
    }

    public Double getTaxRate() {
        return taxRate;
    }

    public void setTaxRate(Double taxRate) {
        this.taxRate = taxRate;
    }

    public Integer getPickedQuantity() {
        return pickedQuantity;
    }

    public void setPickedQuantity(Integer pickedQuantity) {
        this.pickedQuantity = pickedQuantity;
    }

    public ZonedDateTime getPickingCompletedWhen() {
        return pickingCompletedWhen;
    }

    public void setPickingCompletedWhen(ZonedDateTime pickingCompletedWhen) {
        this.pickingCompletedWhen = pickingCompletedWhen;
    }

    public ZonedDateTime getLastEditedWhen() {
        return lastEditedWhen;
    }

    public void setLastEditedWhen(ZonedDateTime lastEditedWhen) {
        this.lastEditedWhen = lastEditedWhen;
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
    public static void validateNeo4jEntity(Class<?> entityClass, Neo4jTemplate neo4jTemplate) {
        System.out.println("Validating Neo4j entity: " + entityClass.getSimpleName());
        var node = Cypher.node(entityClass.getSimpleName());
        neo4jTemplate.findOne(Cypher.match(node).returning(node).limit(1).build(), Map.of(), entityClass);
        System.out.println("Successfully validated Neo4j entity: " + entityClass.getSimpleName());
    }

    public static void main(String[] args) throws Exception {
        String uri = args.length > 0 ? args[0] : QueryRuntimeSupport.getNeo4jUri();
        String user = args.length > 1 ? args[1] : QueryRuntimeSupport.getNeo4jUsername();
        String pass = args.length > 2 ? args[2] : QueryRuntimeSupport.getNeo4jPassword();
        QueryRuntimeSupport.configureLogger();

        try (Driver driver = GraphDatabase.driver(uri, AuthTokens.basic(user, pass))) {
            Neo4jTemplate template = QueryRuntimeSupport.createNeo4jTemplate(driver);
            List<Runnable> queries = List.of(
                    () -> validateNeo4jEntity(Order.class, template),
                    () -> validateNeo4jEntity(Customer.class, template),
                    () -> validateNeo4jEntity(CustomerTransaction.class, template),
                    () -> validateNeo4jEntity(OrderLine.class, template));
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
