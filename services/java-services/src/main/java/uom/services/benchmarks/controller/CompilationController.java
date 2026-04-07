package uom.services.benchmarks.controller;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.env.Environment;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import uom.services.benchmarks.dto.CompileRequest;
import uom.services.benchmarks.dto.CompilationResult;
import uom.services.benchmarks.service.CompilationService;
import uom.services.benchmarks.service.CompilationService.CompileOutput;
import uom.services.benchmarks.service.MavenCompilationService;
import uom.services.benchmarks.service.ValidationService;

import java.nio.file.Path;

/**
 * REST controller for compiling and validating dynamically generated Java source code.
 * <p>
 * Provides two compilation strategies:
 * <ul>
 *   <li>{@code POST /api/compiler/compile} — Fast compilation via {@code javax.tools.JavaCompiler}</li>
 *   <li>{@code POST /api/compiler/maven-compile} — Full Maven compilation as fallback</li>
 * </ul>
 * Both endpoints optionally validate the compiled entity mapping against live databases
 * (Neo4j, MongoDB) by running sample queries.
 */
@RestController
@RequestMapping("/api/compiler")
public class CompilationController {
    @Autowired
    private Environment environment;

    private static final Logger log = LoggerFactory.getLogger(CompilationController.class);

    private final CompilationService compilationService;
    private final MavenCompilationService mavenCompilationService;
    private final ValidationService validationService;

    public CompilationController(
            CompilationService compilationService,
            MavenCompilationService mavenCompilationService,
            ValidationService validationService
    ) {
        this.compilationService = compilationService;
        this.mavenCompilationService = mavenCompilationService;
        this.validationService = validationService;
    }

    /**
     * Compiles Java source code using {@code javax.tools.JavaCompiler} with the full
     * Spring Data classpath. Optionally validates entity mapping against live databases.
     *
     * @param request the compile request containing source code, framework hint, and validate flag
     * @return 200 with success result, or 400 with structured errors
     */
    @PostMapping("/compile")
    public ResponseEntity<CompilationResult> compile(@RequestBody CompileRequest request) {
        log.info("Received compile request: framework={}, validate={}, sourceLength={}",
                request.framework(), request.validate(), request.sourceCode().length());

        CompileOutput output = compilationService.compileWithOutput(request.sourceCode());
        return handleCompileOutput(output, request);
    }

    /**
     * Compiles Java source code using Maven ({@code mvn compile}) as a fallback strategy.
     * Slower but catches dependency resolution issues that javac might miss.
     *
     * @param request the compile request
     * @return 200 with success result, or 400 with structured errors
     */
    @PostMapping("/maven-compile")
    public ResponseEntity<CompilationResult> mavenCompile(@RequestBody CompileRequest request) {
        log.info("Received Maven compile request: framework={}, validate={}, sourceLength={}",
                request.framework(), request.validate(), request.sourceCode().length());

        CompileOutput output = mavenCompilationService.compileWithMaven(request.sourceCode());
        return handleCompileOutput(output, request);
    }

    /**
     * Common handler for compilation output: if compilation succeeded and validation
     * is requested, runs schema validation against the database. Then cleans up.
     */
    private ResponseEntity<CompilationResult> handleCompileOutput(CompileOutput output, CompileRequest request) {
        CompilationResult result = output.result();
        Path classesDir = output.classesDir();

        try {
            // If compilation failed, return immediately
            if (!result.success()) {
                log.info("Compilation failed, returning errors.");
                return ResponseEntity.badRequest().body(result);
            }

            // If validation is not requested, return compilation success
            if (!request.validate()) {
                log.info("Compilation succeeded, validation not requested.");
                return ResponseEntity.ok(result);
            }

            // Validation requested: load compiled classes and run sample queries
            log.info("Compilation succeeded, running validation against {} ...", request.framework());
            CompilationResult validationResult = validationService.validate(classesDir, request.framework());

            if (validationResult.success()) {
                // Merge compilation warnings with validation result
                var allWarnings = new java.util.ArrayList<>(result.warnings());
                allWarnings.addAll(validationResult.warnings());
                return ResponseEntity.ok(CompilationResult.success(
                        result.message() + " " + validationResult.message(),
                        allWarnings
                ));
            } else {
                // Validation failed — return as 400 with both compilation and validation info
                var allWarnings = new java.util.ArrayList<>(result.warnings());
                allWarnings.addAll(validationResult.warnings());
                return ResponseEntity.badRequest().body(CompilationResult.failure(
                        "Compilation succeeded but validation failed: " + validationResult.message(),
                        validationResult.errors(),
                        allWarnings
                ));
            }
        } finally {
            // Always clean up the compilation output directory in production
            if (classesDir != null && !environment.matchesProfiles("development")) {
                // classesDir is inside the temp compile dir (e.g., /app/sandbox/compile-xxx/classes)
                // We want to clean up the parent temp dir
                Path tempDir = classesDir.getParent();
                compilationService.cleanupDirectory(tempDir);
            }
        }
    }
}
