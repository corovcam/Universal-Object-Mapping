package uom.services.benchmarks.dto;

import java.util.List;

/**
 * Response DTO for the Java compilation and validation endpoints.
 *
 * @param success  whether compilation (and optional validation) succeeded
 * @param message  human-readable summary
 * @param errors   structured list of compilation or validation errors
 * @param warnings any non-fatal warnings (e.g., schema mismatches that didn't prevent compilation)
 */
public record CompilationResult(
    boolean success,
    String message,
    List<CompilationError> errors,
    List<String> warnings
) {

    /**
     * A single compilation or validation error with location information.
     *
     * @param code       the compiler error code (e.g., "compiler.err.cant.resolve") or "VALIDATION_ERROR"
     * @param message    the error message
     * @param lineNumber the 1-based line number where the error occurred (-1 if unknown)
     * @param columnNumber the 1-based column number (-1 if unknown)
     * @param sourceFile the source file name (if available)
     */
    public record CompilationError(
        String code,
        String message,
        long lineNumber,
        long columnNumber,
        String sourceFile
    ) {}

    public static CompilationResult success(String message) {
        return new CompilationResult(true, message, List.of(), List.of());
    }

    public static CompilationResult success(String message, List<String> warnings) {
        return new CompilationResult(true, message, List.of(), warnings);
    }

    public static CompilationResult failure(String message, List<CompilationError> errors) {
        return new CompilationResult(false, message, errors, List.of());
    }

    public static CompilationResult failure(String message, List<CompilationError> errors, List<String> warnings) {
        return new CompilationResult(false, message, errors, warnings);
    }
}
