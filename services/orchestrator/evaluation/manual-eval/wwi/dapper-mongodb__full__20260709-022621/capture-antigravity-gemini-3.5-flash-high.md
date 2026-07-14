```source_schema_body
using System;
using System.Collections.Generic;

public class OrderLine
{
    public int OrderLineID { get; set; }
    public int OrderID { get; set; }
    public int StockItemID { get; set; }
    public required string Description { get; set; }
    public int PackageTypeID { get; set; }
    public int Quantity { get; set; }
    public decimal? UnitPrice { get; set; }
    public decimal TaxRate { get; set; }
    public int PickedQuantity { get; set; }
    public DateTime? PickingCompletedWhen { get; set; }
    public int LastEditedBy { get; set; }
    public DateTime LastEditedWhen { get; set; }
}

public class Order
{
    public int OrderID { get; set; }
    public int CustomerID { get; set; }
    public int SalespersonPersonID { get; set; }
    public int? PickedByPersonID { get; set; }
    public int ContactPersonID { get; set; }
    public int? BackorderOrderID { get; set; }
    public DateTime OrderDate { get; set; }
    public DateTime ExpectedDeliveryDate { get; set; }
    public string? CustomerPurchaseOrderNumber { get; set; }
    public bool IsUndersupplyBackordered { get; set; }
    public string? Comments { get; set; }
    public string? DeliveryInstructions { get; set; }
    public string? InternalComments { get; set; }
    public DateTime? PickingCompletedWhen { get; set; }
    public int LastEditedBy { get; set; }
    public DateTime LastEditedWhen { get; set; }
    public List<OrderLine> OrderLines { get; set; } = [];
}

public class Person
{
    public int PersonID { get; set; }
    public required string FullName { get; set; }
    public required string PreferredName { get; set; }
    public string? EmailAddress { get; set; }
    public string? CustomFields { get; set; }
    public string? OtherLanguages { get; set; }
}

public class Supplier
{
    public int SupplierID { get; set; }
    public required string SupplierName { get; set; }
    public string? SupplierReference { get; set; }
    public int PaymentDays { get; set; }
}
```

