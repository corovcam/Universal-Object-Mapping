```source_schema_body
public class OrderLine
{
    public virtual int OrderLineID { get; set; }
    public virtual int OrderID { get; set; }
    public virtual int StockItemID { get; set; }
    public virtual required string Description { get; set; }
    public virtual int Quantity { get; set; }
    public virtual decimal? UnitPrice { get; set; }
    public virtual decimal TaxRate { get; set; }
    public virtual int PickedQuantity { get; set; }
    public virtual DateTime? PickingCompletedWhen { get; set; }
    public virtual int LastEditedBy { get; set; }
    public virtual DateTime LastEditedWhen { get; set; }
}

public class Order
{
    public virtual int OrderID { get; set; }
    public virtual int CustomerID { get; set; }
    public virtual int? BackorderOrderID { get; set; }
    public virtual DateTime OrderDate { get; set; }
    public virtual DateTime ExpectedDeliveryDate { get; set; }
    public virtual string? CustomerPurchaseOrderNumber { get; set; }
    public virtual bool IsUndersupplyBackordered { get; set; }
    public virtual string? Comments { get; set; }
    public virtual string? DeliveryInstructions { get; set; }
    public virtual string? InternalComments { get; set; }
    public virtual DateTime? PickingCompletedWhen { get; set; }
    public virtual DateTime LastEditedWhen { get; set; }
    public virtual IList<OrderLine> OrderLines { get; set; } = [];
}

public class Person
{
    public virtual int PersonID { get; set; }
    public virtual required string FullName { get; set; }
    public virtual required string PreferredName { get; set; }
    public virtual string? EmailAddress { get; set; }
    public virtual string? CustomFields { get; set; }
    public virtual string? OtherLanguages { get; set; }
}

public class Supplier
{
    public virtual int SupplierID { get; set; }
    public virtual required string SupplierName { get; set; }
    public virtual string? SupplierReference { get; set; }
    public virtual int PaymentDays { get; set; }
    public virtual string? PhoneNumber { get; set; }
    public virtual string? FaxNumber { get; set; }
    public virtual string? WebsiteURL { get; set; }
    public virtual string? BankAccountName { get; set; }
    public virtual string? BankAccountBranch { get; set; }
    public virtual string? BankAccountCode { get; set; }
    public virtual string? BankAccountNumber { get; set; }
    public virtual string? BankInternationalCode { get; set; }
}

public class CustomerTransaction
{
    public virtual int CustomerTransactionID { get; set; }
    public virtual int CustomerID { get; set; }
    public virtual DateTime TransactionDate { get; set; }
    public virtual decimal TransactionAmount { get; set; }
    public virtual decimal OutstandingBalance { get; set; }
    public virtual bool IsFinalized { get; set; }
}

public class PurchaseOrder
{
    public virtual int PurchaseOrderID { get; set; }
    public virtual int SupplierID { get; set; }
    public virtual DateTime OrderDate { get; set; }
    public virtual DateTime ExpectedDeliveryDate { get; set; }
    public virtual string? SupplierReference { get; set; }
    public virtual bool IsOrderFinalized { get; set; }
}

public class StockItem
{
    public virtual int StockItemID { get; set; }
    public virtual required string StockItemName { get; set; }
    public virtual int SupplierID { get; set; }
    public virtual int QuantityPerOuter { get; set; }
    public virtual int LeadTimeDays { get; set; }
    public virtual bool IsChillerStock { get; set; }
    public virtual decimal? UnitPrice { get; set; }
    public virtual decimal RecommendedRetailPrice { get; set; }
}

public class StockItemStockGroup
{
    public virtual int StockItemStockGroupID { get; set; }
    public virtual int StockItemID { get; set; }
    public virtual int StockGroupID { get; set; }
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

public class OrderLineMap : ClassMapping<OrderLine> {
    public OrderLineMap() {
        Table("OrderLines"); Schema("Sales");
        Id(x => x.OrderLineID, m => m.Generator(Generators.Identity));
        Property(x => x.OrderID, m => { m.Insert(false); m.Update(false); });
        Property(x => x.StockItemID);
        Property(x => x.Description);
        Property(x => x.Quantity);
        Property(x => x.UnitPrice);
        Property(x => x.TaxRate);
        Property(x => x.PickedQuantity);
        Property(x => x.PickingCompletedWhen);
        Property(x => x.LastEditedBy);
        Property(x => x.LastEditedWhen);
    }
}

public class OrderMap : ClassMapping<Order> {
    public OrderMap() {
        Table("Orders"); Schema("Sales");
        Id(x => x.OrderID, m => m.Generator(Generators.Identity));
        Property(x => x.CustomerID);
        Property(x => x.BackorderOrderID);
        Property(x => x.OrderDate);
        Property(x => x.ExpectedDeliveryDate);
        Property(x => x.CustomerPurchaseOrderNumber);
        Property(x => x.IsUndersupplyBackordered);
        Property(x => x.Comments);
        Property(x => x.DeliveryInstructions);
        Property(x => x.InternalComments);
        Property(x => x.PickingCompletedWhen);
        Property(x => x.LastEditedWhen);
        Bag(x => x.OrderLines, map => { map.Key(k => k.Column("OrderID")); map.Inverse(true); }, rel => rel.OneToMany());
    }
}

public class PersonMap : ClassMapping<Person> {
    public PersonMap() {
        Table("People"); Schema("Application");
        Id(x => x.PersonID, m => m.Generator(Generators.Identity));
        Property(x => x.FullName);
        Property(x => x.PreferredName);
        Property(x => x.EmailAddress);
        Property(x => x.CustomFields);
        Property(x => x.OtherLanguages);
    }
}

public class SupplierMap : ClassMapping<Supplier> {
    public SupplierMap() {
        Table("Suppliers"); Schema("Purchasing");
        Id(x => x.SupplierID, m => m.Generator(Generators.Identity));
        Property(x => x.SupplierName);
        Property(x => x.SupplierReference);
        Property(x => x.PaymentDays);
        Property(x => x.PhoneNumber);
        Property(x => x.FaxNumber);
        Property(x => x.WebsiteURL);
        Property(x => x.BankAccountName);
        Property(x => x.BankAccountBranch);
        Property(x => x.BankAccountCode);
        Property(x => x.BankAccountNumber);
        Property(x => x.BankInternationalCode);
    }
}

public class CustomerTransactionMap : ClassMapping<CustomerTransaction> {
    public CustomerTransactionMap() {
        Table("CustomerTransactions"); Schema("Sales");
        Id(x => x.CustomerTransactionID, m => m.Generator(Generators.Identity));
        Property(x => x.CustomerID);
        Property(x => x.TransactionDate);
        Property(x => x.TransactionAmount);
        Property(x => x.OutstandingBalance);
        Property(x => x.IsFinalized);
    }
}

public class PurchaseOrderMap : ClassMapping<PurchaseOrder> {
    public PurchaseOrderMap() {
        Table("PurchaseOrders"); Schema("Purchasing");
        Id(x => x.PurchaseOrderID, m => m.Generator(Generators.Identity));
        Property(x => x.SupplierID);
        Property(x => x.OrderDate);
        Property(x => x.ExpectedDeliveryDate);
        Property(x => x.SupplierReference);
        Property(x => x.IsOrderFinalized);
    }
}

public class StockItemMap : ClassMapping<StockItem> {
    public StockItemMap() {
        Table("StockItems"); Schema("Warehouse");
        Id(x => x.StockItemID, m => m.Generator(Generators.Identity));
        Property(x => x.StockItemName);
        Property(x => x.SupplierID);
        Property(x => x.QuantityPerOuter);
        Property(x => x.LeadTimeDays);
        Property(x => x.IsChillerStock);
        Property(x => x.UnitPrice);
        Property(x => x.RecommendedRetailPrice);
    }
}

public class StockItemStockGroupMap : ClassMapping<StockItemStockGroup> {
    public StockItemStockGroupMap() {
        Table("StockItemStockGroups"); Schema("Warehouse");
        Id(x => x.StockItemStockGroupID, m => m.Generator(Generators.Identity));
        Property(x => x.StockItemID);
        Property(x => x.StockGroupID);
    }
}

public record TaxRateCount { public decimal TaxRate { get; set; } public long Count { get; set; } }
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
    private LocalDateTime orderDate;
    @Field("expectedDeliveryDate")
    private LocalDateTime expectedDeliveryDate;
    @Field("customerPurchaseOrderNumber")
    private String customerPurchaseOrderNumber;
    @Field("isUndersupplyBackordered")
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

@Document(collection = "customerTransactions")
class CustomerTransaction {
    @Id
    private String id;
    @Field("customerTransactionId")
    private Integer customerTransactionId;
    @Field("customerId")
    private Integer customerId;
    @Field("transactionDate")
    private LocalDateTime transactionDate;
    @Field("transactionAmount")
    private BigDecimal transactionAmount;
    @Field("outstandingBalance")
    private BigDecimal outstandingBalance;
    @Field("isFinalized")
    private Boolean isFinalized;

    public CustomerTransaction() {}

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    public Integer getCustomerTransactionId() { return customerTransactionId; }
    public void setCustomerTransactionId(Integer customerTransactionId) { this.customerTransactionId = customerTransactionId; }
    public Integer getCustomerId() { return customerId; }
    public void setCustomerId(Integer customerId) { this.customerId = customerId; }
    public LocalDateTime getTransactionDate() { return transactionDate; }
    public void setTransactionDate(LocalDateTime transactionDate) { this.transactionDate = transactionDate; }
    public BigDecimal getTransactionAmount() { return transactionAmount; }
    public void setTransactionAmount(BigDecimal transactionAmount) { this.transactionAmount = transactionAmount; }
    public BigDecimal getOutstandingBalance() { return outstandingBalance; }
    public void setOutstandingBalance(BigDecimal outstandingBalance) { this.outstandingBalance = outstandingBalance; }
    public Boolean getIsFinalized() { return isFinalized; }
    public void setIsFinalized(Boolean isFinalized) { this.isFinalized = isFinalized; }
}

@Document(collection = "purchaseOrders")
class PurchaseOrder {
    @Id
    private String id;
    @Field("purchaseOrderId")
    private Integer purchaseOrderId;
    @Field("supplierId")
    private Integer supplierId;
    @Field("orderDate")
    private LocalDateTime orderDate;
    @Field("expectedDeliveryDate")
    private LocalDateTime expectedDeliveryDate;
    @Field("supplierReference")
    private String supplierReference;
    @Field("isOrderFinalized")
    private Boolean isOrderFinalized;

    public PurchaseOrder() {}

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    public Integer getPurchaseOrderId() { return purchaseOrderId; }
    public void setPurchaseOrderId(Integer purchaseOrderId) { this.purchaseOrderId = purchaseOrderId; }
    public Integer getSupplierId() { return supplierId; }
    public void setSupplierId(Integer supplierId) { this.supplierId = supplierId; }
    public LocalDateTime getOrderDate() { return orderDate; }
    public void setOrderDate(LocalDateTime orderDate) { this.orderDate = orderDate; }
    public LocalDateTime getExpectedDeliveryDate() { return expectedDeliveryDate; }
    public void setExpectedDeliveryDate(LocalDateTime expectedDeliveryDate) { this.expectedDeliveryDate = expectedDeliveryDate; }
    public String getSupplierReference() { return supplierReference; }
    public void setSupplierReference(String supplierReference) { this.supplierReference = supplierReference; }
    public Boolean getIsOrderFinalized() { return isOrderFinalized; }
    public void setIsOrderFinalized(Boolean isOrderFinalized) { this.isOrderFinalized = isOrderFinalized; }
}

@Document(collection = "stockItems")
class StockItem {
    @Id
    private String id;
    @Field("stockItemId")
    private Integer stockItemId;
    @Field("stockItemName")
    private String stockItemName;
    @Field("supplierId")
    private Integer supplierId;
    @Field("quantityPerOuter")
    private Integer quantityPerOuter;
    @Field("leadTimeDays")
    private Integer leadTimeDays;
    @Field("isChillerStock")
    private Boolean isChillerStock;
    @Field("unitPrice")
    private BigDecimal unitPrice;
    @Field("recommendedRetailPrice")
    private BigDecimal recommendedRetailPrice;

    public StockItem() {}

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
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

@Document(collection = "stockItemStockGroups")
class StockItemStockGroup {
    @Id
    private String id;
    @Field("stockItemStockGroupId")
    private Integer stockItemStockGroupId;
    @Field("stockItemId")
    private Integer stockItemId;
    @Field("stockGroupId")
    private Integer stockGroupId;

    public StockItemStockGroup() {}

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
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
    private LocalDateTime orderDate;

    public PurchaseOrderInfo() {}

    public Integer getPurchaseOrderId() { return purchaseOrderId; }
    public void setPurchaseOrderId(Integer purchaseOrderId) { this.purchaseOrderId = purchaseOrderId; }
    public String getSupplierName() { return supplierName; }
    public void setSupplierName(String supplierName) { this.supplierName = supplierName; }
    public LocalDateTime getOrderDate() { return orderDate; }
    public void setOrderDate(LocalDateTime orderDate) { this.orderDate = orderDate; }
}

record TaxRateCount(BigDecimal taxRate, Long count) {}
record CountProjection(Long count) {}
```

