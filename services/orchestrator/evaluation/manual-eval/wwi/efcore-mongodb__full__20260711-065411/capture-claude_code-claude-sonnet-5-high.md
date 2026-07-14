Translating the WWI schema (OrderLine, Order, Person/CustomFields, Supplier, and the unused-by-queries CustomerTransaction/PurchaseOrder/StockItem/StockItemStockGroup + DTOs) and all 15 queries to Spring Data MongoDB with `MongoTemplate`+`Query`/`Criteria`/`Aggregation`. Key design points: Mongo `_id` is a separate `String`, business keys kept as their own `@Field`; `Person.customFields`/`otherLanguages` become raw `String` fields (regex-matched) since Mongo stores them as JSON strings, not subdocuments; `Order.orderLines` becomes a lazy `@DocumentReference` since orderLines live in a separate collection; Query7/8/9 use the aggregation framework; Query11/12/6 use `find()`-based counting since `count()` ignores `limit`.

```source_schema_body
[Table("OrderLines", Schema = "Sales")]
public class OrderLine
{
  [Key]
  public int OrderLineID { get; set; }
  [ForeignKey(nameof(Order))]
  public int OrderID { get; set; }
  public int StockItemID { get; set; }
  public required string Description { get; set; }
  public int Quantity { get; set; }
  public decimal? UnitPrice { get; set; }
  public decimal TaxRate { get; set; }
  public int PickedQuantity { get; set; }
  public DateTime? PickingCompletedWhen { get; set; }
  public int LastEditedBy { get; set; }
  public DateTime LastEditedWhen { get; set; }
}

[Table("Orders", Schema = "Sales")]
public class Order
{
  [Key]
  public int OrderID { get; set; }
  public int CustomerID { get; set; }
  public int? BackorderOrderID { get; set; }
  public DateTime OrderDate { get; set; }
  public DateTime ExpectedDeliveryDate { get; set; }
  public string? CustomerPurchaseOrderNumber { get; set; }
  public bool IsUndersupplyBackordered { get; set; }
  public string? Comments { get; set; }
  public string? DeliveryInstructions { get; set; }
  public string? InternalComments { get; set; }
  public DateTime? PickingCompletedWhen { get; set; }
  public DateTime LastEditedWhen { get; set; }
  public List<OrderLine> OrderLines { get; set; } = [];
}

[Table("People", Schema = "Application")]
public class Person
{
  [Key]
  public int PersonID { get; set; }
  public required string FullName { get; set; }
  public required string PreferredName { get; set; }
  public string? EmailAddress { get; set; }
  public CustomFields? CustomFields { get; set; }
  public List<string>? OtherLanguages { get; set; }
}

public class CustomFields
{
  public List<string>? OtherLanguages { get; set; }
  public DateTime? HireDate { get; set; }
  public string? Title { get; set; }
}

[Table("Suppliers", Schema = "Purchasing")]
public class Supplier
{
  [Key]
  public int SupplierID { get; set; }
  public required string SupplierName { get; set; }
  public string? SupplierReference { get; set; }
  public int PaymentDays { get; set; }
  public string? PhoneNumber { get; set; }
  public string? FaxNumber { get; set; }
  public string? WebsiteURL { get; set; }
  public string? BankAccountName { get; set; }
  public string? BankAccountBranch { get; set; }
  public string? BankAccountCode { get; set; }
  public string? BankAccountNumber { get; set; }
  public string? BankInternationalCode { get; set; }
}

[Table("CustomerTransactions", Schema = "Sales")]
public class CustomerTransaction
{
  [Key]
  public int CustomerTransactionID { get; set; }
  public int CustomerID { get; set; }
  public DateTime TransactionDate { get; set; }
  public decimal TransactionAmount { get; set; }
  public decimal OutstandingBalance { get; set; }
  public bool IsFinalized { get; set; }
}

[Table("PurchaseOrders", Schema = "Purchasing")]
public class PurchaseOrder
{
  [Key]
  public int PurchaseOrderID { get; set; }
  public int SupplierID { get; set; }
  public DateTime OrderDate { get; set; }
  public DateTime ExpectedDeliveryDate { get; set; }
  public string? SupplierReference { get; set; }
  public bool IsOrderFinalized { get; set; }
}

[Table("StockItems", Schema = "Warehouse")]
public class StockItem
{
  [Key]
  public int StockItemID { get; set; }
  public required string StockItemName { get; set; }
  public int SupplierID { get; set; }
  public int QuantityPerOuter { get; set; }
  public int LeadTimeDays { get; set; }
  public bool IsChillerStock { get; set; }
  public decimal? UnitPrice { get; set; }
  public decimal RecommendedRetailPrice { get; set; }
}

[Table("StockItemStockGroups", Schema = "Warehouse")]
public class StockItemStockGroup
{
  [Key]
  public int StockItemStockGroupID { get; set; }
  public int StockItemID { get; set; }
  public int StockGroupID { get; set; }
}

public class SupplierContactInfo
{
  public int SupplierID { get; set; }
  public string? SupplierName { get; set; }
  public string? PhoneNumber { get; set; }
  public string? FaxNumber { get; set; }
  public string? WebsiteURL { get; set; }
}

public class SupplierBankAccount
{
  public int SupplierID { get; set; }
  public string? BankAccountName { get; set; }
  public string? BankAccountBranch { get; set; }
  public string? BankAccountCode { get; set; }
  public string? BankAccountNumber { get; set; }
  public string? BankInternationalCode { get; set; }
}

public class SupplierAccounts
{
  public SupplierContactInfo? ContactInfo { get; set; }
  public SupplierBankAccount? BankAccount { get; set; }
}

public class PurchaseOrderInfo
{
  public int PurchaseOrderID { get; set; }
  public string? SupplierName { get; set; }
  public DateTime OrderDate { get; set; }
}

public class SandboxDbContext(DbContextOptions<SandboxDbContext> options) : DbContext(options)
{
  public DbSet<Order> Orders => Set<Order>();
  public DbSet<OrderLine> OrderLines => Set<OrderLine>();
  public DbSet<Person> People => Set<Person>();
  public DbSet<Supplier> Suppliers => Set<Supplier>();
  public DbSet<CustomerTransaction> CustomerTransactions => Set<CustomerTransaction>();
  public DbSet<PurchaseOrder> PurchaseOrders => Set<PurchaseOrder>();
  public DbSet<StockItem> StockItems => Set<StockItem>();
  public DbSet<StockItemStockGroup> StockItemStockGroups => Set<StockItemStockGroup>();

  protected override void OnModelCreating(ModelBuilder modelBuilder)
  {
    modelBuilder.Entity<Person>().OwnsOne(p => p.CustomFields, cb => { cb.ToJson(); });
    base.OnModelCreating(modelBuilder);
  }
}
```

