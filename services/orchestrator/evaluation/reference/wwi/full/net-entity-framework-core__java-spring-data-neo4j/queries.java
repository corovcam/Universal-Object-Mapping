import java.util.Map;
import java.util.LinkedHashMap;

import org.neo4j.cypherdsl.core.Cypher;
import org.neo4j.cypherdsl.core.SortItem.Direction;
import org.springframework.data.neo4j.core.Neo4jTemplate;
import org.springframework.data.neo4j.core.Neo4jClient;

final class Query1 {
    static Map<String, Object> harness(Neo4jTemplate template, Neo4jClient client) {
        var ol = Cypher.node("OrderLine").named("ol");
        var o = Cypher.node("Order").named("o");
        var base = Cypher.match(ol.relationshipTo(o, "ORDERS"))
                .where(o.property("orderId").isEqualTo(Cypher.literalOf(26866)));
        long count = template.count(base.returning(Cypher.count(ol)).build());
        Object first = null;
        Object last = null;
        if (count > 0) {
            var firstStmt = base.returning(ol)
                    .orderBy(Cypher.sort(ol.property("orderLineId"), Direction.ASC))
                    .limit(1)
                    .build();
            first = template.findOne(firstStmt, firstStmt.getCatalog().getParameters(), OrderLine.class).orElse(null);
        }
        if (count > 1) {
            var lastStmt = base.returning(ol)
                    .orderBy(Cypher.sort(ol.property("orderLineId"), Direction.DESC))
                    .limit(1)
                    .build();
            last = template.findOne(lastStmt, lastStmt.getCatalog().getParameters(), OrderLine.class).orElse(null);
        }
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
    }
}

import java.util.Map;
import java.util.LinkedHashMap;

import org.neo4j.cypherdsl.core.Cypher;
import org.neo4j.cypherdsl.core.SortItem.Direction;
import org.springframework.data.neo4j.core.Neo4jTemplate;
import org.springframework.data.neo4j.core.Neo4jClient;

final class Query2 {
    static Map<String, Object> harness(Neo4jTemplate template, Neo4jClient client) {
        var ol = Cypher.node("OrderLine").named("ol");
        var base = Cypher.match(ol)
                .where(ol.property("unitPrice").isEqualTo(Cypher.literalOf(25.0)));
        long count = template.count(base.returning(Cypher.count(ol)).build());
        Object first = null;
        Object last = null;
        if (count > 0) {
            var firstStmt = base.returning(ol)
                    .orderBy(Cypher.sort(ol.property("orderLineId"), Direction.ASC))
                    .limit(1)
                    .build();
            first = template.findOne(firstStmt, firstStmt.getCatalog().getParameters(), OrderLine.class).orElse(null);
        }
        if (count > 1) {
            var lastStmt = base.returning(ol)
                    .orderBy(Cypher.sort(ol.property("orderLineId"), Direction.DESC))
                    .limit(1)
                    .build();
            last = template.findOne(lastStmt, lastStmt.getCatalog().getParameters(), OrderLine.class).orElse(null);
        }
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
    }
}

import java.util.Map;
import java.util.LinkedHashMap;

import org.neo4j.cypherdsl.core.Cypher;
import org.neo4j.cypherdsl.core.SortItem.Direction;
import org.springframework.data.neo4j.core.Neo4jTemplate;
import org.springframework.data.neo4j.core.Neo4jClient;

