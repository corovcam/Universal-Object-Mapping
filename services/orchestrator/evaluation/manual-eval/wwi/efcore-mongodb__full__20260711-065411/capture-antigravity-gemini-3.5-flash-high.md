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

    @Field("backorderOrderId")
    private Integer backorderOrderId;

    private LocalDate orderDate;

    private LocalDate expectedDeliveryDate;

    private String customerPurchaseOrderNumber;

    private Boolean isUndersupplyBackordered;

    private String comments;

    private String deliveryInstructions;

    private String internalComments;

    @Field("pickingCompletedWhen")
    private LocalDateTime pickingCompletedWhen;

    @Field("lastEditedWhen")
    private LocalDateTime lastEditedWhen;

    @ReadOnlyProperty
    @DocumentReference(lazy = true, lookup = "{ 'orderId': ?#{#self.orderId} }", sort = "{ 'orderLineId': 1 }")
    private List<OrderLine> orderLines;

    public Order() {}

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
@JsonIgnoreProperties({ "id" })
class Person {
    @Id
    private String id;

    @Field("personId")
    private Integer personId;

    private String fullName;

    private String preferredName;

    private String emailAddress;

    private String customFields;

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

class CustomFields {
    private List<String> otherLanguages;
    private LocalDateTime hireDate;
    private String title;

    public CustomFields() {}

    public List<String> getOtherLanguages() { return otherLanguages; }
    public void setOtherLanguages(List<String> otherLanguages) { this.otherLanguages = otherLanguages; }
    public LocalDateTime getHireDate() { return hireDate; }
    public void setHireDate(LocalDateTime hireDate) { this.hireDate = hireDate; }
    public String getTitle() { return title; }
    public void setTitle(String title) { this.title = title; }
}

@Document(collection = "suppliers")
@JsonIgnoreProperties({ "id" })
class Supplier {
    @Id
    private String id;

    @Field("supplierId")
    private Integer supplierId;

    private String supplierName;

    private String supplierReference;

    private Integer paymentDays;

    private String phoneNumber;

    private String faxNumber;

    private String websiteUrl;

    private String bankAccountName;

    private String bankAccountBranch;

    private String bankAccountCode;

    private String bankAccountNumber;

    private String bankInternationalCode;

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

    public CustomerTransaction() {}

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

    public PurchaseOrder() {}

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

    public StockItem() {}

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

    public StockItemStockGroup() {}

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

    public SupplierContactInfo() {}

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

    public SupplierBankAccount() {}

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

    public SupplierAccounts() {}

    public SupplierContactInfo getContactInfo() { return contactInfo; }
    public void setContactInfo(SupplierContactInfo contactInfo) { this.contactInfo = contactInfo; }
    public SupplierBankAccount getBankAccount() { return bankAccount; }
    public void setBankAccount(SupplierBankAccount bankAccount) { this.bankAccount = bankAccount; }
}

class PurchaseOrderInfo {
    private Integer purchaseOrderId;
    private String supplierName;
    private LocalDate orderDate;

    public PurchaseOrderInfo() {}

