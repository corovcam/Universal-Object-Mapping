package uom.services.benchmarks.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.mongodb.core.query.Query;
import org.springframework.data.neo4j.core.Neo4jTemplate;
import org.springframework.stereotype.Service;
import uom.services.benchmarks.dto.CompilationResult;
import uom.services.benchmarks.dto.CompilationResult.CompilationError;

import java.io.IOException;
import java.net.URL;
import java.net.URLClassLoader;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.stream.Stream;

/**
 * Validates compiled Java entity classes against live databases.
 * <p>
 * After compilation, this service:
 * <ol>
 *   <li>Loads all compiled classes from the output directory using a {@link URLClassLoader}</li>
 *   <li>Identifies root entity classes (annotated with {@code @Document} or {@code @Node})</li>
 *   <li>Runs a sample {@code LIMIT 1} query for each root entity against the live database</li>
 *   <li>Returns validation errors if the mapping is invalid (Spring Data throws {@code MappingException})</li>
 * </ol>
 */
@Service
public class ValidationService {

    private static final Logger log = LoggerFactory.getLogger(ValidationService.class);

    private final Neo4jTemplate neo4jTemplate;
    private final MongoTemplate mongoTemplate;

    public ValidationService(Neo4jTemplate neo4jTemplate, MongoTemplate mongoTemplate) {
        this.neo4jTemplate = neo4jTemplate;
        this.mongoTemplate = mongoTemplate;
    }

    /**
     * Validates compiled entity classes against the live database.
     *
     * @param classesDir the directory containing compiled .class files
     * @param framework  the target framework ("spring-data-neo4j" or "spring-data-mongodb")
     * @return the validation result
     */
    public CompilationResult validate(Path classesDir, String framework) {
        if (classesDir == null || !Files.isDirectory(classesDir)) {
            return CompilationResult.failure(
                    "No compiled classes directory available for validation.",
                    List.of(new CompilationError("NO_CLASSES", "Classes directory is null or does not exist.", -1, -1, null))
            );
        }

        List<Class<?>> loadedClasses;
        URLClassLoader classLoader;
        try {
            classLoader = new URLClassLoader(
                    new URL[]{classesDir.toUri().toURL()},
                    Thread.currentThread().getContextClassLoader() // Parent: Spring Boot classloader
            );
            loadedClasses = loadClassesFromDir(classesDir, classLoader);
        } catch (IOException e) {
            log.error("Failed to create classloader for {}", classesDir, e);
            return CompilationResult.failure(
                    "Failed to load compiled classes: " + e.getMessage(),
                    List.of(new CompilationError("CLASSLOAD_ERROR", e.getMessage(), -1, -1, null))
            );
        }

        if (loadedClasses.isEmpty()) {
            return CompilationResult.failure(
                    "No classes found in compilation output.",
                    List.of(new CompilationError("NO_CLASSES", "No .class files found in " + classesDir, -1, -1, null))
            );
        }

        log.info("Loaded {} class(es) for validation: {}", loadedClasses.size(),
                loadedClasses.stream().map(Class::getSimpleName).toList());

        // Identify root entity classes based on framework-specific annotations
        List<Class<?>> rootEntities = identifyRootEntities(loadedClasses, framework);

        if (rootEntities.isEmpty()) {
            List<String> warnings = List.of(
                    "No root entity annotations found (@Document or @Node). " +
                    "Compilation succeeded but schema validation was skipped."
            );
            return CompilationResult.success(
                    "Compilation successful. No root entities to validate (all classes may be embedded value objects).",
                    warnings
            );
        }

        log.info("Identified {} root entit(ies) to validate: {}", rootEntities.size(),
                rootEntities.stream().map(Class::getSimpleName).toList());

        // Validate each root entity by running a sample query
        List<CompilationError> errors = new ArrayList<>();
        List<String> warnings = new ArrayList<>();
        int validatedCount = 0;

        for (Class<?> entityClass : rootEntities) {
            try {
                validateEntity(entityClass, framework);
                validatedCount++;
                log.info("Validation passed for entity: {}", entityClass.getSimpleName());
            } catch (Exception e) {
                log.warn("Validation failed for entity: {}", entityClass.getSimpleName(), e);
                errors.add(new CompilationError(
                        "VALIDATION_ERROR",
                        String.format("Entity '%s': %s", entityClass.getSimpleName(), extractRootCause(e)),
                        -1, -1,
                        entityClass.getSimpleName() + ".java"
                ));
            }
        }

        if (errors.isEmpty()) {
            String msg = String.format(
                    "Validation passed. %d root entit(ies) validated against %s.",
                    validatedCount, framework
            );
            return CompilationResult.success(msg, warnings);
        } else {
            String msg = String.format(
                    "Validation failed for %d of %d root entit(ies).",
                    errors.size(), rootEntities.size()
            );
            return CompilationResult.failure(msg, errors, warnings);
        }
    }