final class Query3 {
    static Map<String, Object> harness(Neo4jTemplate template, Neo4jClient client) {
        var from = "2014-12-20 00:00:00.0000000";
        var to = "2014-12-31 00:00:00.0000000";
        var ol = Cypher.node("OrderLine").named("ol");
        var base = Cypher.match(ol)
                .where(ol.property("pickingCompletedWhen").isNotNull())
                .and(ol.property("pickingCompletedWhen").gte(Cypher.parameter("from", from)))
                .and(ol.property("pickingCompletedWhen").lte(Cypher.parameter("to", to)));
        long count = template.count(base.returning(Cypher.count(ol)).build());
        Object first = null;
        Object last = null;
        if (count > 0) {
            var firstStmt = base.returning(ol)
                    .orderBy(Cypher.sort(ol.property("orderLineId"), Direction.ASC))
                    .limit(1)
                    .build();
            first = template.findOne(firstStmt, firstStmt.getCatalog().getParameters(), OrderLine.class).orElse(null);
        }
        if (count > 1) {
            var lastStmt = base.returning(ol)
                    .orderBy(Cypher.sort(ol.property("orderLineId"), Direction.DESC))
                    .limit(1)
                    .build();
            last = template.findOne(lastStmt, lastStmt.getCatalog().getParameters(), OrderLine.class).orElse(null);
        }
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
    }
}

import java.util.List;
import java.util.Map;
import java.util.LinkedHashMap;

import org.neo4j.cypherdsl.core.Cypher;
import org.neo4j.cypherdsl.core.SortItem.Direction;
import org.springframework.data.neo4j.core.Neo4jTemplate;
import org.springframework.data.neo4j.core.Neo4jClient;

final class Query4 {
    static Map<String, Object> harness(Neo4jTemplate template, Neo4jClient client) {
        var orderIds = List.of(1, 10, 100, 1000, 10000);
        var ol = Cypher.node("OrderLine").named("ol");
        var o = Cypher.node("Order").named("o");
        var base = Cypher.match(ol.relationshipTo(o, "ORDERS"))
                .where(o.property("orderId").in(Cypher.parameter("orderIds", orderIds)));
        long count = template.count(base.returning(Cypher.count(ol)).build());
        Object first = null;
        Object last = null;
        if (count > 0) {
            var firstStmt = base.returning(ol)
                    .orderBy(Cypher.sort(ol.property("orderLineId"), Direction.ASC))
                    .limit(1)
                    .build();
            first = template.findOne(firstStmt, firstStmt.getCatalog().getParameters(), OrderLine.class).orElse(null);
        }
        if (count > 1) {
            var lastStmt = base.returning(ol)
                    .orderBy(Cypher.sort(ol.property("orderLineId"), Direction.DESC))
                    .limit(1)
                    .build();
            last = template.findOne(lastStmt, lastStmt.getCatalog().getParameters(), OrderLine.class).orElse(null);
        }
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
    }
}

import java.util.Map;
import java.util.LinkedHashMap;

import org.neo4j.cypherdsl.core.Cypher;
import org.neo4j.cypherdsl.core.SortItem.Direction;
import org.springframework.data.neo4j.core.Neo4jTemplate;
import org.springframework.data.neo4j.core.Neo4jClient;

final class Query5 {
    static Map<String, Object> harness(Neo4jTemplate template, Neo4jClient client) {
        var ol = Cypher.node("OrderLine").named("ol");
        var base = Cypher.match(ol)
                .where(ol.property("description").contains(Cypher.literalOf("C++")));
        long count = template.count(base.returning(Cypher.count(ol)).build());
        Object first = null;
        Object last = null;
        if (count > 0) {
            var firstStmt = base.returning(ol)
                    .orderBy(Cypher.sort(ol.property("orderLineId"), Direction.ASC))
                    .limit(1)
                    .build();
            first = template.findOne(firstStmt, firstStmt.getCatalog().getParameters(), OrderLine.class).orElse(null);
        }
        if (count > 1) {
            var lastStmt = base.returning(ol)
                    .orderBy(Cypher.sort(ol.property("orderLineId"), Direction.DESC))
                    .limit(1)
                    .build();
            last = template.findOne(lastStmt, lastStmt.getCatalog().getParameters(), OrderLine.class).orElse(null);
        }
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
    }
}

import java.util.List;
import java.util.Map;
import java.util.LinkedHashMap;

