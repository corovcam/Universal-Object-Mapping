package uom.services.benchmarks.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.env.Environment;
import org.springframework.stereotype.Service;
import uom.services.benchmarks.dto.CompilationResult;
import uom.services.benchmarks.dto.CompilationResult.CompilationError;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.TimeUnit;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Maven-based fallback compilation service.
 * <p>
 * Copies source code into a sandbox Maven project and runs {@code mvn compile}.
 * This catches dependency resolution issues that {@code javax.tools.JavaCompiler}
 * might miss, but is slower (~10-20s vs ~1-2s).
 */
@Service
public class MavenCompilationService {
    @Autowired
    private Environment environment;

    private static final Logger log = LoggerFactory.getLogger(MavenCompilationService.class);

    /**
     * Maven compiler error pattern: {@code [ERROR] /path/File.java:[line,col] error: message}
     */
    private static final Pattern MAVEN_ERROR_PATTERN =
            Pattern.compile("\\[ERROR]\\s+.*?([\\w.]+\\.java):\\[(\\d+),(\\d+)]\\s*(.+)");

    /**
     * Alternate Maven error pattern: {@code [ERROR] /path/File.java:line: error: message}
     */
    private static final Pattern MAVEN_ERROR_PATTERN_ALT =
            Pattern.compile("\\[ERROR]\\s+.*?([\\w.]+\\.java):(\\d+):\\s*(?:error:\\s*)?(.+)");

    private final Path sandboxDir;
    private final Path sandboxPomPath;
    private final int timeoutSeconds;
    private final CompilationService compilationService;

    public MavenCompilationService(
            @Value("${compilation.sandbox.dir:/app/sandbox}") String sandboxDir,
            @Value("${compilation.timeout-seconds:30}") int timeoutSeconds,
            CompilationService compilationService
    ) {
        this.sandboxDir = Path.of(sandboxDir);
        this.sandboxPomPath = Path.of("/app/sandbox-pom.xml");
        this.timeoutSeconds = timeoutSeconds;
        this.compilationService = compilationService;
    }

    /**
     * Compiles source code using Maven as a fallback.
     *
     * @param sourceCode the Java source code
     * @return the compilation result
     */
    public CompilationService.CompileOutput compileWithMaven(String sourceCode) {
        Path projectDir = null;
        try {
            // Create sandbox Maven project structure
            Files.createDirectories(sandboxDir);
            projectDir = Files.createTempDirectory(sandboxDir, "maven-");
            Path srcDir = projectDir.resolve("src/main/java/sandbox");
            Files.createDirectories(srcDir);
            Path classesDir = projectDir.resolve("target/classes");

            // Write pom.xml
            Path pomDest = projectDir.resolve("pom.xml");
            if (Files.exists(sandboxPomPath)) {
                Files.copy(sandboxPomPath, pomDest);
            } else {
                Files.writeString(pomDest, generateSandboxPom());
            }

            // Write source file
            String fileName = compilationService.extractFileName(sourceCode);

            // Prepend package declaration if not present
            String codeWithPackage = sourceCode;
            if (!sourceCode.contains("package ")) {
                codeWithPackage = "package sandbox;\n\n" + sourceCode;
            }

            Path sourceFile = srcDir.resolve(fileName);
            Files.writeString(sourceFile, codeWithPackage);

            log.info("Maven compiling {} in {}", fileName, projectDir);

            // Run mvn compile
            ProcessBuilder pb = new ProcessBuilder(
                    "mvn", "compile",
                    "-f", "pom.xml",
                    "-q", // quiet mode to reduce output noise
                    "--batch-mode",
                    "--no-transfer-progress"
            );
            pb.directory(projectDir.toFile());
            pb.redirectErrorStream(true);

            Process process = pb.start();
            List<String> outputLines = new ArrayList<>();
            try (BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()))) {
                String line;
                while ((line = reader.readLine()) != null) {
                    outputLines.add(line);
                }
            }

            boolean finished = process.waitFor(timeoutSeconds, TimeUnit.SECONDS);
            if (!finished) {
                process.destroyForcibly();
                if (!environment.matchesProfiles("development")) {
                    compilationService.cleanupDirectory(projectDir);
                }
                return new CompilationService.CompileOutput(
                        CompilationResult.failure(
                                "Maven compilation timed out after " + timeoutSeconds + " seconds.",
                                List.of(new CompilationError("TIMEOUT", "Maven process timed out", -1, -1, null))
                        ),
                        null
                );
            }

