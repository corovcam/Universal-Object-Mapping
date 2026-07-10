```source_schema_body
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

public record TaxRateCount(decimal TaxRate, int Count);
```

```target_schema_body
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

    private BigDecimal unitPrice;

    @Field("taxRate")
    private BigDecimal taxRate;

    @Field("pickedQuantity")
    private Integer pickedQuantity;

    @Field("pickingCompletedWhen")
    private LocalDateTime pickingCompletedWhen;

    @Field("lastEditedBy")
    private Integer lastEditedBy;

    @Field("lastEditedWhen")
    private LocalDateTime lastEditedWhen;

    public OrderLine() {
    }

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

    public Order() {
    }

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

    public Person() {
    }

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

    public Supplier() {
    }

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

record CountProjection(Long count) {}
record TotalProjection(BigDecimal total) {}
record TaxRateCount(BigDecimal taxRate, Long count) {}
```

```source_query_body id=1
public static class Query1
{
    public static object Harness(SqlConnection conn)
    {
        string sql = @"SELECT * FROM Sales.OrderLines WHERE OrderID = @OrderID";
        return HarnessSupport.RunRows(() => conn.Query<OrderLine>(sql, new { OrderID = 26866 }), ol => ol.OrderLineID);
    }
}
```

```target_query_body id=1
final class Query1 {
    public static Query query() {
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
        Map<String, Object> map = new HashMap<>();
        map.put("mongoQuery", Map.of("collection", template.getCollectionName(OrderLine.class), "filter", q.getQueryObject()));
        map.put("count", count);
        map.put("firstSample", first);
        map.put("lastSample", last);
        return map;
    }
}
```

```source_query_body id=2
public static class Query2
{
    public static object Harness(SqlConnection conn)
    {
        string sql = @"SELECT * FROM Sales.OrderLines WHERE UnitPrice = @UnitPrice";
        return HarnessSupport.RunRows(() => conn.Query<OrderLine>(sql, new { UnitPrice = 25m }), ol => ol.OrderLineID);
    }
}
```

```target_query_body id=2
final class Query2 {
    public static Query query() {
        return new Query(Criteria.where("unitPrice").is(new BigDecimal("25")));
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
        Map<String, Object> map = new HashMap<>();
        map.put("mongoQuery", Map.of("collection", template.getCollectionName(OrderLine.class), "filter", q.getQueryObject()));
        map.put("count", count);
        map.put("firstSample", first);
        map.put("lastSample", last);
        return map;
    }
}
```

```source_query_body id=3
public static class Query3
{
    public static object Harness(SqlConnection conn)
    {
        var from = new DateTime(2014, 12, 20);
        var to = new DateTime(2014, 12, 31);
        string sql = @"SELECT * FROM Sales.OrderLines WHERE PickingCompletedWhen >= @From AND PickingCompletedWhen <= @To";
        return HarnessSupport.RunRows(() => conn.Query<OrderLine>(sql, new { From = from, To = to }), ol => ol.OrderLineID);
    }
}
```

```target_query_body id=3
final class Query3 {
    public static Query query() {
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
        Map<String, Object> map = new HashMap<>();
        map.put("mongoQuery", Map.of("collection", template.getCollectionName(OrderLine.class), "filter", q.getQueryObject()));
        map.put("count", count);
        map.put("firstSample", first);
        map.put("lastSample", last);
        return map;
    }
}
```

```source_query_body id=4
public static class Query4
{
    public static object Harness(SqlConnection conn)
    {
        var orderIds = new[] { 1, 10, 100, 1000, 10000 };
        string sql = @"SELECT * FROM Sales.OrderLines WHERE OrderID IN @Ids";
        return HarnessSupport.RunRows(() => conn.Query<OrderLine>(sql, new { Ids = orderIds }), ol => ol.OrderLineID);
    }
}
```

```target_query_body id=4
final class Query4 {
    public static Query query() {
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
        Map<String, Object> map = new HashMap<>();
        map.put("mongoQuery", Map.of("collection", template.getCollectionName(OrderLine.class), "filter", q.getQueryObject()));
        map.put("count", count);
        map.put("firstSample", first);
        map.put("lastSample", last);
        return map;
    }
}
```