```target_schema_body
import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import org.springframework.data.annotation.Id;
import org.springframework.data.annotation.ReadOnlyProperty;
import org.springframework.data.mongodb.core.mapping.Document;
import org.springframework.data.mongodb.core.mapping.DocumentReference;
import org.springframework.data.mongodb.core.mapping.Field;
import org.springframework.data.mongodb.core.mapping.FieldType;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

@Document(collection = "orderLines")
@JsonIgnoreProperties({ "id" })
class OrderLine {
    @Id
    private String id;
    @Field("orderLineId")
    private Integer orderLineId;
    @Field("orderId")
    private Integer orderId;
    @Field("stockItemId")
    private Integer stockItemId;
    private String description;
    @Field("packageTypeId")
    private Integer packageTypeId;
    private Integer quantity;
    @Field(targetType = FieldType.DECIMAL128)
    private BigDecimal unitPrice;
    @Field(value = "taxRate", targetType = FieldType.DECIMAL128)
    private BigDecimal taxRate;
    @Field("pickedQuantity")
    private Integer pickedQuantity;
    @Field("pickingCompletedWhen")
    private LocalDateTime pickingCompletedWhen;
    @Field("lastEditedBy")
    private Integer lastEditedBy;
    @Field("lastEditedWhen")
    private LocalDateTime lastEditedWhen;

    public OrderLine() {}

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    public Integer getOrderLineId() { return orderLineId; }
    public void setOrderLineId(Integer orderLineId) { this.orderLineId = orderLineId; }
    public Integer getOrderId() { return orderId; }
    public void setOrderId(Integer orderId) { this.orderId = orderId; }
    public Integer getStockItemId() { return stockItemId; }
    public void setStockItemId(Integer stockItemId) { this.stockItemId = stockItemId; }
    public String getDescription() { return description; }
    public void setDescription(String description) { this.description = description; }
    public Integer getPackageTypeId() { return packageTypeId; }
    public void setPackageTypeId(Integer packageTypeId) { this.packageTypeId = packageTypeId; }
    public Integer getQuantity() { return quantity; }
    public void setQuantity(Integer quantity) { this.quantity = quantity; }
    public BigDecimal getUnitPrice() { return unitPrice; }
    public void setUnitPrice(BigDecimal unitPrice) { this.unitPrice = unitPrice; }
    public BigDecimal getTaxRate() { return taxRate; }
    public void setTaxRate(BigDecimal taxRate) { this.taxRate = taxRate; }
    public Integer getPickedQuantity() { return pickedQuantity; }
    public void setPickedQuantity(Integer pickedQuantity) { this.pickedQuantity = pickedQuantity; }
    public LocalDateTime getPickingCompletedWhen() { return pickingCompletedWhen; }
    public void setPickingCompletedWhen(LocalDateTime pickingCompletedWhen) { this.pickingCompletedWhen = pickingCompletedWhen; }
    public Integer getLastEditedBy() { return lastEditedBy; }
    public void setLastEditedBy(Integer lastEditedBy) { this.lastEditedBy = lastEditedBy; }
    public LocalDateTime getLastEditedWhen() { return lastEditedWhen; }
    public void setLastEditedWhen(LocalDateTime lastEditedWhen) { this.lastEditedWhen = lastEditedWhen; }
}

@Document(collection = "orders")
@JsonIgnoreProperties({ "id" })
class Order {
    @Id
    private String id;
    @Field("orderId")
    private Integer orderId;
    @Field("customerId")
    private Integer customerId;
    @Field("salespersonPersonId")
    private Integer salespersonPersonId;
    @Field("pickedByPersonId")
    private Integer pickedByPersonId;
    @Field("contactPersonId")
    private Integer contactPersonId;
    @Field("backorderOrderId")
    private Integer backorderOrderId;
    @Field("orderDate")
    private LocalDate orderDate;
    @Field("expectedDeliveryDate")
    private LocalDate expectedDeliveryDate;
    @Field("customerPurchaseOrderNumber")
    private String customerPurchaseOrderNumber;
    @Field("isUndersupplyBackordered")
    private Boolean isUndersupplyBackordered;
    private String comments;
    @Field("deliveryInstructions")
    private String deliveryInstructions;
    @Field("internalComments")
    private String internalComments;
    @Field("pickingCompletedWhen")
    private LocalDateTime pickingCompletedWhen;
    @Field("lastEditedBy")
    private Integer lastEditedBy;
    @Field("lastEditedWhen")
    private LocalDateTime lastEditedWhen;

    @ReadOnlyProperty
    @DocumentReference(lazy = true, lookup = "{ 'orderId': ?#{#self.orderId} }", sort = "{ 'orderLineId': 1 }")
    private List<OrderLine> orderLines = new ArrayList<>();

    public Order() {}

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    public Integer getOrderId() { return orderId; }
    public void setOrderId(Integer orderId) { this.orderId = orderId; }
    public Integer getCustomerId() { return customerId; }
    public void setCustomerId(Integer customerId) { this.customerId = customerId; }
    public Integer getSalespersonPersonId() { return salespersonPersonId; }
    public void setSalespersonPersonId(Integer salespersonPersonId) { this.salespersonPersonId = salespersonPersonId; }
    public Integer getPickedByPersonId() { return pickedByPersonId; }
    public void setPickedByPersonId(Integer pickedByPersonId) { this.pickedByPersonId = pickedByPersonId; }
    public Integer getContactPersonId() { return contactPersonId; }
    public void setContactPersonId(Integer contactPersonId) { this.contactPersonId = contactPersonId; }
    public Integer getBackorderOrderId() { return backorderOrderId; }
    public void setBackorderOrderId(Integer backorderOrderId) { this.backorderOrderId = backorderOrderId; }
    public LocalDate getOrderDate() { return orderDate; }
    public void setOrderDate(LocalDate orderDate) { this.orderDate = orderDate; }
    public LocalDate getExpectedDeliveryDate() { return expectedDeliveryDate; }
    public void setExpectedDeliveryDate(LocalDate expectedDeliveryDate) { this.expectedDeliveryDate = expectedDeliveryDate; }
    public String getCustomerPurchaseOrderNumber() { return customerPurchaseOrderNumber; }
    public void setCustomerPurchaseOrderNumber(String customerPurchaseOrderNumber) { this.customerPurchaseOrderNumber = customerPurchaseOrderNumber; }
    public Boolean getIsUndersupplyBackordered() { return isUndersupplyBackordered; }
    public void setIsUndersupplyBackordered(Boolean isUndersupplyBackordered) { this.isUndersupplyBackordered = isUndersupplyBackordered; }
    public String getComments() { return comments; }
    public void setComments(String comments) { this.comments = comments; }
    public String getDeliveryInstructions() { return deliveryInstructions; }
    public void setDeliveryInstructions(String deliveryInstructions) { this.deliveryInstructions = deliveryInstructions; }
    public String getInternalComments() { return internalComments; }
    public void setInternalComments(String internalComments) { this.internalComments = internalComments; }
    public LocalDateTime getPickingCompletedWhen() { return pickingCompletedWhen; }
    public void setPickingCompletedWhen(LocalDateTime pickingCompletedWhen) { this.pickingCompletedWhen = pickingCompletedWhen; }
    public Integer getLastEditedBy() { return lastEditedBy; }
    public void setLastEditedBy(Integer lastEditedBy) { this.lastEditedBy = lastEditedBy; }
    public LocalDateTime getLastEditedWhen() { return lastEditedWhen; }
    public void setLastEditedWhen(LocalDateTime lastEditedWhen) { this.lastEditedWhen = lastEditedWhen; }
    public List<OrderLine> getOrderLines() { return orderLines; }
    public void setOrderLines(List<OrderLine> orderLines) { this.orderLines = orderLines; }
}

@Document(collection = "people")
@JsonIgnoreProperties({ "id" })
class Person {
    @Id
    private String id;
    @Field("personId")
    private Integer personId;
    @Field("fullName")
    private String fullName;
    @Field("preferredName")
    private String preferredName;
    @Field("emailAddress")
    private String emailAddress;
    @Field("customFields")
    private String customFields;
    @Field("otherLanguages")
    private String otherLanguages;

    public Person() {}

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    public Integer getPersonId() { return personId; }
    public void setPersonId(Integer personId) { this.personId = personId; }
    public String getFullName() { return fullName; }
    public void setFullName(String fullName) { this.fullName = fullName; }
    public String getPreferredName() { return preferredName; }
    public void setPreferredName(String preferredName) { this.preferredName = preferredName; }
    public String getEmailAddress() { return emailAddress; }
    public void setEmailAddress(String emailAddress) { this.emailAddress = emailAddress; }
    public String getCustomFields() { return customFields; }
    public void setCustomFields(String customFields) { this.customFields = customFields; }
    public String getOtherLanguages() { return otherLanguages; }
    public void setOtherLanguages(String otherLanguages) { this.otherLanguages = otherLanguages; }
}

@Document(collection = "suppliers")
@JsonIgnoreProperties({ "id" })
class Supplier {
    @Id
    private String id;
    @Field("supplierId")
    private Integer supplierId;
    @Field("supplierName")
    private String supplierName;
    @Field("supplierReference")
    private String supplierReference;
    @Field("paymentDays")
    private Integer paymentDays;

    public Supplier() {}

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    public Integer getSupplierId() { return supplierId; }
    public void setSupplierId(Integer supplierId) { this.supplierId = supplierId; }
    public String getSupplierName() { return supplierName; }
    public void setSupplierName(String supplierName) { this.supplierName = supplierName; }
    public String getSupplierReference() { return supplierReference; }
    public void setSupplierReference(String supplierReference) { this.supplierReference = supplierReference; }
    public Integer getPaymentDays() { return paymentDays; }
    public void setPaymentDays(Integer paymentDays) { this.paymentDays = paymentDays; }
}
```

