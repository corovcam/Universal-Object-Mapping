import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;
import org.springframework.data.domain.Sort;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.mongodb.core.aggregation.Aggregation;
import org.springframework.data.mongodb.core.query.Criteria;
import org.springframework.data.mongodb.core.query.Query;

record TaxRateCount(BigDecimal taxRate, Integer count) {
}

record OrderLineQuantity(Integer orderLineId, Integer quantity) {
}

public class MongoQueryEntrypoint {

    public static List<OrderLine> query1(MongoTemplate mongoTemplate) {
        LocalDate from = LocalDate.of(2014, 12, 20);
        LocalDate to = LocalDate.of(2014, 12, 31);
        Query query = Query.query(Criteria.where("pickingCompletedWhen").gte(from).lte(to));
        return mongoTemplate.find(query, OrderLine.class);
    }

    public static List<Order> query2(MongoTemplate mongoTemplate) {
        Query orderQuery = Query.query(Criteria.where("customerId").is(1));
        List<Order> orders = mongoTemplate.find(orderQuery, Order.class);
        if (!orders.isEmpty()) {
            List<Integer> orderIds = orders.stream().map(Order::getOrderId).toList();
            Query lineQuery = Query.query(Criteria.where("orderId").in(orderIds));
            List<OrderLine> lines = mongoTemplate.find(lineQuery, OrderLine.class);
            Map<Integer, List<OrderLine>> linesByOrderId = lines.stream()
                .collect(Collectors.groupingBy(OrderLine::getOrderId));
            for (Order order : orders) {
                order.setOrderLines(linesByOrderId.getOrDefault(order.getOrderId(), new ArrayList<>()));
            }
        }
        return orders;
    }

    public static List<TaxRateCount> query3(MongoTemplate mongoTemplate) {
        Aggregation aggregation = Aggregation.newAggregation(
            OrderLine.class,
            Aggregation.group("taxRate").count().as("count"),
            Aggregation.project("count").and("taxRate").previousOperation(),
            Aggregation.sort(Sort.Direction.DESC, "count")
        );
        return mongoTemplate.aggregate(aggregation, OrderLine.class, TaxRateCount.class).getMappedResults();
    }

    public static List<OrderLine> query4(MongoTemplate mongoTemplate) {
        Query query = new Query().with(Sort.by(Sort.Direction.DESC, "quantity")).limit(50);
        return mongoTemplate.find(query, OrderLine.class);
    }

    public static List<OrderLineQuantity> query5(MongoTemplate mongoTemplate) {
        Query query = new Query();
        query.fields().include("orderLineId", "quantity").exclude("_id");
        return mongoTemplate.find(query, OrderLineQuantity.class, "orderLines");
    }
}