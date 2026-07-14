@Node("OrderLine")
class OrderLine {

    @Id @GeneratedValue
    private String id;

    @Property("orderLineId")
    private Integer orderLineId;

    @Property("description")
    private String description;

    @Property("quantity")
    private Integer quantity;

    @Property("unitPrice")
    private Double unitPrice;

    @Property("taxRate")
    private Double taxRate;

    @Property("pickedQuantity")
    private Integer pickedQuantity;

    @Property("pickingCompletedWhen")
    private String pickingCompletedWhen;

    @Property("lastEditedWhen")
    private String lastEditedWhen;

    @JsonIgnore
    @Relationship(type = "ORDERS", direction = Relationship.Direction.OUTGOING)
    private Order order;

    public OrderLine() {
    }

    public Integer getOrderLineId() { return orderLineId; }
    public void setOrderLineId(Integer orderLineId) { this.orderLineId = orderLineId; }

    public String getDescription() { return description; }
    public void setDescription(String description) { this.description = description; }

    public Integer getQuantity() { return quantity; }
    public void setQuantity(Integer quantity) { this.quantity = quantity; }

    public Double getUnitPrice() { return unitPrice; }
    public void setUnitPrice(Double unitPrice) { this.unitPrice = unitPrice; }

    public Double getTaxRate() { return taxRate; }
    public void setTaxRate(Double taxRate) { this.taxRate = taxRate; }

    public Integer getPickedQuantity() { return pickedQuantity; }
    public void setPickedQuantity(Integer pickedQuantity) { this.pickedQuantity = pickedQuantity; }

    public String getPickingCompletedWhen() { return pickingCompletedWhen; }
    public void setPickingCompletedWhen(String pickingCompletedWhen) { this.pickingCompletedWhen = pickingCompletedWhen; }

    public String getLastEditedWhen() { return lastEditedWhen; }
    public void setLastEditedWhen(String lastEditedWhen) { this.lastEditedWhen = lastEditedWhen; }

    public Order getOrder() { return order; }
    public void setOrder(Order order) { this.order = order; }
}

@Node("Order")
class Order {

    @Id @GeneratedValue
    private String id;

    @Property("orderId")
    private Integer orderId;

    @Property("orderDate")
    private String orderDate;

    @Property("expectedDeliveryDate")
    private String expectedDeliveryDate;

    @Property("customerPurchaseOrderNumber")
    private String customerPurchaseOrderNumber;

    @Property("isUndersupplyBackordered")
    private Integer isUndersupplyBackordered;

    @Property("pickingCompletedWhen")
    private String pickingCompletedWhen;

    @Property("lastEditedWhen")
    private String lastEditedWhen;

    @Relationship(type = "ORDERS", direction = Relationship.Direction.INCOMING)
    private List<OrderLine> orderLines;

    public Order() {
    }

    public Integer getOrderId() { return orderId; }
    public void setOrderId(Integer orderId) { this.orderId = orderId; }

    public String getOrderDate() { return orderDate; }
    public void setOrderDate(String orderDate) { this.orderDate = orderDate; }

    public String getExpectedDeliveryDate() { return expectedDeliveryDate; }
    public void setExpectedDeliveryDate(String expectedDeliveryDate) { this.expectedDeliveryDate = expectedDeliveryDate; }

    public String getCustomerPurchaseOrderNumber() { return customerPurchaseOrderNumber; }
    public void setCustomerPurchaseOrderNumber(String customerPurchaseOrderNumber) { this.customerPurchaseOrderNumber = customerPurchaseOrderNumber; }

    public Integer getIsUndersupplyBackordered() { return isUndersupplyBackordered; }
    public void setIsUndersupplyBackordered(Integer isUndersupplyBackordered) { this.isUndersupplyBackordered = isUndersupplyBackordered; }

    public String getPickingCompletedWhen() { return pickingCompletedWhen; }
    public void setPickingCompletedWhen(String pickingCompletedWhen) { this.pickingCompletedWhen = pickingCompletedWhen; }

    public String getLastEditedWhen() { return lastEditedWhen; }
    public void setLastEditedWhen(String lastEditedWhen) { this.lastEditedWhen = lastEditedWhen; }

    public List<OrderLine> getOrderLines() { return orderLines; }
    public void setOrderLines(List<OrderLine> orderLines) { this.orderLines = orderLines; }
}

@Node("Person")
class Person {

    @Id @GeneratedValue
    private String id;

    @Property("personId")
    private Integer personId;

    @Property("fullName")
    private String fullName;

    @Property("preferredName")
    private String preferredName;

    @Property("emailAddress")
    private String emailAddress;

    @Property("customFields")
    private String customFields;

    @Property("otherLanguages")
    private String otherLanguages;

    public Person() {
    }

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

@Node("Supplier")
class Supplier {

    @Id @GeneratedValue
    private String id;

    @Property("supplierId")
    private Integer supplierId;

    @Property("supplierName")
    private String supplierName;

    @Property("supplierReference")
    private String supplierReference;

    @Property("paymentDays")
    private Integer paymentDays;

    public Supplier() {
    }

    public Integer getSupplierId() { return supplierId; }
    public void setSupplierId(Integer supplierId) { this.supplierId = supplierId; }

    public String getSupplierName() { return supplierName; }
    public void setSupplierName(String supplierName) { this.supplierName = supplierName; }

    public String getSupplierReference() { return supplierReference; }
    public void setSupplierReference(String supplierReference) { this.supplierReference = supplierReference; }

    public Integer getPaymentDays() { return paymentDays; }
    public void setPaymentDays(Integer paymentDays) { this.paymentDays = paymentDays; }
}

record TaxRateCount(Double taxRate, Long count) {
}

record OrderLineView(Integer orderLineId, String description, Integer quantity, Double unitPrice, Double taxRate, Integer pickedQuantity, String pickingCompletedWhen, String lastEditedWhen) {
}

record OrderView(Integer orderId, String orderDate, String expectedDeliveryDate, String customerPurchaseOrderNumber, Integer isUndersupplyBackordered, String pickingCompletedWhen, String lastEditedWhen, List<OrderLineView> orderLines) {
}