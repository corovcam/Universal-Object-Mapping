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

@Document(collection = "orders")
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
    private Customer customer;
    @ReadOnlyProperty
    @DocumentReference(lazy = true, lookup = "{ 'orderId': ?#{#self.orderId} }", sort = "{ 'orderLineId': 1 }")
    private List<OrderLine> orderLines;

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
    private Integer billToCustomerId;
    private Integer customerCategoryId;
    private Integer buyingGroupId;
    private Integer primaryContactPersonId;
    private Integer alternateContactPersonId;
    private Integer deliveryMethodId;
    private Integer deliveryCityId;
    private Integer postalCityId;
    private BigDecimal standardDiscountPercentage;
    private Boolean isStatementSent;
    private Boolean isOnCreditHold;
    private Integer paymentDays;
    private String phoneNumber;
    private String faxNumber;
    private String deliveryRun;
    private String runPosition;
    private String websiteUrl;
    private String deliveryAddressLine1;
    private String deliveryAddressLine2;
    private String deliveryPostalCode;
    private byte[] deliveryLocation;
    private String postalAddressLine1;
    private String postalAddressLine2;
    private String postalPostalCode;
    private Integer lastEditedBy;
    private LocalDate validFrom;
    private LocalDate validTo;
    private List<CustomerTransaction> customerTransactions = new ArrayList<>();

    public Integer getCustomerId() { return customerId; }
    public void setCustomerId(Integer customerId) { this.customerId = customerId; }
    public String getCustomerName() { return customerName; }
    public void setCustomerName(String customerName) { this.customerName = customerName; }
    public LocalDate getAccountOpenedDate() { return accountOpenedDate; }
    public void setAccountOpenedDate(LocalDate accountOpenedDate) { this.accountOpenedDate = accountOpenedDate; }
    public BigDecimal getCreditLimit() { return creditLimit; }
    public void setCreditLimit(BigDecimal creditLimit) { this.creditLimit = creditLimit; }
    public Integer getBillToCustomerId() { return billToCustomerId; }
    public void setBillToCustomerId(Integer billToCustomerId) { this.billToCustomerId = billToCustomerId; }
    public Integer getCustomerCategoryId() { return customerCategoryId; }
    public void setCustomerCategoryId(Integer customerCategoryId) { this.customerCategoryId = customerCategoryId; }
    public Integer getBuyingGroupId() { return buyingGroupId; }
    public void setBuyingGroupId(Integer buyingGroupId) { this.buyingGroupId = buyingGroupId; }
    public Integer getPrimaryContactPersonId() { return primaryContactPersonId; }
    public void setPrimaryContactPersonId(Integer primaryContactPersonId) { this.primaryContactPersonId = primaryContactPersonId; }
    public Integer getAlternateContactPersonId() { return alternateContactPersonId; }
    public void setAlternateContactPersonId(Integer alternateContactPersonId) { this.alternateContactPersonId = alternateContactPersonId; }
    public Integer getDeliveryMethodId() { return deliveryMethodId; }
    public void setDeliveryMethodId(Integer deliveryMethodId) { this.deliveryMethodId = deliveryMethodId; }
    public Integer getDeliveryCityId() { return deliveryCityId; }
    public void setDeliveryCityId(Integer deliveryCityId) { this.deliveryCityId = deliveryCityId; }
    public Integer getPostalCityId() { return postalCityId; }
    public void setPostalCityId(Integer postalCityId) { this.postalCityId = postalCityId; }
    public BigDecimal getStandardDiscountPercentage() { return standardDiscountPercentage; }
    public void setStandardDiscountPercentage(BigDecimal standardDiscountPercentage) { this.standardDiscountPercentage = standardDiscountPercentage; }
    public Boolean getIsStatementSent() { return isStatementSent; }
    public void setIsStatementSent(Boolean isStatementSent) { this.isStatementSent = isStatementSent; }
    public Boolean getIsOnCreditHold() { return isOnCreditHold; }
    public void setIsOnCreditHold(Boolean isOnCreditHold) { this.isOnCreditHold = isOnCreditHold; }
    public Integer getPaymentDays() { return paymentDays; }
    public void setPaymentDays(Integer paymentDays) { this.paymentDays = paymentDays; }
    public String getPhoneNumber() { return phoneNumber; }
    public void setPhoneNumber(String phoneNumber) { this.phoneNumber = phoneNumber; }
    public String getFaxNumber() { return faxNumber; }
    public void setFaxNumber(String faxNumber) { this.faxNumber = faxNumber; }
    public String getDeliveryRun() { return deliveryRun; }
    public void setDeliveryRun(String deliveryRun) { this.deliveryRun = deliveryRun; }
    public String getRunPosition() { return runPosition; }
    public void setRunPosition(String runPosition) { this.runPosition = runPosition; }
    public String getWebsiteUrl() { return websiteUrl; }
    public void setWebsiteUrl(String websiteUrl) { this.websiteUrl = websiteUrl; }
    public String getDeliveryAddressLine1() { return deliveryAddressLine1; }
    public void setDeliveryAddressLine1(String deliveryAddressLine1) { this.deliveryAddressLine1 = deliveryAddressLine1; }
    public String getDeliveryAddressLine2() { return deliveryAddressLine2; }
    public void setDeliveryAddressLine2(String deliveryAddressLine2) { this.deliveryAddressLine2 = deliveryAddressLine2; }
    public String getDeliveryPostalCode() { return deliveryPostalCode; }
    public void setDeliveryPostalCode(String deliveryPostalCode) { this.deliveryPostalCode = deliveryPostalCode; }
    public byte[] getDeliveryLocation() { return deliveryLocation; }
    public void setDeliveryLocation(byte[] deliveryLocation) { this.deliveryLocation = deliveryLocation; }
    public String getPostalAddressLine1() { return postalAddressLine1; }
    public void setPostalAddressLine1(String postalAddressLine1) { this.postalAddressLine1 = postalAddressLine1; }
    public String getPostalAddressLine2() { return postalAddressLine2; }
    public void setPostalAddressLine2(String postalAddressLine2) { this.postalAddressLine2 = postalAddressLine2; }
    public String getPostalPostalCode() { return postalPostalCode; }
    public void setPostalPostalCode(String postalPostalCode) { this.postalPostalCode = postalPostalCode; }
    public Integer getLastEditedBy() { return lastEditedBy; }
    public void setLastEditedBy(Integer lastEditedBy) { this.lastEditedBy = lastEditedBy; }
    public LocalDate getValidFrom() { return validFrom; }
    public void setValidFrom(LocalDate validFrom) { this.validFrom = validFrom; }
    public LocalDate getValidTo() { return validTo; }
    public void setValidTo(LocalDate validTo) { this.validTo = validTo; }
    public List<CustomerTransaction> getCustomerTransactions() { return customerTransactions; }
    public void setCustomerTransactions(List<CustomerTransaction> customerTransactions) { this.customerTransactions = customerTransactions; }
}