```source_query_body id=1
using Dapper;
using Microsoft.Data.SqlClient;
using System.Collections.Generic;

public static class Query1
{
    public static object Harness(SqlConnection conn)
    {
        string sql = @"SELECT * FROM Sales.OrderLines WHERE OrderID = @OrderID";
        return HarnessSupport.RunRows(() => conn.Query<OrderLine>(sql, new { OrderID = 26866 }), x => x.OrderLineID);
    }
}
```

```target_query_body id=1
final class Query1 {
    static java.util.Map<String, Object> harness(org.springframework.data.mongodb.core.MongoTemplate template) {
        org.springframework.data.mongodb.core.query.Query query = new org.springframework.data.mongodb.core.query.Query(
            org.springframework.data.mongodb.core.query.Criteria.where("orderId").is(26866)
        );
        long count = template.count(query, OrderLine.class);
        Object first = null;
        if (count > 0) {
            first = template.findOne(
                new org.springframework.data.mongodb.core.query.Query(
                    org.springframework.data.mongodb.core.query.Criteria.where("orderId").is(26866)
                ).with(org.springframework.data.domain.Sort.by(org.springframework.data.domain.Sort.Direction.ASC, "orderLineId")).limit(1),
                OrderLine.class
            );
        }
        Object last = null;
        if (count > 1) {
            last = template.findOne(
                new org.springframework.data.mongodb.core.query.Query(
                    org.springframework.data.mongodb.core.query.Criteria.where("orderId").is(26866)
                ).with(org.springframework.data.domain.Sort.by(org.springframework.data.domain.Sort.Direction.DESC, "orderLineId")).limit(1),
                OrderLine.class
            );
        }
        java.util.Map<String, Object> map = new java.util.LinkedHashMap<>();
        map.put("count", count);
        map.put("firstSample", first);
        map.put("lastSample", last);
        return map;
    }
}
```

```source_query_body id=2
using Dapper;
using Microsoft.Data.SqlClient;
using System.Collections.Generic;

public static class Query2
{
    public static object Harness(SqlConnection conn)
    {
        string sql = @"SELECT * FROM Sales.OrderLines WHERE UnitPrice = @UnitPrice";
        return HarnessSupport.RunRows(() => conn.Query<OrderLine>(sql, new { UnitPrice = 25m }), x => x.OrderLineID);
    }
}
```

```target_query_body id=2
final class Query2 {
    static java.util.Map<String, Object> harness(org.springframework.data.mongodb.core.MongoTemplate template) {
        java.math.BigDecimal unitPrice = new java.math.BigDecimal("25");
        org.springframework.data.mongodb.core.query.Query query = new org.springframework.data.mongodb.core.query.Query(
            org.springframework.data.mongodb.core.query.Criteria.where("unitPrice").is(unitPrice)
        );
        long count = template.count(query, OrderLine.class);
        Object first = null;
        if (count > 0) {
            first = template.findOne(
                new org.springframework.data.mongodb.core.query.Query(
                    org.springframework.data.mongodb.core.query.Criteria.where("unitPrice").is(unitPrice)
                ).with(org.springframework.data.domain.Sort.by(org.springframework.data.domain.Sort.Direction.ASC, "orderLineId")).limit(1),
                OrderLine.class
            );
        }
        Object last = null;
        if (count > 1) {
            last = template.findOne(
                new org.springframework.data.mongodb.core.query.Query(
                    org.springframework.data.mongodb.core.query.Criteria.where("unitPrice").is(unitPrice)
                ).with(org.springframework.data.domain.Sort.by(org.springframework.data.domain.Sort.Direction.DESC, "orderLineId")).limit(1),
                OrderLine.class
            );
        }
        java.util.Map<String, Object> map = new java.util.LinkedHashMap<>();
        map.put("count", count);
        map.put("firstSample", first);
        map.put("lastSample", last);
        return map;
    }
}
```