import org.neo4j.cypherdsl.core.Cypher;
import org.neo4j.cypherdsl.core.SortItem.Direction;
import org.springframework.data.neo4j.core.Neo4jTemplate;
import org.springframework.data.neo4j.core.Neo4jClient;

final class Query6 {
    static Map<String, Object> harness(Neo4jTemplate template, Neo4jClient client) {
        var ol = Cypher.node("OrderLine").named("ol");
        var totalStmt = Cypher.match(ol).returning(Cypher.count(ol)).build();
        long total = template.count(totalStmt);
        var pageStmt = Cypher.match(ol)
                .returning(ol)
                .orderBy(Cypher.sort(ol.property("orderLineId"), Direction.ASC))
                .skip(1000)
                .limit(50)
                .build();
        List<OrderLine> page = template.findAll(pageStmt, OrderLine.class);
        long actualCount = page.size();
        Object first = actualCount > 0 ? page.get(0) : null;
        Object last = actualCount > 1 ? page.get(page.size() - 1) : null;
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("count", actualCount);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
    }
}

import java.util.List;
import java.util.Map;
import java.util.LinkedHashMap;
import java.util.ArrayList;
import java.util.Comparator;

import org.neo4j.cypherdsl.core.Cypher;
import org.neo4j.cypherdsl.core.SortItem.Direction;
import org.springframework.data.neo4j.core.Neo4jTemplate;
import org.springframework.data.neo4j.core.Neo4jClient;

final class Query7 {
    record TaxRateCount(Double taxRate, Long count) {
    }

    static Map<String, Object> harness(Neo4jTemplate template, Neo4jClient client) {
        var ol = Cypher.node("OrderLine").named("ol");
        var stmt = Cypher.match(ol)
                .with(ol.property("taxRate").as("taxRate"), Cypher.count(ol).as("count"))
                .returning(Cypher.name("taxRate"), Cypher.name("count"))
                .orderBy(Cypher.sort(Cypher.name("count"), Direction.DESC))
                .build();
        var rows = client.query(stmt.getCypher())
                .bindAll(stmt.getCatalog().getParameters())
                .fetch()
                .all();
        long count = rows.size();
        Object first = null;
        Object last = null;
        if (count > 0) {
            List<Map<String, Object>> sorted = new ArrayList<>(rows);
            sorted.sort(Comparator.comparing((Map<String, Object> row) -> (Double) row.get("taxRate")));
            Map<String, Object> firstRow = sorted.get(0);
            Map<String, Object> lastRow = sorted.get(sorted.size() - 1);
            first = new TaxRateCount((Double) firstRow.get("taxRate"), (Long) firstRow.get("count"));
            last = new TaxRateCount((Double) lastRow.get("taxRate"), (Long) lastRow.get("count"));
        }
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
    }
}

import java.util.Map;
import java.util.LinkedHashMap;

import org.neo4j.cypherdsl.core.Cypher;
import org.springframework.data.neo4j.core.Neo4jTemplate;
import org.springframework.data.neo4j.core.Neo4jClient;

final class Query8 {
    static Map<String, Object> harness(Neo4jTemplate template, Neo4jClient client) {
        var ol = Cypher.node("OrderLine").named("ol");
        var stmt = Cypher.match(ol)
                .returning(Cypher.max(ol.property("unitPrice")).as("maxPrice"))
                .build();
        var row = client.query(stmt.getCypher())
                .bindAll(stmt.getCatalog().getParameters())
                .fetch()
                .one()
                .orElse(null);
        Double max = row != null ? (Double) row.get("maxPrice") : null;
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("count", max != null ? 1L : 0L);
        result.put("firstSample", max);
        result.put("lastSample", null);
        return result;
    }
}

import java.util.Map;
import java.util.LinkedHashMap;

import org.neo4j.cypherdsl.core.Cypher;
import org.springframework.data.neo4j.core.Neo4jTemplate;
import org.springframework.data.neo4j.core.Neo4jClient;

