final class Query1 {
    static BuildableStatement<ResultStatement> query(boolean returnCount) {
        var ol = Cypher.node("OrderLine").named("ol");
        var o = Cypher.node("Order").named("o");
        var si = Cypher.node("StockItem").named("si");
        var p = Cypher.node("Person").named("p");
        var partial = Cypher.match(ol.relationshipTo(o, "ORDERS"))
                .where(o.property("orderId").isEqualTo(Cypher.literalOf(26866)));
        if (returnCount) {
            return partial.returning(Cypher.count(ol).as("count"));
        }
        return partial.optionalMatch(ol.relationshipTo(si, "STOCK_ITEMS"))
                .optionalMatch(ol.relationshipTo(p, "PEOPLE"))
                .returning(
                        ol.property("orderLineId").as("orderLineId"),
                        o.property("orderId").as("orderId"),
                        si.property("stockItemId").as("stockItemId"),
                        ol.property("description").as("description"),
                        ol.property("quantity").as("quantity"),
                        ol.property("unitPrice").as("unitPrice"),
                        ol.property("taxRate").as("taxRate"),
                        ol.property("pickedQuantity").as("pickedQuantity"),
                        ol.property("pickingCompletedWhen").as("pickingCompletedWhen"),
                        p.property("personId").as("lastEditedBy"),
                        ol.property("lastEditedWhen").as("lastEditedWhen"));
    }

    static Integer toInteger(Object value) {
        return value == null ? null : ((Number) value).intValue();
    }

    static Double toDouble(Object value) {
        return value == null ? null : ((Number) value).doubleValue();
    }

    static OrderLineProjection mapRow(Map<String, Object> row) {
        if (row == null) {
            return null;
        }
        return new OrderLineProjection(
                toInteger(row.get("orderLineId")),
                toInteger(row.get("orderId")),
                toInteger(row.get("stockItemId")),
                (String) row.get("description"),
                toInteger(row.get("quantity")),
                toDouble(row.get("unitPrice")),
                toDouble(row.get("taxRate")),
                toInteger(row.get("pickedQuantity")),
                (String) row.get("pickingCompletedWhen"),
                toInteger(row.get("lastEditedBy")),
                (String) row.get("lastEditedWhen"));
    }

    static Map<String, Object> harness(Neo4jTemplate template, Neo4jClient client) {
        long count = template.count(query(true).build());
        var q = query(false);
        Object first = null;
        if (count > 0) {
            var asc = ((OngoingReadingAndReturn) q)
                    .orderBy(Cypher.sort(Cypher.property("ol", "orderLineId"), Direction.ASC))
                    .limit(1)
                    .build();
            first = mapRow(client.query(asc.getCypher())
                    .bindAll(asc.getCatalog().getParameters())
                    .fetch()
                    .one()
                    .orElse(null));
        }
        Object last = null;
        if (count > 1) {
            var desc = ((OngoingReadingAndReturn) q)
                    .orderBy(Cypher.sort(Cypher.property("ol", "orderLineId"), Direction.DESC))
                    .limit(1)
                    .build();
            last = mapRow(client.query(desc.getCypher())
                    .bindAll(desc.getCatalog().getParameters())
                    .fetch()
                    .one()
                    .orElse(null));
        }
        var stmt = q.build();
        Map<String, Object> result = new java.util.HashMap<>();
        result.put("cypher", Map.of("query", stmt.getCypher(), "parameters", stmt.getCatalog().getParameters()));
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
    }
}

final class Query2 {
    static BuildableStatement<ResultStatement> query(boolean returnCount) {
        var ol = Cypher.node("OrderLine").named("ol");
        var o = Cypher.node("Order").named("o");
        var si = Cypher.node("StockItem").named("si");
        var p = Cypher.node("Person").named("p");
        var partial = Cypher.match(ol)
                .where(ol.property("unitPrice").isEqualTo(Cypher.literalOf(25.0)));
        if (returnCount) {
            return partial.returning(Cypher.count(ol).as("count"));
        }
        return partial.optionalMatch(ol.relationshipTo(o, "ORDERS"))
                .optionalMatch(ol.relationshipTo(si, "STOCK_ITEMS"))
                .optionalMatch(ol.relationshipTo(p, "PEOPLE"))
                .returning(
                        ol.property("orderLineId").as("orderLineId"),
                        o.property("orderId").as("orderId"),
                        si.property("stockItemId").as("stockItemId"),
                        ol.property("description").as("description"),
                        ol.property("quantity").as("quantity"),
                        ol.property("unitPrice").as("unitPrice"),
                        ol.property("taxRate").as("taxRate"),
                        ol.property("pickedQuantity").as("pickedQuantity"),
                        ol.property("pickingCompletedWhen").as("pickingCompletedWhen"),
                        p.property("personId").as("lastEditedBy"),
                        ol.property("lastEditedWhen").as("lastEditedWhen"));
    }

    static Integer toInteger(Object value) {
        return value == null ? null : ((Number) value).intValue();
    }

    static Double toDouble(Object value) {
        return value == null ? null : ((Number) value).doubleValue();
    }

