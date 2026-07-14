@com.fasterxml.jackson.annotation.JsonIgnoreProperties({ "id" })
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

    private java.math.BigDecimal unitPrice;

    @Field("taxRate")
    private java.math.BigDecimal taxRate;

    @Field("pickedQuantity")
    private Integer pickedQuantity;

    @Field("pickingCompletedWhen")
    private java.time.Instant pickingCompletedWhen;

    @Field("lastEditedBy")
    private Integer lastEditedBy;

    @Field("lastEditedWhen")
    private java.time.Instant lastEditedWhen;

    OrderLine() {
    }

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public Integer getOrderLineId() {
        return orderLineId;
    }

    public void setOrderLineId(Integer orderLineId) {
        this.orderLineId = orderLineId;
    }

    public Integer getOrderId() {
        return orderId;
    }

    public void setOrderId(Integer orderId) {
        this.orderId = orderId;
    }

    public Integer getStockItemId() {
        return stockItemId;
    }

    public void setStockItemId(Integer stockItemId) {
        this.stockItemId = stockItemId;
    }

    public String getDescription() {
        return description;
    }

    public void setDescription(String description) {
        this.description = description;
    }

    public Integer getPackageTypeId() {
        return packageTypeId;
    }

    public void setPackageTypeId(Integer packageTypeId) {
        this.packageTypeId = packageTypeId;
    }

    public Integer getQuantity() {
        return quantity;
    }

    public void setQuantity(Integer quantity) {
        this.quantity = quantity;
    }

    public java.math.BigDecimal getUnitPrice() {
        return unitPrice;
    }

    public void setUnitPrice(java.math.BigDecimal unitPrice) {
        this.unitPrice = unitPrice;
    }

    public java.math.BigDecimal getTaxRate() {
        return taxRate;
    }

    public void setTaxRate(java.math.BigDecimal taxRate) {
        this.taxRate = taxRate;
    }

    public Integer getPickedQuantity() {
        return pickedQuantity;
    }

    public void setPickedQuantity(Integer pickedQuantity) {
        this.pickedQuantity = pickedQuantity;
    }

    public java.time.Instant getPickingCompletedWhen() {
        return pickingCompletedWhen;
    }

    public void setPickingCompletedWhen(java.time.Instant pickingCompletedWhen) {
        this.pickingCompletedWhen = pickingCompletedWhen;
    }

    public Integer getLastEditedBy() {
        return lastEditedBy;
    }

    public void setLastEditedBy(Integer lastEditedBy) {
        this.lastEditedBy = lastEditedBy;
    }

    public java.time.Instant getLastEditedWhen() {
        return lastEditedWhen;
    }

    public void setLastEditedWhen(java.time.Instant lastEditedWhen) {
        this.lastEditedWhen = lastEditedWhen;
    }
}

