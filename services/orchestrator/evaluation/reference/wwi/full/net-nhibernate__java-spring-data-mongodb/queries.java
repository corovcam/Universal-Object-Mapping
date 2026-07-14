final class Query1 {
    static Query query() {
        return new Query(Criteria.where("orderId").is(26866));
    }

    static Map<String, Object> harness(MongoTemplate template) {
        Query q = query();
        long count = template.count(q, OrderLine.class);
        OrderLine first = null;
        if (count > 0) {
            first = template.findOne(query().with(Sort.by(Sort.Direction.ASC, "orderLineId")).limit(1), OrderLine.class);
        }
        OrderLine last = null;
        if (count > 1) {
            last = template.findOne(query().with(Sort.by(Sort.Direction.DESC, "orderLineId")).limit(1), OrderLine.class);
        }
        var result = new java.util.HashMap<String, Object>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
    }
}

final class Query2 {
    static Query query() {
        return new Query(Criteria.where("unitPrice").is(new java.math.BigDecimal("25")));
    }

    static Map<String, Object> harness(MongoTemplate template) {
        Query q = query();
        long count = template.count(q, OrderLine.class);
        OrderLine first = null;
        if (count > 0) {
            first = template.findOne(query().with(Sort.by(Sort.Direction.ASC, "orderLineId")).limit(1), OrderLine.class);
        }
        OrderLine last = null;
        if (count > 1) {
            last = template.findOne(query().with(Sort.by(Sort.Direction.DESC, "orderLineId")).limit(1), OrderLine.class);
        }
        var result = new java.util.HashMap<String, Object>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
    }
}

final class Query3 {
    static Query query() {
        return new Query(Criteria.where("pickingCompletedWhen")
                .gte(java.time.Instant.parse("2014-12-20T00:00:00Z"))
                .lte(java.time.Instant.parse("2014-12-31T00:00:00Z")));
    }

    static Map<String, Object> harness(MongoTemplate template) {
        Query q = query();
        long count = template.count(q, OrderLine.class);
        OrderLine first = null;
        if (count > 0) {
            first = template.findOne(query().with(Sort.by(Sort.Direction.ASC, "orderLineId")).limit(1), OrderLine.class);
        }
        OrderLine last = null;
        if (count > 1) {
            last = template.findOne(query().with(Sort.by(Sort.Direction.DESC, "orderLineId")).limit(1), OrderLine.class);
        }
        var result = new java.util.HashMap<String, Object>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
    }
}

final class Query4 {
    static Query query() {
        return new Query(Criteria.where("orderId").in(java.util.List.of(1, 10, 100, 1000, 10000)));
    }

    static Map<String, Object> harness(MongoTemplate template) {
        Query q = query();
        long count = template.count(q, OrderLine.class);
        OrderLine first = null;
        if (count > 0) {
            first = template.findOne(query().with(Sort.by(Sort.Direction.ASC, "orderLineId")).limit(1), OrderLine.class);
        }
        OrderLine last = null;
        if (count > 1) {
            last = template.findOne(query().with(Sort.by(Sort.Direction.DESC, "orderLineId")).limit(1), OrderLine.class);
        }
        var result = new java.util.HashMap<String, Object>();
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
        OrderLine first = null;
        if (count > 0) {
            first = template.findOne(query().with(Sort.by(Sort.Direction.ASC, "orderLineId")).limit(1), OrderLine.class);
        }
        OrderLine last = null;
        if (count > 1) {
            last = template.findOne(query().with(Sort.by(Sort.Direction.DESC, "orderLineId")).limit(1), OrderLine.class);
        }
        var result = new java.util.HashMap<String, Object>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
    }
}

final class Query6 {
    static Query query() {
        return new Query()
                .with(Sort.by(Sort.Direction.ASC, "orderLineId"))
                .skip(1000)
                .limit(50);
    }