```target_schema_body
@Document(collection = "orderLines")
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
class Order {

    @Id
    private String id;

    @Field("orderId")
    private Integer orderId;

    @Field("customerId")
    private Integer customerId;

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

    @Field("lastEditedWhen")
    private LocalDateTime lastEditedWhen;

    @ReadOnlyProperty
    @DocumentReference(lazy = true, lookup = "{ 'orderId': ?#{#self.orderId} }", sort = "{ 'orderLineId': 1 }")
    private List<OrderLine> orderLines;

    Order() {
    }

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    public Integer getOrderId() { return orderId; }
    public void setOrderId(Integer orderId) { this.orderId = orderId; }
    public Integer getCustomerId() { return customerId; }
    public void setCustomerId(Integer customerId) { this.customerId = customerId; }
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
    public LocalDateTime getLastEditedWhen() { return lastEditedWhen; }
    public void setLastEditedWhen(LocalDateTime lastEditedWhen) { this.lastEditedWhen = lastEditedWhen; }
    public List<OrderLine> getOrderLines() { return orderLines; }
    public void setOrderLines(List<OrderLine> orderLines) { this.orderLines = orderLines; }
}

@Document(collection = "people")
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

    @Field("phoneNumber")
    private String phoneNumber;

    @Field("faxNumber")
    private String faxNumber;

    @Field("websiteUrl")
    private String websiteUrl;

    @Field("bankAccountName")
    private String bankAccountName;

    @Field("bankAccountBranch")
    private String bankAccountBranch;

    @Field("bankAccountCode")
    private String bankAccountCode;

    @Field("bankAccountNumber")
    private String bankAccountNumber;

    @Field("bankInternationalCode")
    private String bankInternationalCode;

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
    public String getPhoneNumber() { return phoneNumber; }
    public void setPhoneNumber(String phoneNumber) { this.phoneNumber = phoneNumber; }
    public String getFaxNumber() { return faxNumber; }
    public void setFaxNumber(String faxNumber) { this.faxNumber = faxNumber; }
    public String getWebsiteUrl() { return websiteUrl; }
    public void setWebsiteUrl(String websiteUrl) { this.websiteUrl = websiteUrl; }
    public String getBankAccountName() { return bankAccountName; }
    public void setBankAccountName(String bankAccountName) { this.bankAccountName = bankAccountName; }
    public String getBankAccountBranch() { return bankAccountBranch; }
    public void setBankAccountBranch(String bankAccountBranch) { this.bankAccountBranch = bankAccountBranch; }
    public String getBankAccountCode() { return bankAccountCode; }
    public void setBankAccountCode(String bankAccountCode) { this.bankAccountCode = bankAccountCode; }
    public String getBankAccountNumber() { return bankAccountNumber; }
    public void setBankAccountNumber(String bankAccountNumber) { this.bankAccountNumber = bankAccountNumber; }
    public String getBankInternationalCode() { return bankInternationalCode; }
    public void setBankInternationalCode(String bankInternationalCode) { this.bankInternationalCode = bankInternationalCode; }
}

class CustomerTransaction {

    private Integer customerTransactionId;
    private Integer customerId;
    private LocalDate transactionDate;
    private BigDecimal transactionAmount;
    private BigDecimal outstandingBalance;
    private Boolean isFinalized;

    CustomerTransaction() {
    }

    public Integer getCustomerTransactionId() { return customerTransactionId; }
    public void setCustomerTransactionId(Integer customerTransactionId) { this.customerTransactionId = customerTransactionId; }
    public Integer getCustomerId() { return customerId; }
    public void setCustomerId(Integer customerId) { this.customerId = customerId; }
    public LocalDate getTransactionDate() { return transactionDate; }
    public void setTransactionDate(LocalDate transactionDate) { this.transactionDate = transactionDate; }
    public BigDecimal getTransactionAmount() { return transactionAmount; }
    public void setTransactionAmount(BigDecimal transactionAmount) { this.transactionAmount = transactionAmount; }
    public BigDecimal getOutstandingBalance() { return outstandingBalance; }
    public void setOutstandingBalance(BigDecimal outstandingBalance) { this.outstandingBalance = outstandingBalance; }
    public Boolean getIsFinalized() { return isFinalized; }
    public void setIsFinalized(Boolean isFinalized) { this.isFinalized = isFinalized; }
}

class PurchaseOrder {

    private Integer purchaseOrderId;
    private Integer supplierId;
    private LocalDate orderDate;
    private LocalDate expectedDeliveryDate;
    private String supplierReference;
    private Boolean isOrderFinalized;

    PurchaseOrder() {
    }

    public Integer getPurchaseOrderId() { return purchaseOrderId; }
    public void setPurchaseOrderId(Integer purchaseOrderId) { this.purchaseOrderId = purchaseOrderId; }
    public Integer getSupplierId() { return supplierId; }
    public void setSupplierId(Integer supplierId) { this.supplierId = supplierId; }
    public LocalDate getOrderDate() { return orderDate; }
    public void setOrderDate(LocalDate orderDate) { this.orderDate = orderDate; }
    public LocalDate getExpectedDeliveryDate() { return expectedDeliveryDate; }
    public void setExpectedDeliveryDate(LocalDate expectedDeliveryDate) { this.expectedDeliveryDate = expectedDeliveryDate; }
    public String getSupplierReference() { return supplierReference; }
    public void setSupplierReference(String supplierReference) { this.supplierReference = supplierReference; }
    public Boolean getIsOrderFinalized() { return isOrderFinalized; }
    public void setIsOrderFinalized(Boolean isOrderFinalized) { this.isOrderFinalized = isOrderFinalized; }
}

class StockItem {

    private Integer stockItemId;
    private String stockItemName;
    private Integer supplierId;
    private Integer quantityPerOuter;
    private Integer leadTimeDays;
    private Boolean isChillerStock;
    private BigDecimal unitPrice;
    private BigDecimal recommendedRetailPrice;

    StockItem() {
    }

    public Integer getStockItemId() { return stockItemId; }
    public void setStockItemId(Integer stockItemId) { this.stockItemId = stockItemId; }
    public String getStockItemName() { return stockItemName; }
    public void setStockItemName(String stockItemName) { this.stockItemName = stockItemName; }
    public Integer getSupplierId() { return supplierId; }
    public void setSupplierId(Integer supplierId) { this.supplierId = supplierId; }
    public Integer getQuantityPerOuter() { return quantityPerOuter; }
    public void setQuantityPerOuter(Integer quantityPerOuter) { this.quantityPerOuter = quantityPerOuter; }
    public Integer getLeadTimeDays() { return leadTimeDays; }
    public void setLeadTimeDays(Integer leadTimeDays) { this.leadTimeDays = leadTimeDays; }
    public Boolean getIsChillerStock() { return isChillerStock; }
    public void setIsChillerStock(Boolean isChillerStock) { this.isChillerStock = isChillerStock; }
    public BigDecimal getUnitPrice() { return unitPrice; }
    public void setUnitPrice(BigDecimal unitPrice) { this.unitPrice = unitPrice; }
    public BigDecimal getRecommendedRetailPrice() { return recommendedRetailPrice; }
    public void setRecommendedRetailPrice(BigDecimal recommendedRetailPrice) { this.recommendedRetailPrice = recommendedRetailPrice; }
}

class StockItemStockGroup {

    private Integer stockItemStockGroupId;
    private Integer stockItemId;
    private Integer stockGroupId;

    StockItemStockGroup() {
    }

    public Integer getStockItemStockGroupId() { return stockItemStockGroupId; }
    public void setStockItemStockGroupId(Integer stockItemStockGroupId) { this.stockItemStockGroupId = stockItemStockGroupId; }
    public Integer getStockItemId() { return stockItemId; }
    public void setStockItemId(Integer stockItemId) { this.stockItemId = stockItemId; }
    public Integer getStockGroupId() { return stockGroupId; }
    public void setStockGroupId(Integer stockGroupId) { this.stockGroupId = stockGroupId; }
}

class SupplierContactInfo {

    private Integer supplierId;
    private String supplierName;
    private String phoneNumber;
    private String faxNumber;
    private String websiteUrl;

    SupplierContactInfo() {
    }

    public Integer getSupplierId() { return supplierId; }
    public void setSupplierId(Integer supplierId) { this.supplierId = supplierId; }
    public String getSupplierName() { return supplierName; }
    public void setSupplierName(String supplierName) { this.supplierName = supplierName; }
    public String getPhoneNumber() { return phoneNumber; }
    public void setPhoneNumber(String phoneNumber) { this.phoneNumber = phoneNumber; }
    public String getFaxNumber() { return faxNumber; }
    public void setFaxNumber(String faxNumber) { this.faxNumber = faxNumber; }
    public String getWebsiteUrl() { return websiteUrl; }
    public void setWebsiteUrl(String websiteUrl) { this.websiteUrl = websiteUrl; }
}

class SupplierBankAccount {

    private Integer supplierId;
    private String bankAccountName;
    private String bankAccountBranch;
    private String bankAccountCode;
    private String bankAccountNumber;
    private String bankInternationalCode;

    SupplierBankAccount() {
    }

    public Integer getSupplierId() { return supplierId; }
    public void setSupplierId(Integer supplierId) { this.supplierId = supplierId; }
    public String getBankAccountName() { return bankAccountName; }
    public void setBankAccountName(String bankAccountName) { this.bankAccountName = bankAccountName; }
    public String getBankAccountBranch() { return bankAccountBranch; }
    public void setBankAccountBranch(String bankAccountBranch) { this.bankAccountBranch = bankAccountBranch; }
    public String getBankAccountCode() { return bankAccountCode; }
    public void setBankAccountCode(String bankAccountCode) { this.bankAccountCode = bankAccountCode; }
    public String getBankAccountNumber() { return bankAccountNumber; }
    public void setBankAccountNumber(String bankAccountNumber) { this.bankAccountNumber = bankAccountNumber; }
    public String getBankInternationalCode() { return bankInternationalCode; }
    public void setBankInternationalCode(String bankInternationalCode) { this.bankInternationalCode = bankInternationalCode; }
}

class SupplierAccounts {

    private SupplierContactInfo contactInfo;
    private SupplierBankAccount bankAccount;

    SupplierAccounts() {
    }

    public SupplierContactInfo getContactInfo() { return contactInfo; }
    public void setContactInfo(SupplierContactInfo contactInfo) { this.contactInfo = contactInfo; }
    public SupplierBankAccount getBankAccount() { return bankAccount; }
    public void setBankAccount(SupplierBankAccount bankAccount) { this.bankAccount = bankAccount; }
}

class PurchaseOrderInfo {

    private Integer purchaseOrderId;
    private String supplierName;
    private LocalDate orderDate;

    PurchaseOrderInfo() {
    }

    public Integer getPurchaseOrderId() { return purchaseOrderId; }
    public void setPurchaseOrderId(Integer purchaseOrderId) { this.purchaseOrderId = purchaseOrderId; }
    public String getSupplierName() { return supplierName; }
    public void setSupplierName(String supplierName) { this.supplierName = supplierName; }
    public LocalDate getOrderDate() { return orderDate; }
    public void setOrderDate(LocalDate orderDate) { this.orderDate = orderDate; }
}
```

