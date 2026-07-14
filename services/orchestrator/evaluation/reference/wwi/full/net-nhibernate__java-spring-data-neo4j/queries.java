final class Query1 {
    static Map<String, Object> harness(Neo4jTemplate template, Neo4jClient client) {
        var ol = Cypher.node("OrderLine").named("ol");
        var o = Cypher.node("Order").named("o");
        var rel = ol.relationshipTo(o, "ORDERS").named("r");
        var base = Cypher.match(rel)
            .where(o.property("orderId").isEqualTo(Cypher.literalOf(26866)))
            .returning(ol);
        var countStmt = Cypher.match(rel)
            .where(o.property("orderId").isEqualTo(Cypher.literalOf(26866)))
            .returning(Cypher.count(ol)).build();
        long count = template.count(countStmt);
        Object first = null;
        Object last = null;
        if (count > 0) {
            var asc = ((OngoingReadingAndReturn) base).orderBy(Cypher.sort(ol.property("orderLineId"), Direction.ASC)).limit(1).build();
            first = template.findOne(asc, asc.getCatalog().getParameters(), OrderLine.class).orElse(null);
        }
        if (count > 1) {
            var desc = ((OngoingReadingAndReturn) base).orderBy(Cypher.sort(ol.property("orderLineId"), Direction.DESC)).limit(1).build();
            last = template.findOne(desc, desc.getCatalog().getParameters(), OrderLine.class).orElse(null);
        }
        var stmt = base.build();
        Map<String, Object> result = new HashMap<>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        result.put("cypher", Map.of("query", stmt.getCypher(), "parameters", stmt.getCatalog().getParameters()));
        return result;
    }
}

final class Query2 {
    static Map<String, Object> harness(Neo4jTemplate template, Neo4jClient client) {
        var ol = Cypher.node("OrderLine").named("ol");
        var base = Cypher.match(ol)
            .where(ol.property("unitPrice").isEqualTo(Cypher.literalOf(25.0)))
            .returning(ol);
        var countStmt = Cypher.match(ol)
            .where(ol.property("unitPrice").isEqualTo(Cypher.literalOf(25.0)))
            .returning(Cypher.count(ol)).build();
        long count = template.count(countStmt);
        Object first = null;
        Object last = null;
        if (count > 0) {
            var asc = ((OngoingReadingAndReturn) base).orderBy(Cypher.sort(ol.property("orderLineId"), Direction.ASC)).limit(1).build();
            first = template.findOne(asc, asc.getCatalog().getParameters(), OrderLine.class).orElse(null);
        }
        if (count > 1) {
            var desc = ((OngoingReadingAndReturn) base).orderBy(Cypher.sort(ol.property("orderLineId"), Direction.DESC)).limit(1).build();
            last = template.findOne(desc, desc.getCatalog().getParameters(), OrderLine.class).orElse(null);
        }
        var stmt = base.build();
        Map<String, Object> result = new HashMap<>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        result.put("cypher", Map.of("query", stmt.getCypher(), "parameters", stmt.getCatalog().getParameters()));
        return result;
    }
}

final class Query3 {
    static Map<String, Object> harness(Neo4jTemplate template, Neo4jClient client) {
        var ol = Cypher.node("OrderLine").named("ol");
        var from = "2014-12-20 00:00:00.0000000";
        var to = "2014-12-31 00:00:00.0000000";
        var base = Cypher.match(ol)
            .where(ol.property("pickingCompletedWhen").gte(Cypher.parameter("from", from)))
            .and(ol.property("pickingCompletedWhen").lte(Cypher.parameter("to", to)))
            .returning(ol);
        var countStmt = Cypher.match(ol)
            .where(ol.property("pickingCompletedWhen").gte(Cypher.parameter("from", from)))
            .and(ol.property("pickingCompletedWhen").lte(Cypher.parameter("to", to)))
            .returning(Cypher.count(ol)).build();
        long count = template.count(countStmt);
        Object first = null;
        Object last = null;
        if (count > 0) {
            var asc = ((OngoingReadingAndReturn) base).orderBy(Cypher.sort(ol.property("orderLineId"), Direction.ASC)).limit(1).build();
            first = template.findOne(asc, asc.getCatalog().getParameters(), OrderLine.class).orElse(null);
        }
        if (count > 1) {
            var desc = ((OngoingReadingAndReturn) base).orderBy(Cypher.sort(ol.property("orderLineId"), Direction.DESC)).limit(1).build();
            last = template.findOne(desc, desc.getCatalog().getParameters(), OrderLine.class).orElse(null);
        }
        var stmt = base.build();
        Map<String, Object> result = new HashMap<>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        result.put("cypher", Map.of("query", stmt.getCypher(), "parameters", stmt.getCatalog().getParameters()));
        return result;
    }
}