    static OrderLineProjection mapRow(Map<String, Object> row) {
        if (row == null) {
            return null;
        }
        return new OrderLineProjection(
                toInteger(row.get("orderLineId")),
                toInteger(row.get("orderId")),
                toInteger(row.get("stockItemId")),
                (String) row.get("description"),
                toInteger(row.get("quantity")),
                toDouble(row.get("unitPrice")),
                toDouble(row.get("taxRate")),
                toInteger(row.get("pickedQuantity")),
                (String) row.get("pickingCompletedWhen"),
                toInteger(row.get("lastEditedBy")),
                (String) row.get("lastEditedWhen"));
    }

    static Map<String, Object> harness(Neo4jTemplate template, Neo4jClient client) {
        long count = template.count(query(true).build());
        var q = query(false);
        Object first = null;
        if (count > 0) {
            var asc = ((OngoingReadingAndReturn) q)
                    .orderBy(Cypher.sort(Cypher.property("ol", "orderLineId"), Direction.ASC))
                    .limit(1)
                    .build();
            first = mapRow(client.query(asc.getCypher())
                    .bindAll(asc.getCatalog().getParameters())
                    .fetch()
                    .one()
                    .orElse(null));
        }
        Object last = null;
        if (count > 1) {
            var desc = ((OngoingReadingAndReturn) q)
                    .orderBy(Cypher.sort(Cypher.property("ol", "orderLineId"), Direction.DESC))
                    .limit(1)
                    .build();
            last = mapRow(client.query(desc.getCypher())
                    .bindAll(desc.getCatalog().getParameters())
                    .fetch()
                    .one()
                    .orElse(null));
        }
        var stmt = q.build();
        Map<String, Object> result = new java.util.HashMap<>();
        result.put("cypher", Map.of("query", stmt.getCypher(), "parameters", stmt.getCatalog().getParameters()));
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
    }
}

final class Query3 {
    static BuildableStatement<ResultStatement> query(boolean returnCount) {
        var from = "2014-12-20 00:00:00.0000000";
        var to = "2014-12-31 00:00:00.0000000";
        var ol = Cypher.node("OrderLine").named("ol");
        var o = Cypher.node("Order").named("o");
        var si = Cypher.node("StockItem").named("si");
        var p = Cypher.node("Person").named("p");
        var partial = Cypher.match(ol)
                .where(ol.property("pickingCompletedWhen").gte(Cypher.parameter("from", from)))
                .and(ol.property("pickingCompletedWhen").lte(Cypher.parameter("to", to)));
        if (returnCount) {
            return partial.returning(Cypher.count(ol).as("count"));
        }
        return partial.optionalMatch(ol.relationshipTo(o, "ORDERS"))
                .optionalMatch(ol.relationshipTo(si, "STOCK_ITEMS"))
                .optionalMatch(ol.relationshipTo(p, "PEOPLE"))
                .returning(
                        ol.property("orderLineId").as("orderLineId"),
                        o.property("orderId").as("orderId"),
                        si.property("stockItemId").as("stockItemId"),
                        ol.property("description").as("description"),
                        ol.property("quantity").as("quantity"),
                        ol.property("unitPrice").as("unitPrice"),
                        ol.property("taxRate").as("taxRate"),
                        ol.property("pickedQuantity").as("pickedQuantity"),
                        ol.property("pickingCompletedWhen").as("pickingCompletedWhen"),
                        p.property("personId").as("lastEditedBy"),
                        ol.property("lastEditedWhen").as("lastEditedWhen"));
    }

    static Integer toInteger(Object value) {
        return value == null ? null : ((Number) value).intValue();
    }

    static Double toDouble(Object value) {
        return value == null ? null : ((Number) value).doubleValue();
    }

    static OrderLineProjection mapRow(Map<String, Object> row) {
        if (row == null) {
            return null;
        }
        return new OrderLineProjection(
                toInteger(row.get("orderLineId")),
                toInteger(row.get("orderId")),
                toInteger(row.get("stockItemId")),
                (String) row.get("description"),
                toInteger(row.get("quantity")),
                toDouble(row.get("unitPrice")),
                toDouble(row.get("taxRate")),
                toInteger(row.get("pickedQuantity")),
                (String) row.get("pickingCompletedWhen"),
                toInteger(row.get("lastEditedBy")),
                (String) row.get("lastEditedWhen"));
    }

    static Map<String, Object> harness(Neo4jTemplate template, Neo4jClient client) {
        long count = template.count(query(true).build());
        var q = query(false);
        Object first = null;
        if (count > 0) {
            var asc = ((OngoingReadingAndReturn) q)
                    .orderBy(Cypher.sort(Cypher.property("ol", "orderLineId"), Direction.ASC))
                    .limit(1)
                    .build();
            first = mapRow(client.query(asc.getCypher())
                    .bindAll(asc.getCatalog().getParameters())
                    .fetch()
                    .one()
                    .orElse(null));
        }
        Object last = null;
        if (count > 1) {
            var desc = ((OngoingReadingAndReturn) q)
                    .orderBy(Cypher.sort(Cypher.property("ol", "orderLineId"), Direction.DESC))
                    .limit(1)
                    .build();
            last = mapRow(client.query(desc.getCypher())
                    .bindAll(desc.getCatalog().getParameters())
                    .fetch()
                    .one()
                    .orElse(null));
        }
        var stmt = q.build();
        Map<String, Object> result = new java.util.HashMap<>();
        result.put("cypher", Map.of("query", stmt.getCypher(), "parameters", stmt.getCatalog().getParameters()));
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
    }
}