```source_query_body id=1
public static class Query1
{
    public static object Harness(NHibernate.ISession session)
    {
        int orderId = 26866;
        return HarnessSupport.RunQuery(
            () => session.Query<OrderLine>().Where(ol => ol.OrderID == orderId),
            ol => ol.OrderLineID);
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
        result.put("mongoQuery", Map.of("collection", template.getCollectionName(OrderLine.class), "filter", q.getQueryObject()));
        return result;
    }
}
```

```source_query_body id=2
public static class Query2
{
    public static object Harness(NHibernate.ISession session)
    {
        decimal unitPrice = 25m;
        return HarnessSupport.RunQuery(
            () => session.Query<OrderLine>().Where(ol => ol.UnitPrice == unitPrice),
            ol => ol.OrderLineID);
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
        result.put("mongoQuery", Map.of("collection", template.getCollectionName(OrderLine.class), "filter", q.getQueryObject()));
        return result;
    }
}
```

```source_query_body id=3
public static class Query3
{
    public static object Harness(NHibernate.ISession session)
    {
        var from = new DateTime(2014, 12, 20);
        var to = new DateTime(2014, 12, 31);
        return HarnessSupport.RunQuery(
            () => session.Query<OrderLine>().Where(ol => ol.PickingCompletedWhen >= from && ol.PickingCompletedWhen <= to),
            ol => ol.OrderLineID);
    }
}
```