final class Query9 {
    static Map<String, Object> harness(Neo4jTemplate template, Neo4jClient client) {
        var ol = Cypher.node("OrderLine").named("ol");
        var stmt = Cypher.match(ol)
                .returning(Cypher.sum(ol.property("quantity").multiply(ol.property("unitPrice"))).as("total"))
                .build();
        var row = client.query(stmt.getCypher())
                .bindAll(stmt.getCatalog().getParameters())
                .fetch()
                .one()
                .orElse(null);
        Number total = row != null ? (Number) row.get("total") : null;
        Double totalValue = total != null ? total.doubleValue() : null;
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("count", totalValue != null ? 1L : 0L);
        result.put("firstSample", totalValue);
        result.put("lastSample", null);
        return result;
    }
}

import java.util.List;
import java.util.Map;
import java.util.LinkedHashMap;
import java.util.ArrayList;

import org.neo4j.cypherdsl.core.Cypher;
import org.springframework.data.neo4j.core.Neo4jTemplate;
import org.springframework.data.neo4j.core.Neo4jClient;

final class Query10 {
    static Map<String, Object> harness(Neo4jTemplate template, Neo4jClient client) {
        var o = Cypher.node("Order").named("o");
        var ol = Cypher.node("OrderLine").named("ol");
        var orderLinesExpr = Cypher.raw(
                "collect({orderLineId: ol.orderLineId, description: ol.description, quantity: ol.quantity, unitPrice: ol.unitPrice, taxRate: ol.taxRate, pickedQuantity: ol.pickedQuantity, pickingCompletedWhen: ol.pickingCompletedWhen, lastEditedWhen: ol.lastEditedWhen})");
        var stmt = Cypher.match(o)
                .where(o.property("orderId").isEqualTo(Cypher.literalOf(530)))
                .optionalMatch(ol.relationshipTo(o, "ORDERS"))
                .returning(
                        o.property("orderId").as("orderId"),
                        o.property("customerPurchaseOrderNumber").as("customerPurchaseOrderNumber"),
                        o.property("expectedDeliveryDate").as("expectedDeliveryDate"),
                        Cypher.toBoolean(o.property("isUndersupplyBackordered")).as("isUndersupplyBackordered"),
                        o.property("lastEditedWhen").as("lastEditedWhen"),
                        o.property("orderDate").as("orderDate"),
                        o.property("pickingCompletedWhen").as("pickingCompletedWhen"),
                        orderLinesExpr.as("orderLines"))
                .build();
        var row = client.query(stmt.getCypher())
                .bindAll(stmt.getCatalog().getParameters())
                .fetch()
                .one()
                .orElse(null);
        Map<String, Object> result = new LinkedHashMap<>();
        if (row == null) {
            result.put("count", 0L);
            result.put("firstSample", null);
            result.put("lastSample", null);
        } else {
            Map<String, Object> sample = new LinkedHashMap<>(row);
            Object lines = sample.get("orderLines");
            if (lines instanceof List<?>) {
                List<Map<String, Object>> cleaned = new ArrayList<>();
                for (Object item : (List<?>) lines) {
                    if (item instanceof Map<?, ?> mapItem && mapItem.get("orderLineId") != null) {
                        cleaned.add((Map<String, Object>) item);
                    }
                }
                sample.put("orderLines", cleaned);
            }
            result.put("count", 1L);
            result.put("firstSample", sample);
            result.put("lastSample", null);
        }
        return result;
    }
}

import java.util.List;
import java.util.Map;
import java.util.LinkedHashMap;
import java.util.ArrayList;

import org.neo4j.cypherdsl.core.Cypher;
import org.neo4j.cypherdsl.core.SortItem.Direction;
import org.springframework.data.neo4j.core.Neo4jTemplate;
import org.springframework.data.neo4j.core.Neo4jClient;