final class Query4 {
    static Map<String, Object> harness(Neo4jTemplate template, Neo4jClient client) {
        var ol = Cypher.node("OrderLine").named("ol");
        var o = Cypher.node("Order").named("o");
        var rel = ol.relationshipTo(o, "ORDERS").named("r");
        var orderIds = List.of(1, 10, 100, 1000, 10000);
        var base = Cypher.match(rel)
            .where(o.property("orderId").in(Cypher.parameter("orderIds", orderIds)))
            .returning(ol);
        var countStmt = Cypher.match(rel)
            .where(o.property("orderId").in(Cypher.parameter("orderIds", orderIds)))
            .returning(Cypher.count(ol)).build();
        long count = template.count(countStmt);
        Object first = null;
        Object last = null;
        if (count > 0) {
            var asc = ((OngoingReadingAndReturn) base).orderBy(Cypher.sort(ol.property("orderLineId"), Direction.ASC)).limit(1).build();
            first = template.findOne(asc, asc.getCatalog().getParameters(), OrderLine.class).orElse(null);
        }
        if (count > 1) {
            var desc = ((OngoingReadingAndReturn) base).orderBy(Cypher.sort(ol.property("orderLineId"), Direction.DESC)).limit(1).build();
            last = template.findOne(desc, desc.getCatalog().getParameters(), OrderLine.class).orElse(null);
        }
        var stmt = base.build();
        Map<String, Object> result = new HashMap<>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        result.put("cypher", Map.of("query", stmt.getCypher(), "parameters", stmt.getCatalog().getParameters()));
        return result;
    }
}

final class Query5 {
    static Map<String, Object> harness(Neo4jTemplate template, Neo4jClient client) {
        var ol = Cypher.node("OrderLine").named("ol");
        var base = Cypher.match(ol)
            .where(ol.property("description").contains(Cypher.literalOf("C++")))
            .returning(ol);
        var countStmt = Cypher.match(ol)
            .where(ol.property("description").contains(Cypher.literalOf("C++")))
            .returning(Cypher.count(ol)).build();
        long count = template.count(countStmt);
        Object first = null;
        Object last = null;
        if (count > 0) {
            var asc = ((OngoingReadingAndReturn) base).orderBy(Cypher.sort(ol.property("orderLineId"), Direction.ASC)).limit(1).build();
            first = template.findOne(asc, asc.getCatalog().getParameters(), OrderLine.class).orElse(null);
        }
        if (count > 1) {
            var desc = ((OngoingReadingAndReturn) base).orderBy(Cypher.sort(ol.property("orderLineId"), Direction.DESC)).limit(1).build();
            last = template.findOne(desc, desc.getCatalog().getParameters(), OrderLine.class).orElse(null);
        }
        var stmt = base.build();
        Map<String, Object> result = new HashMap<>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        result.put("cypher", Map.of("query", stmt.getCypher(), "parameters", stmt.getCatalog().getParameters()));
        return result;
    }
}

final class Query6 {
    static Map<String, Object> harness(Neo4jTemplate template, Neo4jClient client) {
        var ol = Cypher.node("OrderLine").named("ol");
        var stmt = Cypher.match(ol)
            .returning(ol)
            .orderBy(Cypher.sort(ol.property("orderLineId"), Direction.ASC))
            .skip(1000)
            .limit(50)
            .build();
        List<OrderLine> rows = template.findAll(stmt, OrderLine.class);
        long count = rows.size();
        Object first = count > 0 ? rows.get(0) : null;
        Object last = count > 1 ? rows.get(rows.size() - 1) : null;
        Map<String, Object> result = new HashMap<>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        result.put("cypher", Map.of("query", stmt.getCypher(), "parameters", stmt.getCatalog().getParameters()));
        return result;
    }
}