```target_query_body id=3
final class Query3 {
    public static Query query() {
        LocalDateTime from = LocalDateTime.of(2014, 12, 20, 0, 0, 0);
        LocalDateTime to = LocalDateTime.of(2014, 12, 31, 0, 0, 0);
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
        result.put("mongoQuery", Map.of("collection", template.getCollectionName(OrderLine.class), "filter", q.getQueryObject()));
        return result;
    }
}
```

```source_query_body id=4
public static class Query4
{
    public static object Harness(NHibernate.ISession session)
    {
        var orderIds = new List<int> { 1, 10, 100, 1000, 10000 };
        return HarnessSupport.RunQuery(
            () => session.Query<OrderLine>().Where(ol => orderIds.Contains(ol.OrderID)),
            ol => ol.OrderLineID);
    }
}
```

```target_query_body id=4
final class Query4 {
    public static Query query() {
        List<Integer> orderIds = List.of(1, 10, 100, 1000, 10000);
        return new Query(Criteria.where("orderId").in(orderIds));
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
        result.put("mongoQuery", Map.of("collection", template.getCollectionName(OrderLine.class), "filter", q.getQueryObject()));
        return result;
    }
}
```

```source_query_body id=5
public static class Query5
{
    public static object Harness(NHibernate.ISession session)
    {
        string text = "C++";
        return HarnessSupport.RunQuery(
            () => session.Query<OrderLine>().Where(ol => ol.Description.Contains(text)),
            ol => ol.OrderLineID);
    }
}
```