final class Query4 {
    static BuildableStatement<ResultStatement> query(boolean returnCount) {
        var ids = java.util.List.of(1, 10, 100, 1000, 10000);
        var ol = Cypher.node("OrderLine").named("ol");
        var o = Cypher.node("Order").named("o");
        var si = Cypher.node("StockItem").named("si");
        var p = Cypher.node("Person").named("p");
        var partial = Cypher.match(ol.relationshipTo(o, "ORDERS"))
                .where(o.property("orderId").in(Cypher.parameter("ids", ids)));
        if (returnCount) {
            return partial.returning(Cypher.count(ol).as("count"));
        }
        return partial.optionalMatch(ol.relationshipTo(si, "STOCK_ITEMS"))
                .optionalMatch(ol.relationshipTo(p, "PEOPLE"))
                .returning(
                        ol.property("orderLineId").as("orderLineId"),
                        o.property("orderId").as("orderId"),
                        si.property("stockItemId").as("stockItemId"),
                        ol.property("description").as("description"),
                        ol.property("quantity").as("quantity"),
                        ol.property("unitPrice").as("unitPrice"),
                        ol.property("taxRate").as("taxRate"),
                        ol.property("pickedQuantity").as("pickedQuantity"),
                        ol.property("pickingCompletedWhen").as("pickingCompletedWhen"),
                        p.property("personId").as("lastEditedBy"),
                        ol.property("lastEditedWhen").as("lastEditedWhen"));
    }

    static Integer toInteger(Object value) {
        return value == null ? null : ((Number) value).intValue();
    }

    static Double toDouble(Object value) {
        return value == null ? null : ((Number) value).doubleValue();
    }

    static OrderLineProjection mapRow(Map<String, Object> row) {
        if (row == null) {
            return null;
        }
        return new OrderLineProjection(
                toInteger(row.get("orderLineId")),
                toInteger(row.get("orderId")),
                toInteger(row.get("stockItemId")),
                (String) row.get("description"),
                toInteger(row.get("quantity")),
                toDouble(row.get("unitPrice")),
                toDouble(row.get("taxRate")),
                toInteger(row.get("pickedQuantity")),
                (String) row.get("pickingCompletedWhen"),
                toInteger(row.get("lastEditedBy")),
                (String) row.get("lastEditedWhen"));
    }

    static Map<String, Object> harness(Neo4jTemplate template, Neo4jClient client) {
        long count = template.count(query(true).build());
        var q = query(false);
        Object first = null;
        if (count > 0) {
            var asc = ((OngoingReadingAndReturn) q)
                    .orderBy(Cypher.sort(Cypher.property("ol", "orderLineId"), Direction.ASC))
                    .limit(1)
                    .build();
            first = mapRow(client.query(asc.getCypher())
                    .bindAll(asc.getCatalog().getParameters())
                    .fetch()
                    .one()
                    .orElse(null));
        }
        Object last = null;
        if (count > 1) {
            var desc = ((OngoingReadingAndReturn) q)
                    .orderBy(Cypher.sort(Cypher.property("ol", "orderLineId"), Direction.DESC))
                    .limit(1)
                    .build();
            last = mapRow(client.query(desc.getCypher())
                    .bindAll(desc.getCatalog().getParameters())
                    .fetch()
                    .one()
                    .orElse(null));
        }
        var stmt = q.build();
        Map<String, Object> result = new java.util.HashMap<>();
        result.put("cypher", Map.of("query", stmt.getCypher(), "parameters", stmt.getCatalog().getParameters()));
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
    }
}

final class Query5 {
    static BuildableStatement<ResultStatement> query(boolean returnCount) {
        var ol = Cypher.node("OrderLine").named("ol");
        var o = Cypher.node("Order").named("o");
        var si = Cypher.node("StockItem").named("si");
        var p = Cypher.node("Person").named("p");
        var partial = Cypher.match(ol)
                .where(ol.property("description").contains(Cypher.literalOf("C++")));
        if (returnCount) {
            return partial.returning(Cypher.count(ol).as("count"));
        }
        return partial.optionalMatch(ol.relationshipTo(o, "ORDERS"))
                .optionalMatch(ol.relationshipTo(si, "STOCK_ITEMS"))
                .optionalMatch(ol.relationshipTo(p, "PEOPLE"))
                .returning(
                        ol.property("orderLineId").as("orderLineId"),
                        o.property("orderId").as("orderId"),
                        si.property("stockItemId").as("stockItemId"),
                        ol.property("description").as("description"),
                        ol.property("quantity").as("quantity"),
                        ol.property("unitPrice").as("unitPrice"),
                        ol.property("taxRate").as("taxRate"),
                        ol.property("pickedQuantity").as("pickedQuantity"),
                        ol.property("pickingCompletedWhen").as("pickingCompletedWhen"),
                        p.property("personId").as("lastEditedBy"),
                        ol.property("lastEditedWhen").as("lastEditedWhen"));
    }

    static Integer toInteger(Object value) {
        return value == null ? null : ((Number) value).intValue();
    }

    static Double toDouble(Object value) {
        return value == null ? null : ((Number) value).doubleValue();
    }

