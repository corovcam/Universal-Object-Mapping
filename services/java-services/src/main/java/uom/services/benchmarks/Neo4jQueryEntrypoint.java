package uom.services.benchmarks;

import java.math.BigDecimal;
import java.time.Instant;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.time.ZonedDateTime;
import java.time.format.DateTimeFormatter;
import java.time.temporal.TemporalAccessor;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Map;
import java.util.Set;

import org.neo4j.cypherdsl.core.Cypher;
import org.neo4j.cypherdsl.core.ResultStatement;
import org.neo4j.cypherdsl.core.SortItem.Direction;
import org.neo4j.cypherdsl.core.StatementBuilder.BuildableStatement;
import org.neo4j.cypherdsl.core.StatementBuilder.OngoingReadingAndReturn;
import org.neo4j.driver.AuthTokens;
import org.neo4j.driver.Driver;
import org.neo4j.driver.GraphDatabase;
import org.springframework.data.neo4j.core.Neo4jClient;
import org.springframework.data.neo4j.core.Neo4jTemplate;
import org.springframework.data.neo4j.core.mapping.Neo4jMappingContext;
import org.springframework.data.neo4j.core.schema.Id;
import org.springframework.data.neo4j.core.schema.Node;
import org.springframework.data.neo4j.core.schema.Property;
import org.springframework.data.neo4j.core.schema.Relationship;
import org.springframework.data.neo4j.core.transaction.Neo4jTransactionManager;