    static Map<String, Object> harness(MongoTemplate template) {
        java.util.List<OrderLine> rows = template.find(query(), OrderLine.class);
        long count = rows.size();
        OrderLine first = null;
        if (count > 0) {
            first = rows.get(0);
        }
        OrderLine last = null;
        if (count > 1) {
            last = rows.get(rows.size() - 1);
        }
        var result = new java.util.HashMap<String, Object>();
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
                Aggregation.project("count").and("taxRate").previousOperation(),
                Aggregation.sort(Sort.Direction.DESC, "count"));
    }

    static Map<String, Object> harness(MongoTemplate template) {
        var baseAgg = query();

        var countOps = new java.util.ArrayList<>(baseAgg.getPipeline().getOperations());
        countOps.add(Aggregation.count().as("count"));
        var countAgg = Aggregation.newAggregation(OrderLine.class, countOps);
        CountProjection countResult = template.aggregate(countAgg, OrderLine.class, CountProjection.class).getUniqueMappedResult();
        long count = countResult != null ? countResult.count() : 0L;

        TaxRateCount first = null;
        if (count > 0) {
            var firstOps = new java.util.ArrayList<>(baseAgg.getPipeline().getOperations());
            firstOps.add(Aggregation.sort(Sort.Direction.ASC, "taxRate"));
            firstOps.add(Aggregation.limit(1));
            var firstAgg = Aggregation.newAggregation(OrderLine.class, firstOps);
            first = template.aggregate(firstAgg, OrderLine.class, TaxRateCount.class).getUniqueMappedResult();
        }

        TaxRateCount last = null;
        if (count > 1) {
            var lastOps = new java.util.ArrayList<>(baseAgg.getPipeline().getOperations());
            lastOps.add(Aggregation.sort(Sort.Direction.DESC, "taxRate"));
            lastOps.add(Aggregation.limit(1));
            var lastAgg = Aggregation.newAggregation(OrderLine.class, lastOps);
            last = template.aggregate(lastAgg, OrderLine.class, TaxRateCount.class).getUniqueMappedResult();
        }

        var result = new java.util.HashMap<String, Object>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
    }
}

final class Query8 {
    static Map<String, Object> harness(MongoTemplate template) {
        var agg = Aggregation.newAggregation(
                OrderLine.class,
                Aggregation.group().max("unitPrice").as("maxUnitPrice"));
        MaxProjection maxResult = template.aggregate(agg, OrderLine.class, MaxProjection.class).getUniqueMappedResult();
        java.math.BigDecimal max = maxResult != null ? maxResult.maxUnitPrice() : null;
        long count = max != null ? 1 : 0;

        var result = new java.util.HashMap<String, Object>();
        result.put("count", count);
        result.put("firstSample", max);
        result.put("lastSample", null);
        return result;
    }
}

final class Query9 {
    static Map<String, Object> harness(MongoTemplate template) {
        var agg = Aggregation.newAggregation(
                OrderLine.class,
                Aggregation.group().sum(
                        org.springframework.data.mongodb.core.aggregation.ArithmeticOperators.Multiply.valueOf("quantity").multiplyBy("unitPrice"))
                        .as("total"));
        SumProjection sumResult = template.aggregate(agg, OrderLine.class, SumProjection.class).getUniqueMappedResult();
        java.math.BigDecimal total = sumResult != null ? sumResult.total() : null;
        long count = total != null ? 1 : 0;

        var result = new java.util.HashMap<String, Object>();
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
        Order first = null;
        if (count > 0) {
            first = template.findOne(q, Order.class);
            if (first != null) {
                java.util.List<OrderLine> lines = template.find(
                        new Query(Criteria.where("orderId").is(first.getOrderId()))
                                .with(Sort.by(Sort.Direction.ASC, "orderLineId")),
                        OrderLine.class);
                first.setOrderLines(lines);
            }
        }
        Order last = null;
        if (count > 1) {
            last = template.findOne(
                    new Query(Criteria.where("orderId").is(530))
                            .with(Sort.by(Sort.Direction.DESC, "orderId")),
                    Order.class);
            if (last != null) {
                java.util.List<OrderLine> lines = template.find(
                        new Query(Criteria.where("orderId").is(last.getOrderId()))
                                .with(Sort.by(Sort.Direction.ASC, "orderLineId")),
                        OrderLine.class);
                last.setOrderLines(lines);
            }
        }
        var result = new java.util.HashMap<String, Object>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
    }
}

