# Schema mapping — Spring Data MongoDB 5.0 document classes

How to turn a domain model (or a relational entity being migrated) into Spring Data
MongoDB mapping classes that map cleanly and round-trip through `MongoTemplate`.

## Table of contents

1. The anatomy of an aggregate root
2. The `@Id` / `_id` rule (most common mistake)
3. Field mapping and `@Field`
4. Type mapping table (Java ↔ BSON)
5. Embedding vs referencing
6. `@DocumentReference` and `@DBRef`
7. Indexes
8. Constructors, access modifiers, getters/setters
9. Standalone `MongoTemplate` bootstrap (for harnesses)

---

## 1. Anatomy of an aggregate root

An aggregate root maps to one collection and carries `@Document`. Keep top-level mapping
classes package-private (no `public`), matching project convention.

```java
import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;

import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;
import org.springframework.data.mongodb.core.mapping.Field;

@Document(collection = "orders")
class Order {

    @Id
    private String id;

    @Field("orderId")
    private Integer orderId;

    @Field("customerId")
    private Integer customerId;

    private Customer customer; // embedded value object (no @Document)

    Order() {
    }

    // getters and setters ...
}
```

`@Document(collection = "orders")` pins the collection name. Without the `collection`
attribute the collection defaults to the decapitalized class name (`order`), which is
usually NOT what you want when matching an existing collection — always set it explicitly.

## 2. The `@Id` / `_id` rule (most common mistake)

MongoDB's primary key is `_id`. Spring maps the `@Id`-annotated property to `_id`.

- Use `@Id private String id;`. A `String` accepts both `ObjectId` hex strings and
  natural string keys, so it is the safe default.
- When migrating a relational entity whose key is `int CustomerID`, **do not** put `@Id`
  on an `Integer customerId`. Instead keep a separate `@Id private String id;` for `_id`,
  and map the business key as `@Field("customerId") private Integer customerId;`.
- Use `@MongoId` (from `core.mapping`) only when you must control the BSON type of `_id`
  (e.g. force an `ObjectId`).

Wrong (collapses the natural key onto `_id`, loses the Mongo identity):

```java
@Id
private Integer customerId; // ❌ don't map an int PK onto _id
```

Right:

```java
@Id
private String id;          // _id

@Field("customerId")
private Integer customerId; // business key preserved as its own field
```

## 3. Field mapping and `@Field`

- A property with no annotation is stored under its Java name.
- Use `@Field("documentKey")` when the stored key differs (e.g. the existing collection
  uses camelCase and differs from the Java name, or you want to be explicit).
- The string in `@Field(...)`, in `Criteria.where(...)`, and in aggregation stages is the
  **MongoDB document field name** — not the Java property and not the SQL column.
- Import `Field` by name (clashes with `java.lang.reflect.Field`; see `imports.md`).
- For an explicit BSON type, use `@Field(targetType = FieldType.DECIMAL128)`.

## 4. Type mapping table (Java ↔ BSON)

Choose Java types deliberately when translating from SQL/.NET. These map predictably:

| Source intent | Java type | BSON | Notes |
|---|---|---|---|
| identity / `_id` | `String` | ObjectId or String | `@Id` |
| 32-bit int | `Integer` | int32 | |
| 64-bit int / bigint | `Long` | int64 | |
| `decimal` / money | `BigDecimal` | Decimal128 | In 5.0 the representation default changed; `BigDecimal` → Decimal128 is the safe explicit choice |
| `float`/`double` | `Double` | double | avoid for money |
| `bit`/`bool` | `Boolean` | bool | |
| `date` (no time) | `LocalDate` | Date | build via `LocalDate.of(y, m, d)` |
| `datetime`/`timestamp` | `LocalDateTime` | Date | `LocalDateTime.of(...)` |
| instant / UTC | `Instant` | Date | |
| `nvarchar`/text | `String` | string | |
| `uniqueidentifier`/UUID | `java.util.UUID` | binary/string | 5.0 no longer defaults the UUID representation — set it explicitly if needed |
| array / collection | `List<T>` | array | |

**Never** use `java.util.Date` or `new Date(y, m, d)` — see `imports.md` §11.

## 5. Embedding vs referencing

When a relational parent/child (one-to-many via FK) becomes MongoDB, you choose:

**Embed** the child inside the parent when the child is owned by and always read with the
parent, the child set is bounded, and you want a single read. The embedded class is a
plain value object — **no `@Document`**, no `@Id`.

```java
@Document(collection = "orders")
class Order {
    @Id
    private String id;
    @Field("orderId")
    private Integer orderId;
    private Customer customer;                 // single embedded object
    // getters/setters ...
}

class Customer {                              // embedded value object: NO @Document
    private Integer customerId;
    private String customerName;
    private LocalDate accountOpenedDate;
    private BigDecimal creditLimit;
    private List<CustomerTransaction> customerTransactions = new ArrayList<>(); // embedded array
    // getters/setters ...
}

class CustomerTransaction {                   // embedded value object: NO @Document
    private Integer customerTransactionId;
    private LocalDate transactionDate;
    private BigDecimal transactionAmount;
    // getters/setters ...
}
```