import com.fasterxml.jackson.annotation.JsonInclude.Include;

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
        } else if (value instanceof ZonedDateTime) {
            gen.writeString(DATETIME_FORMATTER.format((ZonedDateTime) value));
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
    private static final String DEFAULT_NEO4J_URI = "neo4j://localhost:7687";
    private static final String DEFAULT_NEO4J_USER = "neo4j";
    private static final String DEFAULT_NEO4J_PASS = "password";

    private QueryRuntimeSupport() {
    }

    static JsonMapper createJsonMapper() {
        SimpleModule customModule = new SimpleModule();
        CustomJsonSerializer customJsonSerializer = new CustomJsonSerializer();
        customModule.addSerializer(LocalDate.class, customJsonSerializer);
        customModule.addSerializer(ZonedDateTime.class, customJsonSerializer);
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

    static Neo4jTemplate createNeo4jTemplate(Driver driver) {
        Neo4jClient client = Neo4jClient.create(driver);
        var mappingContext = new Neo4jMappingContext();
        mappingContext.setInitialEntitySet(Set.of(Order.class, Customer.class, CustomerTransaction.class, OrderLine.class, StockItem.class));
        mappingContext.afterPropertiesSet();
    
        Neo4jTransactionManager transactionManager = new Neo4jTransactionManager(driver);
        return new Neo4jTemplate(client, mappingContext, transactionManager);
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
    private String id;

    @Property("orderId")
    private Integer orderId;
    
    @Property("orderDate")
    private ZonedDateTime orderDate;

    @Property("expectedDeliveryDate")
    private LocalDate expectedDeliveryDate;
    
    @Property("customerPurchaseOrderNumber")
    private String customerPurchaseOrderNumber;
    
    @Property("isUndersupplyBackordered")
    private Integer isUndersupplyBackordered;
    
    @Property("pickingCompletedWhen")
    private ZonedDateTime pickingCompletedWhen;
    
    @Property("lastEditedWhen")
    private ZonedDateTime lastEditedWhen;

    @Relationship(type = "CUSTOMERS", direction = Relationship.Direction.OUTGOING)
    private Customer customer;

    public Order() {
    }

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    public Integer getOrderId() { return orderId; }
    public void setOrderId(Integer orderId) { this.orderId = orderId; }
    public ZonedDateTime getOrderDate() { return orderDate; }
    public void setOrderDate(ZonedDateTime orderDate) { this.orderDate = orderDate; }
    public LocalDate getExpectedDeliveryDate() { return expectedDeliveryDate; }
    public void setExpectedDeliveryDate(LocalDate expectedDeliveryDate) { this.expectedDeliveryDate = expectedDeliveryDate; }
    public String getCustomerPurchaseOrderNumber() { return customerPurchaseOrderNumber; }
    public void setCustomerPurchaseOrderNumber(String customerPurchaseOrderNumber) { this.customerPurchaseOrderNumber = customerPurchaseOrderNumber; }
    public Integer getIsUndersupplyBackordered() { return isUndersupplyBackordered; }
    public void setIsUndersupplyBackordered(Integer isUndersupplyBackordered) { this.isUndersupplyBackordered = isUndersupplyBackordered; }
    public ZonedDateTime getPickingCompletedWhen() { return pickingCompletedWhen; }
    public void setPickingCompletedWhen(ZonedDateTime pickingCompletedWhen) { this.pickingCompletedWhen = pickingCompletedWhen; }
    public ZonedDateTime getLastEditedWhen() { return lastEditedWhen; }
    public void setLastEditedWhen(ZonedDateTime lastEditedWhen) { this.lastEditedWhen = lastEditedWhen; }
    public Customer getCustomer() { return customer; }
    public void setCustomer(Customer customer) { this.customer = customer; }
}

@Node("Customer")
class Customer {

    @Id
    private String id;

    @Property("customerId")
    private Integer customerId;

    @Property("customerName")
    private String customerName;

    @Property("accountOpenedDate")
    private LocalDate accountOpenedDate;

    @Property("creditLimit")
    private Double creditLimit;

    // Based on schema, CustomerTransaction has CUSTOMERS out. So we map the incoming relationship.
    @Relationship(type = "CUSTOMERS", direction = Relationship.Direction.INCOMING)
    private List<CustomerTransaction> customerTransactions = new ArrayList<>();

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

    @Id
    private String id;

    @Property("customerTransactionId")
    private Integer customerTransactionId;

    @Property("transactionDate")
    private ZonedDateTime transactionDate;

    @Property("transactionAmount")
    private Double transactionAmount;
    
    @Property("amountExcludingTax")
    private Double amountExcludingTax;
    
    @Property("taxAmount")
    private Double taxAmount;
    
    @Property("outstandingBalance")
    private Double outstandingBalance;
    
    @Property("finalizationDate")
    private ZonedDateTime finalizationDate;
    
    @Property("isFinalized")
    private Integer isFinalized;
    
    @Property("lastEditedWhen")
    private ZonedDateTime lastEditedWhen;

    @Relationship(type = "CUSTOMERS", direction = Relationship.Direction.OUTGOING)
    private Customer customer;

    public CustomerTransaction() {
    }

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    public Integer getCustomerTransactionId() { return customerTransactionId; }
    public void setCustomerTransactionId(Integer customerTransactionId) { this.customerTransactionId = customerTransactionId; }
    public ZonedDateTime getTransactionDate() { return transactionDate; }
    public void setTransactionDate(ZonedDateTime transactionDate) { this.transactionDate = transactionDate; }
    public Double getTransactionAmount() { return transactionAmount; }
    public void setTransactionAmount(Double transactionAmount) { this.transactionAmount = transactionAmount; }
    public Double getAmountExcludingTax() { return amountExcludingTax; }
    public void setAmountExcludingTax(Double amountExcludingTax) { this.amountExcludingTax = amountExcludingTax; }
    public Double getTaxAmount() { return taxAmount; }
    public void setTaxAmount(Double taxAmount) { this.taxAmount = taxAmount; }
    public Double getOutstandingBalance() { return outstandingBalance; }
    public void setOutstandingBalance(Double outstandingBalance) { this.outstandingBalance = outstandingBalance; }
    public ZonedDateTime getFinalizationDate() { return finalizationDate; }
    public void setFinalizationDate(ZonedDateTime finalizationDate) { this.finalizationDate = finalizationDate; }
    public Integer getIsFinalized() { return isFinalized; }
    public void setIsFinalized(Integer isFinalized) { this.isFinalized = isFinalized; }
    public ZonedDateTime getLastEditedWhen() { return lastEditedWhen; }
    public void setLastEditedWhen(ZonedDateTime lastEditedWhen) { this.lastEditedWhen = lastEditedWhen; }
    public Customer getCustomer() { return customer; }
    public void setCustomer(Customer customer) { this.customer = customer; }
}

@Node("OrderLine")
class OrderLine {

    @Id
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

    @Relationship(type = "STOCK_ITEMS", direction = Relationship.Direction.OUTGOING)
    private StockItem stockItem;
    
    @Relationship(type = "ORDERS", direction = Relationship.Direction.OUTGOING)
    private Order order;

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
    public StockItem getStockItem() { return stockItem; }
    public void setStockItem(StockItem stockItem) { this.stockItem = stockItem; }
    public Order getOrder() { return order; }
    public void setOrder(Order order) { this.order = order; }
}

@Node("StockItem")
class StockItem {

    @Id
    private String id;

    @Property("stockItemId")
    private Integer stockItemId;
    
    @Property("stockItemName")
    private String stockItemName;
    
    // Additional properties can map here based on schema...

    public StockItem() {
    }

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    public Integer getStockItemId() { return stockItemId; }
    public void setStockItemId(Integer stockItemId) { this.stockItemId = stockItemId; }
    public String getStockItemName() { return stockItemName; }
    public void setStockItemName(String stockItemName) { this.stockItemName = stockItemName; }
}

// --- Query Entrypoint ---

public class Neo4jQueryEntrypoint {
    
    public static BuildableStatement<ResultStatement> query() {
        ZonedDateTime from = ZonedDateTime.of(2014, 12, 20, 0, 0, 0, 0, ZoneOffset.UTC);
        ZonedDateTime to = ZonedDateTime.of(2014, 12, 31, 0, 0, 0, 0, ZoneOffset.UTC);
        
        var orderLine = Cypher.node("OrderLine").named("ol");
        var buildStatement = Cypher.match(orderLine)
            .where(orderLine.property("pickingCompletedWhen").gte(Cypher.parameter("from", from)))
            .and(orderLine.property("pickingCompletedWhen").lte(Cypher.parameter("to", to)))
            .returning(orderLine);
        
        return buildStatement;
    }

    public static void main(String[] args) throws Exception {
        String uri = "neo4j://localhost:7697";
        String user = "neo4j";
        String pass = "password";

        try (Driver driver = GraphDatabase.driver(uri, AuthTokens.basic(user, pass))) {
            Neo4jTemplate template = QueryRuntimeSupport.createNeo4jTemplate(driver);

            var ascQuery = ((OngoingReadingAndReturn)query()).orderBy(Cypher.sort(Cypher.property("ol", "orderLineId"), Direction.ASC)).limit(1).build();
            var descQuery = ((OngoingReadingAndReturn)query()).orderBy(Cypher.sort(Cypher.property("ol", "orderLineId"), Direction.DESC)).limit(1).build();
        
            OrderLine firstSample = template.findOne(ascQuery, ascQuery.getCatalog().getParameters(), OrderLine.class).orElse(null);
            OrderLine lastSample = template.findOne(descQuery, descQuery.getCatalog().getParameters(), OrderLine.class).orElse(null);

            var explainStatement = query().explain();
            var estimatedRowCount = driver.executableQuery(explainStatement.getCypher())
                .withParameters(explainStatement.getCatalog().getParameters()).execute().summary().plan()
                .arguments().getOrDefault("EstimatedRows", null);
            var statement = query().build();
            var resultMap = Map.of(
                "cypher", Map.of("cypherString", statement.getCypher(), "parameters", statement.getCatalog().getParameters()),
                "estimatedRowCount", estimatedRowCount != null ? estimatedRowCount.asDouble() : null,
                "firstSample", firstSample,
                "lastSample", lastSample
            );

            System.out.println(QueryRuntimeSupport.createJsonMapper().writeValueAsString(resultMap));
        }
    }
}
