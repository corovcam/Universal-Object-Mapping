package uom.services.benchmarks.dto;

/**
 * Request DTO for the Java compilation and validation endpoints.
 *
 * @param sourceCode the Java source code to compile (may contain multiple classes in one file)
 * @param framework  the target Spring Data framework: "spring-data-neo4j" or "spring-data-mongodb"
 * @param validate   if true, also validate entity mapping against the live database after compilation
 */
public record CompileRequest(
    String sourceCode,
    String framework,
    boolean validate
) {}
