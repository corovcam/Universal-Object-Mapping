package uom.services.benchmarks.controller;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.http.ResponseEntity;
import org.springframework.web.client.RestTemplate;
import uom.services.benchmarks.dto.CompileRequest;
import uom.services.benchmarks.dto.CompilationResult;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT, properties = {
        "compilation.sandbox.dir=target/sandbox",
        "spring.mongodb.uri=mongodb://uom_readonly:uom_readonly@localhost:27027/uom",
        "spring.mongodb.database=uom",
        "spring.neo4j.uri=neo4j://localhost:7697",
        "spring.neo4j.authentication.username=neo4j",
        "spring.neo4j.authentication.password=password"
})
class CompilationControllerIntegrationTest {

    @LocalServerPort
    private int port;

    private final RestTemplate restTemplate;

    public CompilationControllerIntegrationTest() {
        this.restTemplate = new RestTemplate();
        this.restTemplate.setErrorHandler(new org.springframework.web.client.DefaultResponseErrorHandler() {
            @Override
            public boolean hasError(org.springframework.http.client.ClientHttpResponse response) {
                return false; // prevent RestTemplate from throwing exceptions on 4xx/5xx responses
            }
        });
    }

    private String url(String path) {
        return "http://localhost:" + port + path;
    }

    @Test
    void testCompileSingleClass() {
        String sourceCode = """
                import org.springframework.data.annotation.Id;
                import org.springframework.data.mongodb.core.mapping.Document;

                @Document(collection = "orders")
                class Order {
                    @Id
                    private String id;
                    private String customerName;

                    public Order() {}
                    public String getId() { return id; }
                    public void setId(String id) { this.id = id; }
                    public String getCustomerName() { return customerName; }
                    public void setCustomerName(String customerName) { this.customerName = customerName; }
                }""";

        CompileRequest request = new CompileRequest(sourceCode, "spring-data-mongodb", false);

        ResponseEntity<CompilationResult> response = restTemplate.postForEntity(
                url("/api/compiler/compile"), request, CompilationResult.class);

        assertThat(response.getStatusCode().is2xxSuccessful()).isTrue();
        assertThat(response.getBody()).isNotNull();
        assertThat(response.getBody().success()).isTrue();
        assertThat(response.getBody().message()).contains("Compilation successful");
    }

    @Test
    void testCompileMultiClassComplexSchema() {
        String sourceCode = """
                import java.math.BigDecimal;
                import java.time.LocalDate;
                import java.time.LocalDateTime;
                import java.util.ArrayList;
                import java.util.List;
                import org.springframework.data.annotation.Id;
                import org.springframework.data.mongodb.core.mapping.Document;
                import org.springframework.data.mongodb.core.mapping.Field;

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
                    private Customer customer;
                    public Order() {}
                    public String getId() { return id; }
                }

                class Customer {
                    private Integer customerId;
                    private String customerName;
                    private BigDecimal creditLimit;
                    private List<CustomerTransaction> customerTransactions = new ArrayList<>();
                    public Customer() {}
                }

                class CustomerTransaction {
                    private Integer customerTransactionId;
                    private BigDecimal transactionAmount;
                    public CustomerTransaction() {}
                }

                @Document(collection = "orderLines")
                class OrderLine {
                    @Id
                    private String id;
                    @Field("orderLineId")
                    private Integer orderLineId;
                    private Integer quantity;
                    private BigDecimal unitPrice;
                    private StockItem stockItem;
                    public OrderLine() {}
                }

                class StockItem {
                    private Integer stockItemId;
                    private String stockItemName;
                    public StockItem() {}
                }""";

        CompileRequest request = new CompileRequest(sourceCode, "spring-data-mongodb", false);

        ResponseEntity<CompilationResult> response = restTemplate.postForEntity(
                url("/api/compiler/compile"), request, CompilationResult.class);

        assertThat(response.getStatusCode().is2xxSuccessful()).isTrue();
        assertThat(response.getBody()).isNotNull();
        assertThat(response.getBody().success()).isTrue();
        assertThat(response.getBody().message()).contains("Compilation successful");
    }

    @Test
    void testCompileAndValidateLiveMongoDb() {
        String sourceCode = """
                import org.springframework.data.annotation.Id;
                import org.springframework.data.mongodb.core.mapping.Document;

                @Document(collection = "orders")
                class Order {
                    @Id
                    private String id;
                    public Order() {}
                }""";

        CompileRequest request = new CompileRequest(sourceCode, "spring-data-mongodb", true);

        // Note: This requires a live MongoDB instance to succeed completely cleanly.
        // We ensure the endpoint returns an OK status.
        ResponseEntity<CompilationResult> response = restTemplate.postForEntity(
                url("/api/compiler/compile"), request, CompilationResult.class);

        assertThat(response.getStatusCode().is2xxSuccessful()).isTrue();
    }

    @Test
    void testCompilationErrorCase() {
        String sourceCode = """
                import org.springframework.data.mongodb.core.mapping.Document;

                @Document(collection = "orders")
                class Order {
                    private UndefinedType foo;
                }""";

        CompileRequest request = new CompileRequest(sourceCode, "spring-data-mongodb", false);

        ResponseEntity<CompilationResult> response = restTemplate.postForEntity(
                url("/api/compiler/compile"), request, CompilationResult.class);

        assertThat(response.getStatusCode().is4xxClientError()).isTrue();
        assertThat(response.getBody()).isNotNull();
        assertThat(response.getBody().success()).isFalse();
        assertThat(response.getBody().message()).contains("Compilation failed");
        assertThat(response.getBody().errors()).isNotEmpty();
        assertThat(response.getBody().errors().get(0).message()).contains("cannot find symbol");
    }

    @Test
    void testMavenFallbackCompilation() {
        String sourceCode = """
                import org.springframework.data.annotation.Id;
                import org.springframework.data.mongodb.core.mapping.Document;

                @Document(collection = "orders")
                class Order {
                    @Id
                    private String id;
                    public Order() {}
                }""";

        CompileRequest request = new CompileRequest(sourceCode, "spring-data-mongodb", false);

        ResponseEntity<CompilationResult> response = restTemplate.postForEntity(
                url("/api/compiler/maven-compile"), request, CompilationResult.class);

        assertThat(response.getStatusCode().is2xxSuccessful()).isTrue();
    }

    @Test
    void testNeo4jCompilationAndValidation() {
        String sourceCode = """
                import org.springframework.data.neo4j.core.schema.Node;
                import org.springframework.data.neo4j.core.schema.Id;

                @Node("Person")
                class Person {
                    @Id
                    private String name;
                    public Person() {}
                }""";

        CompileRequest request = new CompileRequest(sourceCode, "spring-data-neo4j", true);

        ResponseEntity<CompilationResult> response = restTemplate.postForEntity(
                url("/api/compiler/compile"), request, CompilationResult.class);

        assertThat(response.getStatusCode().is2xxSuccessful()).isTrue();
    }
}
