package uom.services.benchmarks.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.env.Environment;
import org.springframework.stereotype.Service;
import uom.services.benchmarks.dto.CompilationResult;
import uom.services.benchmarks.dto.CompilationResult.CompilationError;

import javax.tools.*;
import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Stream;

/**
 * Compiles Java source code dynamically using {@link javax.tools.JavaCompiler}.
 * <p>
 * The source code may contain multiple classes in a single file (root entities
 * annotated with {@code @Document}/{@code @Node} plus embedded value objects).
 * The classpath includes all Spring Data dependencies from the running application.
 */
@Service
public class CompilationService {
    @Autowired
    private Environment environment;

    private static final Logger log = LoggerFactory.getLogger(CompilationService.class);

    /**
     * Pattern to extract a public class name (determines the .java filename).
     * Handles annotations preceding the class declaration on the same line,
     * e.g. {@code @Document(collection="orders") public class Order}.
     * Falls back to any top-level class if no public class is found.
     */
    private static final Pattern PUBLIC_CLASS_PATTERN =
            Pattern.compile("\\bpublic\\s+(?:class|record|enum|interface)\\s+(\\w+)");
    private static final Pattern ANY_CLASS_PATTERN =
            Pattern.compile("(?:^|\\s)(?:class|record|enum|interface)\\s+(\\w+)", Pattern.MULTILINE);

    private final Path sandboxDir;

    public CompilationService(@Value("${compilation.sandbox.dir:/app/sandbox}") String sandboxDir) {
        this.sandboxDir = Path.of(sandboxDir);
    }

    /**
     * Compiles and returns both the result and the output directory path.
     *
     * @param sourceCode the Java source code
     * @return a record containing the result and the output directory
     */
    public CompileOutput compileWithOutput(String sourceCode) {
        JavaCompiler compiler = ToolProvider.getSystemJavaCompiler();
        if (compiler == null) {
            return new CompileOutput(
                    CompilationResult.failure(
                            "No Java compiler available. Ensure the JDK (not JRE) is installed.",
                            List.of(new CompilationError("NO_COMPILER", "javax.tools.JavaCompiler not found", -1, -1, null))
                    ),
                    null
            );
        }

        Path outputDir = null;
        try {
            // Prepare sandbox directories
            Files.createDirectories(sandboxDir);
            outputDir = Files.createTempDirectory(sandboxDir, "compile-");
            Path srcDir = outputDir.resolve("src");
            Files.createDirectories(srcDir);
            Path classesDir = outputDir.resolve("classes");
            Files.createDirectories(classesDir);

            // Determine filename from source code
            String fileName = extractFileName(sourceCode);
            Path sourceFile = srcDir.resolve(fileName);
            Files.writeString(sourceFile, sourceCode);

            log.info("Compiling {} ({} bytes) in {}", fileName, sourceCode.length(), outputDir);

            // Build classpath
            String classpath = buildClasspath();

            // Compile
            DiagnosticCollector<JavaFileObject> diagnostics = new DiagnosticCollector<>();
            try (StandardJavaFileManager fileManager = compiler.getStandardFileManager(diagnostics, null, null)) {
                Iterable<? extends JavaFileObject> compilationUnits =
                        fileManager.getJavaFileObjects(sourceFile.toFile());

                List<String> options = new ArrayList<>();
                options.addAll(List.of("-classpath", classpath));
                options.addAll(List.of("-d", classesDir.toString()));
                options.add("-Xlint:all");

                JavaCompiler.CompilationTask task =
                        compiler.getTask(null, fileManager, diagnostics, options, null, compilationUnits);

                boolean success = task.call();

                List<CompilationError> errors = new ArrayList<>();
                List<String> warnings = new ArrayList<>();

                for (Diagnostic<? extends JavaFileObject> diag : diagnostics.getDiagnostics()) {
                    String source = diag.getSource() != null ? diag.getSource().getName() : null;
                    if (diag.getKind() == Diagnostic.Kind.ERROR) {
                        errors.add(new CompilationError(
                                diag.getCode(),
                                diag.getMessage(null),
                                diag.getLineNumber(),
                                diag.getColumnNumber(),
                                source
                        ));
                    } else if (diag.getKind() == Diagnostic.Kind.WARNING
                            || diag.getKind() == Diagnostic.Kind.MANDATORY_WARNING) {
                        warnings.add(String.format("Line %d: %s", diag.getLineNumber(), diag.getMessage(null)));
                    }
                }

                if (success) {
                    String msg = String.format("Compilation successful. %d class(es) compiled.", countClassFiles(classesDir));
                    log.info(msg);
                    return new CompileOutput(CompilationResult.success(msg, warnings), classesDir);
                } else {
                    String msg = String.format("Compilation failed with %d error(s).", errors.size());
                    log.warn(msg);
                    // Clean up on failure
                    if (!environment.matchesProfiles("development")) {
                        cleanupDirectory(outputDir);
                    }
                    return new CompileOutput(CompilationResult.failure(msg, errors, warnings), null);
                }
            }
        } catch (IOException e) {
            log.error("IO error during compilation", e);
            if (outputDir != null && !environment.matchesProfiles("development")) {
                cleanupDirectory(outputDir);
            }
            return new CompileOutput(
                    CompilationResult.failure(
                            "IO error: " + e.getMessage(),
                            List.of(new CompilationError("IO_ERROR", e.getMessage(), -1, -1, null))
                    ),
                    null
            );
        }
    }

