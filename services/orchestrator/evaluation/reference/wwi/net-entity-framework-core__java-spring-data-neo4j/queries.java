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

public class Neo4jQueryService {

    public List<OrderLine> query1(Neo4jTemplate template) {
        String from = "2014-12-20 00:00:00.0000000";
        String to = "2014-12-31 23:59:59.9999999";
        var orderLine = Cypher.node("OrderLine").named("ol");
        var partialStatement = Cypher.match(orderLine)
            .where(orderLine.property("pickingCompletedWhen").gte(Cypher.parameter("from", from)))
            .and(orderLine.property("pickingCompletedWhen").lte(Cypher.parameter("to", to)));
        var stmt = partialStatement.returning(orderLine).build();
        return template.findAll(stmt, stmt.getCatalog().getParameters(), OrderLine.class);
    }

    public List<OrderLine> query2(Neo4jTemplate template) {
        var orderLine = Cypher.node("OrderLine").named("ol");
        var order = Cypher.node("Order").named("o");
        var rel = orderLine.relationshipTo(order, "ORDERS");
        var partial = Cypher.match(rel)
            .where(order.property("orderId").isEqualTo(Cypher.literalOf(26866)));
        var stmt = partial.returning(orderLine).build();
        return template.findAll(stmt, stmt.getCatalog().getParameters(), OrderLine.class);
    }

    public List<OrderLine> query3(Neo4jTemplate template) {
        var orderLine = Cypher.node("OrderLine").named("ol");
        var partial = Cypher.match(orderLine)
            .where(orderLine.property("unitPrice").isEqualTo(Cypher.literalOf(25.0)));
        var stmt = partial.returning(orderLine).build();
        return template.findAll(stmt, stmt.getCatalog().getParameters(), OrderLine.class);
    }

    public List<OrderLine> query4(Neo4jTemplate template) {
        var orderLine = Cypher.node("OrderLine").named("ol");
        var order = Cypher.node("Order").named("o");
        var rel = orderLine.relationshipTo(order, "ORDERS");
        var partial = Cypher.match(rel)
            .where(order.property("orderId").in(Cypher.parameter("ids", List.of(1, 10, 100, 1000, 10000))));
        var stmt = partial.returning(orderLine).build();
        return template.findAll(stmt, stmt.getCatalog().getParameters(), OrderLine.class);
    }

    public List<OrderLine> query5(Neo4jTemplate template) {
        var orderLine = Cypher.node("OrderLine").named("ol");
        var partial = Cypher.match(orderLine)
            .where(orderLine.property("description").contains(Cypher.literalOf("C++")));
        var stmt = partial.returning(orderLine).build();
        return template.findAll(stmt, stmt.getCatalog().getParameters(), OrderLine.class);
    }
}