```source_query_body id=5
public static class Query5
{
    public static object Harness(SqlConnection conn)
    {
        string sql = @"SELECT * FROM Sales.OrderLines WHERE Description LIKE @Pattern";
        return HarnessSupport.RunRows(() => conn.Query<OrderLine>(sql, new { Pattern = "%C++%" }), ol => ol.OrderLineID);
    }
}
```

```target_query_body id=5
final class Query5 {
    public static Query query() {
        return new Query(Criteria.where("description").regex("C\\+\\+"));
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
        Map<String, Object> map = new HashMap<>();
        map.put("mongoQuery", Map.of("collection", template.getCollectionName(OrderLine.class), "filter", q.getQueryObject()));
        map.put("count", count);
        map.put("firstSample", first);
        map.put("lastSample", last);
        return map;
    }
}
```

```source_query_body id=6
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
    public static Query query() {
        return new Query()
                .with(Sort.by(Sort.Direction.ASC, "orderLineId"))
                .skip(1000)
                .limit(50);
    }

    static Map<String, Object> harness(MongoTemplate template) {
        List<OrderLine> results = template.find(query(), OrderLine.class);
        long count = results.size();
        Object first = results.isEmpty() ? null : results.get(0);
        Object last = results.size() > 1 ? results.get(results.size() - 1) : null;
        Map<String, Object> map = new HashMap<>();
        map.put("mongoQuery", Map.of("collection", template.getCollectionName(OrderLine.class), "filter", query().getQueryObject(), "sort", query().getSortObject()));
        map.put("count", count);
        map.put("firstSample", first);
        map.put("lastSample", last);
        return map;
    }
}
```

```source_query_body id=7
public static class Query7
{
    public static object Harness(SqlConnection conn)
    {
        string sql = @"SELECT TaxRate, COUNT(*) AS Count FROM Sales.OrderLines GROUP BY TaxRate ORDER BY Count DESC";
        return HarnessSupport.RunRows(() => conn.Query<TaxRateCount>(sql), x => x.TaxRate);
    }
}
```

```target_query_body id=7
final class Query7 {
    public static TypedAggregation<OrderLine> query() {
        return Aggregation.newAggregation(
            OrderLine.class,
            Aggregation.group("taxRate").count().as("count"),
            Aggregation.project("count").and("taxRate").previousOperation(),
            Aggregation.sort(Sort.Direction.DESC, "count")
        );
    }

    static Map<String, Object> harness(MongoTemplate template) {
        var baseAgg = query();
        
        var countOps = new ArrayList<>(baseAgg.getPipeline().getOperations());
        countOps.add(Aggregation.count().as("count"));
        var countAgg = Aggregation.newAggregation(OrderLine.class, countOps);
        var countResult = template.aggregate(countAgg, OrderLine.class, CountProjection.class).getUniqueMappedResult();
        long count = countResult != null ? countResult.count() : 0L;
        
        Object first = null;
        if (count > 0) {
            var agg = Aggregation.newAggregation(query().getPipeline().add(Aggregation.sort(Sort.Direction.ASC, "taxRate")).add(Aggregation.limit(1)).getOperations());
            first = template.aggregate(agg, template.getCollectionName(OrderLine.class), Object.class).getUniqueMappedResult();
        }
        Object last = null;
        if (count > 1) {
            var desc = Aggregation.newAggregation(query().getPipeline().add(Aggregation.sort(Sort.Direction.DESC, "taxRate")).add(Aggregation.limit(1)).getOperations());
            last = template.aggregate(desc, template.getCollectionName(OrderLine.class), Object.class).getUniqueMappedResult();
        }
        Map<String, Object> map = new HashMap<>();
        map.put("mongoAggregation", Map.of("collection", template.getCollectionName(OrderLine.class), "pipeline", baseAgg.toString()));
        map.put("count", count);
        map.put("firstSample", first);
        map.put("lastSample", last);
        return map;
    }
}
```

