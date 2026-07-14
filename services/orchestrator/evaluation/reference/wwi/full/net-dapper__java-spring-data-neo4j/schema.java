@Node("OrderLine") @JsonIgnoreProperties({"id"})
class OrderLine {
    @Id @GeneratedValue private String id;
    @Property("orderLineId") private Integer orderLineId;
    @Property("description") private String description;
    @Property("quantity") private Integer quantity;
    @Property("unitPrice") private Double unitPrice;
    @Property("taxRate") private Double taxRate;
    @Property("pickedQuantity") private Integer pickedQuantity;
    @Property("pickingCompletedWhen") private String pickingCompletedWhen;
    @Property("lastEditedWhen") private String lastEditedWhen;
    @Property("packageTypeId") private Integer packageTypeId;
    public OrderLine() {}
    public Integer getOrderLineId() { return orderLineId; }
    public void setOrderLineId(Integer v) { this.orderLineId = v; }
    public String getDescription() { return description; }
    public void setDescription(String v) { this.description = v; }
    public Integer getQuantity() { return quantity; }
    public void setQuantity(Integer v) { this.quantity = v; }
    public Double getUnitPrice() { return unitPrice; }
    public void setUnitPrice(Double v) { this.unitPrice = v; }
    public Double getTaxRate() { return taxRate; }
    public void setTaxRate(Double v) { this.taxRate = v; }
    public Integer getPickedQuantity() { return pickedQuantity; }
    public void setPickedQuantity(Integer v) { this.pickedQuantity = v; }
    public String getPickingCompletedWhen() { return pickingCompletedWhen; }
    public void setPickingCompletedWhen(String v) { this.pickingCompletedWhen = v; }
    public String getLastEditedWhen() { return lastEditedWhen; }
    public void setLastEditedWhen(String v) { this.lastEditedWhen = v; }
    public Integer getPackageTypeId() { return packageTypeId; }
    public void setPackageTypeId(Integer v) { this.packageTypeId = v; }
}

record OrderLineProjection(Integer orderLineId, Integer orderId, Integer stockItemId, String description, Integer quantity, Double unitPrice, Double taxRate, Integer pickedQuantity, String pickingCompletedWhen, Integer lastEditedBy, String lastEditedWhen) {}

@Node("Order") @JsonIgnoreProperties({"id"})
class Order {
    @Id @GeneratedValue private String id;
    @Property("orderId") private Integer orderId;
    @Property("customerPurchaseOrderNumber") private String customerPurchaseOrderNumber;
    @Property("expectedDeliveryDate") private String expectedDeliveryDate;
    @Property("isUndersupplyBackordered") private Integer isUndersupplyBackordered;
    @Property("lastEditedWhen") private String lastEditedWhen;
    @Property("orderDate") private String orderDate;
    @Property("pickingCompletedWhen") private String pickingCompletedWhen;
    @Property("comments") private String comments;
    @Property("deliveryInstructions") private String deliveryInstructions;
    @Property("internalComments") private String internalComments;
    @Relationship(type = "ORDERS", direction = Relationship.Direction.INCOMING) private List<OrderLine> orderLines;
    public Order() {}
    public Integer getOrderId() { return orderId; }
    public void setOrderId(Integer v) { this.orderId = v; }
    public String getCustomerPurchaseOrderNumber() { return customerPurchaseOrderNumber; }
    public void setCustomerPurchaseOrderNumber(String v) { this.customerPurchaseOrderNumber = v; }
    public String getExpectedDeliveryDate() { return expectedDeliveryDate; }
    public void setExpectedDeliveryDate(String v) { this.expectedDeliveryDate = v; }
    public Integer getIsUndersupplyBackordered() { return isUndersupplyBackordered; }
    public void setIsUndersupplyBackordered(Integer v) { this.isUndersupplyBackordered = v; }
    public String getLastEditedWhen() { return lastEditedWhen; }
    public void setLastEditedWhen(String v) { this.lastEditedWhen = v; }
    public String getOrderDate() { return orderDate; }
    public void setOrderDate(String v) { this.orderDate = v; }
    public String getPickingCompletedWhen() { return pickingCompletedWhen; }
    public void setPickingCompletedWhen(String v) { this.pickingCompletedWhen = v; }
    public String getComments() { return comments; }
    public void setComments(String v) { this.comments = v; }
    public String getDeliveryInstructions() { return deliveryInstructions; }
    public void setDeliveryInstructions(String v) { this.deliveryInstructions = v; }
    public String getInternalComments() { return internalComments; }
    public void setInternalComments(String v) { this.internalComments = v; }
    public List<OrderLine> getOrderLines() { return orderLines; }
    public void setOrderLines(List<OrderLine> v) { this.orderLines = v; }
}

record OrderProjection(Integer orderId, Integer customerId, String orderDate, String expectedDeliveryDate, String customerPurchaseOrderNumber, Boolean isUndersupplyBackordered, String pickingCompletedWhen, String lastEditedWhen, Integer backorderOrderId, List<OrderLineProjection> orderLines) {}

@Node("Person") @JsonIgnoreProperties({"id"})
class Person {
    @Id @GeneratedValue private String id;
    @Property("personId") private Integer personId;
    @Property("fullName") private String fullName;
    @Property("preferredName") private String preferredName;
    @Property("emailAddress") private String emailAddress;
    @Property("customFields") private String customFields;
    @Property("otherLanguages") private String otherLanguages;
    public Person() {}
    public Integer getPersonId() { return personId; }
    public void setPersonId(Integer v) { this.personId = v; }
    public String getFullName() { return fullName; }
    public void setFullName(String v) { this.fullName = v; }
    public String getPreferredName() { return preferredName; }
    public void setPreferredName(String v) { this.preferredName = v; }
    public String getEmailAddress() { return emailAddress; }
    public void setEmailAddress(String v) { this.emailAddress = v; }
    public String getCustomFields() { return customFields; }
    public void setCustomFields(String v) { this.customFields = v; }
    public String getOtherLanguages() { return otherLanguages; }
    public void setOtherLanguages(String v) { this.otherLanguages = v; }
}

record TaxRateCount(Double taxRate, Long count) {}

@Node("Supplier") @JsonIgnoreProperties({"id"})
class Supplier {
    @Id @GeneratedValue private String id;
    @Property("supplierId") private Integer supplierId;
    @Property("supplierName") private String supplierName;
    @Property("supplierReference") private String supplierReference;
    @Property("paymentDays") private Integer paymentDays;
    public Supplier() {}
    public Integer getSupplierId() { return supplierId; }
    public void setSupplierId(Integer v) { this.supplierId = v; }
    public String getSupplierName() { return supplierName; }
    public void setSupplierName(String v) { this.supplierName = v; }
    public String getSupplierReference() { return supplierReference; }
    public void setSupplierReference(String v) { this.supplierReference = v; }
    public Integer getPaymentDays() { return paymentDays; }
    public void setPaymentDays(Integer v) { this.paymentDays = v; }
}