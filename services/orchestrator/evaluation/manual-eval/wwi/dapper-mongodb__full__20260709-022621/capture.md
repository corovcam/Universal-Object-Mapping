The advisor confirmed the approach and flagged four concrete issues (fully-qualify `HashMap`/`Comparator`/`TreeSet`/`@Transient`; never use `template.count()` for limit/skip queries; hand-build Query10's source symmetrically; keep `findDistinct` for Query12). I've incorporated all four. Here is the complete draft.

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

public class TaxRateCount
{
    public decimal TaxRate { get; set; }
    public long Count { get; set; }
}
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

    @Field("description")
    private String description;

    @Field("packageTypeId")
    private Integer packageTypeId;

    @Field("quantity")
    private Integer quantity;

    @Field("unitPrice")
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

    OrderLine() {
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
    private LocalDateTime orderDate;

    @Field("expectedDeliveryDate")
    private LocalDateTime expectedDeliveryDate;

    @Field("customerPurchaseOrderNumber")
    private String customerPurchaseOrderNumber;

    @Field("isUndersupplyBackordered")
    private Boolean isUndersupplyBackordered;

    @Field("comments")
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

    @org.springframework.data.annotation.Transient
    private List<OrderLine> orderLines = new java.util.ArrayList<>();

    Order() {
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
    public LocalDateTime getOrderDate() { return orderDate; }
    public void setOrderDate(LocalDateTime orderDate) { this.orderDate = orderDate; }
    public LocalDateTime getExpectedDeliveryDate() { return expectedDeliveryDate; }
    public void setExpectedDeliveryDate(LocalDateTime expectedDeliveryDate) { this.expectedDeliveryDate = expectedDeliveryDate; }
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

    Person() {
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

    Supplier() {
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

record TaxRateCount(BigDecimal taxRate, Long count) {
}

record DecimalResult(BigDecimal value) {
}
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
    static Query query() {
        return new Query(Criteria.where("orderId").is(26866));
    }

    static Map<String, Object> harness(MongoTemplate template) {
        long count = template.count(query(), OrderLine.class);
        Object first = null;
        if (count > 0) {
            first = template.findOne(query().with(Sort.by(Sort.Direction.ASC, "orderLineId")).limit(1), OrderLine.class);
        }
        Object last = null;
        if (count > 1) {
            last = template.findOne(query().with(Sort.by(Sort.Direction.DESC, "orderLineId")).limit(1), OrderLine.class);
        }
        Map<String, Object> result = new java.util.HashMap<>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
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
    static Query query() {
        return new Query(Criteria.where("unitPrice").is(new BigDecimal("25")));
    }

    static Map<String, Object> harness(MongoTemplate template) {
        long count = template.count(query(), OrderLine.class);
        Object first = null;
        if (count > 0) {
            first = template.findOne(query().with(Sort.by(Sort.Direction.ASC, "orderLineId")).limit(1), OrderLine.class);
        }
        Object last = null;
        if (count > 1) {
            last = template.findOne(query().with(Sort.by(Sort.Direction.DESC, "orderLineId")).limit(1), OrderLine.class);
        }
        Map<String, Object> result = new java.util.HashMap<>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
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
    static Query query() {
        LocalDateTime from = LocalDateTime.of(2014, 12, 20, 0, 0);
        LocalDateTime to = LocalDateTime.of(2014, 12, 31, 0, 0);
        return new Query(Criteria.where("pickingCompletedWhen").gte(from).lte(to));
    }

    static Map<String, Object> harness(MongoTemplate template) {
        long count = template.count(query(), OrderLine.class);
        Object first = null;
        if (count > 0) {
            first = template.findOne(query().with(Sort.by(Sort.Direction.ASC, "orderLineId")).limit(1), OrderLine.class);
        }
        Object last = null;
        if (count > 1) {
            last = template.findOne(query().with(Sort.by(Sort.Direction.DESC, "orderLineId")).limit(1), OrderLine.class);
        }
        Map<String, Object> result = new java.util.HashMap<>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
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
    static Query query() {
        return new Query(Criteria.where("orderId").in(1, 10, 100, 1000, 10000));
    }

    static Map<String, Object> harness(MongoTemplate template) {
        long count = template.count(query(), OrderLine.class);
        Object first = null;
        if (count > 0) {
            first = template.findOne(query().with(Sort.by(Sort.Direction.ASC, "orderLineId")).limit(1), OrderLine.class);
        }
        Object last = null;
        if (count > 1) {
            last = template.findOne(query().with(Sort.by(Sort.Direction.DESC, "orderLineId")).limit(1), OrderLine.class);
        }
        Map<String, Object> result = new java.util.HashMap<>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
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
    static Query query() {
        return new Query(Criteria.where("description").regex("C\\+\\+", "i"));
    }

    static Map<String, Object> harness(MongoTemplate template) {
        long count = template.count(query(), OrderLine.class);
        Object first = null;
        if (count > 0) {
            first = template.findOne(query().with(Sort.by(Sort.Direction.ASC, "orderLineId")).limit(1), OrderLine.class);
        }
        Object last = null;
        if (count > 1) {
            last = template.findOne(query().with(Sort.by(Sort.Direction.DESC, "orderLineId")).limit(1), OrderLine.class);
        }
        Map<String, Object> result = new java.util.HashMap<>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
    }
}
```

```source_query_body id=6
public static class Query6
{
    public static object Harness(SqlConnection conn)
    {
        string sql = @"SELECT * FROM Sales.OrderLines ORDER BY OrderLineID OFFSET @Skip ROWS FETCH NEXT @Take ROWS ONLY";
        return HarnessSupport.RunRows(() => conn.Query<OrderLine>(sql, new { Skip = 1000, Take = 50 }), ol => ol.OrderLineID);
    }
}
```

```target_query_body id=6
final class Query6 {
    static Query query() {
        return new Query().with(Sort.by(Sort.Direction.ASC, "orderLineId")).skip(1000).limit(50);
    }

    static Map<String, Object> harness(MongoTemplate template) {
        List<OrderLine> rows = template.find(query(), OrderLine.class);
        long count = rows.size();
        Object first = count > 0 ? rows.get(0) : null;
        Object last = count > 1 ? rows.get(rows.size() - 1) : null;
        Map<String, Object> result = new java.util.HashMap<>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
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
    static Map<String, Object> harness(MongoTemplate template) {
        TypedAggregation<OrderLine> agg = Aggregation.newAggregation(
                OrderLine.class,
                Aggregation.group("taxRate").count().as("count"),
                Aggregation.project("count").and("taxRate").previousOperation());
        List<TaxRateCount> rows = new java.util.ArrayList<>(
                template.aggregate(agg, OrderLine.class, TaxRateCount.class).getMappedResults());
        rows.sort(java.util.Comparator.comparing(TaxRateCount::taxRate));
        long count = rows.size();
        Object first = count > 0 ? rows.get(0) : null;
        Object last = count > 1 ? rows.get(rows.size() - 1) : null;
        Map<String, Object> result = new java.util.HashMap<>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
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
    static Map<String, Object> harness(MongoTemplate template) {
        Aggregation agg = Aggregation.newAggregation(
                Aggregation.group().max("unitPrice").as("value"));
        DecimalResult r = template.aggregate(agg, OrderLine.class, DecimalResult.class).getUniqueMappedResult();
        BigDecimal max = r != null ? r.value() : null;
        Map<String, Object> result = new java.util.HashMap<>();
        result.put("count", max != null ? 1L : 0L);
        result.put("firstSample", max);
        result.put("lastSample", null);
        return result;
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
    static Map<String, Object> harness(MongoTemplate template) {
        Aggregation agg = Aggregation.newAggregation(
                Aggregation.project().andExpression("quantity * unitPrice").as("lineTotal"),
                Aggregation.group().sum("lineTotal").as("value"));
        DecimalResult r = template.aggregate(agg, OrderLine.class, DecimalResult.class).getUniqueMappedResult();
        BigDecimal sum = r != null ? r.value() : null;
        Map<String, Object> result = new java.util.HashMap<>();
        result.put("count", sum != null ? 1L : 0L);
        result.put("firstSample", sum);
        result.put("lastSample", null);
        return result;
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
            WHERE o.OrderID = 530
            ORDER BY ol.OrderLineID";
        var rows = conn.Query<Order, OrderLine, Order>(sql, MapRow, splitOn: "OrderLineID");
        var order = rows.GroupBy(o => o.OrderID).Select(g =>
        {
            var ord = g.First();
            ord.OrderLines = g.SelectMany(o => o.OrderLines).ToList();
            return ord;
        }).SingleOrDefault();
        return new { count = order != null ? 1 : 0, firstSample = (object?)order, lastSample = (object?)null };
    }
}
```

```target_query_body id=10
final class Query10 {
    static Map<String, Object> harness(MongoTemplate template) {
        Query orderQuery = new Query(Criteria.where("orderId").is(530));
        Order order = template.findOne(orderQuery, Order.class);
        long count = order != null ? 1L : 0L;
        if (order != null) {
            Query linesQuery = new Query(Criteria.where("orderId").is(530))
                    .with(Sort.by(Sort.Direction.ASC, "orderLineId"));
            List<OrderLine> lines = template.find(linesQuery, OrderLine.class);
            order.setOrderLines(lines);
        }
        Map<String, Object> result = new java.util.HashMap<>();
        result.put("count", count);
        result.put("firstSample", order);
        result.put("lastSample", null);
        return result;
    }
}
```

```source_query_body id=11
public static class Query11
{
    public static object Harness(SqlConnection conn)
    {
        string sql = @"SELECT TOP 1000 * FROM Sales.Orders ORDER BY ExpectedDeliveryDate, OrderID";
        return HarnessSupport.RunRows(() => conn.Query<Order>(sql), o => o.OrderID);
    }
}
```

```target_query_body id=11
final class Query11 {
    static Query query() {
        return new Query().with(Sort.by(Sort.Direction.ASC, "expectedDeliveryDate", "orderId")).limit(1000);
    }

    static Map<String, Object> harness(MongoTemplate template) {
        List<Order> rows = new java.util.ArrayList<>(template.find(query(), Order.class));
        long count = rows.size();
        rows.sort(java.util.Comparator.comparing(Order::getOrderId));
        Object first = count > 0 ? rows.get(0) : null;
        Object last = count > 1 ? rows.get(rows.size() - 1) : null;
        Map<String, Object> result = new java.util.HashMap<>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
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
        List<String> distinct = new java.util.ArrayList<>(
                template.findDistinct(new Query(), "customerPurchaseOrderNumber", Order.class, String.class));
        distinct.sort(java.util.Comparator.nullsFirst(java.util.Comparator.<String>naturalOrder()));
        long count = distinct.size();
        Object first = count > 0 ? distinct.get(0) : null;
        Object last = count > 1 ? distinct.get(distinct.size() - 1) : null;
        Map<String, Object> result = new java.util.HashMap<>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
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
        return HarnessSupport.RunRows(() => conn.Query<Person>(sql, new { Title = "Team Member" }), p => p.PersonID);
    }
}
```

```target_query_body id=13
final class Query13 {
    static Query query() {
        return new Query(Criteria.where("customFields").regex("\"Title\"\\s*:\\s*\"Team Member\""));
    }

    static Map<String, Object> harness(MongoTemplate template) {
        long count = template.count(query(), Person.class);
        Object first = null;
        if (count > 0) {
            first = template.findOne(query().with(Sort.by(Sort.Direction.ASC, "personId")).limit(1), Person.class);
        }
        Object last = null;
        if (count > 1) {
            last = template.findOne(query().with(Sort.by(Sort.Direction.DESC, "personId")).limit(1), Person.class);
        }
        Map<String, Object> result = new java.util.HashMap<>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
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
        return HarnessSupport.RunRows(() => conn.Query<Person>(sql, new { Language = "Slovak" }), p => p.PersonID);
    }
}
```

```target_query_body id=14
final class Query14 {
    static Query query() {
        return new Query(Criteria.where("otherLanguages").regex("\"Slovak\""));
    }

    static Map<String, Object> harness(MongoTemplate template) {
        long count = template.count(query(), Person.class);
        Object first = null;
        if (count > 0) {
            first = template.findOne(query().with(Sort.by(Sort.Direction.ASC, "personId")).limit(1), Person.class);
        }
        Object last = null;
        if (count > 1) {
            last = template.findOne(query().with(Sort.by(Sort.Direction.DESC, "personId")).limit(1), Person.class);
        }
        Map<String, Object> result = new java.util.HashMap<>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
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
    static Map<String, Object> harness(MongoTemplate template) {
        java.util.TreeSet<Integer> ids = new java.util.TreeSet<>();
        Query q1 = new Query(Criteria.where("supplierId").lt(5));
        for (Supplier s : template.find(q1, Supplier.class)) {
            ids.add(s.getSupplierId());
        }
        Query q2 = new Query(Criteria.where("supplierId").gte(5).lte(10));
        for (Supplier s : template.find(q2, Supplier.class)) {
            ids.add(s.getSupplierId());
        }
        List<Integer> sorted = new java.util.ArrayList<>(ids);
        long count = sorted.size();
        Object first = count > 0 ? sorted.get(0) : null;
        Object last = count > 1 ? sorted.get(sorted.size() - 1) : null;
        Map<String, Object> result = new java.util.HashMap<>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
    }
}
```

**Notes on the key translation choices:**

- **Order's `orderLines`** is mapped `@Transient` with an empty-list default (not a `@DocumentReference`) so plain-Order queries (Query11) serialize `orderLines: []` matching the source's default `= []`, while Query10 explicitly loads and sets them from the separate `orderLines` collection — mirroring the source `LEFT JOIN`, but respecting that Mongo keeps them in a distinct collection.
- **Query11**'s non-unique `ORDER BY ExpectedDeliveryDate` gets a deterministic `orderId` tiebreaker on both sides so the same 1000 rows are selected.
- **Query10 source is hand-built** (not `RunRows`) to guarantee `count=1, lastSample=null` symmetry — the one guaranteed count-1 case.
- **JSON columns** (Query13/14) use anchored regex on the raw string field; **UNION** (Query15) uses a `TreeSet` dedupe/sort (the two branches are disjoint and `supplierId` is a unique PK, so this is exact); **`MAX`/`SUM`** (Query8/9) use `$group` aggregation.
