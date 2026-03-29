package uom.services.benchmarks.domain;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;
import org.springframework.data.mongodb.core.mapping.Field;

/**
 * Order document with embedded Customer and CustomerTransactions.
 * Maps to the 'orders' collection in MongoDB.
 * 
 * TRANSLATED FROM: C# EFCore Customer, CustomerTransaction entities
 * ARCHITECTURAL SHIFT: Denormalized - Customers no longer a root collection.
 *                      Instead, Customer and its transactions are embedded within Order.
 */
@Document(collection = "orders")
class Order {

    @Id
    private String id;

    @Field("orderId")
    private Integer orderId;

    @Field("customerId")
    private Integer customerId;

    @Field("orderDate")
    private LocalDateTime orderDate;

    @Field("expectedDeliveryDate")
    private LocalDate expectedDeliveryDate;

    // Embedded Customer document (denormalized from Sales.Customers table)
    private Customer customer;

    // Constructors
    public Order() {
    }

    // Getters and Setters
    public String getId() { return id; }
    public void setId(String id) { this.id = id; }

    public Integer getOrderId() { return orderId; }
    public void setOrderId(Integer orderId) { this.orderId = orderId; }

    public Integer getCustomerId() { return customerId; }
    public void setCustomerId(Integer customerId) { this.customerId = customerId; }

    public LocalDateTime getOrderDate() { return orderDate; }
    public void setOrderDate(LocalDateTime orderDate) { this.orderDate = orderDate; }

    public LocalDate getExpectedDeliveryDate() { return expectedDeliveryDate; }
    public void setExpectedDeliveryDate(LocalDate expectedDeliveryDate) { this.expectedDeliveryDate = expectedDeliveryDate; }

    public Customer getCustomer() { return customer; }
    public void setCustomer(Customer customer) { this.customer = customer; }
}

/**
 * Embedded Customer document within Order.
 * Represents the denormalized Sales.Customers table data.
 * 
 * TRANSLATED FROM: C# Customer entity (no longer a @Document root)
 * NOTE: No @Document annotation - this is a value object embedded in Order
 */
class Customer {

    private Integer customerId;
    private String customerName;
    private LocalDate accountOpenedDate;
    private BigDecimal creditLimit;

    // Embedded CustomerTransactions array (denormalized from Sales.CustomerTransactions table)
    private List<CustomerTransaction> customerTransactions = new ArrayList<>();

    // Constructors
    public Customer() {
    }

    // Getters and Setters
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

/**
 * Embedded CustomerTransaction document within Customer.customerTransactions array.
 * Represents the denormalized Sales.CustomerTransactions table data.
 * 
 * TRANSLATED FROM: C# CustomerTransaction entity
 * NOTE: No @Document annotation - this is a value object embedded in Customer
 */
class CustomerTransaction {

    private Integer customerTransactionId;
    private Integer customerId;
    private LocalDate transactionDate;
    private BigDecimal transactionAmount;

    // Additional transaction fields from Sales.CustomerTransactions
    private BigDecimal amountExcludingTax;
    private BigDecimal taxAmount;
    private BigDecimal outstandingBalance;
    private Boolean isFinalized;

    // Constructors
    public CustomerTransaction() {
    }

    // Getters and Setters
    public Integer getCustomerTransactionId() { return customerTransactionId; }
    public void setCustomerTransactionId(Integer customerTransactionId) { this.customerTransactionId = customerTransactionId; }

    public Integer getCustomerId() { return customerId; }
    public void setCustomerId(Integer customerId) { this.customerId = customerId; }

    public LocalDate getTransactionDate() { return transactionDate; }
    public void setTransactionDate(LocalDate transactionDate) { this.transactionDate = transactionDate; }

    public BigDecimal getTransactionAmount() { return transactionAmount; }
    public void setTransactionAmount(BigDecimal transactionAmount) { this.transactionAmount = transactionAmount; }

    public BigDecimal getAmountExcludingTax() { return amountExcludingTax; }
    public void setAmountExcludingTax(BigDecimal amountExcludingTax) { this.amountExcludingTax = amountExcludingTax; }

    public BigDecimal getTaxAmount() { return taxAmount; }
    public void setTaxAmount(BigDecimal taxAmount) { this.taxAmount = taxAmount; }

    public BigDecimal getOutstandingBalance() { return outstandingBalance; }
    public void setOutstandingBalance(BigDecimal outstandingBalance) { this.outstandingBalance = outstandingBalance; }

    public Boolean getIsFinalized() { return isFinalized; }
    public void setIsFinalized(Boolean isFinalized) { this.isFinalized = isFinalized; }
}

/**
 * OrderLine document with embedded StockItem.
 * Maps to the 'orderLines' collection in MongoDB.
 * 
 * TRANSLATED FROM: C# OrderLine entity
 */
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

    // Embedded StockItem document (denormalized reference data)
    private StockItem stockItem;

    // Constructors
    public OrderLine() {
    }

    // Getters and Setters
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

/**
 * Embedded StockItem document within OrderLine.
 * Represents denormalized stock item reference data.
 * 
 * NOTE: No @Document annotation - this is a value object embedded in OrderLine
 */
class StockItem {

    private Integer stockItemId;
    private String stockItemName;
    private BigDecimal unitPrice;

    // Constructors
    public StockItem() {
    }

    // Getters and Setters
    public Integer getStockItemId() { return stockItemId; }
    public void setStockItemId(Integer stockItemId) { this.stockItemId = stockItemId; }

    public String getStockItemName() { return stockItemName; }
    public void setStockItemName(String stockItemName) { this.stockItemName = stockItemName; }

    public BigDecimal getUnitPrice() { return unitPrice; }
    public void setUnitPrice(BigDecimal unitPrice) { this.unitPrice = unitPrice; }
}