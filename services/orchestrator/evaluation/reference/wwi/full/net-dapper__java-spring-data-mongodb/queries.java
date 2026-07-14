final class Query1 {
    static Query query() {
        return new Query(Criteria.where("orderId").is(26866));
    }

    static Map<String, Object> harness(MongoTemplate template) {
        Query q = query();
        long count = template.count(q, OrderLine.class);
        Object first = null;
        if (count > 0) {
            first = template.findOne(query().with(Sort.by(Sort.Direction.ASC, "orderLineId")).limit(1), OrderLine.class);
        }
        Object last = null;
        if (count > 1) {
            last = template.findOne(query().with(Sort.by(Sort.Direction.DESC, "orderLineId")).limit(1), OrderLine.class);
        }
        Map<String, Object> result = new HashMap<>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
    }
}

final class Query2 {
    static Query query() {
        return new Query(Criteria.where("unitPrice").is(new BigDecimal("25.00")));
    }

    static Map<String, Object> harness(MongoTemplate template) {
        Query q = query();
        long count = template.count(q, OrderLine.class);
        Object first = null;
        if (count > 0) {
            first = template.findOne(query().with(Sort.by(Sort.Direction.ASC, "orderLineId")).limit(1), OrderLine.class);
        }
        Object last = null;
        if (count > 1) {
            last = template.findOne(query().with(Sort.by(Sort.Direction.DESC, "orderLineId")).limit(1), OrderLine.class);
        }
        Map<String, Object> result = new HashMap<>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
    }
}

final class Query3 {
    static Query query() {
        LocalDateTime from = LocalDateTime.of(2014, 12, 20, 0, 0);
        LocalDateTime to = LocalDateTime.of(2014, 12, 31, 0, 0);
        return new Query(Criteria.where("pickingCompletedWhen").gte(from).lte(to));
    }

    static Map<String, Object> harness(MongoTemplate template) {
        Query q = query();
        long count = template.count(q, OrderLine.class);
        Object first = null;
        if (count > 0) {
            first = template.findOne(query().with(Sort.by(Sort.Direction.ASC, "orderLineId")).limit(1), OrderLine.class);
        }
        Object last = null;
        if (count > 1) {
            last = template.findOne(query().with(Sort.by(Sort.Direction.DESC, "orderLineId")).limit(1), OrderLine.class);
        }
        Map<String, Object> result = new HashMap<>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
    }
}

final class Query4 {
    static Query query() {
        return new Query(Criteria.where("orderId").in(List.of(1, 10, 100, 1000, 10000)));
    }

    static Map<String, Object> harness(MongoTemplate template) {
        Query q = query();
        long count = template.count(q, OrderLine.class);
        Object first = null;
        if (count > 0) {
            first = template.findOne(query().with(Sort.by(Sort.Direction.ASC, "orderLineId")).limit(1), OrderLine.class);
        }
        Object last = null;
        if (count > 1) {
            last = template.findOne(query().with(Sort.by(Sort.Direction.DESC, "orderLineId")).limit(1), OrderLine.class);
        }
        Map<String, Object> result = new HashMap<>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
    }
}

final class Query5 {
    static Query query() {
        return new Query(Criteria.where("description").regex("C\\+\\+", "i"));
    }

    static Map<String, Object> harness(MongoTemplate template) {
        Query q = query();
        long count = template.count(q, OrderLine.class);
        Object first = null;
        if (count > 0) {
            first = template.findOne(query().with(Sort.by(Sort.Direction.ASC, "orderLineId")).limit(1), OrderLine.class);
        }
        Object last = null;
        if (count > 1) {
            last = template.findOne(query().with(Sort.by(Sort.Direction.DESC, "orderLineId")).limit(1), OrderLine.class);
        }
        Map<String, Object> result = new HashMap<>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
    }
}

final class Query6 {
    static Query query() {
        return new Query().with(Sort.by(Sort.Direction.ASC, "orderLineId")).skip(1000).limit(50);
    }

    static Map<String, Object> harness(MongoTemplate template) {
        List<OrderLine> page = template.find(query(), OrderLine.class);
        long count = page.size();
        Object first = count > 0 ? page.get(0) : null;
        Object last = count > 0 ? page.get(page.size() - 1) : null;
        Map<String, Object> result = new HashMap<>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
    }
}

final class Query7 {
    static TypedAggregation<OrderLine> query() {
        return Aggregation.newAggregation(
            OrderLine.class,
            Aggregation.group("taxRate").count().as("count"),
            Aggregation.project("count").and("taxRate").previousOperation()
        );
    }

    static Map<String, Object> harness(MongoTemplate template) {
        var baseAgg = query();

        var countOps = new ArrayList<>(baseAgg.getPipeline().getOperations());
        countOps.add(Aggregation.count().as("count"));
        var countAgg = Aggregation.newAggregation(OrderLine.class, countOps);
        CountProjection countResult = template.aggregate(countAgg, OrderLine.class, CountProjection.class).getUniqueMappedResult();
        long count = countResult != null ? countResult.count() : 0L;

        Object first = null;
        if (count > 0) {
            var firstOps = new ArrayList<>(baseAgg.getPipeline().getOperations());
            firstOps.add(Aggregation.sort(Sort.Direction.DESC, "count"));
            firstOps.add(Aggregation.limit(1));
            var firstAgg = Aggregation.newAggregation(OrderLine.class, firstOps);
            first = template.aggregate(firstAgg, OrderLine.class, TaxRateCount.class).getUniqueMappedResult();
        }

        Object last = null;
        if (count > 0) {
            var lastOps = new ArrayList<>(baseAgg.getPipeline().getOperations());
            lastOps.add(Aggregation.sort(Sort.Direction.ASC, "count"));
            lastOps.add(Aggregation.limit(1));
            var lastAgg = Aggregation.newAggregation(OrderLine.class, lastOps);
            last = template.aggregate(lastAgg, OrderLine.class, TaxRateCount.class).getUniqueMappedResult();
        }

        Map<String, Object> result = new HashMap<>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
    }
}