final class Query11 {
    static Query query() {
        return new Query()
                .with(Sort.by(Sort.Direction.ASC, "expectedDeliveryDate", "orderId"))
                .limit(1000);
    }

    static Map<String, Object> harness(MongoTemplate template) {
        java.util.List<Order> rows = template.find(query(), Order.class);
        long count = rows.size();
        Order first = null;
        if (count > 0) {
            first = rows.get(0);
        }
        Order last = null;
        if (count > 1) {
            last = rows.get(rows.size() - 1);
        }
        var result = new java.util.HashMap<String, Object>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
    }
}

final class Query12 {
    static Map<String, Object> harness(MongoTemplate template) {
        Query q = new Query();
        q.fields().include("customerPurchaseOrderNumber");
        java.util.List<String> values = template.findDistinct(q, "customerPurchaseOrderNumber", Order.class, String.class);
        java.util.List<String> sorted = values.stream()
                .sorted(java.util.Comparator.nullsFirst(java.util.Comparator.naturalOrder()))
                .toList();
        long count = sorted.size();
        String first = null;
        if (count > 0) {
            first = sorted.get(0);
        }
        String last = null;
        if (count > 1) {
            last = sorted.get(sorted.size() - 1);
        }
        var result = new java.util.HashMap<String, Object>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
    }
}

final class Query13 {
    static Query query() {
        return new Query(Criteria.where("customFields").regex("\"Title\"\\s*:\\s*\"Team Member\"", "i"))
                .with(Sort.by(Sort.Direction.ASC, "personId"));
    }

    static Map<String, Object> harness(MongoTemplate template) {
        Query q = query();
        long count = template.count(q, Person.class);
        Person first = null;
        if (count > 0) {
            first = template.findOne(query().limit(1), Person.class);
        }
        Person last = null;
        if (count > 1) {
            last = template.findOne(
                    new Query(Criteria.where("customFields").regex("\"Title\"\\s*:\\s*\"Team Member\"", "i"))
                            .with(Sort.by(Sort.Direction.DESC, "personId"))
                            .limit(1),
                    Person.class);
        }
        var result = new java.util.HashMap<String, Object>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
    }
}

final class Query14 {
    static Query query() {
        return new Query(Criteria.where("otherLanguages").regex("\"Slovak\"", "i"))
                .with(Sort.by(Sort.Direction.ASC, "personId"));
    }

    static Map<String, Object> harness(MongoTemplate template) {
        Query q = query();
        long count = template.count(q, Person.class);
        Person first = null;
        if (count > 0) {
            first = template.findOne(query().limit(1), Person.class);
        }
        Person last = null;
        if (count > 1) {
            last = template.findOne(
                    new Query(Criteria.where("otherLanguages").regex("\"Slovak\"", "i"))
                            .with(Sort.by(Sort.Direction.DESC, "personId"))
                            .limit(1),
                    Person.class);
        }
        var result = new java.util.HashMap<String, Object>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
    }
}

final class Query15 {
    static Map<String, Object> harness(MongoTemplate template) {
        Query q1 = new Query(Criteria.where("supplierId").lt(5));
        q1.fields().include("supplierId");
        Query q2 = new Query(Criteria.where("supplierId").gte(5).lte(10));
        q2.fields().include("supplierId");

        java.util.List<Integer> first = template.find(q1, Supplier.class).stream()
                .map(Supplier::getSupplierId)
                .toList();
        java.util.List<Integer> last = template.find(q2, Supplier.class).stream()
                .map(Supplier::getSupplierId)
                .toList();

        java.util.Set<Integer> union = new java.util.LinkedHashSet<>(first);
        union.addAll(last);
        java.util.List<Integer> sorted = union.stream().sorted().toList();

        long count = sorted.size();
        Integer firstSample = null;
        if (count > 0) {
            firstSample = sorted.get(0);
        }
        Integer lastSample = null;
        if (count > 1) {
            lastSample = sorted.get(sorted.size() - 1);
        }

        var result = new java.util.HashMap<String, Object>();
        result.put("count", count);
        result.put("firstSample", firstSample);
        result.put("lastSample", lastSample);
        return result;
    }
}