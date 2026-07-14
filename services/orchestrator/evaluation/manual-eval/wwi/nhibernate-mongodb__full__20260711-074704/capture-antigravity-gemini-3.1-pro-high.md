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
    public virtual int SupplierID { get; set; }
    public virtual string? SupplierName { get; set; }
    public virtual string? PhoneNumber { get; set; }
    public virtual string? FaxNumber { get; set; }
    public virtual string? WebsiteURL { get; set; }
}

public class SupplierBankAccount
{
    public virtual int SupplierID { get; set; }
    public virtual string? BankAccountName { get; set; }
    public virtual string? BankAccountBranch { get; set; }
    public virtual string? BankAccountCode { get; set; }
    public virtual string? BankAccountNumber { get; set; }
    public virtual string? BankInternationalCode { get; set; }
}

public class SupplierAccounts
{
    public virtual SupplierContactInfo? ContactInfo { get; set; }
    public virtual SupplierBankAccount? BankAccount { get; set; }
}

public class PurchaseOrderInfo
{
    public virtual int PurchaseOrderID { get; set; }
    public virtual string? SupplierName { get; set; }
    public virtual DateTime OrderDate { get; set; }
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
@org.springframework.data.mongodb.core.mapping.Document(collection = "orderLines")
class OrderLine {
    @org.springframework.data.annotation.Id
    private String id;
    @org.springframework.data.mongodb.core.mapping.Field("orderLineId")
    private Integer orderLineId;
    @org.springframework.data.mongodb.core.mapping.Field("orderId")
    private Integer orderId;
    @org.springframework.data.mongodb.core.mapping.Field("stockItemId")
    private Integer stockItemId;
    private String description;
    private Integer quantity;
    private java.math.BigDecimal unitPrice;
    @org.springframework.data.mongodb.core.mapping.Field("taxRate")
    private java.math.BigDecimal taxRate;
    @org.springframework.data.mongodb.core.mapping.Field("pickedQuantity")
    private Integer pickedQuantity;
    @org.springframework.data.mongodb.core.mapping.Field("pickingCompletedWhen")
    private java.time.LocalDateTime pickingCompletedWhen;
    @org.springframework.data.mongodb.core.mapping.Field("lastEditedBy")
    private Integer lastEditedBy;
    @org.springframework.data.mongodb.core.mapping.Field("lastEditedWhen")
    private java.time.LocalDateTime lastEditedWhen;

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
    public java.math.BigDecimal getUnitPrice() { return unitPrice; }
    public void setUnitPrice(java.math.BigDecimal unitPrice) { this.unitPrice = unitPrice; }
    public java.math.BigDecimal getTaxRate() { return taxRate; }
    public void setTaxRate(java.math.BigDecimal taxRate) { this.taxRate = taxRate; }
    public Integer getPickedQuantity() { return pickedQuantity; }
    public void setPickedQuantity(Integer pickedQuantity) { this.pickedQuantity = pickedQuantity; }
    public java.time.LocalDateTime getPickingCompletedWhen() { return pickingCompletedWhen; }
    public void setPickingCompletedWhen(java.time.LocalDateTime pickingCompletedWhen) { this.pickingCompletedWhen = pickingCompletedWhen; }
    public Integer getLastEditedBy() { return lastEditedBy; }
    public void setLastEditedBy(Integer lastEditedBy) { this.lastEditedBy = lastEditedBy; }
    public java.time.LocalDateTime getLastEditedWhen() { return lastEditedWhen; }
    public void setLastEditedWhen(java.time.LocalDateTime lastEditedWhen) { this.lastEditedWhen = lastEditedWhen; }
}

@org.springframework.data.mongodb.core.mapping.Document(collection = "orders")
class Order {
    @org.springframework.data.annotation.Id
    private String id;
    @org.springframework.data.mongodb.core.mapping.Field("orderId")
    private Integer orderId;
    @org.springframework.data.mongodb.core.mapping.Field("customerId")
    private Integer customerId;
    @org.springframework.data.mongodb.core.mapping.Field("backorderOrderId")
    private Integer backorderOrderId;
    @org.springframework.data.mongodb.core.mapping.Field("orderDate")
    private java.time.LocalDateTime orderDate;
    @org.springframework.data.mongodb.core.mapping.Field("expectedDeliveryDate")
    private java.time.LocalDateTime expectedDeliveryDate;
    @org.springframework.data.mongodb.core.mapping.Field("customerPurchaseOrderNumber")
    private String customerPurchaseOrderNumber;
    @org.springframework.data.mongodb.core.mapping.Field("isUndersupplyBackordered")
    private Boolean isUndersupplyBackordered;
    private String comments;
    private String deliveryInstructions;
    private String internalComments;
    @org.springframework.data.mongodb.core.mapping.Field("pickingCompletedWhen")
    private java.time.LocalDateTime pickingCompletedWhen;
    @org.springframework.data.mongodb.core.mapping.Field("lastEditedWhen")
    private java.time.LocalDateTime lastEditedWhen;