```source_query_body id=3
using Dapper;
using Microsoft.Data.SqlClient;
using System;
using System.Collections.Generic;

public static class Query3
{
    public static object Harness(SqlConnection conn)
    {
        var from = new DateTime(2014, 12, 20);
        var to = new DateTime(2014, 12, 31);
        string sql = @"SELECT * FROM Sales.OrderLines WHERE PickingCompletedWhen >= @From AND PickingCompletedWhen <= @To";
        return HarnessSupport.RunRows(() => conn.Query<OrderLine>(sql, new { From = from, To = to }), x => x.OrderLineID);
    }
}
```

```target_query_body id=3
final class Query3 {
    static java.util.Map<String, Object> harness(org.springframework.data.mongodb.core.MongoTemplate template) {
        java.time.LocalDateTime from = java.time.LocalDateTime.of(2014, 12, 20, 0, 0);
        java.time.LocalDateTime to = java.time.LocalDateTime.of(2014, 12, 31, 0, 0);
        org.springframework.data.mongodb.core.query.Query query = new org.springframework.data.mongodb.core.query.Query(
            org.springframework.data.mongodb.core.query.Criteria.where("pickingCompletedWhen").gte(from).lte(to)
        );
        long count = template.count(query, OrderLine.class);
        Object first = null;
        if (count > 0) {
            first = template.findOne(
                new org.springframework.data.mongodb.core.query.Query(
                    org.springframework.data.mongodb.core.query.Criteria.where("pickingCompletedWhen").gte(from).lte(to)
                ).with(org.springframework.data.domain.Sort.by(org.springframework.data.domain.Sort.Direction.ASC, "orderLineId")).limit(1),
                OrderLine.class
            );
        }
        Object last = null;
        if (count > 1) {
            last = template.findOne(
                new org.springframework.data.mongodb.core.query.Query(
                    org.springframework.data.mongodb.core.query.Criteria.where("pickingCompletedWhen").gte(from).lte(to)
                ).with(org.springframework.data.domain.Sort.by(org.springframework.data.domain.Sort.Direction.DESC, "orderLineId")).limit(1),
                OrderLine.class
            );
        }
        java.util.Map<String, Object> map = new java.util.LinkedHashMap<>();
        map.put("count", count);
        map.put("firstSample", first);
        map.put("lastSample", last);
        return map;
    }
}
```

```source_query_body id=4
using Dapper;
using Microsoft.Data.SqlClient;
using System.Collections.Generic;

public static class Query4
{
    public static object Harness(SqlConnection conn)
    {
        var orderIds = new[] { 1, 10, 100, 1000, 10000 };
        string sql = @"SELECT * FROM Sales.OrderLines WHERE OrderID IN @Ids";
        return HarnessSupport.RunRows(() => conn.Query<OrderLine>(sql, new { Ids = orderIds }), x => x.OrderLineID);
    }
}
```

```target_query_body id=4
final class Query4 {
    static java.util.Map<String, Object> harness(org.springframework.data.mongodb.core.MongoTemplate template) {
        java.util.List<Integer> orderIds = java.util.List.of(1, 10, 100, 1000, 10000);
        org.springframework.data.mongodb.core.query.Query query = new org.springframework.data.mongodb.core.query.Query(
            org.springframework.data.mongodb.core.query.Criteria.where("orderId").in(orderIds)
        );
        long count = template.count(query, OrderLine.class);
        Object first = null;
        if (count > 0) {
            first = template.findOne(
                new org.springframework.data.mongodb.core.query.Query(
                    org.springframework.data.mongodb.core.query.Criteria.where("orderId").in(orderIds)
                ).with(org.springframework.data.domain.Sort.by(org.springframework.data.domain.Sort.Direction.ASC, "orderLineId")).limit(1),
                OrderLine.class
            );
        }
        Object last = null;
        if (count > 1) {
            last = template.findOne(
                new org.springframework.data.mongodb.core.query.Query(
                    org.springframework.data.mongodb.core.query.Criteria.where("orderId").in(orderIds)
                ).with(org.springframework.data.domain.Sort.by(org.springframework.data.domain.Sort.Direction.DESC, "orderLineId")).limit(1),
                OrderLine.class
            );
        }
        java.util.Map<String, Object> map = new java.util.LinkedHashMap<>();
        map.put("count", count);
        map.put("firstSample", first);
        map.put("lastSample", last);
        return map;
    }
}
```

