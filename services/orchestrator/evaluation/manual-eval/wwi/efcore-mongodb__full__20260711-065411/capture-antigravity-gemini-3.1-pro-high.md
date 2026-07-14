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

    private StockItem stockItem;

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
    public StockItem getStockItem() { return stockItem; }
    public void setStockItem(StockItem stockItem) { this.stockItem = stockItem; }
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

    private Customer customer;

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
    public Customer getCustomer() { return customer; }
    public void setCustomer(Customer customer) { this.customer = customer; }
    public List<OrderLine> getOrderLines() { return orderLines; }
    public void setOrderLines(List<OrderLine> orderLines) { this.orderLines = orderLines; }
}

class Customer {
    private Integer customerId;
    private String customerName;
    private LocalDate accountOpenedDate;
    private BigDecimal creditLimit;
    private List<CustomerTransaction> customerTransactions = new ArrayList<>();

    public Customer() {}

    public Integer getCustomerId() { return customerId; }
    public void setCustomerId(Integer customerId) { this.customerId = customerId; }
    public String getCustomerName() { return customerName; }
    public void setCustomerName(String customerName) { this.customerName = customerName; }
    public LocalDate getAccountOpenedDate() { return accountOpenedDate; }
    public void setAccountOpenedDate(LocalDate accountOpenedDate) { this.accountOpenedDate = accountOpenedDate; }
    public BigDecimal getCreditLimit() { return creditLimit; }
    public void setCreditLimit(BigDecimal creditLimit) { this.creditLimit = creditLimit; }
    public List<CustomerTransaction> getCustomerTransactions() { return customerTransactions; }
    public void setCustomerTransactions(List<CustomerTransaction> customerTransactions) { this.customerTransactions = customerTransactions; }
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

