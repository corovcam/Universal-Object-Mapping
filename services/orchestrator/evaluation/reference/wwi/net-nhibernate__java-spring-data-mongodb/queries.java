package uom.services;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;

import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.mongodb.core.query.Criteria;
import org.springframework.data.mongodb.core.query.Query;

public class MongoQueries {

    public static Query query1() {
        LocalDate from = LocalDate.of(2014, 12, 20);
        LocalDate to = LocalDate.of(2014, 12, 31);
        return new Query(Criteria.where("pickingCompletedWhen").gte(from).lte(to));
    }

    public static Query query2() {
        return new Query(Criteria.where("orderId").is(26866));
    }

    public static Query query3() {
        return new Query(Criteria.where("unitPrice").is(new BigDecimal("25.00")));
    }

    public static Query query4() {
        return new Query(Criteria.where("orderId").in(List.of(1, 10, 100, 1000, 10000)));
    }

    public static Query query5() {
        return new Query(Criteria.where("description").regex("C\\+\\+"));
    }
}