final class Query11 {
    static Map<String, Object> harness(Neo4jTemplate template, Neo4jClient client) {
        var o = Cypher.node("Order").named("o");
        var totalStmt = Cypher.match(o).returning(Cypher.count(o)).build();
        long total = template.count(totalStmt);
        var pageStmt = Cypher.match(o)
                .returning(
                        o.property("orderId").as("orderId"),
                        o.property("customerPurchaseOrderNumber").as("customerPurchaseOrderNumber"),
                        o.property("expectedDeliveryDate").as("expectedDeliveryDate"),
                        Cypher.toBoolean(o.property("isUndersupplyBackordered")).as("isUndersupplyBackordered"),
                        o.property("lastEditedWhen").as("lastEditedWhen"),
                        o.property("orderDate").as("orderDate"),
                        o.property("pickingCompletedWhen").as("pickingCompletedWhen"),
                        Cypher.raw("[]").as("orderLines"))
                .orderBy(
                        Cypher.sort(o.property("expectedDeliveryDate"), Direction.ASC),
                        Cypher.sort(o.property("orderId"), Direction.ASC))
                .limit(1000)
                .build();
        List<Map<String, Object>> rows = new ArrayList<>(
                client.query(pageStmt.getCypher())
                        .bindAll(pageStmt.getCatalog().getParameters())
                        .fetch()
                        .all());
        long actualCount = rows.size();
        Object first = actualCount > 0 ? rows.get(0) : null;
        Object last = actualCount > 1 ? rows.get(rows.size() - 1) : null;
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("count", actualCount);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
    }
}

import java.util.List;
import java.util.Map;
import java.util.LinkedHashMap;
import java.util.ArrayList;
import java.util.Comparator;

import org.neo4j.cypherdsl.core.Cypher;
import org.springframework.data.neo4j.core.Neo4jTemplate;
import org.springframework.data.neo4j.core.Neo4jClient;

final class Query12 {
    static Map<String, Object> harness(Neo4jTemplate template, Neo4jClient client) {
        var o = Cypher.node("Order").named("o");
        var stmt = Cypher.match(o)
                .returningDistinct(o.property("customerPurchaseOrderNumber").as("po"))
                .build();
        var rows = client.query(stmt.getCypher())
                .bindAll(stmt.getCatalog().getParameters())
                .fetch()
                .all();
        List<String> values = new ArrayList<>();
        for (Map<String, Object> row : rows) {
            values.add((String) row.get("po"));
        }
        values.sort(Comparator.nullsFirst(Comparator.naturalOrder()));
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("count", (long) values.size());
        result.put("firstSample", values.isEmpty() ? null : values.get(0));
        result.put("lastSample", values.size() > 1 ? values.get(values.size() - 1) : null);
        return result;
    }
}

import java.util.Map;
import java.util.LinkedHashMap;

import org.neo4j.cypherdsl.core.Cypher;
import org.neo4j.cypherdsl.core.SortItem.Direction;
import org.neo4j.cypherdsl.core.Statement;
import org.springframework.data.neo4j.core.Neo4jTemplate;
import org.springframework.data.neo4j.core.Neo4jClient;

final class Query13 {
    private static String toIsoString(String value) {
        if (value == null) {
            return null;
        }
        if (value.endsWith("Z")) {
            return value;
        }
        return value + ".000Z";
    }

    private static Map<String, Object> buildPersonSample(Neo4jClient client, Statement stmt) {
        var row = client.query(stmt.getCypher())
                .bindAll(stmt.getCatalog().getParameters())
                .fetch()
                .one()
                .orElse(null);
        if (row == null) {
            return null;
        }
        Map<String, Object> sample = new LinkedHashMap<>();
        Number personId = (Number) row.get("personId");
        sample.put("personId", personId != null ? personId.intValue() : null);
        sample.put("fullName", row.get("fullName"));
        sample.put("preferredName", row.get("preferredName"));
        sample.put("emailAddress", row.get("emailAddress"));
        Map<String, Object> customFields = new LinkedHashMap<>();
        customFields.put("hireDate", toIsoString((String) row.get("hireDate")));
        customFields.put("title", row.get("title"));
        customFields.put("otherLanguages", row.get("customOtherLanguages"));
        sample.put("customFields", customFields);
        sample.put("otherLanguages", row.get("otherLanguages"));
        return sample;
    }