```source_query_body id=1
public static class Query1
{
    public static object Harness(SandboxDbContext ctx)
    {
        int orderId = 26866;
        return HarnessSupport.RunQuery(() => ctx.OrderLines.Where(ol => ol.OrderID == orderId), ol => ol.OrderLineID);
    }
}
```

```target_query_body id=1
final class Query1 {
    public static Query query() {
        return new Query(Criteria.where("orderId").is(26866));
    }

    public static Map<String, Object> harness(MongoTemplate template) {
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
        Map<String, Object> result = new HashMap<>();
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
    public static object Harness(SandboxDbContext ctx)
    {
        decimal unitPrice = 25m;
        return HarnessSupport.RunQuery(() => ctx.OrderLines.Where(ol => ol.UnitPrice == unitPrice), ol => ol.OrderLineID);
    }
}
```

```target_query_body id=2
final class Query2 {
    public static Query query() {
        return new Query(Criteria.where("unitPrice").is(new BigDecimal("25.00")));
    }

    public static Map<String, Object> harness(MongoTemplate template) {
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
        Map<String, Object> result = new HashMap<>();
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
    public static object Harness(SandboxDbContext ctx)
    {
        var from = new DateTime(2014, 12, 20);
        var to = new DateTime(2014, 12, 31);
        return HarnessSupport.RunQuery(() => ctx.OrderLines.Where(ol => ol.PickingCompletedWhen >= from && ol.PickingCompletedWhen <= to), ol => ol.OrderLineID);
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

    public static Map<String, Object> harness(MongoTemplate template) {
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
        Map<String, Object> result = new HashMap<>();
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
    public static object Harness(SandboxDbContext ctx)
    {
        var orderIds = new[] { 1, 10, 100, 1000, 10000 };
        return HarnessSupport.RunQuery(() => ctx.OrderLines.Where(ol => orderIds.Contains(ol.OrderID)), ol => ol.OrderLineID);
    }
}
```

