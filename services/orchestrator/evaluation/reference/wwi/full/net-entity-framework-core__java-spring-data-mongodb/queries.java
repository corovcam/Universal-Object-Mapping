final class Query1 {
    static Map<String, Object> harness(MongoTemplate template) {
        Query q = new Query(Criteria.where("orderId").is(26866));
        long count = template.count(q, OrderLine.class);
        Object first = null;
        if (count > 0) {
            first = template.findOne(q.with(Sort.by(Sort.Direction.ASC, "orderLineId")).limit(1), OrderLine.class);
        }
        Object last = null;
        if (count > 1) {
            last = template.findOne(q.with(Sort.by(Sort.Direction.DESC, "orderLineId")).limit(1), OrderLine.class);
        }
        return Map.of("count", count, "firstSample", first, "lastSample", last);
    }
}

final class Query2 {
    static Map<String, Object> harness(MongoTemplate template) {
        Query q = new Query(Criteria.where("unitPrice").is(new BigDecimal("25.00")));
        long count = template.count(q, OrderLine.class);
        Object first = null;
        if (count > 0) {
            first = template.findOne(q.with(Sort.by(Sort.Direction.ASC, "orderLineId")).limit(1), OrderLine.class);
        }
        Object last = null;
        if (count > 1) {
            last = template.findOne(q.with(Sort.by(Sort.Direction.DESC, "orderLineId")).limit(1), OrderLine.class);
        }
        return Map.of("count", count, "firstSample", first, "lastSample", last);
    }
}

final class Query3 {
    static Map<String, Object> harness(MongoTemplate template) {
        LocalDateTime from = LocalDateTime.of(2014, 12, 20, 0, 0);
        LocalDateTime to = LocalDateTime.of(2014, 12, 31, 0, 0);
        Query q = new Query(Criteria.where("pickingCompletedWhen").gte(from).lte(to));
        long count = template.count(q, OrderLine.class);
        Object first = null;
        if (count > 0) {
            first = template.findOne(q.with(Sort.by(Sort.Direction.ASC, "orderLineId")).limit(1), OrderLine.class);
        }
        Object last = null;
        if (count > 1) {
            last = template.findOne(q.with(Sort.by(Sort.Direction.DESC, "orderLineId")).limit(1), OrderLine.class);
        }
        return Map.of("count", count, "firstSample", first, "lastSample", last);
    }
}

final class Query4 {
    static Map<String, Object> harness(MongoTemplate template) {
        List<Integer> orderIds = List.of(1, 10, 100, 1000, 10000);
        Query q = new Query(Criteria.where("orderId").in(orderIds));
        long count = template.count(q, OrderLine.class);
        Object first = null;
        if (count > 0) {
            first = template.findOne(q.with(Sort.by(Sort.Direction.ASC, "orderLineId")).limit(1), OrderLine.class);
        }
        Object last = null;
        if (count > 1) {
            last = template.findOne(q.with(Sort.by(Sort.Direction.DESC, "orderLineId")).limit(1), OrderLine.class);
        }
        return Map.of("count", count, "firstSample", first, "lastSample", last);
    }
}

final class Query5 {
    static Map<String, Object> harness(MongoTemplate template) {
        Query q = new Query(Criteria.where("description").regex("C\\+\\+"));
        long count = template.count(q, OrderLine.class);
        Object first = null;
        if (count > 0) {
            first = template.findOne(q.with(Sort.by(Sort.Direction.ASC, "orderLineId")).limit(1), OrderLine.class);
        }
        Object last = null;
        if (count > 1) {
            last = template.findOne(q.with(Sort.by(Sort.Direction.DESC, "orderLineId")).limit(1), OrderLine.class);
        }
        return Map.of("count", count, "firstSample", first, "lastSample", last);
    }
}