    @org.springframework.data.annotation.ReadOnlyProperty
    @org.springframework.data.mongodb.core.mapping.DocumentReference(lazy = true, lookup = "{ 'orderId': ?#{#self.orderId} }", sort = "{ 'orderLineId': 1 }")
    private java.util.List<OrderLine> orderLines = new java.util.ArrayList<>();

    public Order() {}

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    public Integer getOrderId() { return orderId; }
    public void setOrderId(Integer orderId) { this.orderId = orderId; }
    public Integer getCustomerId() { return customerId; }
    public void setCustomerId(Integer customerId) { this.customerId = customerId; }
    public Integer getBackorderOrderId() { return backorderOrderId; }
    public void setBackorderOrderId(Integer backorderOrderId) { this.backorderOrderId = backorderOrderId; }
    public java.time.LocalDateTime getOrderDate() { return orderDate; }
    public void setOrderDate(java.time.LocalDateTime orderDate) { this.orderDate = orderDate; }
    public java.time.LocalDateTime getExpectedDeliveryDate() { return expectedDeliveryDate; }
    public void setExpectedDeliveryDate(java.time.LocalDateTime expectedDeliveryDate) { this.expectedDeliveryDate = expectedDeliveryDate; }
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
    public java.time.LocalDateTime getPickingCompletedWhen() { return pickingCompletedWhen; }
    public void setPickingCompletedWhen(java.time.LocalDateTime pickingCompletedWhen) { this.pickingCompletedWhen = pickingCompletedWhen; }
    public java.time.LocalDateTime getLastEditedWhen() { return lastEditedWhen; }
    public void setLastEditedWhen(java.time.LocalDateTime lastEditedWhen) { this.lastEditedWhen = lastEditedWhen; }
    public java.util.List<OrderLine> getOrderLines() { return orderLines; }
    public void setOrderLines(java.util.List<OrderLine> orderLines) { this.orderLines = orderLines; }
}

@org.springframework.data.mongodb.core.mapping.Document(collection = "people")
class Person {
    @org.springframework.data.annotation.Id
    private String id;
    @org.springframework.data.mongodb.core.mapping.Field("personId")
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

@org.springframework.data.mongodb.core.mapping.Document(collection = "suppliers")
class Supplier {
    @org.springframework.data.annotation.Id
    private String id;
    @org.springframework.data.mongodb.core.mapping.Field("supplierId")
    private Integer supplierId;
    private String supplierName;
    private String supplierReference;
    private Integer paymentDays;
    private String phoneNumber;
    private String faxNumber;
    private String websiteURL;
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
    public String getWebsiteURL() { return websiteURL; }
    public void setWebsiteURL(String websiteURL) { this.websiteURL = websiteURL; }
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
    private java.time.LocalDateTime transactionDate;
    private java.math.BigDecimal transactionAmount;
    private java.math.BigDecimal outstandingBalance;
    private Boolean isFinalized;

    public CustomerTransaction() {}