@com.fasterxml.jackson.annotation.JsonIgnoreProperties({ "id" })
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
    private java.time.Instant orderDate;

    @Field("expectedDeliveryDate")
    private java.time.Instant expectedDeliveryDate;

    @Field("customerPurchaseOrderNumber")
    private String customerPurchaseOrderNumber;

    @Field("isUndersupplyBackordered")
    private Boolean isUndersupplyBackordered;

    private String comments;

    private String deliveryInstructions;

    private String internalComments;

    @Field("pickingCompletedWhen")
    private java.time.Instant pickingCompletedWhen;

    @Field("lastEditedBy")
    private Integer lastEditedBy;

    @Field("lastEditedWhen")
    private java.time.Instant lastEditedWhen;

    @ReadOnlyProperty
    @DocumentReference(lazy = true, lookup = "{ 'orderId': ?#{#self.orderId} }", sort = "{ 'orderLineId': 1 }")
    private java.util.List<OrderLine> orderLines = new java.util.ArrayList<>();

    Order() {
    }

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public Integer getOrderId() {
        return orderId;
    }

    public void setOrderId(Integer orderId) {
        this.orderId = orderId;
    }

    public Integer getCustomerId() {
        return customerId;
    }

    public void setCustomerId(Integer customerId) {
        this.customerId = customerId;
    }

    public Integer getSalespersonPersonId() {
        return salespersonPersonId;
    }

    public void setSalespersonPersonId(Integer salespersonPersonId) {
        this.salespersonPersonId = salespersonPersonId;
    }

    public Integer getPickedByPersonId() {
        return pickedByPersonId;
    }

    public void setPickedByPersonId(Integer pickedByPersonId) {
        this.pickedByPersonId = pickedByPersonId;
    }

    public Integer getContactPersonId() {
        return contactPersonId;
    }

    public void setContactPersonId(Integer contactPersonId) {
        this.contactPersonId = contactPersonId;
    }

    public Integer getBackorderOrderId() {
        return backorderOrderId;
    }

    public void setBackorderOrderId(Integer backorderOrderId) {
        this.backorderOrderId = backorderOrderId;
    }

    public java.time.Instant getOrderDate() {
        return orderDate;
    }

    public void setOrderDate(java.time.Instant orderDate) {
        this.orderDate = orderDate;
    }

    public java.time.Instant getExpectedDeliveryDate() {
        return expectedDeliveryDate;
    }

    public void setExpectedDeliveryDate(java.time.Instant expectedDeliveryDate) {
        this.expectedDeliveryDate = expectedDeliveryDate;
    }

    public String getCustomerPurchaseOrderNumber() {
        return customerPurchaseOrderNumber;
    }

    public void setCustomerPurchaseOrderNumber(String customerPurchaseOrderNumber) {
        this.customerPurchaseOrderNumber = customerPurchaseOrderNumber;
    }

    public Boolean getIsUndersupplyBackordered() {
        return isUndersupplyBackordered;
    }

    public void setIsUndersupplyBackordered(Boolean isUndersupplyBackordered) {
        this.isUndersupplyBackordered = isUndersupplyBackordered;
    }

    public String getComments() {
        return comments;
    }

    public void setComments(String comments) {
        this.comments = comments;
    }

    public String getDeliveryInstructions() {
        return deliveryInstructions;
    }

    public void setDeliveryInstructions(String deliveryInstructions) {
        this.deliveryInstructions = deliveryInstructions;
    }

    public String getInternalComments() {
        return internalComments;
    }

    public void setInternalComments(String internalComments) {
        this.internalComments = internalComments;
    }

    public java.time.Instant getPickingCompletedWhen() {
        return pickingCompletedWhen;
    }

    public void setPickingCompletedWhen(java.time.Instant pickingCompletedWhen) {
        this.pickingCompletedWhen = pickingCompletedWhen;
    }

    public Integer getLastEditedBy() {
        return lastEditedBy;
    }

    public void setLastEditedBy(Integer lastEditedBy) {
        this.lastEditedBy = lastEditedBy;
    }

    public java.time.Instant getLastEditedWhen() {
        return lastEditedWhen;
    }

    public void setLastEditedWhen(java.time.Instant lastEditedWhen) {
        this.lastEditedWhen = lastEditedWhen;
    }

    public java.util.List<OrderLine> getOrderLines() {
        return orderLines;
    }

    public void setOrderLines(java.util.List<OrderLine> orderLines) {
        this.orderLines = orderLines;
    }
}

@com.fasterxml.jackson.annotation.JsonIgnoreProperties({ "id" })
@Document(collection = "people")
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

    Person() {
    }

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public Integer getPersonId() {
        return personId;
    }

    public void setPersonId(Integer personId) {
        this.personId = personId;
    }

    public String getFullName() {
        return fullName;
    }

    public void setFullName(String fullName) {
        this.fullName = fullName;
    }

    public String getPreferredName() {
        return preferredName;
    }

    public void setPreferredName(String preferredName) {
        this.preferredName = preferredName;
    }

    public String getEmailAddress() {
        return emailAddress;
    }

    public void setEmailAddress(String emailAddress) {
        this.emailAddress = emailAddress;
    }

    public String getCustomFields() {
        return customFields;
    }

    public void setCustomFields(String customFields) {
        this.customFields = customFields;
    }

    public String getOtherLanguages() {
        return otherLanguages;
    }

    public void setOtherLanguages(String otherLanguages) {
        this.otherLanguages = otherLanguages;
    }
}

@com.fasterxml.jackson.annotation.JsonIgnoreProperties({ "id" })
@Document(collection = "suppliers")
class Supplier {

    @Id
    private String id;

    @Field("supplierId")
    private Integer supplierId;

    private String supplierName;

    private String supplierReference;

    private Integer paymentDays;

    Supplier() {
    }

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public Integer getSupplierId() {
        return supplierId;
    }

    public void setSupplierId(Integer supplierId) {
        this.supplierId = supplierId;
    }

    public String getSupplierName() {
        return supplierName;
    }

    public void setSupplierName(String supplierName) {
        this.supplierName = supplierName;
    }

    public String getSupplierReference() {
        return supplierReference;
    }

    public void setSupplierReference(String supplierReference) {
        this.supplierReference = supplierReference;
    }

    public Integer getPaymentDays() {
        return paymentDays;
    }

    public void setPaymentDays(Integer paymentDays) {
        this.paymentDays = paymentDays;
    }
}

record TaxRateCount(java.math.BigDecimal taxRate, Long count) {
}

record CountProjection(Long count) {
}

record MaxProjection(java.math.BigDecimal maxUnitPrice) {
}

record SumProjection(java.math.BigDecimal total) {
}