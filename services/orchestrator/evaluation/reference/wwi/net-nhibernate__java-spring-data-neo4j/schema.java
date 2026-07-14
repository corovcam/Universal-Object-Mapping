package uom.services;

import java.util.List;

import org.springframework.data.neo4j.core.schema.GeneratedValue;
import org.springframework.data.neo4j.core.schema.Id;
import org.springframework.data.neo4j.core.schema.Node;
import org.springframework.data.neo4j.core.schema.Property;
import org.springframework.data.neo4j.core.schema.Relationship;

@Node("Order")
class Order {

    @Id @GeneratedValue
    private String id;

    @Property("orderId")
    private Integer orderId;

    @Relationship(type = "CUSTOMERS", direction = Relationship.Direction.OUTGOING)
    private Customer customer;

    @Relationship(type = "ORDERS", direction = Relationship.Direction.INCOMING)
    private List<OrderLine> orderLines;

    public Order() {
    }

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    public Integer getOrderId() { return orderId; }
    public void setOrderId(Integer orderId) { this.orderId = orderId; }
    public Customer getCustomer() { return customer; }
    public void setCustomer(Customer customer) { this.customer = customer; }
    public List<OrderLine> getOrderLines() { return orderLines; }
    public void setOrderLines(List<OrderLine> orderLines) { this.orderLines = orderLines; }
}

@Node("Customer")
class Customer {

    @Id @GeneratedValue
    private String id;

    @Property("customerId")
    private Integer customerId;

    @Property("customerName")
    private String customerName;

    @Property("accountOpenedDate")
    private String accountOpenedDate;

    @Property("creditLimit")
    private Double creditLimit;

    @Relationship(type = "CUSTOMERS", direction = Relationship.Direction.INCOMING)
    private List<CustomerTransaction> customerTransactions;

    public Customer() {
    }

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    public Integer getCustomerId() { return customerId; }
    public void setCustomerId(Integer customerId) { this.customerId = customerId; }
    public String getCustomerName() { return customerName; }
    public void setCustomerName(String customerName) { this.customerName = customerName; }
    public String getAccountOpenedDate() { return accountOpenedDate; }
    public void setAccountOpenedDate(String accountOpenedDate) { this.accountOpenedDate = accountOpenedDate; }
    public Double getCreditLimit() { return creditLimit; }
    public void setCreditLimit(Double creditLimit) { this.creditLimit = creditLimit; }
    public List<CustomerTransaction> getCustomerTransactions() { return customerTransactions; }
    public void setCustomerTransactions(List<CustomerTransaction> customerTransactions) { this.customerTransactions = customerTransactions; }
}

@Node("CustomerTransaction")
class CustomerTransaction {

    @Id @GeneratedValue
    private String id;

    @Property("customerTransactionId")
    private Integer customerTransactionId;

    @Property("transactionDate")
    private String transactionDate;

    @Property("transactionAmount")
    private Double transactionAmount;

    public CustomerTransaction() {
    }

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    public Integer getCustomerTransactionId() { return customerTransactionId; }
    public void setCustomerTransactionId(Integer customerTransactionId) { this.customerTransactionId = customerTransactionId; }
    public String getTransactionDate() { return transactionDate; }
    public void setTransactionDate(String transactionDate) { this.transactionDate = transactionDate; }
    public Double getTransactionAmount() { return transactionAmount; }
    public void setTransactionAmount(Double transactionAmount) { this.transactionAmount = transactionAmount; }
}

@Node("OrderLine")
class OrderLine {

    @Id @GeneratedValue
    private String id;

    @Property("orderLineId")
    private Integer orderLineId;

    @Property("orderId")
    private Integer orderId;

    @Property("description")
    private String description;

    @Property("packageTypeId")
    private Integer packageTypeId;

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

    @Property("lastEditedBy")
    private Integer lastEditedBy;

    @Property("lastEditedWhen")
    private String lastEditedWhen;

    public OrderLine() {
    }

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    public Integer getOrderLineId() { return orderLineId; }
    public void setOrderLineId(Integer orderLineId) { this.orderLineId = orderLineId; }
    public Integer getOrderId() { return orderId; }
    public void setOrderId(Integer orderId) { this.orderId = orderId; }
    public String getDescription() { return description; }
    public void setDescription(String description) { this.description = description; }
    public Integer getPackageTypeId() { return packageTypeId; }
    public void setPackageTypeId(Integer packageTypeId) { this.packageTypeId = packageTypeId; }
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
    public Integer getLastEditedBy() { return lastEditedBy; }
    public void setLastEditedBy(Integer lastEditedBy) { this.lastEditedBy = lastEditedBy; }
    public String getLastEditedWhen() { return lastEditedWhen; }
    public void setLastEditedWhen(String lastEditedWhen) { this.lastEditedWhen = lastEditedWhen; }
}