    static OrderLineProjection mapRow(Map<String, Object> row) {
        if (row == null) {
            return null;
        }
        return new OrderLineProjection(
                toInteger(row.get("orderLineId")),
                toInteger(row.get("orderId")),
                toInteger(row.get("stockItemId")),
                (String) row.get("description"),
                toInteger(row.get("quantity")),
                toDouble(row.get("unitPrice")),
                toDouble(row.get("taxRate")),
                toInteger(row.get("pickedQuantity")),
                (String) row.get("pickingCompletedWhen"),
                toInteger(row.get("lastEditedBy")),
                (String) row.get("lastEditedWhen"));
    }

    static Map<String, Object> harness(Neo4jTemplate template, Neo4jClient client) {
        long count = template.count(query(true).build());
        var q = query(false);
        Object first = null;
        if (count > 0) {
            var asc = ((OngoingReadingAndReturn) q)
                    .orderBy(Cypher.sort(Cypher.property("ol", "orderLineId"), Direction.ASC))
                    .limit(1)
                    .build();
            first = mapRow(client.query(asc.getCypher())
                    .bindAll(asc.getCatalog().getParameters())
                    .fetch()
                    .one()
                    .orElse(null));
        }
        Object last = null;
        if (count > 1) {
            var desc = ((OngoingReadingAndReturn) q)
                    .orderBy(Cypher.sort(Cypher.property("ol", "orderLineId"), Direction.DESC))
                    .limit(1)
                    .build();
            last = mapRow(client.query(desc.getCypher())
                    .bindAll(desc.getCatalog().getParameters())
                    .fetch()
                    .one()
                    .orElse(null));
        }
        var stmt = q.build();
        Map<String, Object> result = new java.util.HashMap<>();
        result.put("cypher", Map.of("query", stmt.getCypher(), "parameters", stmt.getCatalog().getParameters()));
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
    }
}

final class Query6 {
    static BuildableStatement<ResultStatement> query(boolean returnCount) {
        var ol = Cypher.node("OrderLine").named("ol");
        if (returnCount) {
            return Cypher.match(ol).returning(Cypher.count(ol).as("count"));
        }
        var page = Cypher.match(ol)
                .returning(ol)
                .orderBy(Cypher.sort(ol.property("orderLineId"), Direction.ASC))
                .skip(1000)
                .limit(50)
                .build();
        var o = Cypher.node("Order").named("o");
        var si = Cypher.node("StockItem").named("si");
        var p = Cypher.node("Person").named("p");
        return Cypher.call(page)
                .optionalMatch(ol.relationshipTo(o, "ORDERS"))
                .optionalMatch(ol.relationshipTo(si, "STOCK_ITEMS"))
                .optionalMatch(ol.relationshipTo(p, "PEOPLE"))
                .returning(
                        ol.property("orderLineId").as("orderLineId"),
                        o.property("orderId").as("orderId"),
                        si.property("stockItemId").as("stockItemId"),
                        ol.property("description").as("description"),
                        ol.property("quantity").as("quantity"),
                        ol.property("unitPrice").as("unitPrice"),
                        ol.property("taxRate").as("taxRate"),
                        ol.property("pickedQuantity").as("pickedQuantity"),
                        ol.property("pickingCompletedWhen").as("pickingCompletedWhen"),
                        p.property("personId").as("lastEditedBy"),
                        ol.property("lastEditedWhen").as("lastEditedWhen"));
    }

    static Integer toInteger(Object value) {
        return value == null ? null : ((Number) value).intValue();
    }

    static Double toDouble(Object value) {
        return value == null ? null : ((Number) value).doubleValue();
    }

    static OrderLineProjection mapRow(Map<String, Object> row) {
        if (row == null) {
            return null;
        }
        return new OrderLineProjection(
                toInteger(row.get("orderLineId")),
                toInteger(row.get("orderId")),
                toInteger(row.get("stockItemId")),
                (String) row.get("description"),
                toInteger(row.get("quantity")),
                toDouble(row.get("unitPrice")),
                toDouble(row.get("taxRate")),
                toInteger(row.get("pickedQuantity")),
                (String) row.get("pickingCompletedWhen"),
                toInteger(row.get("lastEditedBy")),
                (String) row.get("lastEditedWhen"));
    }

    static Map<String, Object> harness(Neo4jTemplate template, Neo4jClient client) {
        long total = template.count(query(true).build());
        long actualCount = Math.min(total, 50);
        var q = query(false);
        Object first = null;
        if (actualCount > 0) {
            var asc = ((OngoingReadingAndReturn) q)
                    .orderBy(Cypher.sort(Cypher.property("ol", "orderLineId"), Direction.ASC))
                    .limit(1).build();
            first = mapRow(client.query(asc.getCypher())
                    .bindAll(asc.getCatalog().getParameters())
                    .fetch()
                    .one()
                    .orElse(null));
        }
        Object last = null;
        if (actualCount > 1) {
            var desc = ((OngoingReadingAndReturn) q)
                    .orderBy(Cypher.sort(Cypher.property("ol", "orderLineId"), Direction.DESC))
                    .limit(1).build();
            last = mapRow(client.query(desc.getCypher())
                    .bindAll(desc.getCatalog().getParameters())
                    .fetch()
                    .one()
                    .orElse(null));
        }
        var stmt = q.build();
        Map<String, Object> result = new java.util.HashMap<>();
        result.put("cypher", Map.of("query", stmt.getCypher(), "parameters", stmt.getCatalog().getParameters()));
        result.put("count", actualCount);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
    }
}