```source_query_body id=5
using Dapper;
using Microsoft.Data.SqlClient;
using System.Collections.Generic;

public static class Query5
{
    public static object Harness(SqlConnection conn)
    {
        string sql = @"SELECT * FROM Sales.OrderLines WHERE Description LIKE @Pattern";
        return HarnessSupport.RunRows(() => conn.Query<OrderLine>(sql, new { Pattern = "%C++%" }), x => x.OrderLineID);
    }
}
```

```target_query_body id=5
final class Query5 {
    static java.util.Map<String, Object> harness(org.springframework.data.mongodb.core.MongoTemplate template) {
        org.springframework.data.mongodb.core.query.Query query = new org.springframework.data.mongodb.core.query.Query(
            org.springframework.data.mongodb.core.query.Criteria.where("description").regex("C\\+\\+")
        );
        long count = template.count(query, OrderLine.class);
        Object first = null;
        if (count > 0) {
            first = template.findOne(
                new org.springframework.data.mongodb.core.query.Query(
                    org.springframework.data.mongodb.core.query.Criteria.where("description").regex("C\\+\\+")
                ).with(org.springframework.data.domain.Sort.by(org.springframework.data.domain.Sort.Direction.ASC, "orderLineId")).limit(1),
                OrderLine.class
            );
        }
        Object last = null;
        if (count > 1) {
            last = template.findOne(
                new org.springframework.data.mongodb.core.query.Query(
                    org.springframework.data.mongodb.core.query.Criteria.where("description").regex("C\\+\\+")
                ).with(org.springframework.data.domain.Sort.by(org.springframework.data.domain.Sort.Direction.DESC, "orderLineId")).limit(1),
                OrderLine.class
            );
        }
        java.util.Map<String, Object> map = new java.util.LinkedHashMap<>();
        map.put("count", count);
        map.put("firstSample", first);
        map.put("lastSample", last);
        return map;
    }
}
```

```source_query_body id=6
using Dapper;
using Microsoft.Data.SqlClient;
using System.Collections.Generic;

public static class Query6
{
    public static object Harness(SqlConnection conn)
    {
        string sql = @"SELECT * FROM Sales.OrderLines ORDER BY OrderLineID OFFSET @Skip ROWS FETCH NEXT @Take ROWS ONLY";
        return HarnessSupport.RunRows(() => conn.Query<OrderLine>(sql, new { Skip = 1000, Take = 50 }), null);
    }
}
```

```target_query_body id=6
final class Query6 {
    static java.util.Map<String, Object> harness(org.springframework.data.mongodb.core.MongoTemplate template) {
        org.springframework.data.mongodb.core.query.Query query = new org.springframework.data.mongodb.core.query.Query()
            .with(org.springframework.data.domain.Sort.by(org.springframework.data.domain.Sort.Direction.ASC, "orderLineId"))
            .skip(1000)
            .limit(50);
        java.util.List<OrderLine> results = template.find(query, OrderLine.class);
        long count = results.size();
        Object first = results.isEmpty() ? null : results.get(0);
        Object last = results.size() < 2 ? null : results.get(results.size() - 1);

        java.util.Map<String, Object> map = new java.util.LinkedHashMap<>();
        map.put("count", count);
        map.put("firstSample", first);
        map.put("lastSample", last);
        return map;
    }
}
```

```source_query_body id=7
using Dapper;
using Microsoft.Data.SqlClient;
using System.Collections.Generic;

public static class Query7
{
    public class TaxRateCount
    {
        public decimal TaxRate { get; set; }
        public int Count { get; set; }
    }

    public static object Harness(SqlConnection conn)
    {
        string sql = @"SELECT TaxRate, COUNT(*) AS Count FROM Sales.OrderLines GROUP BY TaxRate ORDER BY Count DESC";
        return HarnessSupport.RunRows(() => conn.Query<TaxRateCount>(sql), x => x.TaxRate);
    }
}
```

```target_query_body id=7
final class Query7 {
    static class TaxRateCount {
        private java.math.BigDecimal taxRate;
        private Long count;
        public TaxRateCount() {}
        public java.math.BigDecimal getTaxRate() { return taxRate; }
        public void setTaxRate(java.math.BigDecimal taxRate) { this.taxRate = taxRate; }
        public Long getCount() { return count; }
        public void setCount(Long count) { this.count = count; }
    }

    static java.util.Map<String, Object> harness(org.springframework.data.mongodb.core.MongoTemplate template) {
        org.springframework.data.mongodb.core.aggregation.TypedAggregation<OrderLine> agg = org.springframework.data.mongodb.core.aggregation.Aggregation.newAggregation(
            OrderLine.class,
            org.springframework.data.mongodb.core.aggregation.Aggregation.group("taxRate").count().as("count"),
            org.springframework.data.mongodb.core.aggregation.Aggregation.project("count").and("taxRate").previousOperation(),
            org.springframework.data.mongodb.core.aggregation.Aggregation.sort(org.springframework.data.domain.Sort.Direction.DESC, "count")
        );
        java.util.List<TaxRateCount> results = template.aggregate(agg, OrderLine.class, TaxRateCount.class).getMappedResults();
        long count = results.size();
        Object first = results.isEmpty() ? null : results.get(0);
        Object last = results.size() < 2 ? null : results.get(results.size() - 1);

        java.util.Map<String, Object> map = new java.util.LinkedHashMap<>();
        map.put("count", count);
        map.put("firstSample", first);
        map.put("lastSample", last);
        return map;
    }
}
```