```target_query_body id=5
final class Query5 {
    public static Query query() {
        return new Query(Criteria.where("description").regex("C\\+\\+"));
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
        result.put("mongoQuery", Map.of("collection", template.getCollectionName(OrderLine.class), "filter", q.getQueryObject()));
        return result;
    }
}
```

```source_query_body id=6
public static class Query6
{
    public static object Harness(NHibernate.ISession session)
    {
        int skip = 1000;
        int take = 50;
        return HarnessSupport.RunQuery(
            () => session.Query<OrderLine>().OrderBy(ol => ol.OrderLineID).Skip(skip).Take(take),
            ol => ol.OrderLineID);
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

    public static Map<String, Object> harness(MongoTemplate template) {
        Query q = query();
        List<OrderLine> list = template.find(q, OrderLine.class);
        long count = list.size();
        Object first = count > 0 ? list.get(0) : null;
        Object last = count > 1 ? list.get(list.size() - 1) : null;
        Map<String, Object> result = new HashMap<>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        result.put("mongoQuery", Map.of("collection", template.getCollectionName(OrderLine.class), "filter", q.getQueryObject(), "sort", q.getSortObject()));
        return result;
    }
}
```

```source_query_body id=7
public static class Query7
{
    public static object Harness(NHibernate.ISession session)
    {
        var dict = session.Query<OrderLine>()
            .GroupBy(ol => ol.TaxRate)
            .Select(g => new { TaxRate = g.Key, Count = g.Count() })
            .OrderByDescending(x => x.Count)
            .ToDictionary(x => x.TaxRate, x => x.Count);
        var list = dict.Select(kvp => new TaxRateCount { TaxRate = kvp.Key, Count = kvp.Value }).ToList();
        return new {
            count = list.Count,
            firstSample = list.Count > 0 ? (object)list[0] : null,
            lastSample = list.Count > 1 ? (object)list[^1] : null
        };
    }
}
```

