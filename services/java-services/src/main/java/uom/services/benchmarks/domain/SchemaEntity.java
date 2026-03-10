package uom.services.benchmarks.domain;

import org.springframework.data.neo4j.core.schema.Id;
import org.springframework.data.neo4j.core.schema.Node;
import org.springframework.data.neo4j.core.schema.Property;
import org.springframework.data.neo4j.core.schema.Relationship;

import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

@Node("Schema")
public class SchemaEntity {

    @Id
    private final String name;

    @Property("type")
    private final String type;

    @Relationship(type = "HAS_TABLE", direction = Relationship.Direction.OUTGOING)
    private final List<TableEntity> tables;

    public SchemaEntity(String name, String type) {
        this.name = Objects.requireNonNull(name, "Schema name cannot be null");
        this.type = type;
        this.tables = new ArrayList<>();
    }

    public String name() {
        return name;
    }

    public String type() {
        return type;
    }

    public List<TableEntity> tables() {
        return tables;
    }
}

@Node("Table")
class TableEntity {
    @Id
    private final String tableName;

    public TableEntity(String tableName) {
        this.tableName = tableName;
    }

    public String tableName() {
        return tableName;
    }
}