```source_query_body id=8
using Dapper;
using Microsoft.Data.SqlClient;
using System.Collections.Generic;

public static class Query8
{
    public static object Harness(SqlConnection conn)
    {
        string sql = @"SELECT MAX(UnitPrice) FROM Sales.OrderLines";
        decimal? max = conn.ExecuteScalar<decimal?>(sql);
        return new { count = max.HasValue ? 1 : 0, firstSample = (object?)max, lastSample = (object?)null };
    }
}
```

```target_query_body id=8
final class Query8 {
    static class MaxResult {
        private java.math.BigDecimal maxVal;
        public MaxResult() {}
        public java.math.BigDecimal getMaxVal() { return maxVal; }
        public void setMaxVal(java.math.BigDecimal maxVal) { this.maxVal = maxVal; }
    }

    static java.util.Map<String, Object> harness(org.springframework.data.mongodb.core.MongoTemplate template) {
        org.springframework.data.mongodb.core.aggregation.TypedAggregation<OrderLine> agg = org.springframework.data.mongodb.core.aggregation.Aggregation.newAggregation(
            OrderLine.class,
            org.springframework.data.mongodb.core.aggregation.Aggregation.group().max("unitPrice").as("maxVal")
        );
        MaxResult result = template.aggregate(agg, OrderLine.class, MaxResult.class).getUniqueMappedResult();
        java.math.BigDecimal max = result != null ? result.getMaxVal() : null;
        long count = max != null ? 1 : 0;

        java.util.Map<String, Object> map = new java.util.LinkedHashMap<>();
        map.put("count", count);
        map.put("firstSample", max);
        map.put("lastSample", null);
        return map;
    }
}
```

```source_query_body id=9
using Dapper;
using Microsoft.Data.SqlClient;
using System.Collections.Generic;

public static class Query9
{
    public static object Harness(SqlConnection conn)
    {
        string sql = @"SELECT SUM(Quantity * UnitPrice) FROM Sales.OrderLines";
        decimal? sum = conn.ExecuteScalar<decimal?>(sql);
        return new { count = sum.HasValue ? 1 : 0, firstSample = (object?)sum, lastSample = (object?)null };
    }
}
```

```target_query_body id=9
final class Query9 {
    static class SumResult {
        private java.math.BigDecimal sumVal;
        public SumResult() {}
        public java.math.BigDecimal getSumVal() { return sumVal; }
        public void setSumVal(java.math.BigDecimal sumVal) { this.sumVal = sumVal; }
    }

    static java.util.Map<String, Object> harness(org.springframework.data.mongodb.core.MongoTemplate template) {
        org.springframework.data.mongodb.core.aggregation.TypedAggregation<OrderLine> agg = org.springframework.data.mongodb.core.aggregation.Aggregation.newAggregation(
            OrderLine.class,
            org.springframework.data.mongodb.core.aggregation.Aggregation.project().andExpression("quantity * unitPrice").as("lineTotal"),
            org.springframework.data.mongodb.core.aggregation.Aggregation.group().sum("lineTotal").as("sumVal")
        );
        SumResult result = template.aggregate(agg, OrderLine.class, SumResult.class).getUniqueMappedResult();
        java.math.BigDecimal sum = result != null ? result.getSumVal() : null;
        long count = sum != null ? 1 : 0;

        java.util.Map<String, Object> map = new java.util.LinkedHashMap<>();
        map.put("count", count);
        map.put("firstSample", sum);
        map.put("lastSample", null);
        return map;
    }
}
```

```source_query_body id=10
using Dapper;
using Microsoft.Data.SqlClient;
using System.Collections.Generic;
using System.Linq;

public static class Query10
{
    private static Order MapRow(Order o, OrderLine ol)
    {
        if (ol != null) o.OrderLines.Add(ol);
        return o;
    }

    public static object Harness(SqlConnection conn)
    {
        string sql = @"
            SELECT o.*, ol.*
            FROM Sales.Orders o
            LEFT JOIN Sales.OrderLines ol ON o.OrderID = ol.OrderID
            WHERE o.OrderID = 530";
        var rows = conn.Query<Order, OrderLine, Order>(sql, MapRow, splitOn: "OrderLineID");
        var orders = rows.GroupBy(o => o.OrderID).Select(g => {
            var order = g.First();
            order.OrderLines = g.SelectMany(o => o.OrderLines).ToList();
            return order;
        }).ToList();
        var count = orders.Count;
        var first = orders.FirstOrDefault();
        return new { count, firstSample = first, lastSample = (object?)null };
    }
}
```