```target_query_body id=4
final class Query4 {
    public static Query query() {
        return new Query(Criteria.where("orderId").in(1, 10, 100, 1000, 10000));
    }

    public static Map<String, Object> harness(MongoTemplate template) {
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
        Map<String, Object> result = new HashMap<>();
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
    public static object Harness(SandboxDbContext ctx)
    {
        string text = "C++";
        return HarnessSupport.RunQuery(() => ctx.OrderLines.Where(ol => ol.Description.Contains(text)), ol => ol.OrderLineID);
    }
}
```

```target_query_body id=5
final class Query5 {
    public static Query query() {
        return new Query(Criteria.where("description").regex(java.util.regex.Pattern.quote("C++")));
    }

    public static Map<String, Object> harness(MongoTemplate template) {
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
        Map<String, Object> result = new HashMap<>();
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
    public static object Harness(SandboxDbContext ctx)
    {
        int skip = 1000;
        int take = 50;
        return HarnessSupport.RunQuery(() => ctx.OrderLines.OrderBy(ol => ol.OrderLineID).Skip(skip).Take(take), null);
    }
}
```

```target_query_body id=6
final class Query6 {
    public static Query query() {
        return new Query().with(Sort.by(Sort.Direction.ASC, "orderLineId")).skip(1000).limit(50);
    }

    public static Map<String, Object> harness(MongoTemplate template) {
        List<OrderLine> rows = template.find(query(), OrderLine.class);
        long count = rows.size();
        Object first = count > 0 ? rows.get(0) : null;
        Object last = count > 1 ? rows.get(rows.size() - 1) : null;
        Map<String, Object> result = new HashMap<>();
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
    public static object Harness(SandboxDbContext ctx)
    {
        return HarnessSupport.RunQuery(
            () => ctx.OrderLines.GroupBy(ol => ol.TaxRate).Select(g => new { TaxRate = g.Key, Count = g.Count() }),
            x => x.TaxRate);
    }
}
```

