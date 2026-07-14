package uom.services;

import java.util.List;
import java.util.Map;

import org.neo4j.cypherdsl.core.Cypher;
import org.neo4j.cypherdsl.core.SortItem.Direction;
import org.neo4j.cypherdsl.core.StatementBuilder.ResultStatement;
import org.neo4j.cypherdsl.core.StatementBuilder.BuildableStatement;
import org.springframework.data.neo4j.core.Neo4jTemplate;

final class Query1 {
    public static BuildableStatement<ResultStatement> query() {
        String from = "2014-12-20 00:00:00.0000000";
        String to = "2014-12-31 23:59:59.9999999";
        var orderLine = Cypher.node("OrderLine").named("ol");
        return Cypher.match(orderLine)
            .where(orderLine.property("pickingCompletedWhen").gte(Cypher.parameter("from", from)))
            .and(orderLine.property("pickingCompletedWhen").lte(Cypher.parameter("to", to)))
            .returning(orderLine);
    }
}

final class Query2 {
    public static BuildableStatement<ResultStatement> query() {
        var orderLine = Cypher.node("OrderLine").named("ol");
        var order = Cypher.node("Order").named("o");
        return Cypher.match(orderLine.relationshipTo(order, "ORDERS"))
            .where(order.property("orderId").isEqualTo(Cypher.literalOf(26866)))
            .returning(orderLine);
    }
}

final class Query3 {
    public static BuildableStatement<ResultStatement> query() {
        var orderLine = Cypher.node("OrderLine").named("ol");
        return Cypher.match(orderLine)
            .where(orderLine.property("unitPrice").isEqualTo(Cypher.literalOf(25.0)))
            .returning(orderLine);
    }
}

final class Query4 {
    public static BuildableStatement<ResultStatement> query() {
        var orderLine = Cypher.node("OrderLine").named("ol");
        var order = Cypher.node("Order").named("o");
        var ids = List.of(1L, 10L, 100L, 1000L, 10000L);
        return Cypher.match(orderLine.relationshipTo(order, "ORDERS"))
            .where(order.property("orderId").in(Cypher.parameter("ids", ids)))
            .returning(orderLine);
    }
}

final class Query5 {
    public static BuildableStatement<ResultStatement> query() {
        var orderLine = Cypher.node("OrderLine").named("ol");
        return Cypher.match(orderLine)
            .where(orderLine.property("description").contains(Cypher.literalOf("C++")))
            .returning(orderLine);
    }
}