    /**
     * Extracts the primary class name to determine the .java filename.
     * Prefers a public class; falls back to the first top-level class.
     */
    String extractFileName(String sourceCode) {
        Matcher publicMatcher = PUBLIC_CLASS_PATTERN.matcher(sourceCode);
        if (publicMatcher.find()) {
            return publicMatcher.group(1) + ".java";
        }

        Matcher anyMatcher = ANY_CLASS_PATTERN.matcher(sourceCode);
        if (anyMatcher.find()) {
            return anyMatcher.group(1) + ".java";
        }

        // Fallback
        return "GeneratedCode.java";
    }

    /**
     * Builds the classpath string for the dynamic compiler.
     * <p>
     * When running under {@code mvn spring-boot:run}, the {@code java.class.path}
     * system property only contains the Maven launcher jar. The actual application
     * classes and dependencies are loaded by a custom classloader. We need to
     * reconstruct the full classpath by scanning known locations.
     */
    String buildClasspath() {
        List<String> paths = new ArrayList<>();

        // 1. Application's own compiled classes
        Path appClasses = Path.of("/app/target/classes");
        if (Files.isDirectory(appClasses)) {
            paths.add(appClasses.toString());
        }

        // 2. Maven local repository jars (used by mvn spring-boot:run)
        //    Spring Boot Maven plugin resolves deps to ~/.m2/repository
        Path m2Repo = Path.of(System.getProperty("user.home", "/root"), ".m2", "repository");
        if (Files.isDirectory(m2Repo)) {
            try (Stream<Path> jars = Files.walk(m2Repo)) {
                jars.filter(p -> p.toString().endsWith(".jar"))
                        .forEach(p -> paths.add(p.toString()));
            } catch (IOException e) {
                log.warn("Failed to scan Maven local repository at {}", m2Repo, e);
            }
        }

        // 3. Also try any copied dependency jars in target/dependency/
        Path depsDir = Path.of("/app/target/dependency");
        if (Files.isDirectory(depsDir)) {
            try (Stream<Path> jars = Files.walk(depsDir)) {
                jars.filter(p -> p.toString().endsWith(".jar"))
                        .forEach(p -> paths.add(p.toString()));
            } catch (IOException e) {
                log.warn("Failed to scan dependency directory", e);
            }
        }

        // 4. Fallback: if we found nothing above, try java.class.path
        if (paths.isEmpty()) {
            String runtimeClasspath = System.getProperty("java.class.path");
            if (runtimeClasspath != null && !runtimeClasspath.isBlank()) {
                log.info("Using runtime java.class.path as fallback ({} chars)", runtimeClasspath.length());
                return runtimeClasspath;
            }
        }

        String classpath = String.join(File.pathSeparator, paths);
        log.info("Built classpath with {} entries ({} chars)", paths.size(), classpath.length());
        return classpath;
    }

    private long countClassFiles(Path classesDir) {
        try (Stream<Path> files = Files.walk(classesDir)) {
            return files.filter(p -> p.toString().endsWith(".class")).count();
        } catch (IOException e) {
            return 0;
        }
    }

    /**
     * Cleans up a temporary directory and all its contents.
     */
    public void cleanupDirectory(Path dir) {
        if (dir == null || !Files.exists(dir)) return;
        try (Stream<Path> paths = Files.walk(dir)) {
            paths.sorted(Comparator.reverseOrder())
                    .forEach(p -> {
                        try {
                            Files.deleteIfExists(p);
                        } catch (IOException e) {
                            log.warn("Failed to delete {}", p, e);
                        }
                    });
        } catch (IOException e) {
            log.warn("Failed to clean up directory {}", dir, e);
        }
    }

    /**
     * Result of a compilation that includes the path to compiled classes.
     *
     * @param result     the compilation result
     * @param classesDir path to the directory containing compiled .class files (null on failure)
     */
    public record CompileOutput(CompilationResult result, Path classesDir) {}
}