    /**
     * Loads all .class files from a directory into classes.
     */
    private List<Class<?>> loadClassesFromDir(Path classesDir, URLClassLoader classLoader) throws IOException {
        List<Class<?>> classes = new ArrayList<>();
        try (Stream<Path> paths = Files.walk(classesDir)) {
            List<Path> classFiles = paths
                    .filter(p -> p.toString().endsWith(".class"))
                    .toList();

            for (Path classFile : classFiles) {
                // Convert file path to class name: /dir/com/example/Foo.class -> com.example.Foo
                Path relative = classesDir.relativize(classFile);
                String className = relative.toString()
                        .replace('/', '.')
                        .replace('\\', '.')
                        .replaceAll("\\.class$", "");

                try {
                    Class<?> loaded = classLoader.loadClass(className);
                    classes.add(loaded);
                    log.debug("Loaded class: {}", className);
                } catch (ClassNotFoundException | NoClassDefFoundError e) {
                    log.warn("Could not load class {}: {}", className, e.getMessage());
                }
            }
        }
        return classes;
    }

    /**
     * Identifies root entity classes from loaded classes based on framework annotations.
     */
    private List<Class<?>> identifyRootEntities(List<Class<?>> classes, String framework) {
        List<Class<?>> rootEntities = new ArrayList<>();
        for (Class<?> clazz : classes) {
            if (isRootEntity(clazz, framework)) {
                rootEntities.add(clazz);
            }
        }
        return rootEntities;
    }

    /**
     * Checks if a class is a root entity for the given framework.
     */
    private boolean isRootEntity(Class<?> clazz, String framework) {
        return switch (framework.toLowerCase()) {
            case "spring-data-mongodb" -> hasAnnotation(clazz, "org.springframework.data.mongodb.core.mapping.Document");
            case "spring-data-neo4j" -> hasAnnotation(clazz, "org.springframework.data.neo4j.core.schema.Node");
            default -> {
                // Check both
                yield hasAnnotation(clazz, "org.springframework.data.mongodb.core.mapping.Document")
                        || hasAnnotation(clazz, "org.springframework.data.neo4j.core.schema.Node");
            }
        };
    }

    /**
     * Checks if a class has an annotation by its fully qualified name.
     * Uses name comparison to handle classloader boundaries.
     */
    private boolean hasAnnotation(Class<?> clazz, String annotationFqn) {
        for (var annotation : clazz.getAnnotations()) {
            if (annotation.annotationType().getName().equals(annotationFqn)) {
                return true;
            }
        }
        return false;
    }

    /**
     * Validates a single entity class by running a sample query against the database.
     */
    private void validateEntity(Class<?> entityClass, String framework) {
        switch (framework.toLowerCase()) {
            case "spring-data-mongodb" -> validateMongoEntity(entityClass);
            case "spring-data-neo4j" -> validateNeo4jEntity(entityClass);
            default -> {
                // Try to detect from annotations
                if (hasAnnotation(entityClass, "org.springframework.data.mongodb.core.mapping.Document")) {
                    validateMongoEntity(entityClass);
                } else if (hasAnnotation(entityClass, "org.springframework.data.neo4j.core.schema.Node")) {
                    validateNeo4jEntity(entityClass);
                } else {
                    log.warn("Cannot determine framework for entity: {}", entityClass.getSimpleName());
                }
            }
        }
    }

    /**
     * Validates a MongoDB entity by running {@code mongoTemplate.find(query, entityClass)}
     * with a limit of 1. If the mapping is invalid, Spring Data MongoDB will throw.
     */
    private void validateMongoEntity(Class<?> entityClass) {
        log.info("Validating MongoDB entity: {}", entityClass.getSimpleName());
        Query query = new Query().limit(1);
        // This will throw MappingException or similar if the entity mapping is invalid
        // or if the collection doesn't exist / has incompatible data
        mongoTemplate.find(query, entityClass);
    }

    /**
     * Validates a Neo4j entity by running {@code neo4jTemplate.findAll(entityClass)}
     * which translates to a MATCH query. If the mapping is invalid, Spring Data Neo4j
     * will throw a MappingException.
     * <p>
     * Note: Neo4jTemplate doesn't natively support LIMIT in findAll, so we use
     * findAll and accept that it may return more results. For validation purposes,
     * even one record returning without error is sufficient.
     */
    private void validateNeo4jEntity(Class<?> entityClass) {
        log.info("Validating Neo4j entity: {}", entityClass.getSimpleName());
        // findAll will execute MATCH (n:Label) RETURN n
        // If the mapping is invalid, this throws MappingException
        neo4jTemplate.findAll(entityClass);
    }

    /**
     * Extracts the root cause message from a nested exception chain.
     */
    private String extractRootCause(Throwable t) {
        Throwable root = t;
        while (root.getCause() != null && root.getCause() != root) {
            root = root.getCause();
        }
        String msg = root.getMessage();
        if (msg == null || msg.isBlank()) {
            msg = root.getClass().getSimpleName();
        }
        // Include the direct exception type for context
        if (root != t) {
            return String.format("%s (caused by %s: %s)", t.getMessage(), root.getClass().getSimpleName(), msg);
        }
        return msg;
    }
}