final class Query7 {
    static Map<String, Object> harness(Neo4jTemplate template, Neo4jClient client) {
        var ol = Cypher.node("OrderLine").named("ol");
        var base = Cypher.match(ol)
            .with(ol.property("taxRate").as("taxRate"), Cypher.count(ol).as("count"))
            .returning(Cypher.name("taxRate"), Cypher.name("count"));
        var countStmt = Cypher.match(ol)
            .with(ol.property("taxRate").as("taxRate"), Cypher.count(ol).as("count"))
            .returning(Cypher.count(Cypher.asterisk())).build();
        long count = template.count(countStmt);
        Object first = null;
        Object last = null;
        if (count > 0) {
            var asc = Cypher.call(base.build()).returning(Cypher.asterisk())
                .orderBy(Cypher.sort(Cypher.name("taxRate"), Direction.ASC)).limit(1).build();
            var firstMap = client.query(asc.getCypher()).bindAll(asc.getCatalog().getParameters()).fetch().one().orElse(null);
            if (firstMap != null) {
                Number taxRateNum = (Number) firstMap.get("taxRate");
                Number countNum = (Number) firstMap.get("count");
                first = new TaxRateCount(taxRateNum != null ? taxRateNum.doubleValue() : null, countNum != null ? countNum.longValue() : null);
            }
        }
        if (count > 1) {
            var desc = Cypher.call(base.build()).returning(Cypher.asterisk())
                .orderBy(Cypher.sort(Cypher.name("taxRate"), Direction.DESC)).limit(1).build();
            var lastMap = client.query(desc.getCypher()).bindAll(desc.getCatalog().getParameters()).fetch().one().orElse(null);
            if (lastMap != null) {
                Number taxRateNum = (Number) lastMap.get("taxRate");
                Number countNum = (Number) lastMap.get("count");
                last = new TaxRateCount(taxRateNum != null ? taxRateNum.doubleValue() : null, countNum != null ? countNum.longValue() : null);
            }
        }
        var stmt = base.build();
        Map<String, Object> result = new HashMap<>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        result.put("cypher", Map.of("query", stmt.getCypher(), "parameters", stmt.getCatalog().getParameters()));
        return result;
    }
}

final class Query8 {
    static Map<String, Object> harness(Neo4jTemplate template, Neo4jClient client) {
        var ol = Cypher.node("OrderLine").named("ol");
        var stmt = Cypher.match(ol)
            .returning(Cypher.max(ol.property("unitPrice")).as("maxUnitPrice"))
            .build();
        var row = client.query(stmt.getCypher()).bindAll(stmt.getCatalog().getParameters()).fetch().one().orElse(null);
        Double max = null;
        if (row != null && row.get("maxUnitPrice") instanceof Number n) {
            max = n.doubleValue();
        }
        long count = max != null ? 1 : 0;
        Map<String, Object> result = new HashMap<>();
        result.put("count", count);
        result.put("firstSample", max);
        result.put("lastSample", null);
        result.put("cypher", Map.of("query", stmt.getCypher(), "parameters", stmt.getCatalog().getParameters()));
        return result;
    }
}

final class Query9 {
    static Map<String, Object> harness(Neo4jTemplate template, Neo4jClient client) {
        var ol = Cypher.node("OrderLine").named("ol");
        var stmt = Cypher.match(ol)
            .returning(Cypher.sum(Cypher.raw("ol.quantity * ol.unitPrice")).as("total"))
            .build();
        var row = client.query(stmt.getCypher()).bindAll(stmt.getCatalog().getParameters()).fetch().one().orElse(null);
        Double sum = null;
        if (row != null && row.get("total") instanceof Number n) {
            sum = n.doubleValue();
        }
        long count = sum != null ? 1 : 0;
        Map<String, Object> result = new HashMap<>();
        result.put("count", count);
        result.put("firstSample", sum);
        result.put("lastSample", null);
        result.put("cypher", Map.of("query", stmt.getCypher(), "parameters", stmt.getCatalog().getParameters()));
        return result;
    }
}

