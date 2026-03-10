package uom.services.benchmarks.controller;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import uom.services.benchmarks.domain.SchemaEntity;
import uom.services.benchmarks.repository.SchemaRepository;

import java.util.List;

@RestController
@RequestMapping("/api/schemas")
public class SchemaController {

    private static final Logger log = LoggerFactory.getLogger(SchemaController.class);
    private final SchemaRepository schemaRepository;

    public SchemaController(SchemaRepository schemaRepository) {
        this.schemaRepository = schemaRepository;
    }

    @GetMapping("/{name}")
    public ResponseEntity<SchemaEntity> getSchema(@PathVariable String name) {
        log.info("fetch_schema name={}", name);
        return schemaRepository.findOneByName(name)
                .map(ResponseEntity::ok)
                .orElseGet(() -> {
                    log.warn("schema_not_found name={}", name);
                    return ResponseEntity.notFound().build();
                });
    }

    @GetMapping("/type/{type}")
    public ResponseEntity<List<SchemaEntity>> getSchemasByType(@PathVariable String type) {
        log.info("fetch_schemas_by_type type={}", type);
        List<SchemaEntity> schemas = schemaRepository.findSchemasByTypeWithCustomQuery(type);
        return ResponseEntity.ok(schemas);
    }
}