```target_query_body id=10
final class Query10 {
    static java.util.Map<String, Object> harness(org.springframework.data.mongodb.core.MongoTemplate template) {
        org.springframework.data.mongodb.core.query.Query query = new org.springframework.data.mongodb.core.query.Query(
            org.springframework.data.mongodb.core.query.Criteria.where("orderId").is(530)
        );
        Order order = template.findOne(query, Order.class);
        if (order != null) {
            order.getOrderLines();
        }
        long count = order != null ? 1 : 0;

        java.util.Map<String, Object> map = new java.util.LinkedHashMap<>();
        map.put("count", count);
        map.put("firstSample", order);
        map.put("lastSample", null);
        return map;
    }
}
```

```source_query_body id=11
using Dapper;
using Microsoft.Data.SqlClient;
using System.Collections.Generic;

public static class Query11
{
    public static object Harness(SqlConnection conn)
    {
        string sql = @"SELECT TOP 1000 * FROM Sales.Orders ORDER BY ExpectedDeliveryDate";
        return HarnessSupport.RunRows(() => conn.Query<Order>(sql), x => x.OrderID);
    }
}
```

```target_query_body id=11
final class Query11 {
    static java.util.Map<String, Object> harness(org.springframework.data.mongodb.core.MongoTemplate template) {
        org.springframework.data.mongodb.core.query.Query query = new org.springframework.data.mongodb.core.query.Query()
            .with(org.springframework.data.domain.Sort.by(org.springframework.data.domain.Sort.Direction.ASC, "expectedDeliveryDate"))
            .limit(1000);
        java.util.List<Order> results = template.find(query, Order.class);
        long count = results.size();
        Object first = results.isEmpty() ? null : results.get(0);
        Object last = results.size() < 2 ? null : results.get(results.size() - 1);

        java.util.Map<String, Object> map = new java.util.LinkedHashMap<>();
        map.put("count", count);
        map.put("firstSample", first);
        map.put("lastSample", last);
        return map;
    }
}
```

```source_query_body id=12
using Dapper;
using Microsoft.Data.SqlClient;
using System.Collections.Generic;

public static class Query12
{
    public static object Harness(SqlConnection conn)
    {
        string sql = @"SELECT DISTINCT CustomerPurchaseOrderNumber FROM Sales.Orders";
        return HarnessSupport.RunRows(() => conn.Query<string>(sql), x => x);
    }
}
```

```target_query_body id=12
final class Query12 {
    static java.util.Map<String, Object> harness(org.springframework.data.mongodb.core.MongoTemplate template) {
        java.util.List<String> results = new java.util.ArrayList<>(
            template.findDistinct(new org.springframework.data.mongodb.core.query.Query(), "customerPurchaseOrderNumber", Order.class, String.class)
        );
        results.sort(java.util.Comparator.nullsFirst(java.util.Comparator.naturalOrder()));
        long count = results.size();
        Object first = results.isEmpty() ? null : results.get(0);
        Object last = results.size() < 2 ? null : results.get(results.size() - 1);

        java.util.Map<String, Object> map = new java.util.LinkedHashMap<>();
        map.put("count", count);
        map.put("firstSample", first);
        map.put("lastSample", last);
        return map;
    }
}
```

```source_query_body id=13
using Dapper;
using Microsoft.Data.SqlClient;
using System.Collections.Generic;

public static class Query13
{
    public static object Harness(SqlConnection conn)
    {
        string sql = @"
            SELECT PersonID, FullName, PreferredName, EmailAddress, CustomFields, OtherLanguages
            FROM Application.People
            WHERE JSON_VALUE(CustomFields, '$.Title') = @Title
            ORDER BY PersonID";
        return HarnessSupport.RunRows(() => conn.Query<Person>(sql, new { Title = "Team Member" }), null);
    }
}
```

```target_query_body id=13
final class Query13 {
    static java.util.Map<String, Object> harness(org.springframework.data.mongodb.core.MongoTemplate template) {
        org.springframework.data.mongodb.core.query.Query query = new org.springframework.data.mongodb.core.query.Query(
            org.springframework.data.mongodb.core.query.Criteria.where("customFields").regex("\"Title\"\\s*:\\s*\"Team Member\"")
        ).with(org.springframework.data.domain.Sort.by(org.springframework.data.domain.Sort.Direction.ASC, "personId"));
        long count = template.count(query, Person.class);
        Object first = null;
        if (count > 0) {
            first = template.findOne(
                new org.springframework.data.mongodb.core.query.Query(
                    org.springframework.data.mongodb.core.query.Criteria.where("customFields").regex("\"Title\"\\s*:\\s*\"Team Member\"")
                ).with(org.springframework.data.domain.Sort.by(org.springframework.data.domain.Sort.Direction.ASC, "personId")).limit(1),
                Person.class
            );
        }
        Object last = null;
        if (count > 1) {
            last = template.findOne(
                new org.springframework.data.mongodb.core.query.Query(
                    org.springframework.data.mongodb.core.query.Criteria.where("customFields").regex("\"Title\"\\s*:\\s*\"Team Member\"")
                ).with(org.springframework.data.domain.Sort.by(org.springframework.data.domain.Sort.Direction.DESC, "personId")).limit(1),
                Person.class
            );
        }
        java.util.Map<String, Object> map = new java.util.LinkedHashMap<>();
        map.put("count", count);
        map.put("firstSample", first);
        map.put("lastSample", last);
        return map;
    }
}
```