final class Query10 {
    static Map<String, Object> harness(Neo4jTemplate template, Neo4jClient client) {
        var o = Cypher.node("Order").named("o");
        var ol = Cypher.node("OrderLine").named("ol");
        var rel = ol.relationshipTo(o, "ORDERS").named("r");
        var stmt = Cypher.match(o)
            .where(o.property("orderId").isEqualTo(Cypher.literalOf(530)))
            .optionalMatch(rel)
            .with(o, Cypher.collect(rel).as("relList"), Cypher.collect(ol).as("orderLines"))
            .returning(o.getRequiredSymbolicName(), Cypher.name("relList"), Cypher.name("orderLines"))
            .build();
        Order order = template.findOne(stmt, stmt.getCatalog().getParameters(), Order.class).orElse(null);
        long count = order != null ? 1 : 0;
        Map<String, Object> result = new HashMap<>();
        result.put("count", count);
        result.put("firstSample", order);
        result.put("lastSample", null);
        result.put("cypher", Map.of("query", stmt.getCypher(), "parameters", stmt.getCatalog().getParameters()));
        return result;
    }
}

final class Query11 {
    static Map<String, Object> harness(Neo4jTemplate template, Neo4jClient client) {
        var o = Cypher.node("Order").named("o");
        var stmt = Cypher.match(o)
            .returning(o)
            .orderBy(
                Cypher.sort(o.property("expectedDeliveryDate"), Direction.ASC),
                Cypher.sort(o.property("orderId"), Direction.ASC))
            .limit(1000)
            .build();
        List<Order> rows = template.findAll(stmt, Order.class);
        List<OrderView> views = rows.stream()
            .map(order -> new OrderView(
                order.getOrderId(),
                order.getOrderDate(),
                order.getExpectedDeliveryDate(),
                order.getCustomerPurchaseOrderNumber(),
                order.getIsUndersupplyBackordered(),
                order.getPickingCompletedWhen(),
                order.getLastEditedWhen(),
                null))
            .toList();
        long count = views.size();
        Object first = null;
        Object last = null;
        if (count > 0) {
            var sorted = new ArrayList<>(views);
            sorted.sort(Comparator.comparing(OrderView::orderId));
            first = sorted.get(0);
            last = sorted.get(sorted.size() - 1);
        }
        Map<String, Object> result = new HashMap<>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        result.put("cypher", Map.of("query", stmt.getCypher(), "parameters", stmt.getCatalog().getParameters()));
        return result;
    }
}

final class Query12 {
    static Map<String, Object> harness(Neo4jTemplate template, Neo4jClient client) {
        var o = Cypher.node("Order").named("o");
        var stmt = Cypher.match(o)
            .returningDistinct(o.property("customerPurchaseOrderNumber").as("customerPurchaseOrderNumber"))
            .build();
        var rows = new ArrayList<>(client.query(stmt.getCypher())
            .bindAll(stmt.getCatalog().getParameters())
            .fetch().all());
        List<String> values = rows.stream()
            .map(row -> row.get("customerPurchaseOrderNumber") instanceof String s ? s : null)
            .toList();
        long count = values.size();
        Object first = null;
        Object last = null;
        if (count > 0) {
            var sorted = new ArrayList<>(values);
            sorted.sort(Comparator.nullsFirst(Comparator.naturalOrder()));
            first = sorted.get(0);
            last = sorted.get(sorted.size() - 1);
        }
        Map<String, Object> result = new HashMap<>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        result.put("cypher", Map.of("query", stmt.getCypher(), "parameters", stmt.getCatalog().getParameters()));
        return result;
    }
}