```target_query_body id=7
final class Query7 {
    static record TaxRateCount(BigDecimal taxRate, Long count) {
    }

    static record CountOnly(Long count) {
    }

    public static TypedAggregation<OrderLine> query() {
        return Aggregation.newAggregation(
                OrderLine.class,
                Aggregation.group("taxRate").count().as("count"),
                Aggregation.project("count").and("taxRate").previousOperation(),
                Aggregation.sort(Sort.Direction.DESC, "count")
        );
    }

    public static Map<String, Object> harness(MongoTemplate template) {
        TypedAggregation<OrderLine> baseAgg = query();

        List<org.springframework.data.mongodb.core.aggregation.AggregationOperation> countOps =
                new ArrayList<>(baseAgg.getPipeline().getOperations());
        countOps.add(Aggregation.count().as("count"));
        TypedAggregation<OrderLine> countAgg = Aggregation.newAggregation(OrderLine.class, countOps);
        CountOnly countResult = template.aggregate(countAgg, OrderLine.class, CountOnly.class).getUniqueMappedResult();
        long count = countResult != null ? countResult.count() : 0L;

        Object first = null;
        if (count > 0) {
            List<org.springframework.data.mongodb.core.aggregation.AggregationOperation> ascOps =
                    new ArrayList<>(query().getPipeline().getOperations());
            ascOps.add(Aggregation.sort(Sort.Direction.ASC, "taxRate"));
            ascOps.add(Aggregation.limit(1));
            TypedAggregation<OrderLine> ascAgg = Aggregation.newAggregation(OrderLine.class, ascOps);
            first = template.aggregate(ascAgg, OrderLine.class, TaxRateCount.class).getUniqueMappedResult();
        }
        Object last = null;
        if (count > 1) {
            List<org.springframework.data.mongodb.core.aggregation.AggregationOperation> descOps =
                    new ArrayList<>(query().getPipeline().getOperations());
            descOps.add(Aggregation.sort(Sort.Direction.DESC, "taxRate"));
            descOps.add(Aggregation.limit(1));
            TypedAggregation<OrderLine> descAgg = Aggregation.newAggregation(OrderLine.class, descOps);
            last = template.aggregate(descAgg, OrderLine.class, TaxRateCount.class).getUniqueMappedResult();
        }

        Map<String, Object> result = new HashMap<>();
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
    public static object Harness(SandboxDbContext ctx)
    {
        decimal? max = ctx.OrderLines.Max(ol => ol.UnitPrice);
        return new { count = max.HasValue ? 1 : 0, firstSample = (object?)max, lastSample = (object?)null };
    }
}
```