final class Query7 {
    static BuildableStatement<ResultStatement> query(boolean returnCount) {
        var ol = Cypher.node("OrderLine").named("ol");
        var withClause = Cypher.match(ol)
                .with(ol.property("taxRate").as("taxRate"), Cypher.count(ol).as("count"));
        if (returnCount) return withClause.returning(Cypher.count(Cypher.asterisk()));
        return withClause.returning(Cypher.name("taxRate"), Cypher.name("count"))
                .orderBy(Cypher.sort(Cypher.name("count"), Direction.DESC));
    }

    static TaxRateCount mapRow(Map<String, Object> row) {
        if (row == null) return null;
        Number taxRate = (Number) row.get("taxRate");
        Number count = (Number) row.get("count");
        return new TaxRateCount(taxRate != null ? taxRate.doubleValue() : null,
                                count != null ? count.longValue() : null);
    }

    static Map<String, Object> harness(Neo4jTemplate template, Neo4jClient client) {
        long count = template.count(query(true).build());
        Object first = null;
        if (count > 0) {
            var asc = Cypher.call(query(false).build()).returning(Cypher.asterisk())
                    .orderBy(Cypher.sort(Cypher.name("taxRate"), Direction.ASC))
                    .limit(1).build();
            var firstMap = client.query(asc.getCypher()).bindAll(asc.getCatalog().getParameters()).fetch().one().orElse(null);
            first = mapRow(firstMap);
        }
        Object last = null;
        if (count > 1) {
            var desc = Cypher.call(query(false).build()).returning(Cypher.asterisk())
                    .orderBy(Cypher.sort(Cypher.name("taxRate"), Direction.DESC))
                    .limit(1).build();
            var lastMap = client.query(desc.getCypher()).bindAll(desc.getCatalog().getParameters()).fetch().one().orElse(null);
            last = mapRow(lastMap);
        }
        var stmt = query(false).build();
        Map<String, Object> result = new java.util.HashMap<>();
        result.put("cypher", Map.of("query", stmt.getCypher(), "parameters", stmt.getCatalog().getParameters()));
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
    }
}

final class Query8 {
    static Map<String, Object> harness(Neo4jTemplate template, Neo4jClient client) {
        var ol = Cypher.node("OrderLine").named("ol");
        var stmt = Cypher.match(ol)
                .returning(Cypher.max(ol.property("unitPrice")).as("maxUnitPrice"))
                .build();
        var row = client.query(stmt.getCypher())
                .bindAll(stmt.getCatalog().getParameters())
                .fetch().one().orElse(null);
        Double max = row != null && row.get("maxUnitPrice") != null
                ? ((Number) row.get("maxUnitPrice")).doubleValue()
                : null;
        Map<String, Object> result = new java.util.HashMap<>();
        result.put("cypher", Map.of("query", stmt.getCypher(), "parameters", stmt.getCatalog().getParameters()));
        result.put("count", max != null ? 1 : 0);
        result.put("firstSample", max);
        result.put("lastSample", null);
        return result;
    }
}

final class Query9 {
    static Map<String, Object> harness(Neo4jTemplate template, Neo4jClient client) {
        var ol = Cypher.node("OrderLine").named("ol");
        var stmt = Cypher.match(ol)
                .returning(Cypher.sum(ol.property("quantity").multiply(ol.property("unitPrice"))).as("total"))
                .build();
        var row = client.query(stmt.getCypher())
                .bindAll(stmt.getCatalog().getParameters())
                .fetch().one().orElse(null);
        Double total = row != null && row.get("total") != null
                ? ((Number) row.get("total")).doubleValue()
                : null;
        Map<String, Object> result = new java.util.HashMap<>();
        result.put("cypher", Map.of("query", stmt.getCypher(), "parameters", stmt.getCatalog().getParameters()));
        result.put("count", total != null ? 1 : 0);
        result.put("firstSample", total);
        result.put("lastSample", null);
        return result;
    }
}