final class Query6 {
    static Map<String, Object> harness(MongoTemplate template) {
        long total = template.count(new Query(), OrderLine.class);
        long count = Math.max(0, Math.min(50, total - 1000));
        Object first = null;
        if (count > 0) {
            first = template.findOne(new Query().with(Sort.by(Sort.Direction.ASC, "orderLineId")).skip(1000).limit(1), OrderLine.class);
        }
        Object last = null;
        if (count > 1) {
            last = template.findOne(new Query().with(Sort.by(Sort.Direction.ASC, "orderLineId")).skip(1000 + count - 1).limit(1), OrderLine.class);
        }
        return Map.of("count", count, "firstSample", first, "lastSample", last);
    }
}

final class Query7 {
    static Map<String, Object> harness(MongoTemplate template) {
        TypedAggregation<OrderLine> agg = Aggregation.newAggregation(
            OrderLine.class,
            Aggregation.group("taxRate").count().as("count"),
            Aggregation.project("count").and("taxRate").previousOperation()
        );

        var countOps = new ArrayList<>(agg.getPipeline().getOperations());
        countOps.add(Aggregation.count().as("count"));
        var countAgg = Aggregation.newAggregation(OrderLine.class, countOps);
        CountProjection countResult = template.aggregate(countAgg, OrderLine.class, CountProjection.class).getUniqueMappedResult();
        long count = countResult != null ? countResult.count() : 0L;

        Object first = null;
        if (count > 0) {
            var firstOps = new ArrayList<>(agg.getPipeline().getOperations());
            firstOps.add(Aggregation.sort(Sort.by(Sort.Order.desc("count"), Sort.Order.asc("taxRate"))));
            firstOps.add(Aggregation.limit(1));
            var firstAgg = Aggregation.newAggregation(OrderLine.class, firstOps);
            first = template.aggregate(firstAgg, OrderLine.class, TaxRateCount.class).getUniqueMappedResult();
        }

        Object last = null;
        if (count > 1) {
            var lastOps = new ArrayList<>(agg.getPipeline().getOperations());
            lastOps.add(Aggregation.sort(Sort.by(Sort.Order.asc("count"), Sort.Order.desc("taxRate"))));
            lastOps.add(Aggregation.limit(1));
            var lastAgg = Aggregation.newAggregation(OrderLine.class, lastOps);
            last = template.aggregate(lastAgg, OrderLine.class, TaxRateCount.class).getUniqueMappedResult();
        }

        return Map.of("count", count, "firstSample", first, "lastSample", last);
    }
}

final class Query8 {
    static Map<String, Object> harness(MongoTemplate template) {
        Query q = new Query(Criteria.where("unitPrice").ne(null).exists(true))
                .with(Sort.by(Sort.Direction.DESC, "unitPrice")).limit(1);
        OrderLine ol = template.findOne(q, OrderLine.class);
        BigDecimal max = ol != null ? ol.getUnitPrice() : null;
        long count = max != null ? 1 : 0;
        Map<String, Object> result = new java.util.HashMap<>();
        result.put("count", count);
        result.put("firstSample", max);
        result.put("lastSample", null);
        return result;
    }
}

final class Query9 {
    static Map<String, Object> harness(MongoTemplate template) {
        List<OrderLine> lines = template.find(new Query(), OrderLine.class);
        BigDecimal sum = null;
        for (OrderLine ol : lines) {
            Integer qty = ol.getQuantity();
            BigDecimal price = ol.getUnitPrice();
            if (qty != null && price != null) {
                BigDecimal lineTotal = price.multiply(BigDecimal.valueOf(qty));
                sum = sum == null ? lineTotal : sum.add(lineTotal);
            }
        }
        long count = sum != null ? 1 : 0;
        Map<String, Object> result = new java.util.HashMap<>();
        result.put("count", count);
        result.put("firstSample", sum);
        result.put("lastSample", null);
        return result;
    }
}

final class Query10 {
    static Map<String, Object> harness(MongoTemplate template) {
        Query q = new Query(Criteria.where("orderId").is(530));
        long count = template.count(q, Order.class);
        Object first = null;
        if (count > 0) {
            Order order = template.findOne(q.with(Sort.by(Sort.Direction.ASC, "orderId")).limit(1), Order.class);
            if (order != null) {
                List<OrderLine> lines = template.find(
                    new Query(Criteria.where("orderId").is(order.getOrderId()))
                        .with(Sort.by(Sort.Direction.ASC, "orderLineId")),
                    OrderLine.class);
                order.setOrderLines(lines);
            }
            first = order;
        }
        Object last = null;
        if (count > 1) {
            last = template.findOne(q.with(Sort.by(Sort.Direction.DESC, "orderId")).limit(1), Order.class);
        }
        Map<String, Object> result = new java.util.HashMap<>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
    }
}