```target_query_body id=8
final class Query8 {
    static record MaxProjection(BigDecimal max) {
    }

    public static TypedAggregation<OrderLine> query() {
        return Aggregation.newAggregation(
                OrderLine.class,
                Aggregation.group().max("unitPrice").as("max")
        );
    }

    public static Map<String, Object> harness(MongoTemplate template) {
        MaxProjection result = template.aggregate(query(), OrderLine.class, MaxProjection.class).getUniqueMappedResult();
        BigDecimal max = result != null ? result.max() : null;
        Map<String, Object> out = new HashMap<>();
        out.put("count", max != null ? 1 : 0);
        out.put("firstSample", max);
        out.put("lastSample", null);
        return out;
    }
}
```

```source_query_body id=9
public static class Query9
{
    public static object Harness(SandboxDbContext ctx)
    {
        decimal? sum = ctx.OrderLines.Sum(ol => ol.Quantity * ol.UnitPrice);
        return new { count = sum.HasValue ? 1 : 0, firstSample = (object?)sum, lastSample = (object?)null };
    }
}
```

```target_query_body id=9
final class Query9 {
    static record SumProjection(BigDecimal total) {
    }

    public static TypedAggregation<OrderLine> query() {
        return Aggregation.newAggregation(
                OrderLine.class,
                Aggregation.group().sum(org.springframework.data.mongodb.core.aggregation.ArithmeticOperators.valueOf("quantity").multiplyBy("unitPrice")).as("total")
        );
    }

    public static Map<String, Object> harness(MongoTemplate template) {
        SumProjection result = template.aggregate(query(), OrderLine.class, SumProjection.class).getUniqueMappedResult();
        BigDecimal total = result != null ? result.total() : null;
        Map<String, Object> out = new HashMap<>();
        out.put("count", total != null ? 1 : 0);
        out.put("firstSample", total);
        out.put("lastSample", null);
        return out;
    }
}
```