```source_query_body id=8
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
    public static Query query() {
        Query q = new Query();
        q.fields().include("unitPrice");
        return q.with(Sort.by(Sort.Direction.DESC, "unitPrice")).limit(1);
    }

    static Map<String, Object> harness(MongoTemplate template) {
        OrderLine res = template.findOne(query(), OrderLine.class);
        BigDecimal max = (res != null) ? res.getUnitPrice() : null;
        long count = (max != null) ? 1 : 0;
        
        Map<String, Object> map = new HashMap<>();
        map.put("mongoQuery", Map.of("collection", template.getCollectionName(OrderLine.class), "filter", query().getQueryObject(), "sort", query().getSortObject()));
        map.put("count", count);
        map.put("firstSample", max);
        map.put("lastSample", null);
        return map;
    }
}
```

```source_query_body id=9
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
    public static TypedAggregation<OrderLine> query() {
        return Aggregation.newAggregation(
            OrderLine.class,
            Aggregation.project().andExpression("quantity * unitPrice").as("lineTotal"),
            Aggregation.group().sum("lineTotal").as("total")
        );
    }

    static Map<String, Object> harness(MongoTemplate template) {
        var agg = query();
        TotalProjection result = template.aggregate(agg, OrderLine.class, TotalProjection.class).getUniqueMappedResult();
        BigDecimal total = result != null ? result.total() : null;
        long count = (total != null) ? 1 : 0;
        
        Map<String, Object> map = new HashMap<>();
        map.put("mongoAggregation", Map.of("collection", template.getCollectionName(OrderLine.class), "pipeline", agg.toString()));
        map.put("count", count);
        map.put("firstSample", total);
        map.put("lastSample", null);
        return map;
    }
}
```

```source_query_body id=10
public static class Query10
{
    static Order MapRow(Order o, OrderLine ol)
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
        return HarnessSupport.RunRows<Order>(() =>
        {
            var rows = conn.Query<Order, OrderLine, Order>(sql, MapRow, splitOn: "OrderLineID");
            return rows.GroupBy(o => o.OrderID).Select(g => {
                var order = g.First();
                order.OrderLines = g.SelectMany(o => o.OrderLines).ToList();
                return order;
            });
        }, o => o.OrderID);
    }
}
```

```target_query_body id=10
final class Query10 {
    public static Query query() {
        return new Query(Criteria.where("orderId").is(530));
    }

    static Map<String, Object> harness(MongoTemplate template) {
        Query q = query();
        long count = template.count(q, Order.class);
        Object first = template.findOne(q, Order.class);
        
        Map<String, Object> map = new HashMap<>();
        map.put("mongoQuery", Map.of("collection", template.getCollectionName(Order.class), "filter", q.getQueryObject()));
        map.put("count", count);
        map.put("firstSample", first);
        map.put("lastSample", null);
        return map;
    }
}
```

```source_query_body id=11
public static class Query11
{
    public static object Harness(SqlConnection conn)
    {
        string sql = @"SELECT TOP 1000 * FROM Sales.Orders ORDER BY ExpectedDeliveryDate";
        return HarnessSupport.RunRows(() => conn.Query<Order>(sql), o => o.OrderID);
    }
}
```

```target_query_body id=11
final class Query11 {
    public static Query query() {
        return new Query()
                .with(Sort.by(Sort.Direction.ASC, "expectedDeliveryDate"))
                .limit(1000);
    }

    static Map<String, Object> harness(MongoTemplate template) {
        List<Order> list = template.find(query(), Order.class);
        list.sort(Comparator.comparing(Order::getOrderId));
        long count = list.size();
        Object first = list.isEmpty() ? null : list.get(0);
        Object last = list.size() > 1 ? list.get(list.size() - 1) : null;
        
        Map<String, Object> map = new HashMap<>();
        map.put("mongoQuery", Map.of("collection", template.getCollectionName(Order.class), "filter", query().getQueryObject(), "sort", query().getSortObject()));
        map.put("count", count);
        map.put("firstSample", first);
        map.put("lastSample", last);
        return map;
    }
}
```

```source_query_body id=12
public static class Query12
{
    public static object Harness(SqlConnection conn)
    {
        string sql = @"SELECT DISTINCT CustomerPurchaseOrderNumber FROM Sales.Orders";
        return HarnessSupport.RunRows(() => conn.Query<string?>(sql), x => x);
    }
}
```

