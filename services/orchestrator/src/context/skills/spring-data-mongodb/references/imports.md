# Canonical imports — Spring Data MongoDB 5.0 / Spring Boot 4 / Jackson 3

This is the source of truth for imports. If a class is not here, look it up before using
it — do not guess the package. Every entry below is valid for Spring Data MongoDB 5.0.x
(Spring Boot 4.0.x) on Java 25.

## Table of contents

1. Mapping annotations
2. Identity (`@Id`) and lifecycle annotations
3. Indexing annotations
4. Query API (`Query`, `Criteria`, `Update`)
5. Sorting / paging (`Sort`, `Pageable`)
6. `MongoTemplate` and operations interfaces
7. Manual bootstrap (standalone `MongoTemplate`, no Spring context)
8. Aggregation framework
9. MongoDB Java driver
10. Jackson 3 (serialization for harnesses)
11. Renamed / removed — do NOT use the left column

---

## 1. Mapping annotations — `org.springframework.data.mongodb.core.mapping`

```java
import org.springframework.data.mongodb.core.mapping.Document;          // class -> collection
import org.springframework.data.mongodb.core.mapping.Field;             // field -> document key (import by name; see note)
import org.springframework.data.mongodb.core.mapping.FieldType;         // explicit BSON type for @Field(targetType = ...)
import org.springframework.data.mongodb.core.mapping.MongoId;           // _id with explicit target type (alternative to @Id)
import org.springframework.data.mongodb.core.mapping.DocumentReference; // reference stored as target's _id (preferred ref)
import org.springframework.data.mongodb.core.mapping.DBRef;            // legacy {$ref,$id} reference
import org.springframework.data.mongodb.core.mapping.Sharded;          // sharded collection metadata
import org.springframework.data.mongodb.core.mapping.TimeSeries;       // time-series collection
```

> **`@Field` import note.** `org.springframework.data.mongodb.core.mapping.Field` clashes
> with `java.lang.reflect.Field`. Always import it explicitly by name, even if you
> wildcard the rest of `core.mapping`. The project snippets do exactly this:
> `import org.springframework.data.mongodb.core.mapping.*;` followed by
> `import org.springframework.data.mongodb.core.mapping.Field;`.

## 2. Identity & lifecycle — `org.springframework.data.annotation`

These are NOT in the mongodb package. This is the most common import mistake.

```java
import org.springframework.data.annotation.Id;                 // maps property to _id
import org.springframework.data.annotation.Transient;          // exclude from persistence
import org.springframework.data.annotation.ReadOnlyProperty;   // populated on read, never written
import org.springframework.data.annotation.PersistenceCreator; // chosen constructor for instantiation
import org.springframework.data.annotation.Version;            // optimistic locking
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.LastModifiedDate;
```

`@Id` (from `data.annotation`) is the idiomatic choice. Use `@MongoId` (from
`core.mapping`) only when you need to pin the BSON target type of `_id`.

## 3. Indexing — `org.springframework.data.mongodb.core.index`

```java
import org.springframework.data.mongodb.core.index.Indexed;
import org.springframework.data.mongodb.core.index.CompoundIndex;
import org.springframework.data.mongodb.core.index.CompoundIndexes;
import org.springframework.data.mongodb.core.index.TextIndexed;
import org.springframework.data.mongodb.core.index.GeoSpatialIndexed;
import org.springframework.data.mongodb.core.index.HashIndexed;
```

## 4. Query API — `org.springframework.data.mongodb.core.query`

```java
import org.springframework.data.mongodb.core.query.Query;     // Query, Query.query(...), new Query(criteria)
import org.springframework.data.mongodb.core.query.Criteria;  // Criteria.where(...), and/or/not operators
import org.springframework.data.mongodb.core.query.Update;    // Update.update(...), set/inc/push for writes
import org.springframework.data.mongodb.core.query.Collation; // case-insensitive / locale collation
import org.springframework.data.mongodb.core.query.BasicQuery;// raw JSON query string
```

Static-import convenience (optional, mirrors the official docs):

```java
import static org.springframework.data.mongodb.core.query.Criteria.where;
import static org.springframework.data.mongodb.core.query.Query.query;
import static org.springframework.data.mongodb.core.query.Update.update;
```

## 5. Sorting & paging — `org.springframework.data.domain`

```java
import org.springframework.data.domain.Sort;        // Sort.by(Sort.Direction.ASC, "field")
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.PageRequest;  // PageRequest.of(page, size, sort)
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Slice;
```

## 6. Template & operations — `org.springframework.data.mongodb.core`