final class Query13 {
    static Map<String, Object> harness(Neo4jTemplate template, Neo4jClient client) {
        var p = Cypher.node("Person").named("p");
        var cf = Cypher.call("apoc.convert.fromJsonMap").withArgs(p.property("customFields")).asFunction();
        var base = Cypher.match(p)
            .where(p.property("customFields").isNotNull())
            .and(Cypher.property(cf, "Title").isEqualTo(Cypher.literalOf("Team Member")))
            .returning(p);
        var countStmt = Cypher.match(p)
            .where(p.property("customFields").isNotNull())
            .and(Cypher.property(cf, "Title").isEqualTo(Cypher.literalOf("Team Member")))
            .returning(Cypher.count(p)).build();
        long count = template.count(countStmt);
        Object first = null;
        Object last = null;
        if (count > 0) {
            var asc = ((OngoingReadingAndReturn) base).orderBy(Cypher.sort(p.property("personId"), Direction.ASC)).limit(1).build();
            first = template.findOne(asc, asc.getCatalog().getParameters(), Person.class).orElse(null);
        }
        if (count > 1) {
            var desc = ((OngoingReadingAndReturn) base).orderBy(Cypher.sort(p.property("personId"), Direction.DESC)).limit(1).build();
            last = template.findOne(desc, desc.getCatalog().getParameters(), Person.class).orElse(null);
        }
        var stmt = base.build();
        Map<String, Object> result = new HashMap<>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        result.put("cypher", Map.of("query", stmt.getCypher(), "parameters", stmt.getCatalog().getParameters()));
        return result;
    }
}

final class Query14 {
    static Map<String, Object> harness(Neo4jTemplate template, Neo4jClient client) {
        var p = Cypher.node("Person").named("p");
        var langs = Cypher.call("apoc.convert.fromJsonList").withArgs(p.property("otherLanguages")).asFunction();
        var base = Cypher.match(p)
            .where(p.property("otherLanguages").isNotNull())
            .and(Cypher.literalOf("Slovak").in(langs))
            .returning(p);
        var countStmt = Cypher.match(p)
            .where(p.property("otherLanguages").isNotNull())
            .and(Cypher.literalOf("Slovak").in(langs))
            .returning(Cypher.count(p)).build();
        long count = template.count(countStmt);
        Object first = null;
        Object last = null;
        if (count > 0) {
            var asc = ((OngoingReadingAndReturn) base).orderBy(Cypher.sort(p.property("personId"), Direction.ASC)).limit(1).build();
            first = template.findOne(asc, asc.getCatalog().getParameters(), Person.class).orElse(null);
        }
        if (count > 1) {
            var desc = ((OngoingReadingAndReturn) base).orderBy(Cypher.sort(p.property("personId"), Direction.DESC)).limit(1).build();
            last = template.findOne(desc, desc.getCatalog().getParameters(), Person.class).orElse(null);
        }
        var stmt = base.build();
        Map<String, Object> result = new HashMap<>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        result.put("cypher", Map.of("query", stmt.getCypher(), "parameters", stmt.getCatalog().getParameters()));
        return result;
    }
}

final class Query15 {
    static Map<String, Object> harness(Neo4jTemplate template, Neo4jClient client) {
        var s1 = Cypher.node("Supplier").named("s1");
        var s2 = Cypher.node("Supplier").named("s2");
        var firstStmt = Cypher.match(s1)
            .where(s1.property("supplierId").lt(Cypher.literalOf(5)))
            .returning(s1.property("supplierId").as("id")).build();
        var lastStmt = Cypher.match(s2)
            .where(s2.property("supplierId").gte(Cypher.literalOf(5)))
            .and(s2.property("supplierId").lte(Cypher.literalOf(10)))
            .returning(s2.property("supplierId").as("id")).build();
        var union = Cypher.union(firstStmt, lastStmt);
        var rows = new ArrayList<>(client.query(union.getCypher())
            .bindAll(union.getCatalog().getParameters())
            .fetch().all());
        rows.sort(Comparator.comparing(row -> ((Number) row.get("id")).intValue()));
        long count = rows.size();
        Object first = null;
        Object last = null;
        if (count > 0) {
            first = ((Number) rows.get(0).get("id")).intValue();
        }
        if (count > 1) {
            last = ((Number) rows.get(rows.size() - 1).get("id")).intValue();
        }
        Map<String, Object> result = new HashMap<>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        result.put("cypher", Map.of("query", union.getCypher(), "parameters", union.getCatalog().getParameters()));
        return result;
    }
}