final class Query11 {
    static Map<String, Object> harness(MongoTemplate template) {
        Query q = new Query().with(Sort.by(Sort.Direction.ASC, "expectedDeliveryDate")).limit(1000);
        List<Order> rows = template.find(q, Order.class);
        long count = rows.size();
        rows.sort((a, b) -> Integer.compare(a.getOrderId(), b.getOrderId()));
        Object first = count > 0 ? rows.get(0) : null;
        Object last = count > 1 ? rows.get((int)count - 1) : null;
        return Map.of("count", count, "firstSample", first, "lastSample", last);
    }
}

final class Query12 {
    static Map<String, Object> harness(MongoTemplate template) {
        TypedAggregation<Order> agg = Aggregation.newAggregation(
            Order.class,
            Aggregation.group("customerPurchaseOrderNumber"),
            Aggregation.project().and("value").previousOperation(),
            Aggregation.sort(Sort.Direction.ASC, "value")
        );
        List<ValueProjection> rows = template.aggregate(agg, Order.class, ValueProjection.class).getMappedResults();
        long count = rows.size();
        Object first = count > 0 ? rows.get(0).value() : null;
        Object last = count > 1 ? rows.get((int)count - 1).value() : null;
        return Map.of("count", count, "firstSample", first, "lastSample", last);
    }
}

final class Query13 {
    static Map<String, Object> harness(MongoTemplate template) {
        Query q = new Query(Criteria.where("customFields").regex("\"Title\"\\s*:\\s*\"Team Member\""))
                      .with(Sort.by(Sort.Direction.ASC, "personId"));
        long count = template.count(q, Person.class);
        Object first = null;
        if (count > 0) {
            first = template.findOne(q.with(Sort.by(Sort.Direction.ASC, "personId")).limit(1), Person.class);
        }
        Object last = null;
        if (count > 1) {
            last = template.findOne(q.with(Sort.by(Sort.Direction.DESC, "personId")).limit(1), Person.class);
        }
        return Map.of("count", count, "firstSample", first, "lastSample", last);
    }
}

final class Query14 {
    static Map<String, Object> harness(MongoTemplate template) {
        Query q = new Query(Criteria.where("otherLanguages").regex("\"Slovak\""))
                      .with(Sort.by(Sort.Direction.ASC, "personId"));
        long count = template.count(q, Person.class);
        Object first = null;
        if (count > 0) {
            first = template.findOne(q.with(Sort.by(Sort.Direction.ASC, "personId")).limit(1), Person.class);
        }
        Object last = null;
        if (count > 1) {
            last = template.findOne(q.with(Sort.by(Sort.Direction.DESC, "personId")).limit(1), Person.class);
        }
        return Map.of("count", count, "firstSample", first, "lastSample", last);
    }
}

final class Query15 {
    static Map<String, Object> harness(MongoTemplate template) {
        Query q1 = new Query(Criteria.where("supplierId").lt(5));
        q1.fields().include("supplierId");
        List<Supplier> s1 = template.find(q1, Supplier.class);

        Query q2 = new Query(Criteria.where("supplierId").gte(5).lte(10));
        q2.fields().include("supplierId");
        List<Supplier> s2 = template.find(q2, Supplier.class);

        List<Integer> ids = new ArrayList<>();
        for (Supplier s : s1) ids.add(s.getSupplierId());
        for (Supplier s : s2) ids.add(s.getSupplierId());

        List<Integer> union = ids.stream().distinct().sorted().toList();
        long count = union.size();
        Object first = count > 0 ? union.get(0) : null;
        Object last = count > 1 ? union.get((int)count - 1) : null;
        return Map.of("count", count, "firstSample", first, "lastSample", last);
    }
}