```source_query_body id=14
using Dapper;
using Microsoft.Data.SqlClient;
using System.Collections.Generic;

public static class Query14
{
    public static object Harness(SqlConnection conn)
    {
        string sql = @"
            SELECT PersonID, FullName, PreferredName, EmailAddress, CustomFields, OtherLanguages
            FROM Application.People
            WHERE EXISTS (
                SELECT 1 FROM OPENJSON(OtherLanguages)
                WHERE value = @Language
            )
            ORDER BY PersonID";
        return HarnessSupport.RunRows(() => conn.Query<Person>(sql, new { Language = "Slovak" }), null);
    }
}
```

```target_query_body id=14
final class Query14 {
    static java.util.Map<String, Object> harness(org.springframework.data.mongodb.core.MongoTemplate template) {
        org.springframework.data.mongodb.core.query.Query query = new org.springframework.data.mongodb.core.query.Query(
            org.springframework.data.mongodb.core.query.Criteria.where("otherLanguages").regex("\"Slovak\"")
        ).with(org.springframework.data.domain.Sort.by(org.springframework.data.domain.Sort.Direction.ASC, "personId"));
        long count = template.count(query, Person.class);
        Object first = null;
        if (count > 0) {
            first = template.findOne(
                new org.springframework.data.mongodb.core.query.Query(
                    org.springframework.data.mongodb.core.query.Criteria.where("otherLanguages").regex("\"Slovak\"")
                ).with(org.springframework.data.domain.Sort.by(org.springframework.data.domain.Sort.Direction.ASC, "personId")).limit(1),
                Person.class
            );
        }
        Object last = null;
        if (count > 1) {
            last = template.findOne(
                new org.springframework.data.mongodb.core.query.Query(
                    org.springframework.data.mongodb.core.query.Criteria.where("otherLanguages").regex("\"Slovak\"")
                ).with(org.springframework.data.domain.Sort.by(org.springframework.data.domain.Sort.Direction.DESC, "personId")).limit(1),
                Person.class
            );
        }
        java.util.Map<String, Object> map = new java.util.LinkedHashMap<>();
        map.put("count", count);
        map.put("firstSample", first);
        map.put("lastSample", last);
        return map;
    }
}
```

```source_query_body id=15
using Dapper;
using Microsoft.Data.SqlClient;
using System.Collections.Generic;

public static class Query15
{
    public static object Harness(SqlConnection conn)
    {
        string sql = @"
            SELECT SupplierID FROM Purchasing.Suppliers WHERE SupplierID < 5
            UNION
            SELECT SupplierID FROM Purchasing.Suppliers WHERE SupplierID BETWEEN 5 AND 10
            ORDER BY SupplierID";
        return HarnessSupport.RunRows(() => conn.Query<int>(sql), null);
    }
}
```

```target_query_body id=15
final class Query15 {
    static class SupplierIdProjection {
        private Integer supplierId;
        public SupplierIdProjection() {}
        public Integer getSupplierId() { return supplierId; }
        public void setSupplierId(Integer supplierId) { this.supplierId = supplierId; }
    }

    static java.util.Map<String, Object> harness(org.springframework.data.mongodb.core.MongoTemplate template) {
        org.springframework.data.mongodb.core.aggregation.TypedAggregation<Supplier> agg = org.springframework.data.mongodb.core.aggregation.Aggregation.newAggregation(
            Supplier.class,
            org.springframework.data.mongodb.core.aggregation.Aggregation.match(org.springframework.data.mongodb.core.query.Criteria.where("supplierId").lt(5)),
            org.springframework.data.mongodb.core.aggregation.Aggregation.unionWith(
                "suppliers",
                org.springframework.data.mongodb.core.aggregation.Aggregation.newAggregation(
                    Supplier.class,
                    org.springframework.data.mongodb.core.aggregation.Aggregation.match(org.springframework.data.mongodb.core.query.Criteria.where("supplierId").gte(5).lte(10))
                )
            ),
            org.springframework.data.mongodb.core.aggregation.Aggregation.group("supplierId"),
            org.springframework.data.mongodb.core.aggregation.Aggregation.project("supplierId").and("supplierId").previousOperation(),
            org.springframework.data.mongodb.core.aggregation.Aggregation.sort(org.springframework.data.domain.Sort.Direction.ASC, "supplierId")
        );
        java.util.List<SupplierIdProjection> results = template.aggregate(agg, Supplier.class, SupplierIdProjection.class).getMappedResults();
        java.util.List<Integer> ids = new java.util.ArrayList<>();
        for (SupplierIdProjection proj : results) {
            ids.add(proj.getSupplierId());
        }
        long count = ids.size();
        Object first = ids.isEmpty() ? null : ids.get(0);
        Object last = ids.size() < 2 ? null : ids.get(ids.size() - 1);

        java.util.Map<String, Object> map = new java.util.LinkedHashMap<>();
        map.put("count", count);
        map.put("firstSample", first);
        map.put("lastSample", last);
        return map;
    }
}
```
