package uom.services;

import java.math.*;
import java.time.*;
import java.time.format.*;
import java.time.temporal.*;
import java.util.*;
import java.util.Set;
import java.util.function.*;

import org.neo4j.cypherdsl.core.*;
import org.neo4j.cypherdsl.core.SortItem.*;
import org.neo4j.cypherdsl.core.StatementBuilder.*;
import org.neo4j.driver.*;
import org.slf4j.*;
import org.springframework.data.neo4j.core.*;
import org.springframework.data.neo4j.core.mapping.*;
import org.springframework.data.neo4j.core.schema.*;
import org.springframework.data.neo4j.core.schema.Node;
import org.springframework.data.neo4j.core.schema.Property;
import org.springframework.data.neo4j.core.schema.Relationship;
import org.springframework.data.neo4j.core.transaction.*;

import com.fasterxml.jackson.annotation.*;
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

    static Neo4jTemplate createNeo4jTemplate(Driver driver) {
        Neo4jClient client = Neo4jClient.create(driver);
        var mappingContext = new Neo4jMappingContext();
        mappingContext.setInitialEntitySet(Set.of(Order.class, Customer.class, CustomerTransaction.class, OrderLine.class));
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
@JsonIgnoreProperties({ "id" })
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
@JsonIgnoreProperties({ "id" })
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
@JsonIgnoreProperties({ "id" })
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
@JsonIgnoreProperties({ "id" })
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

record Query3Projection(Double taxRate, Long count) {
}

record Query5Projection(Integer orderLineId, Integer quantity) {
}

// --- Queries ---

final class Query1 {
    public static BuildableStatement<ResultStatement> query(boolean returnCount) {
        ZonedDateTime from = ZonedDateTime.of(2014, 12, 20, 0, 0, 0, 0, ZoneOffset.UTC);
        ZonedDateTime to = ZonedDateTime.of(2014, 12, 31, 0, 0, 0, 0, ZoneOffset.UTC);
        var orderLine = Cypher.node("OrderLine").named("ol");
        var partialStatement = Cypher.match(orderLine)
            .where(orderLine.property("pickingCompletedWhen").gte(Cypher.parameter("from", from)))
            .and(orderLine.property("pickingCompletedWhen").lte(Cypher.parameter("to", to)));
        if (returnCount) return partialStatement.returning(Cypher.count(orderLine));
        return partialStatement.returning(orderLine);
    }

    public static Map<String, Object> harness(Neo4jTemplate template) {
        long count = template.count(query(true).build());
        var q = query(false);
        Object first = null;
        if (count > 0) {
            var asc = ((OngoingReadingAndReturn)q).orderBy(Cypher.sort(Cypher.property("ol", "orderLineId"), Direction.ASC)).limit(1).build();
            first = template.findOne(asc, asc.getCatalog().getParameters(), OrderLine.class).orElse(null);
        }
        Object last = null;
        if (count > 1) {
            var desc = ((OngoingReadingAndReturn)q).orderBy(Cypher.sort(Cypher.property("ol", "orderLineId"), Direction.DESC)).limit(1).build();
            last = template.findOne(desc, desc.getCatalog().getParameters(), OrderLine.class).orElse(null);
        }
        var stmt = q.build();
        return Map.of("cypher", Map.of("query", stmt.getCypher(), "parameters", stmt.getCatalog().getParameters()), "count", count, "firstSample", first, "lastSample", last);
    }
}

final class Query2 {
    // Note: Avoid cartesian products, collect nodes and relationships and their properties into SDN aggregate roots/projections, see https://docs.spring.io/spring-data/neo4j/reference/appendix/custom-queries.html
    public static BuildableStatement<ResultStatement> query(boolean returnCount) {
        var order = Cypher.node("Order").named("o");
        var customer = Cypher.node("Customer").named("c");
        var rel1 = order.relationshipTo(customer, "CUSTOMERS").named("r1");
        var orderLine = Cypher.node("OrderLine").named("ol");
        var rel2 = order.relationshipFrom(orderLine, "ORDERS").named("r2");
        var transaction = Cypher.node("CustomerTransaction").named("ct");
        var rel3 = customer.relationshipFrom(transaction, "CUSTOMERS").named("r3");

        var orderLines = Cypher.name("orderLines");
        var rel2List = Cypher.name("rel2List");
        var customerTransactions = Cypher.name("customerTransactions");
        var rel3List = Cypher.name("rel3List");

        var partial = Cypher.match(rel2, rel1, rel3)
            .where(customer.property("customerId").isEqualTo(Cypher.literalOf(1)))
            .with(order, Cypher.collect(rel2).as(rel2List), Cypher.collect(orderLine).as(orderLines), rel1, customer, rel3, transaction)
            .with(order, rel2List, orderLines, rel1, customer, Cypher.collect(rel3).as(rel3List), Cypher.collect(transaction).as(customerTransactions));

        if (returnCount) return partial.returning(Cypher.count(order));
        return partial.returning(order.getRequiredSymbolicName(), rel2List, orderLines, rel1.getRequiredSymbolicName(), customer.getRequiredSymbolicName(), rel3List, customerTransactions);
    }

    public static Map<String, Object> harness(Neo4jTemplate template) {
        long count = template.count(query(true).build());
        var q = query(false);
        Object first = null;
        if (count > 0) {
            var asc = ((OngoingReadingAndReturn)query(false)).orderBy(Cypher.sort(Cypher.property("o", "orderId"), Direction.ASC)).limit(1).build();
            first = template.findOne(asc, asc.getCatalog().getParameters(), Order.class).orElse(null);
        }
        Object last = null;
        if (count > 1) {
            var desc = ((OngoingReadingAndReturn)query(false)).orderBy(Cypher.sort(Cypher.property("o", "orderId"), Direction.DESC)).limit(1).build();
            last = template.findOne(desc, desc.getCatalog().getParameters(), Order.class).orElse(null);
        }
        var stmt = q.build();
        return Map.of("cypher", Map.of("query", stmt.getCypher(), "parameters", stmt.getCatalog().getParameters()), "count", count, "firstSample", first, "lastSample", last);
    }
}

final class Query3 {
    public static BuildableStatement<ResultStatement> query(boolean returnCount) {
        var orderLine = Cypher.node("OrderLine").named("ol");
        var withClause = Cypher.match(orderLine)
            .with(orderLine.property("taxRate").as("taxRate"), Cypher.count(orderLine).as("count"));
        if (returnCount) return withClause.returning(Cypher.count(Cypher.asterisk()));
        return withClause.returning(Cypher.name("taxRate"), Cypher.name("count")).orderBy(Cypher.sort(Cypher.name("count"), Direction.DESC));
    }

    public static Map<String, Object> harness(Neo4jTemplate template, Neo4jClient client) {
        long count = template.count(query(true).build());
        Object first = null;
        if (count > 0) {
            var asc = Cypher.call(query(false).build()).returning(Cypher.asterisk()).orderBy(Cypher.sort(Cypher.name("taxRate"), Direction.ASC)).limit(1).build();
            var firstMap = client.query(asc.getCypher()).bindAll(asc.getCatalog().getParameters()).fetch().one().orElse(null);
            first = new Query3Projection((Double) firstMap.get("taxRate"), (Long) firstMap.get("count"));
        }
        Object last = null;
        if (count > 1) {
            var desc = Cypher.call(query(false).build()).returning(Cypher.asterisk()).orderBy(Cypher.sort(Cypher.name("taxRate"), Direction.DESC)).limit(1).build();
            var lastMap = client.query(desc.getCypher()).bindAll(desc.getCatalog().getParameters()).fetch().one().orElse(null);
            last = new Query3Projection((Double) lastMap.get("taxRate"), (Long) lastMap.get("count"));
        }
        var stmt = query(false).build();
        return Map.of("cypher", Map.of("query", stmt.getCypher(), "parameters", stmt.getCatalog().getParameters()), "count", count, "firstSample", first, "lastSample", last);
    }
}

final class Query4 {
    public static BuildableStatement<ResultStatement> query(boolean returnCount) {
        var orderLine = Cypher.node("OrderLine").named("ol");
        var partial = Cypher.match(orderLine);
        if (returnCount) return partial.returning(Cypher.count(orderLine));
        return partial.returning(orderLine).orderBy(Cypher.sort(orderLine.property("quantity"), Direction.DESC)).limit(50);
    }

    public static Map<String, Object> harness(Neo4jTemplate template) {
        long count = template.count(query(true).build());
        long actualCount = Math.min(count, 50);

        var q = query(false);
        Object first = null;
        if (actualCount > 0) {
            var asc = ((OngoingReadingAndReturn)q).orderBy(Cypher.sort(Cypher.property("ol", "orderLineId"), Direction.ASC)).limit(1).build();
            first = template.findOne(asc, asc.getCatalog().getParameters(), OrderLine.class).orElse(null);
        }
        Object last = null;
        if (actualCount > 1) {
            var desc = ((OngoingReadingAndReturn)q).orderBy(Cypher.sort(Cypher.property("ol", "orderLineId"), Direction.DESC)).limit(1).build();
            last = template.findOne(desc, desc.getCatalog().getParameters(), OrderLine.class).orElse(null);
        }
        var stmt = q.build();
        return Map.of("cypher", Map.of("query", stmt.getCypher(), "parameters", stmt.getCatalog().getParameters()), "count", actualCount, "firstSample", first, "lastSample", last);
    }
}

final class Query5 {
    public static BuildableStatement<ResultStatement> query(boolean returnCount) {
        var orderLine = Cypher.node("OrderLine").named("ol");
        if (returnCount) return Cypher.match(orderLine).returning(Cypher.count(orderLine));
        return Cypher.match(orderLine).returning(
            orderLine.property("orderLineId").as("orderLineId"),
            orderLine.property("quantity").as("quantity")
        );
    }

    public static Map<String, Object> harness(Neo4jTemplate template, Neo4jClient client) {
        long count = template.count(query(true).build());

        var q = query(false);
        Object first = null;
        if (count > 0) {
            var asc = ((OngoingReadingAndReturn)q)
                .orderBy(Cypher.sort(Cypher.property("ol", "orderLineId"), Direction.ASC))
                .limit(1).build();
            var firstMap = client.query(asc.getCypher())
                                 .bindAll(asc.getCatalog().getParameters())
                                 .fetch().one().orElse(null);
            if (firstMap != null) {
                Number id = (Number) firstMap.get("orderLineId");
                Number quantity = (Number) firstMap.get("quantity");
                first = new Query5Projection(id != null ? id.intValue() : null, quantity != null ? quantity.intValue() : null);
            }
        }
        Object last = null;
        if (count > 1) {
            var desc = ((OngoingReadingAndReturn)q)
                .orderBy(Cypher.sort(Cypher.property("ol", "orderLineId"), Direction.DESC))
                .limit(1).build();
            var lastMap = client.query(desc.getCypher())
                                .bindAll(desc.getCatalog().getParameters())
                                .fetch().one().orElse(null);
            if (lastMap != null) {
                Number id = (Number) lastMap.get("orderLineId");
                Number quantity = (Number) lastMap.get("quantity");
                last = new Query5Projection(id != null ? id.intValue() : null, quantity != null ? quantity.intValue() : null);
            }
        }
        var stmt = q.build();
        return Map.of("cypher", Map.of("query", stmt.getCypher(), "parameters", stmt.getCatalog().getParameters()), "count", count, "firstSample", first, "lastSample", last);
    }
}

// --- Query Entrypoint ---

public class Neo4jQueryEntrypoint {
    public static void main(String[] args) throws Exception {
        String uri = args.length > 0 ? args[0] : QueryRuntimeSupport.getNeo4jUri();
        String user = args.length > 1 ? args[1] : QueryRuntimeSupport.getNeo4jUsername();
        String pass = args.length > 2 ? args[2] : QueryRuntimeSupport.getNeo4jPassword();
        QueryRuntimeSupport.configureLogger();

        try (Driver driver = GraphDatabase.driver(uri, AuthTokens.basic(user, pass))) {
            Neo4jTemplate template = QueryRuntimeSupport.createNeo4jTemplate(driver);
            Neo4jClient client = Neo4jClient.create(driver);

            var results = new LinkedHashMap<String, Object>();
            List<Supplier<Map<String, Object>>> harnesses = List.of(
                () -> Query1.harness(template),
                () -> Query2.harness(template),
                () -> Query3.harness(template, client),
                () -> Query4.harness(template),
                () -> Query5.harness(template, client)
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
            QueryRuntimeSupport.createJsonMapper().writeValue(new java.io.File(System.getenv("NEO4J_RESULTS_PATH") + "/neo4j_results_" + System.currentTimeMillis() + ".json"), results);
        }
    }
}