    public Integer getCustomerTransactionId() { return customerTransactionId; }
    public void setCustomerTransactionId(Integer customerTransactionId) { this.customerTransactionId = customerTransactionId; }
    public Integer getCustomerId() { return customerId; }
    public void setCustomerId(Integer customerId) { this.customerId = customerId; }
    public java.time.LocalDateTime getTransactionDate() { return transactionDate; }
    public void setTransactionDate(java.time.LocalDateTime transactionDate) { this.transactionDate = transactionDate; }
    public java.math.BigDecimal getTransactionAmount() { return transactionAmount; }
    public void setTransactionAmount(java.math.BigDecimal transactionAmount) { this.transactionAmount = transactionAmount; }
    public java.math.BigDecimal getOutstandingBalance() { return outstandingBalance; }
    public void setOutstandingBalance(java.math.BigDecimal outstandingBalance) { this.outstandingBalance = outstandingBalance; }
    public Boolean getIsFinalized() { return isFinalized; }
    public void setIsFinalized(Boolean isFinalized) { this.isFinalized = isFinalized; }
}

class PurchaseOrder {
    private Integer purchaseOrderId;
    private Integer supplierId;
    private java.time.LocalDateTime orderDate;
    private java.time.LocalDateTime expectedDeliveryDate;
    private String supplierReference;
    private Boolean isOrderFinalized;

    public PurchaseOrder() {}

    public Integer getPurchaseOrderId() { return purchaseOrderId; }
    public void setPurchaseOrderId(Integer purchaseOrderId) { this.purchaseOrderId = purchaseOrderId; }
    public Integer getSupplierId() { return supplierId; }
    public void setSupplierId(Integer supplierId) { this.supplierId = supplierId; }
    public java.time.LocalDateTime getOrderDate() { return orderDate; }
    public void setOrderDate(java.time.LocalDateTime orderDate) { this.orderDate = orderDate; }
    public java.time.LocalDateTime getExpectedDeliveryDate() { return expectedDeliveryDate; }
    public void setExpectedDeliveryDate(java.time.LocalDateTime expectedDeliveryDate) { this.expectedDeliveryDate = expectedDeliveryDate; }
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
    private java.math.BigDecimal unitPrice;
    private java.math.BigDecimal recommendedRetailPrice;

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
    public java.math.BigDecimal getUnitPrice() { return unitPrice; }
    public void setUnitPrice(java.math.BigDecimal unitPrice) { this.unitPrice = unitPrice; }
    public java.math.BigDecimal getRecommendedRetailPrice() { return recommendedRetailPrice; }
    public void setRecommendedRetailPrice(java.math.BigDecimal recommendedRetailPrice) { this.recommendedRetailPrice = recommendedRetailPrice; }
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
    private String websiteURL;

    public SupplierContactInfo() {}

    public Integer getSupplierId() { return supplierId; }
    public void setSupplierId(Integer supplierId) { this.supplierId = supplierId; }
    public String getSupplierName() { return supplierName; }
    public void setSupplierName(String supplierName) { this.supplierName = supplierName; }
    public String getPhoneNumber() { return phoneNumber; }
    public void setPhoneNumber(String phoneNumber) { this.phoneNumber = phoneNumber; }
    public String getFaxNumber() { return faxNumber; }
    public void setFaxNumber(String faxNumber) { this.faxNumber = faxNumber; }
    public String getWebsiteURL() { return websiteURL; }
    public void setWebsiteURL(String websiteURL) { this.websiteURL = websiteURL; }
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
    private java.time.LocalDateTime orderDate;

    public PurchaseOrderInfo() {}