    static Map<String, Object> harness(Neo4jTemplate template, Neo4jClient client) {
        var p = Cypher.node("Person").named("p");
        var customFields = Cypher.call("apoc.convert.fromJsonMap")
                .withArgs(p.property("customFields"))
                .asFunction();
        var languages = Cypher.call("apoc.convert.fromJsonList")
                .withArgs(p.property("otherLanguages"))
                .asFunction();
        var base = Cypher.match(p)
                .where(p.property("customFields").isNotNull())
                .and(Cypher.property(customFields, "Title").isEqualTo(Cypher.literalOf("Team Member")));
        long count = template.count(base.returning(Cypher.count(p)).build());
        Object first = null;
        Object last = null;
        if (count > 0) {
            var firstStmt = base.returning(
                            p.property("personId").as("personId"),
                            p.property("fullName").as("fullName"),
                            p.property("preferredName").as("preferredName"),
                            p.property("emailAddress").as("emailAddress"),
                            Cypher.property(customFields, "HireDate").as("hireDate"),
                            Cypher.property(customFields, "Title").as("title"),
                            Cypher.property(customFields, "OtherLanguages").as("customOtherLanguages"),
                            languages.as("otherLanguages"))
                    .orderBy(Cypher.sort(p.property("personId"), Direction.ASC))
                    .limit(1)
                    .build();
            first = buildPersonSample(client, firstStmt);
        }
        if (count > 1) {
            var lastStmt = base.returning(
                            p.property("personId").as("personId"),
                            p.property("fullName").as("fullName"),
                            p.property("preferredName").as("preferredName"),
                            p.property("emailAddress").as("emailAddress"),
                            Cypher.property(customFields, "HireDate").as("hireDate"),
                            Cypher.property(customFields, "Title").as("title"),
                            Cypher.property(customFields, "OtherLanguages").as("customOtherLanguages"),
                            languages.as("otherLanguages"))
                    .orderBy(Cypher.sort(p.property("personId"), Direction.DESC))
                    .limit(1)
                    .build();
            last = buildPersonSample(client, lastStmt);
        }
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
    }
}

import java.util.Map;
import java.util.LinkedHashMap;

import org.neo4j.cypherdsl.core.Cypher;
import org.neo4j.cypherdsl.core.SortItem.Direction;
import org.neo4j.cypherdsl.core.Statement;
import org.springframework.data.neo4j.core.Neo4jTemplate;
import org.springframework.data.neo4j.core.Neo4jClient;

final class Query14 {
    private static String toIsoString(String value) {
        if (value == null) {
            return null;
        }
        if (value.endsWith("Z")) {
            return value;
        }
        return value + ".000Z";
    }

    private static Map<String, Object> buildPersonSample(Neo4jClient client, Statement stmt) {
        var row = client.query(stmt.getCypher())
                .bindAll(stmt.getCatalog().getParameters())
                .fetch()
                .one()
                .orElse(null);
        if (row == null) {
            return null;
        }
        Map<String, Object> sample = new LinkedHashMap<>();
        Number personId = (Number) row.get("personId");
        sample.put("personId", personId != null ? personId.intValue() : null);
        sample.put("fullName", row.get("fullName"));
        sample.put("preferredName", row.get("preferredName"));
        sample.put("emailAddress", row.get("emailAddress"));
        Map<String, Object> customFields = new LinkedHashMap<>();
        customFields.put("hireDate", toIsoString((String) row.get("hireDate")));
        customFields.put("title", row.get("title"));
        customFields.put("otherLanguages", row.get("customOtherLanguages"));
        sample.put("customFields", customFields);
        sample.put("otherLanguages", row.get("otherLanguages"));
        return sample;
    }