    public Integer getPurchaseOrderId() { return purchaseOrderId; }
    public void setPurchaseOrderId(Integer purchaseOrderId) { this.purchaseOrderId = purchaseOrderId; }
    public String getSupplierName() { return supplierName; }
    public void setSupplierName(String supplierName) { this.supplierName = supplierName; }
    public LocalDate getOrderDate() { return orderDate; }
    public void setOrderDate(LocalDate orderDate) { this.orderDate = orderDate; }
}

record TaxRateCount(BigDecimal taxRate, Long count) {}
record SumResult(BigDecimal total) {}
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
    static Map<String, Object> harness(MongoTemplate template) {
        Query q = new Query(Criteria.where("orderId").is(26866));
        long count = template.count(q, OrderLine.class);
        Object first = null;
        if (count > 0) {
            first = template.findOne(new Query(Criteria.where("orderId").is(26866)).with(Sort.by(Sort.Direction.ASC, "orderLineId")).limit(1), OrderLine.class);
        }
        Object last = null;
        if (count > 1) {
            last = template.findOne(new Query(Criteria.where("orderId").is(26866)).with(Sort.by(Sort.Direction.DESC, "orderLineId")).limit(1), OrderLine.class);
        }
        Map<String, Object> result = new LinkedHashMap<>();
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
    static Map<String, Object> harness(MongoTemplate template) {
        BigDecimal unitPrice = new BigDecimal("25");
        Query q = new Query(Criteria.where("unitPrice").is(unitPrice));
        long count = template.count(q, OrderLine.class);
        Object first = null;
        if (count > 0) {
            first = template.findOne(new Query(Criteria.where("unitPrice").is(unitPrice)).with(Sort.by(Sort.Direction.ASC, "orderLineId")).limit(1), OrderLine.class);
        }
        Object last = null;
        if (count > 1) {
            last = template.findOne(new Query(Criteria.where("unitPrice").is(unitPrice)).with(Sort.by(Sort.Direction.DESC, "orderLineId")).limit(1), OrderLine.class);
        }
        Map<String, Object> result = new LinkedHashMap<>();
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
    static Map<String, Object> harness(MongoTemplate template) {
        LocalDateTime from = LocalDateTime.of(2014, 12, 20, 0, 0);
        LocalDateTime to = LocalDateTime.of(2014, 12, 31, 0, 0);
        Query q = new Query(Criteria.where("pickingCompletedWhen").gte(from).lte(to));
        long count = template.count(q, OrderLine.class);
        Object first = null;
        if (count > 0) {
            first = template.findOne(new Query(Criteria.where("pickingCompletedWhen").gte(from).lte(to)).with(Sort.by(Sort.Direction.ASC, "orderLineId")).limit(1), OrderLine.class);
        }
        Object last = null;
        if (count > 1) {
            last = template.findOne(new Query(Criteria.where("pickingCompletedWhen").gte(from).lte(to)).with(Sort.by(Sort.Direction.DESC, "orderLineId")).limit(1), OrderLine.class);
        }
        Map<String, Object> result = new LinkedHashMap<>();
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
    static Map<String, Object> harness(MongoTemplate template) {
        List<Integer> orderIds = List.of(1, 10, 100, 1000, 10000);
        Query q = new Query(Criteria.where("orderId").in(orderIds));
        long count = template.count(q, OrderLine.class);
        Object first = null;
        if (count > 0) {
            first = template.findOne(new Query(Criteria.where("orderId").in(orderIds)).with(Sort.by(Sort.Direction.ASC, "orderLineId")).limit(1), OrderLine.class);
        }
        Object last = null;
        if (count > 1) {
            last = template.findOne(new Query(Criteria.where("orderId").in(orderIds)).with(Sort.by(Sort.Direction.DESC, "orderLineId")).limit(1), OrderLine.class);
        }
        Map<String, Object> result = new LinkedHashMap<>();
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
    static Map<String, Object> harness(MongoTemplate template) {
        String text = "C++";
        Query q = new Query(Criteria.where("description").regex(java.util.regex.Pattern.quote(text)));
        long count = template.count(q, OrderLine.class);
        Object first = null;
        if (count > 0) {
            first = template.findOne(new Query(Criteria.where("description").regex(java.util.regex.Pattern.quote(text))).with(Sort.by(Sort.Direction.ASC, "orderLineId")).limit(1), OrderLine.class);
        }
        Object last = null;
        if (count > 1) {
            last = template.findOne(new Query(Criteria.where("description").regex(java.util.regex.Pattern.quote(text))).with(Sort.by(Sort.Direction.DESC, "orderLineId")).limit(1), OrderLine.class);
        }
        Map<String, Object> result = new LinkedHashMap<>();
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
    static Map<String, Object> harness(MongoTemplate template) {
        Query q = new Query().with(Sort.by(Sort.Direction.ASC, "orderLineId")).skip(1000).limit(50);
        List<OrderLine> list = template.find(q, OrderLine.class);
        long count = list.size();
        Object first = list.isEmpty() ? null : list.get(0);
        Object last = list.size() > 1 ? list.get(list.size() - 1) : null;
        Map<String, Object> result = new LinkedHashMap<>();
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
    static Map<String, Object> harness(MongoTemplate template) {
        TypedAggregation<OrderLine> agg = Aggregation.newAggregation(
            OrderLine.class,
            Aggregation.group("taxRate").count().as("count"),
            Aggregation.project("count").and("taxRate").previousOperation()
        );
        List<TaxRateCount> list = template.aggregate(agg, OrderLine.class, TaxRateCount.class).getMappedResults();
        list.sort((a, b) -> {
            if (a.taxRate() == null && b.taxRate() == null) return 0;
            if (a.taxRate() == null) return -1;
            if (b.taxRate() == null) return 1;
            return a.taxRate().compareTo(b.taxRate());
        });
        long count = list.size();
        Object first = list.isEmpty() ? null : list.get(0);
        Object last = list.size() > 1 ? list.get(list.size() - 1) : null;
        Map<String, Object> result = new LinkedHashMap<>();
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
    static Map<String, Object> harness(MongoTemplate template) {
        Query q = new Query().with(Sort.by(Sort.Direction.DESC, "unitPrice")).limit(1);
        q.fields().include("unitPrice");
        OrderLine line = template.findOne(q, OrderLine.class);
        BigDecimal max = (line != null) ? line.getUnitPrice() : null;
        Map<String, Object> result = new LinkedHashMap<>();
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
    public static object Harness(SandboxDbContext ctx)
    {
        decimal? sum = ctx.OrderLines.Sum(ol => ol.Quantity * ol.UnitPrice);
        return new { count = sum.HasValue ? 1 : 0, firstSample = (object?)sum, lastSample = (object?)null };
    }
}
```

```target_query_body id=9
final class Query9 {
    static Map<String, Object> harness(MongoTemplate template) {
        TypedAggregation<OrderLine> agg = Aggregation.newAggregation(
            OrderLine.class,
            Aggregation.project().andExpression("quantity * unitPrice").as("value"),
            Aggregation.group().sum("value").as("total")
        );
        List<SumResult> results = template.aggregate(agg, OrderLine.class, SumResult.class).getMappedResults();
        BigDecimal sum = (results != null && !results.isEmpty()) ? results.get(0).total() : null;
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("count", sum != null ? 1L : 0L);
        result.put("firstSample", sum);
        result.put("lastSample", null);
        return result;
    }
}
```

```source_query_body id=10
using Microsoft.EntityFrameworkCore;

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
    static Map<String, Object> harness(MongoTemplate template) {
        Query q = new Query(Criteria.where("orderId").is(530));
        long count = template.count(q, Order.class);
        Object first = null;
        if (count > 0) {
            Order order = template.findOne(q, Order.class);
            if (order != null && order.getOrderLines() != null) {
                order.getOrderLines().size();
            }
            first = order;
        }
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", null);
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
    static Map<String, Object> harness(MongoTemplate template) {
        Query q = new Query().with(Sort.by(Sort.Direction.ASC, "expectedDeliveryDate")).limit(1000);
        List<Order> list = template.find(q, Order.class);
        list.sort((a, b) -> {
            if (a.getOrderId() == null && b.getOrderId() == null) return 0;
            if (a.getOrderId() == null) return -1;
            if (b.getOrderId() == null) return 1;
            return a.getOrderId().compareTo(b.getOrderId());
        });
        long count = list.size();
        Object first = list.isEmpty() ? null : list.get(0);
        Object last = list.size() > 1 ? list.get(list.size() - 1) : null;
        Map<String, Object> result = new LinkedHashMap<>();
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
    static Map<String, Object> harness(MongoTemplate template) {
        List<String> list = template.findDistinct(new Query(), "customerPurchaseOrderNumber", Order.class, String.class);
        list.sort((a, b) -> {
            if (a == null && b == null) return 0;
            if (a == null) return -1;
            if (b == null) return 1;
            return a.compareTo(b);
        });
        long count = list.size();
        Object first = list.isEmpty() ? null : list.get(0);
        Object last = list.size() > 1 ? list.get(list.size() - 1) : null;
        Map<String, Object> result = new LinkedHashMap<>();
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
    static Map<String, Object> harness(MongoTemplate template) {
        Query q = new Query(Criteria.where("customFields").regex("\"Title\"\\s*:\\s*\"Team Member\""));
        long count = template.count(q, Person.class);
        Object first = null;
        if (count > 0) {
            first = template.findOne(new Query(Criteria.where("customFields").regex("\"Title\"\\s*:\\s*\"Team Member\""))
                .with(Sort.by(Sort.Direction.ASC, "personId")).limit(1), Person.class);
        }
        Object last = null;
        if (count > 1) {
            last = template.findOne(new Query(Criteria.where("customFields").regex("\"Title\"\\s*:\\s*\"Team Member\""))
                .with(Sort.by(Sort.Direction.DESC, "personId")).limit(1), Person.class);
        }
        Map<String, Object> result = new LinkedHashMap<>();
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
    static Map<String, Object> harness(MongoTemplate template) {
        Query q = new Query(Criteria.where("otherLanguages").regex("\"Slovak\""));
        long count = template.count(q, Person.class);
        Object first = null;
        if (count > 0) {
            first = template.findOne(new Query(Criteria.where("otherLanguages").regex("\"Slovak\""))
                .with(Sort.by(Sort.Direction.ASC, "personId")).limit(1), Person.class);
        }
        Object last = null;
        if (count > 1) {
            last = template.findOne(new Query(Criteria.where("otherLanguages").regex("\"Slovak\""))
                .with(Sort.by(Sort.Direction.DESC, "personId")).limit(1), Person.class);
        }
        Map<String, Object> result = new LinkedHashMap<>();
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
        return new { count = union.Count,
                     firstSample = union.Count > 0 ? (object?)union[0] : null,
                     lastSample = union.Count > 1 ? (object?)union[^1] : null };
    }
}
```

```target_query_body id=15
final class Query15 {
    static Map<String, Object> harness(MongoTemplate template) {
        Query q1 = new Query(Criteria.where("supplierId").lt(5));
        q1.fields().include("supplierId");
        List<Supplier> firstList = template.find(q1, Supplier.class);
        Query q2 = new Query(Criteria.where("supplierId").gte(5).lte(10));
        q2.fields().include("supplierId");
        List<Supplier> lastList = template.find(q2, Supplier.class);
        Set<Integer> unionSet = new HashSet<>();
        for (Supplier s : firstList) {
            if (s.getSupplierId() != null) {
                unionSet.add(s.getSupplierId());
            }
        }
        for (Supplier s : lastList) {
            if (s.getSupplierId() != null) {
                unionSet.add(s.getSupplierId());
            }
        }
        List<Integer> unionList = new ArrayList<>(unionSet);
        Collections.sort(unionList);
        long count = unionList.size();
        Object first = unionList.isEmpty() ? null : unionList.get(0);
        Object last = unionList.size() > 1 ? unionList.get(unionList.size() - 1) : null;
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        return result;
    }
}
```
