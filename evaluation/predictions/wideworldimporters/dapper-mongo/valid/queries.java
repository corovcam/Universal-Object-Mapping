import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;
import org.springframework.data.domain.Sort;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.mongodb.core.aggregation.Aggregation;
import org.springframework.data.mongodb.core.query.Criteria;
import org.springframework.data.mongodb.core.query.Query;

class MongoQueryEntrypoint {
    private final MongoTemplate mongoTemplate;

    MongoQueryEntrypoint(MongoTemplate mongoTemplate) {
        this.mongoTemplate = mongoTemplate;
    }

    List<OrderLine> query1() {
        LocalDateTime from = LocalDateTime.of(2014, 12, 20, 0, 0);
        LocalDateTime to = LocalDateTime.of(2014, 12, 31, 23, 59, 59);
        Query query = Query.query(Criteria.where("pickingCompletedWhen").gte(from).lte(to));
        return mongoTemplate.find(query, OrderLine.class);
    }

    List<Order> query2() {
        Query query = Query.query(Criteria.where("customerId").is(1));
        return mongoTemplate.find(query, Order.class);
    }

    record TaxRateCount(BigDecimal taxRate, Long count) {
    }

    List<TaxRateCount> query3() {
        var aggregation = Aggregation.newAggregation(
            OrderLine.class,
            Aggregation.group("taxRate").count().as("count"),
            Aggregation.project("count").and("_id").as("taxRate"),
            Aggregation.sort(Sort.Direction.DESC, "count")
        );
        return mongoTemplate.aggregate(aggregation, OrderLine.class, TaxRateCount.class).getMappedResults();
    }

    List<OrderLine> query4() {
        Query query = new Query().with(Sort.by(Sort.Direction.DESC, "quantity")).limit(50);
        return mongoTemplate.find(query, OrderLine.class);
    }

    record OrderLineQuantity(Integer orderLineId, Integer quantity) {
    }

    List<OrderLineQuantity> query5() {
        Query query = new Query();
        query.fields().include("orderLineId", "quantity");
        return mongoTemplate.find(query, OrderLine.class).stream()
            .map(ol -> new OrderLineQuantity(ol.getOrderLineId(), ol.getQuantity()))
            .toList();
    }
}