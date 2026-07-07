package uom.services;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;

import org.springframework.data.mongodb.core.query.Criteria;
import org.springframework.data.mongodb.core.query.Query;

final class Query1 {
    public static Query query() {
        LocalDate from = LocalDate.of(2014, 12, 20);
        LocalDate to = LocalDate.of(2014, 12, 31);
        return new Query(Criteria.where("pickingCompletedWhen").gte(from).lte(to));
    }
}

final class Query2 {
    public static Query query() {
        return new Query(Criteria.where("orderId").is(26866));
    }
}

final class Query3 {
    public static Query query() {
        BigDecimal unitPrice = new BigDecimal("25.00");
        return new Query(Criteria.where("unitPrice").is(unitPrice));
    }
}

final class Query4 {
    public static Query query() {
        List<Integer> ids = List.of(1, 10, 100, 1000, 10000);
        return new Query(Criteria.where("orderId").in(ids));
    }
}

final class Query5 {
    public static Query query() {
        return new Query(Criteria.where("description").regex(".*C\\+\\+.*"));
    }
}