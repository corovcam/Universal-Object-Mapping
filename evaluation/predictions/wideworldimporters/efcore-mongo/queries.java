import java.math.*;
import java.time.*;
import java.util.*;
import java.util.stream.*;

import javax.management.*;

import org.springframework.data.domain.Sort;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.mongodb.core.aggregation.Aggregation;
import org.springframework.data.mongodb.core.query.Criteria;ia;

class TaxRateCount {
    private BigDecimal taxRate;
    private Long count;

    public BigDecimal getTaxRate() { return taxRate; }
    public void setTaxRate(BigDecimal taxRate) { this.taxRate = taxRate; }
    public Long getCount() { return count; }
    public void setCount(Long count) { this.count = count; }
}

interface OrderLineProjection {
    Integer getOrderLineId();
    Integer getQuantity();
}

class MongoQueryEntrypoint {
    private final MongoTemplate mongoTemplate;

    MongoQueryEntrypoint(MongoTemplate mongoTemplate) {
        this.mongoTemplate = mongoTemplate;
    }

    List<OrderLine> query1() {
        LocalDate from = LocalDate.of(2014, 12, 20);
        LocalDate to = LocalDate.of(2014, 12, 31);
        Query query = Query.query(Criteria.where("pickingCompletedWhen").gte(from).lte(to));
        return mongoTemplate.find(query, OrderLine.class);
    }

    List<Order> query2() {
        Query query = Query.query(Criteria.where("customerId").is(1));
        return mongoTemplate.find(query, Order.class);
    }

    List<TaxRateCount> query3() {
        Aggregation aggregation = Aggregation.newAggregation(
            Aggregation.group("taxRate").count().as("count"),
            Aggregation.project("count").and("taxRate").previousOperation(),
            Aggregation.sort(Sort.Direction.DESC, "count")
        );
        AggregationResults<TaxRateCount> results = mongoTemplate.aggregate(aggregation, "orderLines", TaxRateCount.class);
        return results.getMappedResults();
    }

    List<OrderLine> query4() {
        Query query = new Query().with(Sort.by(Sort.Direction.DESC, "quantity")).limit(50);
        return mongoTemplate.find(query, OrderLine.class);
    }

    List<OrderLineProjection> query5() {
        Query query = new Query();
        query.fields().include("orderLineId", "quantity");
        return mongoTemplate.query(OrderLine.class)
            .as(OrderLineProjection.class)
            .matching(query)
            .all();
    }
}