            int exitCode = process.exitValue();
            if (exitCode == 0) {
                String msg = "Maven compilation successful.";
                log.info(msg);
                return new CompilationService.CompileOutput(
                        CompilationResult.success(msg),
                        classesDir
                );
            } else {
                // Parse Maven error output
                List<CompilationError> errors = parseMavenErrors(outputLines);
                if (errors.isEmpty()) {
                    // If we couldn't parse structured errors, return raw output
                    String rawOutput = String.join("\n", outputLines);
                    errors.add(new CompilationError(
                            "MAVEN_ERROR",
                            rawOutput.length() > 2000 ? rawOutput.substring(0, 2000) + "..." : rawOutput,
                            -1, -1, null
                    ));
                }

                String msg = String.format("Maven compilation failed with %d error(s).", errors.size());
                log.warn(msg);
                if (!environment.matchesProfiles("development")) {
                    compilationService.cleanupDirectory(projectDir);
                }
                return new CompilationService.CompileOutput(
                        CompilationResult.failure(msg, errors),
                        null
                );
            }
        } catch (IOException e) {
            log.error("IO error during Maven compilation", e);
            if (projectDir != null && !environment.matchesProfiles("development"))
                compilationService.cleanupDirectory(projectDir);
            return new CompilationService.CompileOutput(
                    CompilationResult.failure(
                            "IO error: " + e.getMessage(),
                            List.of(new CompilationError("IO_ERROR", e.getMessage(), -1, -1, null))
                    ),
                    null
            );
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            if (projectDir != null && !environment.matchesProfiles("development"))
                compilationService.cleanupDirectory(projectDir);
            return new CompilationService.CompileOutput(
                    CompilationResult.failure(
                            "Maven compilation interrupted.",
                            List.of(new CompilationError("INTERRUPTED", e.getMessage(), -1, -1, null))
                    ),
                    null
            );
        }
    }

    /**
     * Parses Maven compiler output to extract structured errors.
     */
    private List<CompilationError> parseMavenErrors(List<String> outputLines) {
        List<CompilationError> errors = new ArrayList<>();
        for (String line : outputLines) {
            if (!line.contains("[ERROR]")) continue;

            Matcher m = MAVEN_ERROR_PATTERN.matcher(line);
            if (m.find()) {
                errors.add(new CompilationError(
                        "MAVEN_COMPILE_ERROR",
                        m.group(4).trim(),
                        Long.parseLong(m.group(2)),
                        Long.parseLong(m.group(3)),
                        m.group(1)
                ));
                continue;
            }

            Matcher mAlt = MAVEN_ERROR_PATTERN_ALT.matcher(line);
            if (mAlt.find()) {
                errors.add(new CompilationError(
                        "MAVEN_COMPILE_ERROR",
                        mAlt.group(3).trim(),
                        Long.parseLong(mAlt.group(2)),
                        -1,
                        mAlt.group(1)
                ));
            }
        }
        return errors;
    }

    /**
     * Generates a minimal sandbox pom.xml with Spring Data dependencies.
     */
    private String generateSandboxPom() {
        return """
                <?xml version="1.0" encoding="UTF-8"?>
                <project xmlns="http://maven.apache.org/POM/4.0.0"
                         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
                    <modelVersion>4.0.0</modelVersion>
                    <groupId>uom.sandbox</groupId>
                    <artifactId>sandbox</artifactId>
                    <version>1.0.0</version>
                    <properties>
                        <java.version>25</java.version>
                        <maven.compiler.source>25</maven.compiler.source>
                        <maven.compiler.target>25</maven.compiler.target>
                    </properties>
                    <dependencies>
                        <dependency>
                            <groupId>org.springframework.boot</groupId>
                            <artifactId>spring-boot-starter-data-mongodb</artifactId>
                            <version>4.0.3</version>
                        </dependency>
                        <dependency>
                            <groupId>org.springframework.boot</groupId>
                            <artifactId>spring-boot-starter-data-neo4j</artifactId>
                            <version>4.0.3</version>
                        </dependency>
                    </dependencies>
                </project>
                """;
    }
}