```target_query_body id=7
final class Query7 {
    public static Map<BigDecimal, Integer> query(MongoTemplate template) {
        var agg = Aggregation.newAggregation(
            OrderLine.class,
            Aggregation.group("taxRate").count().as("count"),
            Aggregation.project("count").and("taxRate").previousOperation(),
            Aggregation.sort(Sort.Direction.DESC, "count")
        );
        List<TaxRateCount> results = template.aggregate(agg, OrderLine.class, TaxRateCount.class).getMappedResults();
        Map<BigDecimal, Integer> map = new java.util.LinkedHashMap<>();
        for (TaxRateCount trc : results) {
            map.put(trc.taxRate(), trc.count().intValue());
        }
        return map;
    }

    public static Map<String, Object> harness(MongoTemplate template) {
        Map<BigDecimal, Integer> map = query(template);
        List<TaxRateCount> list = new ArrayList<>();
        for (Map.Entry<BigDecimal, Integer> entry : map.entrySet()) {
            list.add(new TaxRateCount(entry.getKey(), entry.getValue().longValue()));
        }
        long count = list.size();
        Object first = count > 0 ? list.get(0) : null;
        Object last = count > 1 ? list.get(list.size() - 1) : null;
        
        Map<String, Object> result = new HashMap<>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        result.put("mongoAggregation", Map.of(
            "collection", template.getCollectionName(OrderLine.class),
            "pipeline", Aggregation.newAggregation(
                OrderLine.class,
                Aggregation.group("taxRate").count().as("count"),
                Aggregation.project("count").and("taxRate").previousOperation(),
                Aggregation.sort(Sort.Direction.DESC, "count")
            ).toString()
        ));
        return result;
    }
}
```

```source_query_body id=8
public static class Query8
{
    public static object Harness(NHibernate.ISession session)
    {
        decimal? max = session.Query<OrderLine>().Max(ol => ol.UnitPrice);
        return new { count = max.HasValue ? 1 : 0, firstSample = (object?)max, lastSample = (object?)null };
    }
}
```

```target_query_body id=8
final class Query8 {
    public static BigDecimal query(MongoTemplate template) {
        var agg = Aggregation.newAggregation(
            OrderLine.class,
            Aggregation.group().max("unitPrice").as("maxVal")
        );
        record MaxResult(BigDecimal maxVal) {}
        MaxResult res = template.aggregate(agg, OrderLine.class, MaxResult.class).getUniqueMappedResult();
        return res != null ? res.maxVal() : null;
    }

    public static Map<String, Object> harness(MongoTemplate template) {
        BigDecimal max = query(template);
        long count = max != null ? 1 : 0;
        Map<String, Object> result = new HashMap<>();
        result.put("count", count);
        result.put("firstSample", max);
        result.put("lastSample", null);
        result.put("mongoAggregation", Map.of(
            "collection", template.getCollectionName(OrderLine.class),
            "pipeline", Aggregation.newAggregation(
                OrderLine.class,
                Aggregation.group().max("unitPrice").as("maxVal")
            ).toString()
        ));
        return result;
    }
}
```

