@Document(collection = "orderLines")
@JsonIgnoreProperties({ "id" })
class OrderLine {
    @Id
    private String id;
    private Integer orderLineId;
    private Integer orderId;
    private Integer stockItemId;
    private String description;
    private Integer packageTypeId;
    private Integer quantity;
    private BigDecimal unitPrice;
    private BigDecimal taxRate;
    private Integer pickedQuantity;
    private LocalDateTime pickingCompletedWhen;
    private Integer lastEditedBy;
    private LocalDateTime lastEditedWhen;

    OrderLine() {}

    String getId() { return id; }
    void setId(String id) { this.id = id; }
    Integer getOrderLineId() { return orderLineId; }
    void setOrderLineId(Integer orderLineId) { this.orderLineId = orderLineId; }
    Integer getOrderId() { return orderId; }
    void setOrderId(Integer orderId) { this.orderId = orderId; }
    Integer getStockItemId() { return stockItemId; }
    void setStockItemId(Integer stockItemId) { this.stockItemId = stockItemId; }
    String getDescription() { return description; }
    void setDescription(String description) { this.description = description; }
    Integer getPackageTypeId() { return packageTypeId; }
    void setPackageTypeId(Integer packageTypeId) { this.packageTypeId = packageTypeId; }
    Integer getQuantity() { return quantity; }
    void setQuantity(Integer quantity) { this.quantity = quantity; }
    BigDecimal getUnitPrice() { return unitPrice; }
    void setUnitPrice(BigDecimal unitPrice) { this.unitPrice = unitPrice; }
    BigDecimal getTaxRate() { return taxRate; }
    void setTaxRate(BigDecimal taxRate) { this.taxRate = taxRate; }
    Integer getPickedQuantity() { return pickedQuantity; }
    void setPickedQuantity(Integer pickedQuantity) { this.pickedQuantity = pickedQuantity; }
    LocalDateTime getPickingCompletedWhen() { return pickingCompletedWhen; }
    void setPickingCompletedWhen(LocalDateTime pickingCompletedWhen) { this.pickingCompletedWhen = pickingCompletedWhen; }
    Integer getLastEditedBy() { return lastEditedBy; }
    void setLastEditedBy(Integer lastEditedBy) { this.lastEditedBy = lastEditedBy; }
    LocalDateTime getLastEditedWhen() { return lastEditedWhen; }
    void setLastEditedWhen(LocalDateTime lastEditedWhen) { this.lastEditedWhen = lastEditedWhen; }
}

@Document(collection = "orders")
@JsonIgnoreProperties({ "id" })
class Order {
    @Id
    private String id;
    private Integer orderId;
    private Integer customerId;
    private Integer salespersonPersonId;
    private Integer pickedByPersonId;
    private Integer contactPersonId;
    private Integer backorderOrderId;
    private LocalDateTime orderDate;
    private LocalDateTime expectedDeliveryDate;
    private String customerPurchaseOrderNumber;
    private Boolean isUndersupplyBackordered;
    private String comments;
    private String deliveryInstructions;
    private String internalComments;
    private LocalDateTime pickingCompletedWhen;
    private Integer lastEditedBy;
    private LocalDateTime lastEditedWhen;

    @ReadOnlyProperty
    @DocumentReference(lazy = true, lookup = "{ 'orderId': ?#{#self.orderId} }", sort = "{ 'orderLineId': 1 }")
    private List<OrderLine> orderLines = new ArrayList<>();

    Order() {}

