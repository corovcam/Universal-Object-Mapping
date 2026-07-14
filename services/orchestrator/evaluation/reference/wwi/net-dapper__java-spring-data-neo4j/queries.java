package uom.services;

import java.util.List;
import java.util.Map;

import org.neo4j.cypherdsl.core.Cypher;
import org.neo4j.cypherdsl.core.StatementBuilder.ResultStatement;
import org.springframework.data.neo4j.core.Neo4jTemplate;

public class Neo4jQueryService {

    public List<OrderLine> query1(Neo4jTemplate template) {
        var orderLine = Cypher.node("OrderLine").named("ol");
        var fromParam = Cypher.parameter("from", "2014-12-20 00:00:00.0000000");
        var toParam = Cypher.parameter("to", "2014-12-31 23:59:59.9999999");
        var statement = Cypher.match(orderLine)
            .where(orderLine.property("pickingCompletedWhen").gte(fromParam))
            .and(orderLine.property("pickingCompletedWhen").lte(toParam))
            .returning(orderLine)
            .build();
        return template.findAll(statement, statement.getCatalog().getParameters(), OrderLine.class);
    }

    public List<OrderLine> query2(Neo4jTemplate template) {
        var orderLine = Cypher.node("OrderLine").named("ol");
        var order = Cypher.node("Order").named("o");
        var rel = orderLine.relationshipTo(order, "ORDERS");
        var statement = Cypher.match(rel)
            .where(order.property("orderId").isEqualTo(Cypher.parameter("orderId", 26866)))
            .returning(orderLine)
            .build();
        return template.findAll(statement, statement.getCatalog().getParameters(), OrderLine.class);
    }

    public List<OrderLine> query3(Neo4jTemplate template) {
        var orderLine = Cypher.node("OrderLine").named("ol");
        var statement = Cypher.match(orderLine)
            .where(orderLine.property("unitPrice").isEqualTo(Cypher.parameter("unitPrice", 25.0)))
            .returning(orderLine)
            .build();
        return template.findAll(statement, statement.getCatalog().getParameters(), OrderLine.class);
    }

    public List<OrderLine> query4(Neo4jTemplate template) {
        var orderLine = Cypher.node("OrderLine").named("ol");
        var order = Cypher.node("Order").named("o");
        var rel = orderLine.relationshipTo(order, "ORDERS");
        var ids = List.of(1L, 10L, 100L, 1000L, 10000L);
        var statement = Cypher.match(rel)
            .where(order.property("orderId").in(Cypher.parameter("ids", ids)))
            .returning(orderLine)
            .build();
        return template.findAll(statement, statement.getCatalog().getParameters(), OrderLine.class);
    }

    public List<OrderLine> query5(Neo4jTemplate template) {
        var orderLine = Cypher.node("OrderLine").named("ol");
        var statement = Cypher.match(orderLine)
            .where(orderLine.property("description").contains(Cypher.parameter("pattern", "C++")))
            .returning(orderLine)
            .build();
        return template.findAll(statement, statement.getCatalog().getParameters(), OrderLine.class);
    }
}