```source_query_body id=9
public static class Query9
{
    public static object Harness(NHibernate.ISession session)
    {
        decimal? sum = session.Query<OrderLine>().Sum(ol => ol.Quantity * ol.UnitPrice);
        return new { count = sum.HasValue ? 1 : 0, firstSample = (object?)sum, lastSample = (object?)null };
    }
}
```

```target_query_body id=9
final class Query9 {
    public static BigDecimal query(MongoTemplate template) {
        var agg = Aggregation.newAggregation(
            OrderLine.class,
            Aggregation.project().andExpression("quantity * unitPrice").as("lineTotal"),
            Aggregation.group().sum("lineTotal").as("sumVal")
        );
        record SumResult(BigDecimal sumVal) {}
        SumResult res = template.aggregate(agg, OrderLine.class, SumResult.class).getUniqueMappedResult();
        return res != null ? res.sumVal() : null;
    }

    public static Map<String, Object> harness(MongoTemplate template) {
        BigDecimal sum = query(template);
        long count = sum != null ? 1 : 0;
        Map<String, Object> result = new HashMap<>();
        result.put("count", count);
        result.put("firstSample", sum);
        result.put("lastSample", null);
        result.put("mongoAggregation", Map.of(
            "collection", template.getCollectionName(OrderLine.class),
            "pipeline", Aggregation.newAggregation(
                OrderLine.class,
                Aggregation.project().andExpression("quantity * unitPrice").as("lineTotal"),
                Aggregation.group().sum("lineTotal").as("sumVal")
            ).toString()
        ));
        return result;
    }
}
```

```source_query_body id=10
public static class Query10
{
    public static object Harness(NHibernate.ISession session)
    {
        return HarnessSupport.RunQuery(
            () => session.Query<Order>().Fetch(o => o.OrderLines).Where(o => o.OrderID == 530),
            o => o.OrderID);
    }
}
```

```target_query_body id=10
final class Query10 {
    public static Order query(MongoTemplate template) {
        Query q = new Query(Criteria.where("orderId").is(530));
        Order order = template.findOne(q, Order.class);
        if (order != null && order.getOrderLines() != null) {
            order.getOrderLines().size();
        }
        return order;
    }

    public static Map<String, Object> harness(MongoTemplate template) {
        Order order = query(template);
        long count = order != null ? 1 : 0;
        Map<String, Object> result = new HashMap<>();
        result.put("count", count);
        result.put("firstSample", order);
        result.put("lastSample", null);
        result.put("mongoQuery", Map.of("collection", template.getCollectionName(Order.class), "filter", new Query(Criteria.where("orderId").is(530)).getQueryObject()));
        return result;
    }
}
```

```source_query_body id=11
public static class Query11
{
    public static object Harness(NHibernate.ISession session)
    {
        return HarnessSupport.RunQuery(
            () => session.Query<Order>().OrderBy(o => o.ExpectedDeliveryDate).Take(1000),
            o => o.OrderID);
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

    public static Map<String, Object> harness(MongoTemplate template) {
        Query q = query();
        List<Order> list = template.find(q, Order.class);
        long count = list.size();
        Object first = count > 0 ? list.get(0) : null;
        Object last = count > 1 ? list.get(list.size() - 1) : null;
        Map<String, Object> result = new HashMap<>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        result.put("mongoQuery", Map.of("collection", template.getCollectionName(Order.class), "filter", q.getQueryObject(), "sort", q.getSortObject()));
        return result;
    }
}
```

```source_query_body id=12
public static class Query12
{
    public static object Harness(NHibernate.ISession session)
    {
        return HarnessSupport.RunQuery(
            () => session.Query<Order>().Select(o => o.CustomerPurchaseOrderNumber).Distinct(),
            s => s);
    }
}
```

```target_query_body id=12
final class Query12 {
    public static List<String> query(MongoTemplate template) {
        List<String> distinct = template.findDistinct(new Query(), "customerPurchaseOrderNumber", Order.class, String.class);
        distinct.sort((a, b) -> {
            if (a == null && b == null) return 0;
            if (a == null) return -1;
            if (b == null) return 1;
            return a.compareTo(b);
        });
        return distinct;
    }

    public static Map<String, Object> harness(MongoTemplate template) {
        List<String> list = query(template);
        long count = list.size();
        Object first = count > 0 ? list.get(0) : null;
        Object last = count > 1 ? list.get(list.size() - 1) : null;
        Map<String, Object> result = new HashMap<>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        result.put("mongoQuery", Map.of("collection", template.getCollectionName(Order.class), "distinct", "customerPurchaseOrderNumber"));
        return result;
    }
}
```