```source_query_body id=10
public static class Query10
{
    public static object Harness(SandboxDbContext ctx)
    {
        return HarnessSupport.RunQuery(
            () => ctx.Orders.Include(o => o.OrderLines).Where(o => o.OrderID == 530),
            o => o.OrderID);
    }
}
```

```target_query_body id=10
final class Query10 {
    public static Query query() {
        return new Query(Criteria.where("orderId").is(530));
    }

    public static Map<String, Object> harness(MongoTemplate template) {
        Query q = query();
        long count = template.count(q, Order.class);
        Object first = null;
        if (count > 0) {
            first = template.findOne(query(), Order.class);
        }
        Object last = null;
        if (count > 1) {
            last = template.findOne(query().with(Sort.by(Sort.Direction.DESC, "orderId")).limit(1), Order.class);
        }
        Map<String, Object> result = new HashMap<>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
    }
}
```

```source_query_body id=11
public static class Query11
{
    public static object Harness(SandboxDbContext ctx)
    {
        return HarnessSupport.RunQuery(
            () => ctx.Orders.OrderBy(o => o.ExpectedDeliveryDate).Take(1000),
            o => o.OrderID);
    }
}
```

```target_query_body id=11
final class Query11 {
    public static Query query() {
        return new Query().with(Sort.by(Sort.Direction.ASC, "expectedDeliveryDate")).limit(1000);
    }

    public static Map<String, Object> harness(MongoTemplate template) {
        List<Order> rows = template.find(query(), Order.class);
        rows.sort(java.util.Comparator.comparing(Order::getOrderId));
        long count = rows.size();
        Object first = count > 0 ? rows.get(0) : null;
        Object last = count > 1 ? rows.get(rows.size() - 1) : null;
        Map<String, Object> result = new HashMap<>();
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
    public static object Harness(SandboxDbContext ctx)
    {
        return HarnessSupport.RunQuery(
            () => ctx.Orders.Select(o => o.CustomerPurchaseOrderNumber).Distinct(),
            x => x);
    }
}
```