final class Query10 {
    static BuildableStatement<ResultStatement> query(boolean returnCount) {
        var o = Cypher.node("Order").named("o");
        var c = Cypher.node("Customer").named("c");
        var bo = Cypher.node("Order").named("bo");
        var ol = Cypher.node("OrderLine").named("ol");
        var si = Cypher.node("StockItem").named("si");
        var p = Cypher.node("Person").named("p");
        var partial = Cypher.match(o)
                .where(o.property("orderId").isEqualTo(Cypher.literalOf(530)))
                .optionalMatch(o.relationshipTo(c, "CUSTOMERS"))
                .optionalMatch(o.relationshipTo(bo, "ORDERS"))
                .optionalMatch(ol.relationshipTo(o, "ORDERS"))
                .optionalMatch(ol.relationshipTo(si, "STOCK_ITEMS"))
                .optionalMatch(ol.relationshipTo(p, "PEOPLE"))
                .with(
                        o.property("orderId").as("orderId"),
                        c.property("customerId").as("customerId"),
                        o.property("orderDate").as("orderDate"),
                        o.property("expectedDeliveryDate").as("expectedDeliveryDate"),
                        o.property("customerPurchaseOrderNumber").as("customerPurchaseOrderNumber"),
                        o.property("isUndersupplyBackordered").as("isUndersupplyBackordered"),
                        o.property("pickingCompletedWhen").as("pickingCompletedWhen"),
                        o.property("lastEditedWhen").as("lastEditedWhen"),
                        bo.property("orderId").as("backorderOrderId"),
                        Cypher.collect(ol.property("orderLineId")).as("orderLineIds"),
                        Cypher.collect(ol.property("description")).as("descriptions"),
                        Cypher.collect(ol.property("quantity")).as("quantities"),
                        Cypher.collect(ol.property("unitPrice")).as("unitPrices"),
                        Cypher.collect(ol.property("taxRate")).as("taxRates"),
                        Cypher.collect(ol.property("pickedQuantity")).as("pickedQuantities"),
                        Cypher.collect(ol.property("pickingCompletedWhen")).as("pickingCompletedWhens"),
                        Cypher.collect(ol.property("lastEditedWhen")).as("lastEditedWhens"),
                        Cypher.collect(si.property("stockItemId")).as("stockItemIds"),
                        Cypher.collect(p.property("personId")).as("lastEditedBys"));
        if (returnCount) {
            return partial.returning(Cypher.count(Cypher.asterisk()).as("count"));
        }
        return partial.returning(
                Cypher.name("orderId"),
                Cypher.name("customerId"),
                Cypher.name("orderDate"),
                Cypher.name("expectedDeliveryDate"),
                Cypher.name("customerPurchaseOrderNumber"),
                Cypher.name("isUndersupplyBackordered"),
                Cypher.name("pickingCompletedWhen"),
                Cypher.name("lastEditedWhen"),
                Cypher.name("backorderOrderId"),
                Cypher.name("orderLineIds"),
                Cypher.name("descriptions"),
                Cypher.name("quantities"),
                Cypher.name("unitPrices"),
                Cypher.name("taxRates"),
                Cypher.name("pickedQuantities"),
                Cypher.name("pickingCompletedWhens"),
                Cypher.name("lastEditedWhens"),
                Cypher.name("stockItemIds"),
                Cypher.name("lastEditedBys"));
    }

    static Integer toInteger(Object value) {
        return value == null ? null : ((Number) value).intValue();
    }

    static Double toDouble(Object value) {
        return value == null ? null : ((Number) value).doubleValue();
    }

    static Boolean toBoolean(Object value) {
        if (value == null) return null;
        if (value instanceof Boolean b) return b;
        return ((Number) value).intValue() != 0;
    }

    static OrderProjection mapOrder(Map<String, Object> row) {
        if (row == null) return null;
        Integer orderId = toInteger(row.get("orderId"));
        List<OrderLineProjection> lines = new java.util.ArrayList<>();
        List<?> orderLineIds = (List<?>) row.get("orderLineIds");
        if (orderLineIds != null && !orderLineIds.isEmpty() && orderLineIds.get(0) != null) {
            List<?> descriptions = (List<?>) row.get("descriptions");
            List<?> quantities = (List<?>) row.get("quantities");
            List<?> unitPrices = (List<?>) row.get("unitPrices");
            List<?> taxRates = (List<?>) row.get("taxRates");
            List<?> pickedQuantities = (List<?>) row.get("pickedQuantities");
            List<?> pickingCompletedWhens = (List<?>) row.get("pickingCompletedWhens");
            List<?> lastEditedWhens = (List<?>) row.get("lastEditedWhens");
            List<?> stockItemIds = (List<?>) row.get("stockItemIds");
            List<?> lastEditedBys = (List<?>) row.get("lastEditedBys");
            for (int i = 0; i < orderLineIds.size(); i++) {
                lines.add(new OrderLineProjection(
                        toInteger(orderLineIds.get(i)),
                        orderId,
                        toInteger(stockItemIds.get(i)),
                        (String) descriptions.get(i),
                        toInteger(quantities.get(i)),
                        toDouble(unitPrices.get(i)),
                        toDouble(taxRates.get(i)),
                        toInteger(pickedQuantities.get(i)),
                        (String) pickingCompletedWhens.get(i),
                        toInteger(lastEditedBys.get(i)),
                        (String) lastEditedWhens.get(i)));
            }
        }
        return new OrderProjection(
                orderId,
                toInteger(row.get("customerId")),
                (String) row.get("orderDate"),
                (String) row.get("expectedDeliveryDate"),
                (String) row.get("customerPurchaseOrderNumber"),
                toBoolean(row.get("isUndersupplyBackordered")),
                (String) row.get("pickingCompletedWhen"),
                (String) row.get("lastEditedWhen"),
                toInteger(row.get("backorderOrderId")),
                lines);
    }

    static Map<String, Object> harness(Neo4jTemplate template, Neo4jClient client) {
        var countStmt = query(true).build();
        long count = 0;
        var countRow = client.query(countStmt.getCypher())
                .bindAll(countStmt.getCatalog().getParameters())
                .fetch()
                .one()
                .orElse(null);
        if (countRow != null) {
            count = ((Number) countRow.get("count")).longValue();
        }
        Object sample = null;
        if (count > 0) {
            var stmt = query(false).build();
            var row = client.query(stmt.getCypher())
                    .bindAll(stmt.getCatalog().getParameters())
                    .fetch()
                    .one()
                    .orElse(null);
            sample = mapOrder(row);
        }
        var stmt = query(false).build();
        Map<String, Object> result = new java.util.HashMap<>();
        result.put("cypher", Map.of("query", stmt.getCypher(), "parameters", stmt.getCatalog().getParameters()));
        result.put("count", count);
        result.put("firstSample", sample);
        result.put("lastSample", count > 1 ? sample : null);
        return result;
    }
}