```java
import org.springframework.data.mongodb.core.MongoTemplate;     // primary entry point
import org.springframework.data.mongodb.core.MongoOperations;   // interface MongoTemplate implements
import org.springframework.data.mongodb.core.ExecutableFindOperation; // fluent template().query(...) API
```

## 7. Manual bootstrap (standalone `MongoTemplate`)

Use this when wiring a `MongoTemplate` by hand (validation/translation harnesses) rather
than relying on Spring Boot autoconfiguration.

```java
import org.springframework.data.mongodb.MongoDatabaseFactory;                  // NOTE: ...mongodb, not ...mongodb.core
import org.springframework.data.mongodb.core.SimpleMongoClientDatabaseFactory; // current name (NOT ...DbFactory)
import org.springframework.data.mongodb.core.convert.MappingMongoConverter;
import org.springframework.data.mongodb.core.convert.DefaultDbRefResolver;
import org.springframework.data.mongodb.core.convert.DefaultMongoTypeMapper;
import org.springframework.data.mongodb.core.convert.MongoCustomConversions;
import org.springframework.data.mongodb.core.mapping.MongoMappingContext;
```

## 8. Aggregation — `org.springframework.data.mongodb.core.aggregation`

```java
import org.springframework.data.mongodb.core.aggregation.Aggregation;        // factory: newAggregation, group, project, match, sort, unwind, limit, count, lookup
import org.springframework.data.mongodb.core.aggregation.TypedAggregation;   // type-bound pipeline
import org.springframework.data.mongodb.core.aggregation.AggregationResults; // .getMappedResults(), .getUniqueMappedResult()
import org.springframework.data.mongodb.core.aggregation.AggregationOperation;
import org.springframework.data.mongodb.core.aggregation.GroupOperation;
import org.springframework.data.mongodb.core.aggregation.ProjectionOperation;
import org.springframework.data.mongodb.core.aggregation.MatchOperation;
```

Static-import convenience (recommended for readable pipelines, matches official docs):

```java
import static org.springframework.data.mongodb.core.aggregation.Aggregation.*;
// gives: newAggregation, group, project, match, sort, unwind, limit, skip, count, lookup, previousOperation, bind
import static org.springframework.data.domain.Sort.Direction.ASC;
import static org.springframework.data.domain.Sort.Direction.DESC;
```

## 9. MongoDB Java driver — `com.mongodb.client`

```java
import com.mongodb.client.MongoClients; // MongoClients.create(uri)
import com.mongodb.client.MongoClient;
```

## 10. Jackson 3 (only when a harness serializes results to JSON)

Jackson 3 moved **databind and core** to the `tools.jackson` namespace. Annotations did
**not** move — they remain under `com.fasterxml.jackson.annotation`.

```java
// databind / core — tools.jackson.*
import tools.jackson.databind.json.JsonMapper;
import tools.jackson.databind.SerializationFeature;
import tools.jackson.databind.MapperFeature;
import tools.jackson.databind.module.SimpleModule;
import tools.jackson.databind.ser.std.StdSerializer;
import tools.jackson.databind.SerializationContext;
import tools.jackson.core.JsonGenerator;
import tools.jackson.core.StreamWriteFeature;
import tools.jackson.databind.cfg.DateTimeFeature;

// annotations — still com.fasterxml.jackson.annotation
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonInclude.Include;
```

## 11. Renamed / removed — do NOT use the left column

| Wrong (old / hallucinated) | Correct (5.0) |
|---|---|
| `org.springframework.data.mongodb.MongoDbFactory` | `org.springframework.data.mongodb.MongoDatabaseFactory` |
| `SimpleMongoClientDbFactory` | `SimpleMongoClientDatabaseFactory` |
| `SimpleMongoDbFactory` (driver 3.x) | `SimpleMongoClientDatabaseFactory` |
| `com.fasterxml.jackson.databind.ObjectMapper` | `tools.jackson.databind.json.JsonMapper` (Jackson 3) |
| `com.fasterxml.jackson.databind.*` (databind) | `tools.jackson.databind.*` |
| `new com.mongodb.MongoClient(...)` (driver 3.x) | `com.mongodb.client.MongoClients.create(uri)` |
| `@org.springframework.data.mongodb.core.mapping.Id` | `@org.springframework.data.annotation.Id` |
| `java.util.Date` for date columns | `java.time.LocalDate` / `LocalDateTime` / `Instant` |
| `new Date(2014, 12, 20)` | `LocalDate.of(2014, 12, 20)` |
| `MongoTemplate#findAllAndRemove` confusions | use `find`, `findOne`, `count`, `exists` (see queries.md) |