```target_query_body id=12
final class Query12 {
    public static Map<String, Object> harness(MongoTemplate template) {
        List<String> values = template.findDistinct(new Query(), "customerPurchaseOrderNumber", Order.class, String.class);
        List<String> sorted = new ArrayList<>(values);
        sorted.sort(java.util.Comparator.nullsFirst(java.util.Comparator.naturalOrder()));
        long count = sorted.size();
        Object first = count > 0 ? sorted.get(0) : null;
        Object last = count > 1 ? sorted.get(sorted.size() - 1) : null;
        Map<String, Object> result = new HashMap<>();
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
    public static object Harness(SandboxDbContext ctx)
    {
        return HarnessSupport.RunQuery(
            () => ctx.People.Where(p => p.CustomFields!.Title == "Team Member").OrderBy(p => p.PersonID),
            null);
    }
}
```

```target_query_body id=13
final class Query13 {
    public static Query query() {
        return new Query(Criteria.where("customFields").regex("\"Title\"\\s*:\\s*\"Team Member\""))
                .with(Sort.by(Sort.Direction.ASC, "personId"));
    }

    public static Map<String, Object> harness(MongoTemplate template) {
        Query q = query();
        List<Person> rows = template.find(q, Person.class);
        long count = rows.size();
        Object first = count > 0 ? rows.get(0) : null;
        Object last = count > 1 ? rows.get(rows.size() - 1) : null;
        Map<String, Object> result = new HashMap<>();
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
    public static object Harness(SandboxDbContext ctx)
    {
        return HarnessSupport.RunQuery(
            () => ctx.People.Where(p => p.OtherLanguages!.Contains("Slovak")).OrderBy(p => p.PersonID),
            null);
    }
}
```

```target_query_body id=14
final class Query14 {
    public static Query query() {
        return new Query(Criteria.where("otherLanguages").regex("\"Slovak\""))
                .with(Sort.by(Sort.Direction.ASC, "personId"));
    }

    public static Map<String, Object> harness(MongoTemplate template) {
        Query q = query();
        List<Person> rows = template.find(q, Person.class);
        long count = rows.size();
        Object first = count > 0 ? rows.get(0) : null;
        Object last = count > 1 ? rows.get(rows.size() - 1) : null;
        Map<String, Object> result = new HashMap<>();
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
    public static object Harness(SandboxDbContext ctx)
    {
        var first = ctx.Suppliers.Where(s => s.SupplierID < 5).Select(s => s.SupplierID).ToList();
        var last = ctx.Suppliers.Where(s => s.SupplierID >= 5 && s.SupplierID <= 10).Select(s => s.SupplierID).ToList();
        var union = first.Union(last).OrderBy(s => s).ToList();
        return new
        {
            count = union.Count,
            firstSample = union.Count > 0 ? (object?)union[0] : null,
            lastSample = union.Count > 1 ? (object?)union[^1] : null
        };
    }
}
```

```target_query_body id=15
final class Query15 {
    public static Map<String, Object> harness(MongoTemplate template) {
        Query q1 = new Query(Criteria.where("supplierId").lt(5));
        q1.fields().include("supplierId");
        List<Integer> first = new ArrayList<>();
        for (Supplier s : template.find(q1, Supplier.class)) {
            first.add(s.getSupplierId());
        }

        Query q2 = new Query(Criteria.where("supplierId").gte(5).lte(10));
        q2.fields().include("supplierId");
        List<Integer> last = new ArrayList<>();
        for (Supplier s : template.find(q2, Supplier.class)) {
            last.add(s.getSupplierId());
        }

        java.util.TreeSet<Integer> union = new java.util.TreeSet<>();
        union.addAll(first);
        union.addAll(last);
        List<Integer> sorted = new ArrayList<>(union);

        Map<String, Object> result = new HashMap<>();
        result.put("count", sorted.size());
        result.put("firstSample", sorted.isEmpty() ? null : sorted.get(0));
        result.put("lastSample", sorted.size() > 1 ? sorted.get(sorted.size() - 1) : null);
        return result;
    }
}
```

All 15 queries and the schema (source + target) are translated above. Since no tools are available in this chat, this is not compiler-verified — a couple of spots carry residual risk worth flagging: the `ArithmeticOperators.valueOf(...).multiplyBy(...)` call in Query9 and the exact `customFields`/`otherLanguages` JSON regex formatting in Query13/14 (spacing may differ from what's actually stored).