final class Query11 {
    static BuildableStatement<ResultStatement> query(boolean returnCount) {
        var o = Cypher.node("Order").named("o");
        if (returnCount) {
            return Cypher.match(o).returning(Cypher.count(o).as("count"));
        }
        var page = Cypher.match(o)
                .returning(o)
                .orderBy(
                        Cypher.sort(o.property("expectedDeliveryDate").isNotNull()),
                        Cypher.sort(o.property("expectedDeliveryDate"), Direction.ASC),
                        Cypher.sort(o.property("orderId"), Direction.ASC))
                .limit(1000)
                .build();
        var c = Cypher.node("Customer").named("c");
        var bo = Cypher.node("Order").named("bo");
        return Cypher.call(page)
                .optionalMatch(o.relationshipTo(c, "CUSTOMERS"))
                .optionalMatch(o.relationshipTo(bo, "ORDERS"))
                .returning(
                        o.property("orderId").as("orderId"),
                        c.property("customerId").as("customerId"),
                        o.property("orderDate").as("orderDate"),
                        o.property("expectedDeliveryDate").as("expectedDeliveryDate"),
                        o.property("customerPurchaseOrderNumber").as("customerPurchaseOrderNumber"),
                        Cypher.toBoolean(o.property("isUndersupplyBackordered")).as("isUndersupplyBackordered"),
                        o.property("pickingCompletedWhen").as("pickingCompletedWhen"),
                        o.property("lastEditedWhen").as("lastEditedWhen"),
                        bo.property("orderId").as("backorderOrderId"));
    }

    static Integer toInteger(Object value) {
        return value == null ? null : ((Number) value).intValue();
    }

    static Boolean toBoolean(Object value) {
        if (value == null) return null;
        if (value instanceof Boolean b) return b;
        return ((Number) value).intValue() != 0;
    }

    static OrderProjection mapOrder(Map<String, Object> row) {
        if (row == null) return null;
        return new OrderProjection(
                toInteger(row.get("orderId")),
                toInteger(row.get("customerId")),
                (String) row.get("orderDate"),
                (String) row.get("expectedDeliveryDate"),
                (String) row.get("customerPurchaseOrderNumber"),
                toBoolean(row.get("isUndersupplyBackordered")),
                (String) row.get("pickingCompletedWhen"),
                (String) row.get("lastEditedWhen"),
                toInteger(row.get("backorderOrderId")),
                java.util.List.of());
    }

    static Map<String, Object> harness(Neo4jTemplate template, Neo4jClient client) {
        long total = template.count(query(true).build());
        long actualCount = Math.min(total, 1000);
        var q = query(false);
        Object first = null;
        if (actualCount > 0) {
            var asc = Cypher.call(q.build()).returning(Cypher.asterisk())
                    .orderBy(Cypher.sort(Cypher.name("orderId"), Direction.ASC))
                    .limit(1).build();
            first = mapOrder(client.query(asc.getCypher())
                    .bindAll(asc.getCatalog().getParameters())
                    .fetch()
                    .one()
                    .orElse(null));
        }
        Object last = null;
        if (actualCount > 1) {
            var desc = Cypher.call(q.build()).returning(Cypher.asterisk())
                    .orderBy(Cypher.sort(Cypher.name("orderId"), Direction.DESC))
                    .limit(1).build();
            last = mapOrder(client.query(desc.getCypher())
                    .bindAll(desc.getCatalog().getParameters())
                    .fetch()
                    .one()
                    .orElse(null));
        }
        var stmt = q.build();
        Map<String, Object> result = new java.util.HashMap<>();
        result.put("cypher", Map.of("query", stmt.getCypher(), "parameters", stmt.getCatalog().getParameters()));
        result.put("count", actualCount);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
    }
}

final class Query12 {
    static BuildableStatement<ResultStatement> query(boolean returnCount) {
        var o = Cypher.node("Order").named("o");
        if (returnCount) return Cypher.match(o).returning(Cypher.countDistinct(o.property("customerPurchaseOrderNumber")));
        return Cypher.match(o)
                .returningDistinct(o.property("customerPurchaseOrderNumber").as("customerPurchaseOrderNumber"))
                .orderBy(
                        Cypher.sort(Cypher.name("customerPurchaseOrderNumber").isNotNull()),
                        Cypher.sort(Cypher.name("customerPurchaseOrderNumber"), Direction.ASC));
    }