class CustomerTransaction {
    private Integer customerTransactionId;
    private Integer customerId;
    private Integer transactionTypeId;
    private Integer invoiceId;
    private Integer paymentMethodId;
    private LocalDate transactionDate;
    private BigDecimal amountExcludingTax;
    private BigDecimal taxAmount;
    private BigDecimal transactionAmount;
    private BigDecimal outstandingBalance;
    private LocalDate finalizationDate;
    private Boolean isFinalized;
    private Integer lastEditedBy;
    private LocalDateTime lastEditedWhen;

    public Integer getCustomerTransactionId() { return customerTransactionId; }
    public void setCustomerTransactionId(Integer customerTransactionId) { this.customerTransactionId = customerTransactionId; }
    public Integer getCustomerId() { return customerId; }
    public void setCustomerId(Integer customerId) { this.customerId = customerId; }
    public Integer getTransactionTypeId() { return transactionTypeId; }
    public void setTransactionTypeId(Integer transactionTypeId) { this.transactionTypeId = transactionTypeId; }
    public Integer getInvoiceId() { return invoiceId; }
    public void setInvoiceId(Integer invoiceId) { this.invoiceId = invoiceId; }
    public Integer getPaymentMethodId() { return paymentMethodId; }
    public void setPaymentMethodId(Integer paymentMethodId) { this.paymentMethodId = paymentMethodId; }
    public LocalDate getTransactionDate() { return transactionDate; }
    public void setTransactionDate(LocalDate transactionDate) { this.transactionDate = transactionDate; }
    public BigDecimal getAmountExcludingTax() { return amountExcludingTax; }
    public void setAmountExcludingTax(BigDecimal amountExcludingTax) { this.amountExcludingTax = amountExcludingTax; }
    public BigDecimal getTaxAmount() { return taxAmount; }
    public void setTaxAmount(BigDecimal taxAmount) { this.taxAmount = taxAmount; }
    public BigDecimal getTransactionAmount() { return transactionAmount; }
    public void setTransactionAmount(BigDecimal transactionAmount) { this.transactionAmount = transactionAmount; }
    public BigDecimal getOutstandingBalance() { return outstandingBalance; }
    public void setOutstandingBalance(BigDecimal outstandingBalance) { this.outstandingBalance = outstandingBalance; }
    public LocalDate getFinalizationDate() { return finalizationDate; }
    public void setFinalizationDate(LocalDate finalizationDate) { this.finalizationDate = finalizationDate; }
    public Boolean getIsFinalized() { return isFinalized; }
    public void setIsFinalized(Boolean isFinalized) { this.isFinalized = isFinalized; }
    public Integer getLastEditedBy() { return lastEditedBy; }
    public void setLastEditedBy(Integer lastEditedBy) { this.lastEditedBy = lastEditedBy; }
    public LocalDateTime getLastEditedWhen() { return lastEditedWhen; }
    public void setLastEditedWhen(LocalDateTime lastEditedWhen) { this.lastEditedWhen = lastEditedWhen; }
}

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