```source_query_body id=13
public static class Query13
{
    public static object Harness(NHibernate.ISession session)
    {
        var sql = """
                      SELECT PersonID, FullName, PreferredName, EmailAddress, CustomFields, OtherLanguages
                      FROM Application.People
                      WHERE JSON_VALUE(CustomFields, '$.Title') = :title
                      ORDER BY PersonID
                  """;
        return HarnessSupport.RunRows(
            () => session.CreateSQLQuery(sql)
                         .SetParameter("title", "Team Member")
                         .SetResultTransformer(Transformers.AliasToBean<Person>())
                         .List<Person>(),
            p => p.PersonID);
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
        List<Person> list = template.find(q, Person.class);
        long count = list.size();
        Object first = count > 0 ? list.get(0) : null;
        Object last = count > 1 ? list.get(list.size() - 1) : null;
        Map<String, Object> result = new HashMap<>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        result.put("mongoQuery", Map.of("collection", template.getCollectionName(Person.class), "filter", q.getQueryObject(), "sort", q.getSortObject()));
        return result;
    }
}
```

```source_query_body id=14
public static class Query14
{
    public static object Harness(NHibernate.ISession session)
    {
        var sql = """
                      SELECT PersonID, FullName, PreferredName, EmailAddress, CustomFields, OtherLanguages
                      FROM Application.People
                      WHERE EXISTS (
                          SELECT 1 FROM OPENJSON(OtherLanguages)
                          WHERE value = :lang
                      )
                      ORDER BY PersonID
                  """;
        return HarnessSupport.RunRows(
            () => session.CreateSQLQuery(sql)
                         .SetParameter("lang", "Slovak")
                         .SetResultTransformer(Transformers.AliasToBean<Person>())
                         .List<Person>(),
            p => p.PersonID);
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
        List<Person> list = template.find(q, Person.class);
        long count = list.size();
        Object first = count > 0 ? list.get(0) : null;
        Object last = count > 1 ? list.get(list.size() - 1) : null;
        Map<String, Object> result = new HashMap<>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        result.put("mongoQuery", Map.of("collection", template.getCollectionName(Person.class), "filter", q.getQueryObject(), "sort", q.getSortObject()));
        return result;
    }
}
```

```source_query_body id=15
public static class Query15
{
    public static object Harness(NHibernate.ISession session)
    {
        var first = session.Query<Supplier>()
            .Where(s => s.SupplierID < 5)
            .Select(s => s.SupplierID)
            .ToList();
        var last = session.Query<Supplier>()
            .Where(s => s.SupplierID >= 5 && s.SupplierID <= 10)
            .Select(s => s.SupplierID)
            .ToList();
        var union = first.Union(last).OrderBy(s => s).ToList();
        return new {
            count = union.Count,
            firstSample = union.Count > 0 ? (object?)union[0] : null,
            lastSample = union.Count > 1 ? (object?)union[^1] : null
        };
    }
}
```

```target_query_body id=15
final class Query15 {
    public static List<Integer> query(MongoTemplate template) {
        Query q1 = new Query(Criteria.where("supplierId").lt(5));
        List<Integer> first = template.find(q1, Supplier.class).stream()
            .map(Supplier::getSupplierId).toList();

        Query q2 = new Query(Criteria.where("supplierId").gte(5).lte(10));
        List<Integer> last = template.find(q2, Supplier.class).stream()
            .map(Supplier::getSupplierId).toList();

        Set<Integer> set = new HashSet<>(first);
        set.addAll(last);
        List<Integer> union = new ArrayList<>(set);
        union.sort(null);
        return union;
    }

    public static Map<String, Object> harness(MongoTemplate template) {
        List<Integer> list = query(template);
        long count = list.size();
        Object first = count > 0 ? list.get(0) : null;
        Object last = count > 1 ? list.get(list.size() - 1) : null;
        Map<String, Object> result = new HashMap<>();
        result.put("count", count);
        result.put("firstSample", first);
        result.put("lastSample", last);
        result.put("mongoQuery", Map.of("collection", template.getCollectionName(Supplier.class), "operation", "union"));
        return result;
    }
}
```