    static Map<String, Object> harness(Neo4jTemplate template, Neo4jClient client) {
        long count = template.count(query(true).build());
        Object first = null;
        if (count > 0) {
            var asc = ((OngoingReadingAndReturn) query(false)).limit(1).build();
            var firstMap = client.query(asc.getCypher())
                    .bindAll(asc.getCatalog().getParameters())
                    .fetch().one().orElse(null);
            first = firstMap != null ? firstMap.get("customerPurchaseOrderNumber") : null;
        }
        Object last = null;
        if (count > 1) {
            var desc = Cypher.call(query(false).build()).returning(Cypher.asterisk())
                    .orderBy(
                            Cypher.sort(Cypher.name("customerPurchaseOrderNumber").isNull()),
                            Cypher.sort(Cypher.name("customerPurchaseOrderNumber"), Direction.DESC))
                    .limit(1).build();
            var lastMap = client.query(desc.getCypher())
                    .bindAll(desc.getCatalog().getParameters())
                    .fetch().one().orElse(null);
            last = lastMap != null ? lastMap.get("customerPurchaseOrderNumber") : null;
        }
        var stmt = query(false).build();
        Map<String, Object> result = new java.util.HashMap<>();
        result.put("cypher", Map.of("query", stmt.getCypher(), "parameters", stmt.getCatalog().getParameters()));
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
    }
}

final class Query13 {
    static BuildableStatement<ResultStatement> query(boolean returnCount) {
        var p = Cypher.node("Person").named("p");
        var title = Cypher.raw("apoc.convert.fromJsonMap($E).Title", p.property("customFields"));
        var partial = Cypher.match(p)
                .where(p.property("customFields").isNotNull())
                .and(title.isEqualTo(Cypher.literalOf("Team Member")));
        if (returnCount) return partial.returning(Cypher.count(p));
        return partial.returning(p)
                .orderBy(Cypher.sort(p.property("personId"), Direction.ASC));
    }

    static Map<String, Object> harness(Neo4jTemplate template, Neo4jClient client) {
        long count = template.count(query(true).build());
        var q = query(false);
        Object first = null;
        if (count > 0) {
            var asc = ((OngoingReadingAndReturn) q).limit(1).build();
            first = template.findOne(asc, asc.getCatalog().getParameters(), Person.class).orElse(null);
        }
        Object last = null;
        if (count > 1) {
            var desc = ((OngoingReadingAndReturn) q)
                    .orderBy(Cypher.sort(Cypher.property("p", "personId"), Direction.DESC))
                    .limit(1).build();
            last = template.findOne(desc, desc.getCatalog().getParameters(), Person.class).orElse(null);
        }
        var stmt = q.build();
        Map<String, Object> result = new java.util.HashMap<>();
        result.put("cypher", Map.of("query", stmt.getCypher(), "parameters", stmt.getCatalog().getParameters()));
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
    }
}

final class Query14 {
    static BuildableStatement<ResultStatement> query(boolean returnCount) {
        var p = Cypher.node("Person").named("p");
        var langs = Cypher.call("apoc.convert.fromJsonList")
                .withArgs(p.property("otherLanguages")).asFunction();
        var partial = Cypher.match(p)
                .where(p.property("otherLanguages").isNotNull())
                .and(Cypher.literalOf("Slovak").in(langs));
        if (returnCount) return partial.returning(Cypher.count(p));
        return partial.returning(p)
                .orderBy(Cypher.sort(p.property("personId"), Direction.ASC));
    }

    static Map<String, Object> harness(Neo4jTemplate template, Neo4jClient client) {
        long count = template.count(query(true).build());
        var q = query(false);
        Object first = null;
        if (count > 0) {
            var asc = ((OngoingReadingAndReturn) q).limit(1).build();
            first = template.findOne(asc, asc.getCatalog().getParameters(), Person.class).orElse(null);
        }
        Object last = null;
        if (count > 1) {
            var desc = ((OngoingReadingAndReturn) q)
                    .orderBy(Cypher.sort(Cypher.property("p", "personId"), Direction.DESC))
                    .limit(1).build();
            last = template.findOne(desc, desc.getCatalog().getParameters(), Person.class).orElse(null);
        }
        var stmt = q.build();
        Map<String, Object> result = new java.util.HashMap<>();
        result.put("cypher", Map.of("query", stmt.getCypher(), "parameters", stmt.getCatalog().getParameters()));
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
    }
}

final class Query15 {
    static Map<String, Object> harness(Neo4jTemplate template, Neo4jClient client) {
        var s1 = Cypher.node("Supplier").named("s1");
        var a = Cypher.match(s1)
                .where(s1.property("supplierId").lt(Cypher.literalOf(5)))
                .returning(s1.property("supplierId").as("supplierId")).build();
        var s2 = Cypher.node("Supplier").named("s2");
        var b = Cypher.match(s2)
                .where(s2.property("supplierId").gte(Cypher.literalOf(5))
                        .and(s2.property("supplierId").lte(Cypher.literalOf(10))))
                .returning(s2.property("supplierId").as("supplierId")).build();
        var union = Cypher.union(a, b);
        var ordered = Cypher.call(union).returning(Cypher.asterisk())
                .orderBy(Cypher.sort(Cypher.name("supplierId"), Direction.ASC))
                .build();
        var rows = client.query(ordered.getCypher())
                .bindAll(ordered.getCatalog().getParameters())
                .fetch().all();
        var list = new java.util.ArrayList<Map<String, Object>>(rows);
        long count = list.size();
        Object first = count > 0 ? ((Number) list.get(0).get("supplierId")).intValue() : null;
        Object last = count > 1 ? ((Number) list.get((int) count - 1).get("supplierId")).intValue() : null;
        Map<String, Object> result = new java.util.HashMap<>();
        result.put("cypher", Map.of("query", ordered.getCypher(), "parameters", ordered.getCatalog().getParameters()));
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
    }
}