```target_query_body id=12
final class Query12 {
    static Map<String, Object> harness(MongoTemplate template) {
        List<String> distinct = template.findDistinct(new Query(), "customerPurchaseOrderNumber", Order.class, String.class);
        distinct.sort((a, b) -> {
            if (a == null && b == null) return 0;
            if (a == null) return -1;
            if (b == null) return 1;
            return a.compareTo(b);
        });
        long count = distinct.size();
        Object first = distinct.isEmpty() ? null : distinct.get(0);
        Object last = distinct.size() > 1 ? distinct.get(distinct.size() - 1) : null;
        
        Map<String, Object> map = new HashMap<>();
        map.put("mongoQuery", Map.of("collection", template.getCollectionName(Order.class), "distinct", "customerPurchaseOrderNumber"));
        map.put("count", count);
        map.put("firstSample", first);
        map.put("lastSample", last);
        return map;
    }
}
```

```source_query_body id=13
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
    public static Query query() {
        return new Query(Criteria.where("customFields").regex("\"Title\"\\s*:\\s*\"Team Member\""))
                .with(Sort.by(Sort.Direction.ASC, "personId"));
    }

    static Map<String, Object> harness(MongoTemplate template) {
        Query q = query();
        long count = template.count(q, Person.class);
        Object first = null;
        if (count > 0) {
            first = template.findOne(query().limit(1), Person.class);
        }
        Object last = null;
        if (count > 1) {
            last = template.findOne(query().skip(count - 1).limit(1), Person.class);
        }
        Map<String, Object> map = new HashMap<>();
        map.put("mongoQuery", Map.of("collection", template.getCollectionName(Person.class), "filter", q.getQueryObject(), "sort", q.getSortObject()));
        map.put("count", count);
        map.put("firstSample", first);
        map.put("lastSample", last);
        return map;
    }
}
```

```source_query_body id=14
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
    public static Query query() {
        return new Query(Criteria.where("otherLanguages").regex("\"Slovak\""))
                .with(Sort.by(Sort.Direction.ASC, "personId"));
    }

    static Map<String, Object> harness(MongoTemplate template) {
        Query q = query();
        long count = template.count(q, Person.class);
        Object first = null;
        if (count > 0) {
            first = template.findOne(query().limit(1), Person.class);
        }
        Object last = null;
        if (count > 1) {
            last = template.findOne(query().skip(count - 1).limit(1), Person.class);
        }
        Map<String, Object> map = new HashMap<>();
        map.put("mongoQuery", Map.of("collection", template.getCollectionName(Person.class), "filter", q.getQueryObject(), "sort", q.getSortObject()));
        map.put("count", count);
        map.put("firstSample", first);
        map.put("lastSample", last);
        return map;
    }
}
```

```source_query_body id=15
public static class Query15
{
    public static object Harness(SqlConnection conn)
    {
        string sql = @"
            SELECT SupplierID FROM Purchasing.Suppliers WHERE SupplierID < 5
            UNION
            SELECT SupplierID FROM Purchasing.Suppliers WHERE SupplierID BETWEEN 5 AND 10
            ORDER BY SupplierID";
        return HarnessSupport.RunRows(() => conn.Query<int>(sql), x => x);
    }
}
```

```target_query_body id=15
final class Query15 {
    public static Query query() {
        return new Query(new Criteria().orOperator(
            Criteria.where("supplierId").lt(5),
            Criteria.where("supplierId").gte(5).lte(10)
        )).with(Sort.by(Sort.Direction.ASC, "supplierId"));
    }

    static Map<String, Object> harness(MongoTemplate template) {
        Query q = query();
        List<Supplier> suppliers = template.find(q, Supplier.class);
        List<Integer> ids = suppliers.stream().map(Supplier::getSupplierId).toList();
        long count = ids.size();
        Object first = ids.isEmpty() ? null : ids.get(0);
        Object last = ids.size() > 1 ? ids.get(ids.size() - 1) : null;
        
        Map<String, Object> map = new HashMap<>();
        map.put("mongoQuery", Map.of("collection", template.getCollectionName(Supplier.class), "filter", q.getQueryObject(), "sort", q.getSortObject()));
        map.put("count", count);
        map.put("firstSample", first);
        map.put("lastSample", last);
        return map;
    }
}
```