    String getId() { return id; }
    void setId(String id) { this.id = id; }
    Integer getOrderId() { return orderId; }
    void setOrderId(Integer orderId) { this.orderId = orderId; }
    Integer getCustomerId() { return customerId; }
    void setCustomerId(Integer customerId) { this.customerId = customerId; }
    Integer getSalespersonPersonId() { return salespersonPersonId; }
    void setSalespersonPersonId(Integer salespersonPersonId) { this.salespersonPersonId = salespersonPersonId; }
    Integer getPickedByPersonId() { return pickedByPersonId; }
    void setPickedByPersonId(Integer pickedByPersonId) { this.pickedByPersonId = pickedByPersonId; }
    Integer getContactPersonId() { return contactPersonId; }
    void setContactPersonId(Integer contactPersonId) { this.contactPersonId = contactPersonId; }
    Integer getBackorderOrderId() { return backorderOrderId; }
    void setBackorderOrderId(Integer backorderOrderId) { this.backorderOrderId = backorderOrderId; }
    LocalDateTime getOrderDate() { return orderDate; }
    void setOrderDate(LocalDateTime orderDate) { this.orderDate = orderDate; }
    LocalDateTime getExpectedDeliveryDate() { return expectedDeliveryDate; }
    void setExpectedDeliveryDate(LocalDateTime expectedDeliveryDate) { this.expectedDeliveryDate = expectedDeliveryDate; }
    String getCustomerPurchaseOrderNumber() { return customerPurchaseOrderNumber; }
    void setCustomerPurchaseOrderNumber(String customerPurchaseOrderNumber) { this.customerPurchaseOrderNumber = customerPurchaseOrderNumber; }
    Boolean getIsUndersupplyBackordered() { return isUndersupplyBackordered; }
    void setIsUndersupplyBackordered(Boolean isUndersupplyBackordered) { this.isUndersupplyBackordered = isUndersupplyBackordered; }
    String getComments() { return comments; }
    void setComments(String comments) { this.comments = comments; }
    String getDeliveryInstructions() { return deliveryInstructions; }
    void setDeliveryInstructions(String deliveryInstructions) { this.deliveryInstructions = deliveryInstructions; }
    String getInternalComments() { return internalComments; }
    void setInternalComments(String internalComments) { this.internalComments = internalComments; }
    LocalDateTime getPickingCompletedWhen() { return pickingCompletedWhen; }
    void setPickingCompletedWhen(LocalDateTime pickingCompletedWhen) { this.pickingCompletedWhen = pickingCompletedWhen; }
    Integer getLastEditedBy() { return lastEditedBy; }
    void setLastEditedBy(Integer lastEditedBy) { this.lastEditedBy = lastEditedBy; }
    LocalDateTime getLastEditedWhen() { return lastEditedWhen; }
    void setLastEditedWhen(LocalDateTime lastEditedWhen) { this.lastEditedWhen = lastEditedWhen; }
    List<OrderLine> getOrderLines() { return orderLines; }
    void setOrderLines(List<OrderLine> orderLines) { this.orderLines = orderLines; }
}

@Document(collection = "people")
@JsonIgnoreProperties({ "id" })
class Person {
    @Id
    private String id;
    private Integer personId;
    private String fullName;
    private String preferredName;
    private String emailAddress;
    private String customFields;
    private String otherLanguages;

    Person() {}

    String getId() { return id; }
    void setId(String id) { this.id = id; }
    Integer getPersonId() { return personId; }
    void setPersonId(Integer personId) { this.personId = personId; }
    String getFullName() { return fullName; }
    void setFullName(String fullName) { this.fullName = fullName; }
    String getPreferredName() { return preferredName; }
    void setPreferredName(String preferredName) { this.preferredName = preferredName; }
    String getEmailAddress() { return emailAddress; }
    void setEmailAddress(String emailAddress) { this.emailAddress = emailAddress; }
    String getCustomFields() { return customFields; }
    void setCustomFields(String customFields) { this.customFields = customFields; }
    String getOtherLanguages() { return otherLanguages; }
    void setOtherLanguages(String otherLanguages) { this.otherLanguages = otherLanguages; }
}

@Document(collection = "suppliers")
@JsonIgnoreProperties({ "id" })
class Supplier {
    @Id
    private String id;
    private Integer supplierId;
    private String supplierName;
    private String supplierReference;
    private Integer paymentDays;

    Supplier() {}

    String getId() { return id; }
    void setId(String id) { this.id = id; }
    Integer getSupplierId() { return supplierId; }
    void setSupplierId(Integer supplierId) { this.supplierId = supplierId; }
    String getSupplierName() { return supplierName; }
    void setSupplierName(String supplierName) { this.supplierName = supplierName; }
    String getSupplierReference() { return supplierReference; }
    void setSupplierReference(String supplierReference) { this.supplierReference = supplierReference; }
    Integer getPaymentDays() { return paymentDays; }
    void setPaymentDays(Integer paymentDays) { this.paymentDays = paymentDays; }
}

record TaxRateCount(BigDecimal taxRate, Long count) {}
record CountProjection(Long count) {}
record MaxValue(BigDecimal maxValue) {}
record SumTotal(BigDecimal total) {}