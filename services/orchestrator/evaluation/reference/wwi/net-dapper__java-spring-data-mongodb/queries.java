package uom.services;

import java.time.LocalDate;
import java.util.List;

import org.springframework.data.domain.Sort;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.mongodb.core.aggregation.Aggregation;
import org.springframework.data.mongodb.core.aggregation.AggregationOperation;
import org.springframework.data.mongodb.core.query.Criteria;
import org.springframework.data.mongodb.core.query.Query;
import org.springframework.data.mongodb.core.query.Fields;

final class Queries {

    public static List<OrderLine> query1(MongoTemplate template) {
        LocalDate from = LocalDate.of(2014, 12, 20);
        LocalDate to = LocalDate.of(2014, 12, 31);
        Query query = new Query(Criteria.where("pickingCompletedWhen").gte(from).lte(to));
        return template.find(query, OrderLine.class);
    }

    public static List<Order> query2(MongoTemplate template) {
        Query query = new Query(Criteria.where("customerId").is(1));
        return template.find(query, Order.class);
    }

    public static List<?> query3(MongoTemplate template) {
        AggregationOperation group = Aggregation.group("taxRate").count().as("count");
        AggregationOperation project = Aggregation.project("count").and("taxRate").previousOperation();
        AggregationOperation sort = Aggregation.sort(Sort.Direction.DESC, "count");
        Aggregation aggregation = Aggregation.newAggregation(OrderLine.class, group, project, sort);
        return template.aggregate(aggregation, OrderLine.class, Object.class).getMappedResults();
    }

    public static List<OrderLine> query4(MongoTemplate template) {
        Query query = new Query().with(Sort.by(Sort.Direction.DESC, "quantity")).limit(50);
        return template.find(query, OrderLine.class);
    }

    public static List<?> query5(MongoTemplate template) {
        Query query = new Query();
        query.fields().include("orderLineId", "quantity");
        return template.find(query, Query5Projection.class, OrderLine.class);
    }
}

interface Query5Projection {
    Integer getOrderLineId();
    Integer getQuantity();
}