final class Query8 {
    static TypedAggregation<OrderLine> query() {
        return Aggregation.newAggregation(
            OrderLine.class,
            Aggregation.group().max("unitPrice").as("maxValue")
        );
    }

    static Map<String, Object> harness(MongoTemplate template) {
        MaxValue maxValue = template.aggregate(query(), OrderLine.class, MaxValue.class).getUniqueMappedResult();
        Object max = maxValue != null ? maxValue.maxValue() : null;
        long count = max != null ? 1L : 0L;
        Map<String, Object> result = new HashMap<>();
        result.put("count", count);
        result.put("firstSample", max);
        result.put("lastSample", null);
        return result;
    }
}

final class Query9 {
    static TypedAggregation<OrderLine> query() {
        return Aggregation.newAggregation(
            OrderLine.class,
            Aggregation.project().andExpression("quantity * unitPrice").as("lineTotal"),
            Aggregation.group().sum("lineTotal").as("total")
        );
    }

    static Map<String, Object> harness(MongoTemplate template) {
        SumTotal sumTotal = template.aggregate(query(), OrderLine.class, SumTotal.class).getUniqueMappedResult();
        Object total = sumTotal != null ? sumTotal.total() : null;
        long count = total != null ? 1L : 0L;
        Map<String, Object> result = new HashMap<>();
        result.put("count", count);
        result.put("firstSample", total);
        result.put("lastSample", null);
        return result;
    }
}

final class Query10 {
    static Query query() {
        return new Query(Criteria.where("orderId").is(530));
    }

    static Map<String, Object> harness(MongoTemplate template) {
        Query q = query();
        long count = template.count(q, Order.class);
        Order order = null;
        if (count > 0) {
            order = template.findOne(q, Order.class);
            if (order != null) {
                List<OrderLine> lines = template.find(
                    new Query(Criteria.where("orderId").is(530))
                        .with(Sort.by(Sort.Direction.ASC, "orderLineId")),
                    OrderLine.class);
                order.setOrderLines(lines);
            }
        }
        Map<String, Object> result = new HashMap<>();
        result.put("count", count);
        result.put("firstSample", order);
        result.put("lastSample", order);
        return result;
    }
}

final class Query11 {
    static Query query() {
        return new Query().with(Sort.by(Sort.Direction.ASC, "expectedDeliveryDate")).limit(1000);
    }

    static Map<String, Object> harness(MongoTemplate template) {
        List<Order> rows = template.find(query(), Order.class);
        long count = rows.size();
        Object first = count > 0 ? rows.get(0) : null;
        Object last = count > 0 ? rows.get(rows.size() - 1) : null;
        Map<String, Object> result = new HashMap<>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
    }
}

final class Query12 {
    static Map<String, Object> harness(MongoTemplate template) {
        List<String> values = template.findDistinct(
            new Query(), "customerPurchaseOrderNumber", Order.class, String.class);
        values.sort(Comparator.nullsFirst(Comparator.naturalOrder()));
        long count = values.size();
        Object first = count > 0 ? values.get(0) : null;
        Object last = count > 1 ? values.get(values.size() - 1) : null;
        Map<String, Object> result = new HashMap<>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
    }
}

final class Query13 {
    static Query query() {
        return new Query(Criteria.where("customFields")
            .regex(".*\"Title\"\\s*:\\s*\"Team Member\".*", "i"));
    }

    static Map<String, Object> harness(MongoTemplate template) {
        Query q = query();
        long count = template.count(q, Person.class);
        Object first = null;
        if (count > 0) {
            first = template.findOne(query().with(Sort.by(Sort.Direction.ASC, "personId")).limit(1), Person.class);
        }
        Object last = null;
        if (count > 1) {
            last = template.findOne(query().with(Sort.by(Sort.Direction.DESC, "personId")).limit(1), Person.class);
        }
        Map<String, Object> result = new HashMap<>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
    }
}

final class Query14 {
    static Query query() {
        return new Query(Criteria.where("otherLanguages")
            .regex(".*\"Slovak\".*", "i"));
    }

    static Map<String, Object> harness(MongoTemplate template) {
        Query q = query();
        long count = template.count(q, Person.class);
        Object first = null;
        if (count > 0) {
            first = template.findOne(query().with(Sort.by(Sort.Direction.ASC, "personId")).limit(1), Person.class);
        }
        Object last = null;
        if (count > 1) {
            last = template.findOne(query().with(Sort.by(Sort.Direction.DESC, "personId")).limit(1), Person.class);
        }
        Map<String, Object> result = new HashMap<>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
    }
}

final class Query15 {
    static Query query() {
        return new Query(new Criteria().orOperator(
            Criteria.where("supplierId").lt(5),
            Criteria.where("supplierId").gte(5).lte(10)
        )).with(Sort.by(Sort.Direction.ASC, "supplierId"));
    }

    static Map<String, Object> harness(MongoTemplate template) {
        Query q = query();
        long count = template.count(q, Supplier.class);
        List<Supplier> rows = template.find(q, Supplier.class);
        Object first = count > 0 ? rows.get(0).getSupplierId() : null;
        Object last = count > 1 ? rows.get(rows.size() - 1).getSupplierId() : null;
        Map<String, Object> result = new HashMap<>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
    }
}