**Reference** the child as a separate collection when it is large, shared, or queried
independently. See §6.

Rule of thumb when translating: a child table that is only ever accessed through its
parent → embed; a child table that is itself an aggregate root or is huge → reference.

## 6. `@DocumentReference` and `@DBRef`

Prefer `@DocumentReference` (stores the target's `_id`, flexible lookup) over the legacy
`@DBRef` (stores a `{$ref,$id}` document).

A lazy, read-only back-reference resolved by a custom lookup (as used in the project's
`Order` → `OrderLine` link):

```java
import java.util.List;
import org.springframework.data.annotation.ReadOnlyProperty;
import org.springframework.data.mongodb.core.mapping.DocumentReference;

@ReadOnlyProperty
@DocumentReference(lazy = true, lookup = "{ 'orderId': ?#{#self.orderId} }", sort = "{ 'orderLineId': 1 }")
private List<OrderLine> orderLines;
```

- `lazy = true` defers resolution until the field is accessed.
- `lookup = "{ 'orderId': ?#{#self.orderId} }"` matches `OrderLine.orderId` against this
  document's `orderId` (SpEL `#self`), instead of matching on `_id`.
- `@ReadOnlyProperty` means the field is populated on read and never written back.

Simple reference (stores referenced `_id`):

```java
import org.springframework.data.mongodb.core.mapping.DocumentReference;

@DocumentReference
private Warehouse warehouse;
```

## 7. Indexes

```java
import org.springframework.data.mongodb.core.index.Indexed;
import org.springframework.data.mongodb.core.index.CompoundIndex;

@Document(collection = "people")
@CompoundIndex(name = "name_age_idx", def = "{'lastName': 1, 'age': -1}")
class Person {
    @Id
    private String id;
    @Indexed(unique = true)
    private Integer ssn;
    @Field("fName")
    private String firstName;
    // ...
}
```

For a pure migration/validation scenario you usually don't need indexes — add them only
when the source schema or the user calls for them.

## 8. Constructors, access modifiers, getters/setters

- Provide a no-arg constructor (Spring instantiates via it unless a `@PersistenceCreator`
  constructor is present).
- Keep classes package-private; only the harness/entrypoint class with `main` is `public`.
- Provide getters/setters for mapped fields. If serializing results with Jackson in a
  harness, getters are what Jackson reads.
- Do not put `public` on every field/class reflexively — it diverges from the project
  snippets and is unnecessary.

## 9. Standalone `MongoTemplate` bootstrap (for harnesses)

When code must run outside a Spring context (validation/translation harness), build the
`MongoTemplate` by hand. This exact wiring is what the project snippets use:

```java
import com.mongodb.client.MongoClients;
import org.springframework.data.mongodb.MongoDatabaseFactory;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.mongodb.core.SimpleMongoClientDatabaseFactory;
import org.springframework.data.mongodb.core.convert.DefaultDbRefResolver;
import org.springframework.data.mongodb.core.convert.DefaultMongoTypeMapper;
import org.springframework.data.mongodb.core.convert.MappingMongoConverter;
import org.springframework.data.mongodb.core.convert.MongoCustomConversions;
import org.springframework.data.mongodb.core.mapping.MongoMappingContext;

final class MongoTemplateFactory {
    private MongoTemplateFactory() {
    }

    static MongoTemplate create(String mongoUri, String mongoDatabase) {
        MongoDatabaseFactory databaseFactory =
                new SimpleMongoClientDatabaseFactory(MongoClients.create(mongoUri), mongoDatabase);

        MongoCustomConversions customConversions = MongoCustomConversions.create(configuration -> {});

        MongoMappingContext mappingContext = new MongoMappingContext();
        mappingContext.setSimpleTypeHolder(customConversions.getSimpleTypeHolder());
        mappingContext.afterPropertiesSet();

        MappingMongoConverter converter =
                new MappingMongoConverter(new DefaultDbRefResolver(databaseFactory), mappingContext);
        converter.setCustomConversions(customConversions);
        converter.setTypeMapper(new DefaultMongoTypeMapper(null)); // null => omit _class type hints
        converter.afterPropertiesSet();

        return new MongoTemplate(databaseFactory, converter);
    }
}
```

`new DefaultMongoTypeMapper(null)` suppresses the `_class` discriminator field so reads
against an existing collection don't expect Spring-written type hints. Validate each
aggregate root with a one-document fetch:

```java
Query probe = new Query().limit(1);
mongoTemplate.findOne(probe, Order.class); // throws MappingException if the mapping is wrong
```

Only validate `@Document` aggregate roots this way — embedded value objects (no
`@Document`) are not fetched directly.