    private List<PurchaseOrder> purchaseOrders = new ArrayList<>();
    private List<StockItem> stockItems = new ArrayList<>();

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
    public List<PurchaseOrder> getPurchaseOrders() { return purchaseOrders; }
    public void setPurchaseOrders(List<PurchaseOrder> purchaseOrders) { this.purchaseOrders = purchaseOrders; }
    public List<StockItem> getStockItems() { return stockItems; }
    public void setStockItems(List<StockItem> stockItems) { this.stockItems = stockItems; }
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
    private List<StockItemStockGroup> stockItemStockGroups = new ArrayList<>();

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
    public List<StockItemStockGroup> getStockItemStockGroups() { return stockItemStockGroups; }
    public void setStockItemStockGroups(List<StockItemStockGroup> stockItemStockGroups) { this.stockItemStockGroups = stockItemStockGroups; }
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
    static java.util.Map<String, Object> harness(MongoTemplate template) {
        int orderId = 26866;
        Query q = new Query(Criteria.where("orderId").is(orderId));
        long count = template.count(q, OrderLine.class);
        Object first = count > 0 ? template.findOne(new Query(Criteria.where("orderId").is(orderId)).with(Sort.by(Sort.Direction.ASC, "orderLineId")).limit(1), OrderLine.class) : null;
        Object last = count > 1 ? template.findOne(new Query(Criteria.where("orderId").is(orderId)).with(Sort.by(Sort.Direction.DESC, "orderLineId")).limit(1), OrderLine.class) : null;
        java.util.Map<String, Object> res = new java.util.HashMap<>();
        res.put("count", count);
        res.put("firstSample", first);
        res.put("lastSample", last);
        return res;
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
    static java.util.Map<String, Object> harness(MongoTemplate template) {
        java.math.BigDecimal unitPrice = new java.math.BigDecimal("25");
        Query q = new Query(Criteria.where("unitPrice").is(unitPrice));
        long count = template.count(q, OrderLine.class);
        Object first = count > 0 ? template.findOne(new Query(Criteria.where("unitPrice").is(unitPrice)).with(Sort.by(Sort.Direction.ASC, "orderLineId")).limit(1), OrderLine.class) : null;
        Object last = count > 1 ? template.findOne(new Query(Criteria.where("unitPrice").is(unitPrice)).with(Sort.by(Sort.Direction.DESC, "orderLineId")).limit(1), OrderLine.class) : null;
        java.util.Map<String, Object> res = new java.util.HashMap<>();
        res.put("count", count);
        res.put("firstSample", first);
        res.put("lastSample", last);
        return res;
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
    static java.util.Map<String, Object> harness(MongoTemplate template) {
        java.time.LocalDateTime from = java.time.LocalDateTime.of(2014, 12, 20, 0, 0);
        java.time.LocalDateTime to = java.time.LocalDateTime.of(2014, 12, 31, 0, 0);
        Query q = new Query(Criteria.where("pickingCompletedWhen").gte(from).lte(to));
        long count = template.count(q, OrderLine.class);
        Object first = count > 0 ? template.findOne(new Query(Criteria.where("pickingCompletedWhen").gte(from).lte(to)).with(Sort.by(Sort.Direction.ASC, "orderLineId")).limit(1), OrderLine.class) : null;
        Object last = count > 1 ? template.findOne(new Query(Criteria.where("pickingCompletedWhen").gte(from).lte(to)).with(Sort.by(Sort.Direction.DESC, "orderLineId")).limit(1), OrderLine.class) : null;
        java.util.Map<String, Object> res = new java.util.HashMap<>();
        res.put("count", count);
        res.put("firstSample", first);
        res.put("lastSample", last);
        return res;
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
    static java.util.Map<String, Object> harness(MongoTemplate template) {
        java.util.List<Integer> orderIds = java.util.List.of(1, 10, 100, 1000, 10000);
        Query q = new Query(Criteria.where("orderId").in(orderIds));
        long count = template.count(q, OrderLine.class);
        Object first = count > 0 ? template.findOne(new Query(Criteria.where("orderId").in(orderIds)).with(Sort.by(Sort.Direction.ASC, "orderLineId")).limit(1), OrderLine.class) : null;
        Object last = count > 1 ? template.findOne(new Query(Criteria.where("orderId").in(orderIds)).with(Sort.by(Sort.Direction.DESC, "orderLineId")).limit(1), OrderLine.class) : null;
        java.util.Map<String, Object> res = new java.util.HashMap<>();
        res.put("count", count);
        res.put("firstSample", first);
        res.put("lastSample", last);
        return res;
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
    static java.util.Map<String, Object> harness(MongoTemplate template) {
        String text = "C++";
        Query q = new Query(Criteria.where("description").regex(".*" + java.util.regex.Pattern.quote(text) + ".*"));
        long count = template.count(q, OrderLine.class);
        Object first = count > 0 ? template.findOne(new Query(Criteria.where("description").regex(".*" + java.util.regex.Pattern.quote(text) + ".*")).with(Sort.by(Sort.Direction.ASC, "orderLineId")).limit(1), OrderLine.class) : null;
        Object last = count > 1 ? template.findOne(new Query(Criteria.where("description").regex(".*" + java.util.regex.Pattern.quote(text) + ".*")).with(Sort.by(Sort.Direction.DESC, "orderLineId")).limit(1), OrderLine.class) : null;
        java.util.Map<String, Object> res = new java.util.HashMap<>();
        res.put("count", count);
        res.put("firstSample", first);
        res.put("lastSample", last);
        return res;
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
    static java.util.Map<String, Object> harness(MongoTemplate template) {
        int skip = 1000;
        int take = 50;
        Query q = new Query().with(Sort.by(Sort.Direction.ASC, "orderLineId")).skip(skip).limit(take);
        java.util.List<OrderLine> results = template.find(q, OrderLine.class);
        long resultCount = results.size();
        Object first = resultCount > 0 ? results.get(0) : null;
        Object last = resultCount > 1 ? results.get((int) resultCount - 1) : null;
        java.util.Map<String, Object> res = new java.util.HashMap<>();
        res.put("count", resultCount);
        res.put("firstSample", first);
        res.put("lastSample", last);
        return res;
    }
}
```

```source_query_body id=7
public static class Query7
{
  public static object Harness(SandboxDbContext ctx)
  {
    return HarnessSupport.RunQuery(
      () => ctx.OrderLines
        .GroupBy(ol => ol.TaxRate)
        .Select(g => new { TaxRate = g.Key, Count = g.Count() })
        .OrderByDescending(x => x.Count),
      x => x.TaxRate);
  }
}
```

```target_query_body id=7
record Query7Projection(java.math.BigDecimal taxRate, Long count) {}
final class Query7 {
    static java.util.Map<String, Object> harness(MongoTemplate template) {
        var orderedAgg = Aggregation.newAggregation(
            OrderLine.class,
            Aggregation.group("taxRate").count().as("count"),
            Aggregation.project("count").and("taxRate").previousOperation(),
            Aggregation.sort(Sort.Direction.DESC, "count").and(Sort.Direction.ASC, "taxRate")
        );
        var orderedResults = template.aggregate(orderedAgg, OrderLine.class, Query7Projection.class).getMappedResults();
        long count = orderedResults.size();
        Object first = count > 0 ? orderedResults.get(0) : null;
        Object last = count > 1 ? orderedResults.get((int) count - 1) : null;
        java.util.Map<String, Object> res = new java.util.HashMap<>();
        res.put("count", count);
        res.put("firstSample", first);
        res.put("lastSample", last);
        return res;
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
record Query8Projection(java.math.BigDecimal max) {}
final class Query8 {
    static java.util.Map<String, Object> harness(MongoTemplate template) {
        var agg = Aggregation.newAggregation(
            OrderLine.class,
            Aggregation.group().max("unitPrice").as("max")
        );
        var result = template.aggregate(agg, OrderLine.class, Query8Projection.class).getUniqueMappedResult();
        java.math.BigDecimal max = result != null ? result.max() : null;
        long count = max != null ? 1 : 0;
        java.util.Map<String, Object> res = new java.util.HashMap<>();
        res.put("count", count);
        res.put("firstSample", max);
        res.put("lastSample", null);
        return res;
    }
}
```

```source_query_body id=9
public static class Query9
{
  public static object Harness(SandboxDbContext ctx)
  {
    decimal? sum = ctx.OrderLines.Sum(ol => ol.Quantity * ol.UnitPrice);
    return new { count = 1, firstSample = (object?)sum, lastSample = (object?)null };
  }
}
```

```target_query_body id=9
record Query9Projection(java.math.BigDecimal sum) {}
final class Query9 {
    static java.util.Map<String, Object> harness(MongoTemplate template) {
        var agg = Aggregation.newAggregation(
            OrderLine.class,
            Aggregation.project().andExpression("quantity * unitPrice").as("total"),
            Aggregation.group().sum("total").as("sum")
        );
        var result = template.aggregate(agg, OrderLine.class, Query9Projection.class).getUniqueMappedResult();
        java.math.BigDecimal sum = result != null ? result.sum() : null;
        if (sum == null) sum = java.math.BigDecimal.ZERO;
        java.util.Map<String, Object> res = new java.util.HashMap<>();
        res.put("count", 1L);
        res.put("firstSample", sum);
        res.put("lastSample", null);
        return res;
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
    static java.util.Map<String, Object> harness(MongoTemplate template) {
        Query q = new Query(Criteria.where("orderId").is(530));
        long count = template.count(q, Order.class);
        Object first = null;
        if (count > 0) {
            Order firstDoc = template.findOne(new Query(Criteria.where("orderId").is(530)).with(Sort.by(Sort.Direction.ASC, "orderId")).limit(1), Order.class);
            if (firstDoc != null && firstDoc.getOrderLines() != null) {
                firstDoc.getOrderLines().size();
            }
            first = firstDoc;
        }
        Object last = null;
        if (count > 1) {
            Order lastDoc = template.findOne(new Query(Criteria.where("orderId").is(530)).with(Sort.by(Sort.Direction.DESC, "orderId")).limit(1), Order.class);
            if (lastDoc != null && lastDoc.getOrderLines() != null) {
                lastDoc.getOrderLines().size();
            }
            last = lastDoc;
        }
        java.util.Map<String, Object> res = new java.util.HashMap<>();
        res.put("count", count);
        res.put("firstSample", first);
        res.put("lastSample", last);
        return res;
    }
}
```

```source_query_body id=11
public static class Query11
{
  public static object Harness(SandboxDbContext ctx)
  {
    return HarnessSupport.RunQuery(
      () => ctx.Orders.OrderBy(o => o.ExpectedDeliveryDate).Take(1000), null);
  }
}
```

```target_query_body id=11
final class Query11 {
    static java.util.Map<String, Object> harness(MongoTemplate template) {
        Query q = new Query().with(Sort.by(Sort.Direction.ASC, "expectedDeliveryDate")).limit(1000);
        java.util.List<Order> results = template.find(q, Order.class);
        long count = results.size();
        Object first = count > 0 ? results.get(0) : null;
        Object last = count > 1 ? results.get((int) count - 1) : null;
        java.util.Map<String, Object> res = new java.util.HashMap<>();
        res.put("count", count);
        res.put("firstSample", first);
        res.put("lastSample", last);
        return res;
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
    static java.util.Map<String, Object> harness(MongoTemplate template) {
        java.util.List<String> results = template.query(Order.class).distinct("customerPurchaseOrderNumber").as(String.class).all();
        java.util.Collections.sort(results, (a, b) -> {
            if (a == null && b == null) return 0;
            if (a == null) return -1;
            if (b == null) return 1;
            return a.compareTo(b);
        });
        long count = results.size();
        Object first = count > 0 ? results.get(0) : null;
        Object last = count > 1 ? results.get((int) count - 1) : null;
        java.util.Map<String, Object> res = new java.util.HashMap<>();
        res.put("count", count);
        res.put("firstSample", first);
        res.put("lastSample", last);
        return res;
    }
}
```

```source_query_body id=13
public static class Query13
{
  public static object Harness(SandboxDbContext ctx)
  {
    return HarnessSupport.RunQuery(
      () => ctx.People.Where(p => p.CustomFields!.Title == "Team Member").OrderBy(p => p.PersonID), null);
  }
}
```

```target_query_body id=13
final class Query13 {
    static java.util.Map<String, Object> harness(MongoTemplate template) {
        Query q = new Query(Criteria.where("customFields").regex("\"Title\"\\s*:\\s*\"Team Member\""))
                .with(Sort.by(Sort.Direction.ASC, "personId"));
        java.util.List<Person> results = template.find(q, Person.class);
        long count = results.size();
        Object first = count > 0 ? results.get(0) : null;
        Object last = count > 1 ? results.get((int) count - 1) : null;
        java.util.Map<String, Object> res = new java.util.HashMap<>();
        res.put("count", count);
        res.put("firstSample", first);
        res.put("lastSample", last);
        return res;
    }
}
```

```source_query_body id=14
public static class Query14
{
  public static object Harness(SandboxDbContext ctx)
  {
    return HarnessSupport.RunQuery(
      () => ctx.People.Where(p => p.OtherLanguages!.Contains("Slovak")).OrderBy(p => p.PersonID), null);
  }
}
```

```target_query_body id=14
final class Query14 {
    static java.util.Map<String, Object> harness(MongoTemplate template) {
        Query q = new Query(Criteria.where("otherLanguages").regex("\"Slovak\""))
                .with(Sort.by(Sort.Direction.ASC, "personId"));
        java.util.List<Person> results = template.find(q, Person.class);
        long count = results.size();
        Object first = count > 0 ? results.get(0) : null;
        Object last = count > 1 ? results.get((int) count - 1) : null;
        java.util.Map<String, Object> res = new java.util.HashMap<>();
        res.put("count", count);
        res.put("firstSample", first);
        res.put("lastSample", last);
        return res;
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
    static java.util.Map<String, Object> harness(MongoTemplate template) {
        Query q1 = new Query(Criteria.where("supplierId").lt(5));
        q1.fields().include("supplierId");
        java.util.List<Integer> firstIds = new java.util.ArrayList<>();
        for (Supplier s : template.find(q1, Supplier.class)) {
            firstIds.add(s.getSupplierId());
        }

        Query q2 = new Query(Criteria.where("supplierId").gte(5).lte(10));
        q2.fields().include("supplierId");
        java.util.List<Integer> lastIds = new java.util.ArrayList<>();
        for (Supplier s : template.find(q2, Supplier.class)) {
            lastIds.add(s.getSupplierId());
        }

        java.util.Set<Integer> set = new java.util.HashSet<>(firstIds);
        set.addAll(lastIds);
        java.util.List<Integer> union = new java.util.ArrayList<>(set);
        java.util.Collections.sort(union);

        long count = union.size();
        Object firstSample = count > 0 ? union.get(0) : null;
        Object lastSample = count > 1 ? union.get((int) count - 1) : null;

        java.util.Map<String, Object> res = new java.util.HashMap<>();
        res.put("count", count);
        res.put("firstSample", firstSample);
        res.put("lastSample", lastSample);
        return res;
    }
}
```
