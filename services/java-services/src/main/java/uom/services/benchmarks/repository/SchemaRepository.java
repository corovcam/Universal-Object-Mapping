package uom.services.benchmarks.repository;

import org.springframework.data.neo4j.repository.Neo4jRepository;
import org.springframework.data.neo4j.repository.query.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;
import uom.services.benchmarks.domain.SchemaEntity;

import java.util.List;
import java.util.Optional;

@Repository
public interface SchemaRepository extends Neo4jRepository<SchemaEntity, String> {

    Optional<SchemaEntity> findOneByName(String name);

    @Query("MATCH (s:Schema)-[:HAS_TABLE]->(t:Table) " +
           "WHERE s.type = $type " +
           "RETURN s LIMIT 10")
    List<SchemaEntity> findSchemasByTypeWithCustomQuery(@Param("type") String type);
}