    public Integer getPurchaseOrderId() { return purchaseOrderId; }
    public void setPurchaseOrderId(Integer purchaseOrderId) { this.purchaseOrderId = purchaseOrderId; }
    public String getSupplierName() { return supplierName; }
    public void setSupplierName(String supplierName) { this.supplierName = supplierName; }
    public java.time.LocalDateTime getOrderDate() { return orderDate; }
    public void setOrderDate(java.time.LocalDateTime orderDate) { this.orderDate = orderDate; }
}

record TaxRateCount(java.math.BigDecimal taxRate, Long count) {}
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
    public static java.util.Map<String, Object> harness(org.springframework.data.mongodb.core.MongoTemplate template) {
        org.springframework.data.mongodb.core.query.Query q = new org.springframework.data.mongodb.core.query.Query(org.springframework.data.mongodb.core.query.Criteria.where("orderId").is(26866));
        long count = template.count(q, OrderLine.class);
        Object first = count > 0 ? template.findOne(new org.springframework.data.mongodb.core.query.Query(org.springframework.data.mongodb.core.query.Criteria.where("orderId").is(26866)).with(org.springframework.data.domain.Sort.by(org.springframework.data.domain.Sort.Direction.ASC, "orderLineId")).limit(1), OrderLine.class) : null;
        Object last = count > 1 ? template.findOne(new org.springframework.data.mongodb.core.query.Query(org.springframework.data.mongodb.core.query.Criteria.where("orderId").is(26866)).with(org.springframework.data.domain.Sort.by(org.springframework.data.domain.Sort.Direction.DESC, "orderLineId")).limit(1), OrderLine.class) : null;
        java.util.Map<String, Object> map = new java.util.HashMap<>();
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
    public static java.util.Map<String, Object> harness(org.springframework.data.mongodb.core.MongoTemplate template) {
        org.springframework.data.mongodb.core.query.Query q = new org.springframework.data.mongodb.core.query.Query(org.springframework.data.mongodb.core.query.Criteria.where("unitPrice").is(new java.math.BigDecimal("25")));
        long count = template.count(q, OrderLine.class);
        Object first = count > 0 ? template.findOne(new org.springframework.data.mongodb.core.query.Query(org.springframework.data.mongodb.core.query.Criteria.where("unitPrice").is(new java.math.BigDecimal("25"))).with(org.springframework.data.domain.Sort.by(org.springframework.data.domain.Sort.Direction.ASC, "orderLineId")).limit(1), OrderLine.class) : null;
        Object last = count > 1 ? template.findOne(new org.springframework.data.mongodb.core.query.Query(org.springframework.data.mongodb.core.query.Criteria.where("unitPrice").is(new java.math.BigDecimal("25"))).with(org.springframework.data.domain.Sort.by(org.springframework.data.domain.Sort.Direction.DESC, "orderLineId")).limit(1), OrderLine.class) : null;
        java.util.Map<String, Object> map = new java.util.HashMap<>();
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
    public static java.util.Map<String, Object> harness(org.springframework.data.mongodb.core.MongoTemplate template) {
        java.time.LocalDateTime from = java.time.LocalDateTime.of(2014, 12, 20, 0, 0);
        java.time.LocalDateTime to = java.time.LocalDateTime.of(2014, 12, 31, 0, 0);
        org.springframework.data.mongodb.core.query.Query q = new org.springframework.data.mongodb.core.query.Query(org.springframework.data.mongodb.core.query.Criteria.where("pickingCompletedWhen").gte(from).lte(to));
        long count = template.count(q, OrderLine.class);
        Object first = count > 0 ? template.findOne(new org.springframework.data.mongodb.core.query.Query(org.springframework.data.mongodb.core.query.Criteria.where("pickingCompletedWhen").gte(from).lte(to)).with(org.springframework.data.domain.Sort.by(org.springframework.data.domain.Sort.Direction.ASC, "orderLineId")).limit(1), OrderLine.class) : null;
        Object last = count > 1 ? template.findOne(new org.springframework.data.mongodb.core.query.Query(org.springframework.data.mongodb.core.query.Criteria.where("pickingCompletedWhen").gte(from).lte(to)).with(org.springframework.data.domain.Sort.by(org.springframework.data.domain.Sort.Direction.DESC, "orderLineId")).limit(1), OrderLine.class) : null;
        java.util.Map<String, Object> map = new java.util.HashMap<>();
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
    public static java.util.Map<String, Object> harness(org.springframework.data.mongodb.core.MongoTemplate template) {
        java.util.List<Integer> orderIds = java.util.List.of(1, 10, 100, 1000, 10000);
        org.springframework.data.mongodb.core.query.Query q = new org.springframework.data.mongodb.core.query.Query(org.springframework.data.mongodb.core.query.Criteria.where("orderId").in(orderIds));
        long count = template.count(q, OrderLine.class);
        Object first = count > 0 ? template.findOne(new org.springframework.data.mongodb.core.query.Query(org.springframework.data.mongodb.core.query.Criteria.where("orderId").in(orderIds)).with(org.springframework.data.domain.Sort.by(org.springframework.data.domain.Sort.Direction.ASC, "orderLineId")).limit(1), OrderLine.class) : null;
        Object last = count > 1 ? template.findOne(new org.springframework.data.mongodb.core.query.Query(org.springframework.data.mongodb.core.query.Criteria.where("orderId").in(orderIds)).with(org.springframework.data.domain.Sort.by(org.springframework.data.domain.Sort.Direction.DESC, "orderLineId")).limit(1), OrderLine.class) : null;
        java.util.Map<String, Object> map = new java.util.HashMap<>();
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
    public static java.util.Map<String, Object> harness(org.springframework.data.mongodb.core.MongoTemplate template) {
        String text = "C++";
        org.springframework.data.mongodb.core.query.Query q = new org.springframework.data.mongodb.core.query.Query(org.springframework.data.mongodb.core.query.Criteria.where("description").regex(java.util.regex.Pattern.quote(text)));
        long count = template.count(q, OrderLine.class);
        Object first = count > 0 ? template.findOne(new org.springframework.data.mongodb.core.query.Query(org.springframework.data.mongodb.core.query.Criteria.where("description").regex(java.util.regex.Pattern.quote(text))).with(org.springframework.data.domain.Sort.by(org.springframework.data.domain.Sort.Direction.ASC, "orderLineId")).limit(1), OrderLine.class) : null;
        Object last = count > 1 ? template.findOne(new org.springframework.data.mongodb.core.query.Query(org.springframework.data.mongodb.core.query.Criteria.where("description").regex(java.util.regex.Pattern.quote(text))).with(org.springframework.data.domain.Sort.by(org.springframework.data.domain.Sort.Direction.DESC, "orderLineId")).limit(1), OrderLine.class) : null;
        java.util.Map<String, Object> map = new java.util.HashMap<>();
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
    public static object Harness(NHibernate.ISession session)
    {
        int skip = 1000;
        int take = 50;
        return HarnessSupport.RunQuery(
            () => session.Query<OrderLine>().OrderBy(ol => ol.OrderLineID).Skip(skip).Take(take),
            null);
    }
}
```

```target_query_body id=6
final class Query6 {
    public static java.util.Map<String, Object> harness(org.springframework.data.mongodb.core.MongoTemplate template) {
        int skip = 1000;
        int take = 50;
        org.springframework.data.mongodb.core.query.Query q = new org.springframework.data.mongodb.core.query.Query().with(org.springframework.data.domain.Sort.by(org.springframework.data.domain.Sort.Direction.ASC, "orderLineId")).skip(skip).limit(take);
        java.util.List<OrderLine> results = template.find(q, OrderLine.class);
        long count = results.size();
        Object first = count > 0 ? results.get(0) : null;
        Object last = count > 1 ? results.get(results.size() - 1) : null;
        java.util.Map<String, Object> map = new java.util.HashMap<>();
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
    public static object Harness(NHibernate.ISession session)
    {
        return HarnessSupport.RunQuery(
            () => session.Query<OrderLine>()
                .GroupBy(ol => ol.TaxRate)
                .Select(g => new TaxRateCount { TaxRate = g.Key, Count = g.Count() })
                .OrderByDescending(x => x.Count),
            x => x.TaxRate);
    }
}
```

```target_query_body id=7
final class Query7 {
    public static java.util.Map<String, Object> harness(org.springframework.data.mongodb.core.MongoTemplate template) {
        org.springframework.data.mongodb.core.aggregation.TypedAggregation<OrderLine> agg = org.springframework.data.mongodb.core.aggregation.Aggregation.newAggregation(
            OrderLine.class,
            org.springframework.data.mongodb.core.aggregation.Aggregation.group("taxRate").count().as("count"),
            org.springframework.data.mongodb.core.aggregation.Aggregation.project("count").and("taxRate").previousOperation(),
            org.springframework.data.mongodb.core.aggregation.Aggregation.sort(org.springframework.data.domain.Sort.Direction.DESC, "count").and(org.springframework.data.domain.Sort.Direction.ASC, "taxRate")
        );
        java.util.List<TaxRateCount> results = template.aggregate(agg, OrderLine.class, TaxRateCount.class).getMappedResults();
        long count = results.size();
        Object first = count > 0 ? results.get(0) : null;
        Object last = count > 1 ? results.get(results.size() - 1) : null;
        java.util.Map<String, Object> map = new java.util.HashMap<>();
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
    public static object Harness(NHibernate.ISession session)
    {
        decimal? max = session.Query<OrderLine>().Max(ol => ol.UnitPrice);
        return new { count = max.HasValue ? 1 : 0, firstSample = (object?)max, lastSample = (object?)null };
    }
}
```

```target_query_body id=8
record Query8Result(java.math.BigDecimal max) {}

final class Query8 {
    public static java.util.Map<String, Object> harness(org.springframework.data.mongodb.core.MongoTemplate template) {
        org.springframework.data.mongodb.core.aggregation.TypedAggregation<OrderLine> agg = org.springframework.data.mongodb.core.aggregation.Aggregation.newAggregation(
            OrderLine.class,
            org.springframework.data.mongodb.core.aggregation.Aggregation.group().max("unitPrice").as("max")
        );
        Query8Result res = template.aggregate(agg, OrderLine.class, Query8Result.class).getUniqueMappedResult();
        java.math.BigDecimal max = res != null ? res.max() : null;
        long count = max != null ? 1 : 0;
        java.util.Map<String, Object> map = new java.util.HashMap<>();
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
    public static object Harness(NHibernate.ISession session)
    {
        decimal? sum = session.Query<OrderLine>().Sum(ol => ol.Quantity * ol.UnitPrice);
        return new { count = sum.HasValue ? 1 : 0, firstSample = (object?)sum, lastSample = (object?)null };
    }
}
```

```target_query_body id=9
record Query9Result(java.math.BigDecimal sum) {}

final class Query9 {
    public static java.util.Map<String, Object> harness(org.springframework.data.mongodb.core.MongoTemplate template) {
        org.springframework.data.mongodb.core.aggregation.TypedAggregation<OrderLine> agg = org.springframework.data.mongodb.core.aggregation.Aggregation.newAggregation(
            OrderLine.class,
            org.springframework.data.mongodb.core.aggregation.Aggregation.project().andExpression("quantity * unitPrice").as("lineTotal"),
            org.springframework.data.mongodb.core.aggregation.Aggregation.group().sum("lineTotal").as("sum")
        );
        Query9Result res = template.aggregate(agg, OrderLine.class, Query9Result.class).getUniqueMappedResult();
        java.math.BigDecimal sum = res != null ? res.sum() : null;
        long count = sum != null ? 1 : 0;
        java.util.Map<String, Object> map = new java.util.HashMap<>();
        map.put("count", count);
        map.put("firstSample", sum);
        map.put("lastSample", null);
        return map;
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
    public static java.util.Map<String, Object> harness(org.springframework.data.mongodb.core.MongoTemplate template) {
        org.springframework.data.mongodb.core.query.Query q = new org.springframework.data.mongodb.core.query.Query(org.springframework.data.mongodb.core.query.Criteria.where("orderId").is(530));
        long count = template.count(q, Order.class);
        Object first = null;
        if (count > 0) {
            Order o = template.findOne(q, Order.class);
            if (o != null && o.getOrderLines() != null) {
                o.getOrderLines().size();
            }
            first = o;
        }
        java.util.Map<String, Object> map = new java.util.HashMap<>();
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
    public static java.util.Map<String, Object> harness(org.springframework.data.mongodb.core.MongoTemplate template) {
        org.springframework.data.mongodb.core.query.Query q = new org.springframework.data.mongodb.core.query.Query().with(org.springframework.data.domain.Sort.by(org.springframework.data.domain.Sort.Direction.ASC, "expectedDeliveryDate").and(org.springframework.data.domain.Sort.by(org.springframework.data.domain.Sort.Direction.ASC, "orderId"))).limit(1000);
        java.util.List<Order> results = template.find(q, Order.class);
        long count = results.size();
        Object first = count > 0 ? results.get(0) : null;
        Object last = count > 1 ? results.get(results.size() - 1) : null;
        java.util.Map<String, Object> map = new java.util.HashMap<>();
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
    public static object Harness(NHibernate.ISession session)
    {
        return HarnessSupport.RunQuery(
            () => session.Query<Order>().Select(o => o.CustomerPurchaseOrderNumber).Distinct(),
            x => x);
    }
}
```

```target_query_body id=12
final class Query12 {
    public static java.util.Map<String, Object> harness(org.springframework.data.mongodb.core.MongoTemplate template) {
        java.util.List<String> results = template.query(Order.class).distinct("customerPurchaseOrderNumber").as(String.class).all();
        results.sort(java.util.Comparator.nullsFirst(java.util.Comparator.naturalOrder()));
        long count = results.size();
        Object first = count > 0 ? results.get(0) : null;
        Object last = count > 1 ? results.get(results.size() - 1) : null;
        java.util.Map<String, Object> map = new java.util.HashMap<>();
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
    public static java.util.Map<String, Object> harness(org.springframework.data.mongodb.core.MongoTemplate template) {
        org.springframework.data.mongodb.core.query.Query q = new org.springframework.data.mongodb.core.query.Query(org.springframework.data.mongodb.core.query.Criteria.where("customFields").regex("\"Title\"\\s*:\\s*\"Team Member\""))
            .with(org.springframework.data.domain.Sort.by(org.springframework.data.domain.Sort.Direction.ASC, "personId"));
        java.util.List<Person> results = template.find(q, Person.class);
        long count = results.size();
        Object first = count > 0 ? results.get(0) : null;
        Object last = count > 1 ? results.get(results.size() - 1) : null;
        java.util.Map<String, Object> map = new java.util.HashMap<>();
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
    public static java.util.Map<String, Object> harness(org.springframework.data.mongodb.core.MongoTemplate template) {
        org.springframework.data.mongodb.core.query.Query q = new org.springframework.data.mongodb.core.query.Query(org.springframework.data.mongodb.core.query.Criteria.where("otherLanguages").regex("\"Slovak\""))
            .with(org.springframework.data.domain.Sort.by(org.springframework.data.domain.Sort.Direction.ASC, "personId"));
        java.util.List<Person> results = template.find(q, Person.class);
        long count = results.size();
        Object first = count > 0 ? results.get(0) : null;
        Object last = count > 1 ? results.get(results.size() - 1) : null;
        java.util.Map<String, Object> map = new java.util.HashMap<>();
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
        return new { count = union.Count,
                     firstSample = union.Count > 0 ? (object?)union[0] : null,
                     lastSample = union.Count > 1 ? (object?)union[^1] : null };
    }
}
```

```target_query_body id=15
final class Query15 {
    public static java.util.Map<String, Object> harness(org.springframework.data.mongodb.core.MongoTemplate template) {
        org.springframework.data.mongodb.core.query.Query q1 = new org.springframework.data.mongodb.core.query.Query(org.springframework.data.mongodb.core.query.Criteria.where("supplierId").lt(5));
        q1.fields().include("supplierId");
        java.util.List<Supplier> firstSup = template.find(q1, Supplier.class);
        
        org.springframework.data.mongodb.core.query.Query q2 = new org.springframework.data.mongodb.core.query.Query(org.springframework.data.mongodb.core.query.Criteria.where("supplierId").gte(5).lte(10));
        q2.fields().include("supplierId");
        java.util.List<Supplier> lastSup = template.find(q2, Supplier.class);
        
        java.util.Set<Integer> unionSet = new java.util.HashSet<>();
        for (Supplier s : firstSup) unionSet.add(s.getSupplierId());
        for (Supplier s : lastSup) unionSet.add(s.getSupplierId());
        
        java.util.List<Integer> union = new java.util.ArrayList<>(unionSet);
        union.sort(java.util.Comparator.naturalOrder());
        
        long count = union.size();
        Object firstSample = count > 0 ? union.get(0) : null;
        Object lastSample = count > 1 ? union.get(union.size() - 1) : null;
        
        java.util.Map<String, Object> map = new java.util.HashMap<>();
        map.put("count", count);
        map.put("firstSample", firstSample);
        map.put("lastSample", lastSample);
        return map;
    }
}
```