    static Map<String, Object> harness(Neo4jTemplate template, Neo4jClient client) {
        var p = Cypher.node("Person").named("p");
        var customFields = Cypher.call("apoc.convert.fromJsonMap")
                .withArgs(p.property("customFields"))
                .asFunction();
        var languages = Cypher.call("apoc.convert.fromJsonList")
                .withArgs(p.property("otherLanguages"))
                .asFunction();
        var base = Cypher.match(p)
                .where(p.property("otherLanguages").isNotNull())
                .and(Cypher.literalOf("Slovak").in(languages));
        long count = template.count(base.returning(Cypher.count(p)).build());
        Object first = null;
        Object last = null;
        if (count > 0) {
            var firstStmt = base.returning(
                            p.property("personId").as("personId"),
                            p.property("fullName").as("fullName"),
                            p.property("preferredName").as("preferredName"),
                            p.property("emailAddress").as("emailAddress"),
                            Cypher.property(customFields, "HireDate").as("hireDate"),
                            Cypher.property(customFields, "Title").as("title"),
                            Cypher.property(customFields, "OtherLanguages").as("customOtherLanguages"),
                            languages.as("otherLanguages"))
                    .orderBy(Cypher.sort(p.property("personId"), Direction.ASC))
                    .limit(1)
                    .build();
            first = buildPersonSample(client, firstStmt);
        }
        if (count > 1) {
            var lastStmt = base.returning(
                            p.property("personId").as("personId"),
                            p.property("fullName").as("fullName"),
                            p.property("preferredName").as("preferredName"),
                            p.property("emailAddress").as("emailAddress"),
                            Cypher.property(customFields, "HireDate").as("hireDate"),
                            Cypher.property(customFields, "Title").as("title"),
                            Cypher.property(customFields, "OtherLanguages").as("customOtherLanguages"),
                            languages.as("otherLanguages"))
                    .orderBy(Cypher.sort(p.property("personId"), Direction.DESC))
                    .limit(1)
                    .build();
            last = buildPersonSample(client, lastStmt);
        }
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
    }
}

import java.util.List;
import java.util.Map;
import java.util.LinkedHashMap;
import java.util.ArrayList;

import org.neo4j.cypherdsl.core.Cypher;
import org.neo4j.cypherdsl.core.SortItem.Direction;
import org.springframework.data.neo4j.core.Neo4jTemplate;
import org.springframework.data.neo4j.core.Neo4jClient;

final class Query15 {
    static Map<String, Object> harness(Neo4jTemplate template, Neo4jClient client) {
        var s1 = Cypher.node("Supplier").named("s");
        var a = Cypher.match(s1)
                .where(s1.property("supplierId").lt(Cypher.literalOf(5)))
                .returning(s1.property("supplierId").as("supplierId"))
                .build();
        var s2 = Cypher.node("Supplier").named("s");
        var b = Cypher.match(s2)
                .where(s2.property("supplierId").gte(Cypher.literalOf(5))
                        .and(s2.property("supplierId").lte(Cypher.literalOf(10))))
                .returning(s2.property("supplierId").as("supplierId"))
                .build();
        var union = Cypher.union(a, b);
        var sorted = Cypher.call(union)
                .returning(Cypher.asterisk())
                .orderBy(Cypher.sort(Cypher.name("supplierId"), Direction.ASC))
                .build();
        var rows = client.query(sorted.getCypher())
                .bindAll(sorted.getCatalog().getParameters())
                .fetch()
                .all();
        List<Integer> ids = new ArrayList<>();
        for (Map<String, Object> row : rows) {
            Number n = (Number) row.get("supplierId");
            ids.add(n != null ? n.intValue() : null);
        }
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("count", (long) ids.size());
        result.put("firstSample", ids.isEmpty() ? null : ids.get(0));
        result.put("lastSample", ids.size() > 1 ? ids.get(ids.size() - 1) : null);
        return result;
    }
}