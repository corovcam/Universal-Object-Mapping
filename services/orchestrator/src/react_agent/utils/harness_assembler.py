"""Deterministic assembly of validation harness code from canonical snippets.

The new e-INFRA sglang models reliably mis-reproduce the *invariant* harness boilerplate — the
imports, the byte-stable JSON serializer, the runtime-support / template-factory classes — which
produces total compile failures (`CS0246`, `cannot find symbol`) and, when the serializer drifts,
silent DeepDiff mismatches in the equivalence check. None of that boilerplate is dataset-specific.

This module turns the snippets in ``src/context/snippets/`` from *examples to imitate* into a
*fixed prelude to inject*. The model only authors the genuinely variable code (entity classes,
query classes, and the entrypoint ``main`` that drives them); we prepend the canonical, verbatim
prelude (imports + serializer + runtime support + template factory) so those symbols are always
present and byte-identical to the contract the Daytona sandboxes + DeepDiff checker depend on.

Design (see plan "Option A"): inject the prelude verbatim, let the model own everything below the
``// --- Schema and Related Settings ---`` seam. The only failures this can introduce are
duplicate declarations (the model re-emits imports / redeclares an invariant class) — guarded by
:func:`_strip_model_body` — and an occasional ``main``/query bug on a novel dataset, which is
exactly what the outer evaluation→regenerate loop already catches and repairs.
"""

from __future__ import annotations

import re

from react_agent.constants import FRAMEWORK_TO_LANGUAGE_TYPE, FrameworkEnum, LanguageType
from react_agent.utils.utils import get_snippet_content

# The seam every snippet uses to separate the invariant prelude from the dataset-specific schema.
SCHEMA_MARKER = "// --- Schema and Related Settings ---"

# Invariant utility classes that must live in the injected prelude, per language. These carry the
# JSON serializer / runtime support / DB template factory the harness contract depends on. They are
# extracted from the snippet by name (their position relative to the section markers is not uniform
# across frameworks — e.g. the Java template factory sits *after* the schema seam).
_INVARIANT_CLASSES: dict[FrameworkEnum, tuple[str, ...]] = {
    FrameworkEnum.DOTNET_EFCORE: ("CustomJsonSerializer",),
    FrameworkEnum.DOTNET_DAPPER: ("CustomJsonSerializer",),
    FrameworkEnum.DOTNET_NHIBERNATE: ("CustomJsonSerializer",),
    FrameworkEnum.JAVA_SPRING_DATA_MONGODB: (
        "CustomJsonSerializer",
        "QueryRuntimeSupport",
        "MongoTemplateFactory",
    ),
    FrameworkEnum.JAVA_SPRING_DATA_NEO4J: (
        "CustomJsonSerializer",
        "QueryRuntimeSupport",
        "Neo4jTemplateFactory",
    ),
}

# Lines that are top-of-file directives (illegal mid-file, or duplicates of the prelude's).
_IMPORT_LINE_RE = re.compile(r"^\s*(?:package|import)\s+[\w.*]+\s*;")
# C# `using` *directive* (namespace import / alias / static) — distinct from a `using` *statement*
# (`using var x = ...;`, `using (...)`), which must be preserved.
_CSHARP_USING_RE = re.compile(
    r"^\s*using\s+(?:static\s+[\w.]+|[\w.]+(?:\s*=\s*[\w.<>,\s]+)?)\s*;\s*$"
)
_NAMESPACE_RE = re.compile(r"^\s*namespace\s+[\w.]+\s*;")
_FENCE_RE = re.compile(r"^\s*```")


def _extract_named_block(source: str, class_name: str) -> str:
    """Return the full source of a top-level ``class <class_name> { ... }`` block, or ``""``.

    Locates the declaration by name and brace-matches from its opening ``{`` to the matching close.
    The invariant utility classes this is used on contain no braces inside string literals, so a
    plain depth counter is sufficient (and far simpler than a real parser).
    """
    decl = re.search(rf"^[^\n]*\bclass\s+{re.escape(class_name)}\b", source, re.MULTILINE)
    if not decl:
        return ""
    open_idx = source.find("{", decl.end())
    if open_idx == -1:
        return ""
    depth = 0
    for idx in range(open_idx, len(source)):
        ch = source[idx]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return source[decl.start() : idx + 1]
    return ""


def _is_directive(line: str, language: LanguageType) -> bool:
    """Whether ``line`` is a top-of-file directive (package/import/using/namespace)."""
    if _IMPORT_LINE_RE.match(line) or _NAMESPACE_RE.match(line):
        return True
    if language == LanguageType.CSHARP and _CSHARP_USING_RE.match(line):
        return True
    return False


def _build_prelude(snippet: str, framework: FrameworkEnum) -> str:
    """Assemble the verbatim invariant prelude (imports + namespace + utility classes).

    Starts from everything above the schema seam (covers imports, namespace, and the utilities that
    sit there in the well-formed snippets) and then guarantees every required invariant class is
    present, pulling any that live below the seam (e.g. the Java template factory) by name.
    """
    prelude = snippet.split(SCHEMA_MARKER, 1)[0] if SCHEMA_MARKER in snippet else ""
    for class_name in _INVARIANT_CLASSES.get(framework, ()):
        if not re.search(rf"\bclass\s+{re.escape(class_name)}\b", prelude):
            block = _extract_named_block(snippet, class_name)
            if block:
                prelude = prelude.rstrip() + "\n\n" + block + "\n"
    return prelude.rstrip() + "\n"


def _strip_model_body(body: str, framework: FrameworkEnum) -> tuple[str, list[str]]:
    """Sanitize a model-authored body before it is appended under the injected prelude.

    Removes markdown fences, hoists out top-of-file directives (so they cannot sit illegally
    mid-file and so package/namespace are not duplicated), strips a redundant leading schema marker,
    and drops any redeclaration of an invariant utility class (which would be a duplicate-type
    compile error against the prelude).

    Returns:
        tuple[str, list[str]]: the cleaned body, and the import/using directive lines extracted
        from it (to be re-hoisted into the prelude's import block, deduped).
    """
    language = FRAMEWORK_TO_LANGUAGE_TYPE[framework]

    # Drop any redeclaration of an invariant class first (brace-matched, before line filtering).
    for class_name in _INVARIANT_CLASSES.get(framework, ()):
        block = _extract_named_block(body, class_name)
        if block:
            body = body.replace(block, "")

    kept: list[str] = []
    hoisted_imports: list[str] = []
    for line in body.splitlines():
        if _FENCE_RE.match(line):
            continue
        if _NAMESPACE_RE.match(line):
            continue  # namespace/package injected by the prelude; never duplicate it
        if _IMPORT_LINE_RE.match(line) or (
            language == LanguageType.CSHARP and _CSHARP_USING_RE.match(line)
        ):
            hoisted_imports.append(line.strip())
            continue
        kept.append(line)

    cleaned = "\n".join(kept).replace(SCHEMA_MARKER, "").strip()
    return cleaned, hoisted_imports


def _hoist_imports(prelude: str, framework: FrameworkEnum, extra_imports: list[str]) -> str:
    """Insert model-authored imports not already in the prelude, right after its last directive.

    Java allows duplicate imports and C# treats duplicate ``using`` as a warning, but an import that
    appears *below* a type declaration is a hard error — so any import the model wrote must be moved
    up into the prelude's contiguous directive block (after ``package``/the existing ``using``s).
    """
    if not extra_imports:
        return prelude

    language = FRAMEWORK_TO_LANGUAGE_TYPE[framework]
    lines = prelude.splitlines()
    existing = {ln.strip() for ln in lines}
    new_imports = [imp for imp in dict.fromkeys(extra_imports) if imp not in existing]
    if not new_imports:
        return prelude

    last_directive_idx = -1
    for idx, line in enumerate(lines):
        if _is_directive(line, language):
            last_directive_idx = idx
    insert_at = last_directive_idx + 1 if last_directive_idx >= 0 else 0
    lines[insert_at:insert_at] = new_imports
    return "\n".join(lines)


async def assemble_validation_code(
    framework: FrameworkEnum, model_body: str, is_schema: bool = False
) -> tuple[str, str]:
    """Stitch a runnable validation file from the canonical prelude + a model-authored body.

    Args:
        framework: The framework whose canonical snippet supplies the invariant prelude.
        model_body: The model-authored code below the schema seam (entity classes, query classes,
            and the entrypoint ``main``). Imports/namespace and any redeclared invariant utility
            classes are sanitized out.
        is_schema: Select the schema-validation snippet (one-entity-fetch entrypoint) instead of
            the query-execution snippet.

    Returns:
        tuple[str, str]: ``(assembled_code, entry_type_name)`` — the full compilable file and the
        deterministic entrypoint class name (from ``FRAMEWORK_TO_SNIPPET_FILES``, no longer the
        model's responsibility).
    """
    snippet = await get_snippet_content(framework, is_schema=is_schema)
    content = snippet["content"]
    entry_type_name = snippet["entry_type_name"]
    if not content:
        # No snippet mapping: fall back to the raw body so the validator still gets *something*.
        return model_body.strip(), entry_type_name

    prelude = _build_prelude(content, framework)
    cleaned_body, hoisted = _strip_model_body(model_body, framework)
    prelude = _hoist_imports(prelude, framework, hoisted)

    assembled = f"{prelude.rstrip()}\n\n{SCHEMA_MARKER}\n\n{cleaned_body}\n"
    return assembled, entry_type_name


# ---------------------------------------------------------------- per-query fragment assembly
#
# The fragment contract: the model authors (a) one schema fragment per side and (b) one fragment
# per query per side, each exposing a fixed harness entry:
#   C# (all .NET frameworks):  public static class Query{N} { public static object Harness(<ctx>) }
#   Java Spring Data MongoDB:  final class Query{N} { static Map<String, Object> harness(MongoTemplate template) }
#   Java Spring Data Neo4j:    final class Query{N} { static Map<String, Object> harness(Neo4jTemplate template, Neo4jClient client) }
# Everything else — bootstrap, the per-query try/catch protocol, the results JSON write — is
# generated HERE, deterministically, so the results protocol can never drift with the model.

# C# helper injected alongside the generated entrypoint. `RunQuery` keeps count/first/last
# server-side for IQueryable providers (EF Core / NHibernate LINQ); `RunRows` materializes for
# row-sequence providers (Dapper).
_CS_HARNESS_SUPPORT = """\
public static class HarnessSupport
{
    public static object RunQuery<T>(Func<IQueryable<T>> q, Func<T, object>? orderBySelector = null)
    {
        var query = q();
        var count = query.Count();
        return new
        {
            count,
            firstSample = count > 0 ? (orderBySelector != null ? q().OrderBy(orderBySelector).FirstOrDefault() : query.FirstOrDefault()) : default,
            lastSample = count > 1 ? (orderBySelector != null ? q().OrderByDescending(orderBySelector).FirstOrDefault() : query.LastOrDefault()) : default
        };
    }

    public static object RunRows<T>(Func<IEnumerable<T>> q, Func<T, object>? orderBySelector = null)
    {
        var rows = q().ToList();
        var count = rows.Count;
        var ordered = orderBySelector != null ? rows.OrderBy(orderBySelector).ToList() : rows;
        return new
        {
            count,
            firstSample = count > 0 ? ordered[0] : (object?)null,
            lastSample = count > 1 ? ordered[count - 1] : (object?)null
        };
    }
}
"""

_CS_MAIN_TEMPLATE = """\
public static class {entry_name}
{{
{bootstrap}
        var results = new Dictionary<string, object?>();
        var harnesses = new (int Id, Func<object> Run)[]
        {{
{harness_entries}
        }};

        foreach (var (qid, run) in harnesses)
        {{
            Console.WriteLine($"Running Query {{qid}}...");
            try
            {{
                results[$"query{{qid}}"] = run();
                Console.WriteLine($"Successfully ran Query {{qid}}");
            }}
            catch (Exception ex)
            {{
                results[$"query{{qid}}"] = new {{ error = ex.Message }};
                Console.Error.WriteLine($"Error occurred while running Query{{qid}}: {{ex}}");
            }}
        }}
        System.IO.File.WriteAllText($"{{System.Environment.GetEnvironmentVariable("{results_env}")}}/{results_prefix}_{{DateTime.Now:yyyyMMdd_HHmmss}}.json", CustomJsonSerializer.Serialize(results));
    }}
}}
"""

_CS_BOOTSTRAPS: dict[FrameworkEnum, tuple[str, str]] = {
    # (bootstrap code opening Main and creating the context variable, context variable name)
    FrameworkEnum.DOTNET_EFCORE: (
        """\
    public static void Main(string[] args)
    {
        using var context = new SandboxDbContext(
            new DbContextOptionsBuilder<SandboxDbContext>()
                .UseSqlServer(
                    args.ElementAtOrDefault(0) ?? System.Environment.GetEnvironmentVariable("CONNECTION_STRING")
                        ?? "Server=localhost,1333;Database=WideWorldImporters;User Id=sa;Password=Testingorms123;TrustServerCertificate=True"
                )
                .UseQueryTrackingBehavior(QueryTrackingBehavior.NoTracking)
                .EnableSensitiveDataLogging()
                .LogTo(Console.WriteLine, [DbLoggerCategory.Database.Command.Name], minimumLevel: LogLevel.Information, options: DbContextLoggerOptions.SingleLine).Options
        );
""",
        "context",
    ),
    FrameworkEnum.DOTNET_DAPPER: (
        """\
    public static void Main(string[] args)
    {
        string connectionString = args.ElementAtOrDefault(0)
            ?? System.Environment.GetEnvironmentVariable("CONNECTION_STRING")
            ?? "Server=localhost,1333;Database=WideWorldImporters;User Id=sa;Password=Testingorms123;TrustServerCertificate=True";
        using var conn = new SqlConnection(connectionString);
        conn.Open();
""",
        "conn",
    ),
    FrameworkEnum.DOTNET_NHIBERNATE: (
        """\
    public static void Main(string[] args)
    {
        string connectionString = args.ElementAtOrDefault(0)
            ?? System.Environment.GetEnvironmentVariable("CONNECTION_STRING")
            ?? "Server=localhost,1333;Database=WideWorldImporters;User Id=sa;Password=Testingorms123;TrustServerCertificate=True";

        var configuration = new Configuration()
            .DataBaseIntegration(db =>
            {
                db.ConnectionString = connectionString;
                db.Dialect<MsSql2012Dialect>();
                db.Driver<MicrosoftDataSqlClientDriver>();
                db.LogSqlInConsole = true;
            });

        var mapper = new ModelMapper();
        var mappingTypes = typeof(HarnessSupport).Assembly.GetExportedTypes()
            .Where(t => !t.IsAbstract && !t.IsInterface && t.Name.EndsWith("Map"))
            .ToList();
        mapper.AddMappings(mappingTypes);
        configuration.AddMapping(mapper.CompileMappingForAllExplicitlyAddedEntities());

        using var sessionFactory = configuration.BuildSessionFactory();
        using var session = sessionFactory.OpenSession();
""",
        "session",
    ),
}

_CS_RESULTS: dict[FrameworkEnum, tuple[str, str]] = {
    FrameworkEnum.DOTNET_EFCORE: ("EFCORE_RESULTS_PATH", "efcore_results"),
    FrameworkEnum.DOTNET_DAPPER: ("DAPPER_RESULTS_PATH", "dapper_results"),
    FrameworkEnum.DOTNET_NHIBERNATE: ("NHIBERNATE_RESULTS_PATH", "nhibernate_results"),
}

_JAVA_MAIN_TEMPLATE = """\
public class {entry_name} {{

    // java.util.function.Supplier is fully qualified: the model-authored schema fragment may
    // declare an entity named `Supplier` in this same file, which would otherwise shadow it
    // ("type uom.services.Supplier does not take parameters" + every lambda failing).
    record HarnessCase(int id, java.util.function.Supplier<Map<String, Object>> run) {{}}

    public static void main(String[] args) throws Exception {{
{bootstrap}
        var results = new LinkedHashMap<String, Object>();
        List<HarnessCase> harnesses = List.of(
{harness_entries}
        );

        for (var h : harnesses) {{
            System.out.println("Executing query" + h.id() + "...");
            try {{
                // h.run() is the record ACCESSOR (returns the Supplier); .get() executes it.
                // Storing h.run() serialized the lambda as {{}} and every query "returned" null.
                results.put("query" + h.id(), h.run().get());
                System.out.println("Successfully executed query" + h.id());
            }} catch (Exception e) {{
                System.err.println("Error occurred while executing query" + h.id());
                e.printStackTrace();
                results.put("query" + h.id(), Map.of("error", e.toString()));
            }}
        }}
        // writeResults strips store-internal "id" properties (Mongo ObjectId / Neo4j element id)
        // before serializing: they have no source-side counterpart, and a model that forgets
        // @JsonIgnoreProperties({{"id"}}) on one entity must not fail equivalence on shape alone.
        QueryRuntimeSupport.writeResults(System.getenv("{results_env}") + "/{results_prefix}_" + System.currentTimeMillis() + ".json", results);
{closing}
    }}
}}
"""

_JAVA_CONFIG: dict[FrameworkEnum, dict[str, str]] = {
    FrameworkEnum.JAVA_SPRING_DATA_MONGODB: {
        "bootstrap": """\
        var mongoUri = args.length > 0 ? args[0] : QueryRuntimeSupport.defaultMongoUri();
        var mongoDatabase = args.length > 1 ? args[1] : QueryRuntimeSupport.defaultMongoDatabase();
        QueryRuntimeSupport.configureLogger();
        var template = MongoTemplateFactory.create(mongoUri, mongoDatabase);
""",
        "harness_call": "() -> Query{qid}.harness(template)",
        "results_env": "MONGO_RESULTS_PATH",
        "results_prefix": "mongo_results",
        "closing": "",
    },
    FrameworkEnum.JAVA_SPRING_DATA_NEO4J: {
        "bootstrap": """\
        String uri = args.length > 0 ? args[0] : QueryRuntimeSupport.getNeo4jUri();
        String user = args.length > 1 ? args[1] : QueryRuntimeSupport.getNeo4jUsername();
        String pass = args.length > 2 ? args[2] : QueryRuntimeSupport.getNeo4jPassword();
        QueryRuntimeSupport.configureLogger();
        Driver driver = GraphDatabase.driver(uri, AuthTokens.basic(user, pass));
        Neo4jTemplate template = Neo4jTemplateFactory.create(driver);
        Neo4jClient client = Neo4jClient.create(driver);
""",
        "harness_call": "() -> Query{qid}.harness(template, client)",
        "results_env": "NEO4J_RESULTS_PATH",
        "results_prefix": "neo4j_results",
        "closing": "        driver.close();",
    },
}

# The exact per-side fragment shapes, exposed for tool descriptions / prompts.
# The 2026-07-04 traces' dominant .NET failure was a naming trap inside the fragment class:
# a helper method named `Query{N}` collides with the enclosing class (CS0542), and calling
# `Query{N}(conn)` invokes the CLASS name (CS1955), which then cascades into CS0411 inference
# failures on RunQuery/RunRows — repeated identically across whole retry loops. Spell the rule
# out in the signature the model is shown.
_DOTNET_NAMING_RULE = (
    " IMPORTANT: inside Query{N}, never name a helper member `Query{N}` and never call "
    "`Query{N}(...)` — that identifier is the enclosing CLASS (CS0542/CS1955); name helpers "
    "differently (e.g. `Rows`) and call those. Emit any extra `using` directives your fragment "
    "needs (they are hoisted into the file header)."
)

FRAGMENT_SIGNATURES: dict[FrameworkEnum, str] = {
    FrameworkEnum.DOTNET_EFCORE: (
        "public static class Query{N} { public static object Harness(SandboxDbContext ctx) "
        "{ return HarnessSupport.RunQuery(() => /* IQueryable */, x => x.UniqueKey); } } "
        "(HarnessSupport.RunQuery/RunRows are provided; pass a UNIQUE sort selector when the "
        "query itself has no deterministic order, or null when it does)" + _DOTNET_NAMING_RULE
    ),
    FrameworkEnum.DOTNET_DAPPER: (
        "public static class Query{N} { public static object Harness(SqlConnection conn) "
        "{ return HarnessSupport.RunRows(() => /* IEnumerable rows */, x => x.UniqueKey); } } "
        "(HarnessSupport.RunRows is provided; pass a UNIQUE sort selector when the query itself "
        "has no deterministic order, or null when it does)" + _DOTNET_NAMING_RULE
    ),
    FrameworkEnum.DOTNET_NHIBERNATE: (
        "public static class Query{N} { public static object Harness(NHibernate.ISession session) "
        "{ return HarnessSupport.RunQuery(() => /* IQueryable */, x => x.UniqueKey); } } "
        "(HarnessSupport.RunQuery/RunRows are provided; pass a UNIQUE sort selector when the "
        "query itself has no deterministic order, or null when it does)" + _DOTNET_NAMING_RULE
    ),
    FrameworkEnum.JAVA_SPRING_DATA_MONGODB: (
        "final class Query{N} { static Map<String, Object> harness(MongoTemplate template) "
        '{ ... return Map with "count", "firstSample", "lastSample" (+ optional query metadata); } }'
    ),
    FrameworkEnum.JAVA_SPRING_DATA_NEO4J: (
        "final class Query{N} { static Map<String, Object> harness(Neo4jTemplate template, "
        'Neo4jClient client) { ... return Map with "count", "firstSample", "lastSample" '
        "(+ optional query metadata); } }"
    ),
}

# Schema-fragment guidance per framework (what bootstrap types the schema body must include).
SCHEMA_FRAGMENT_HINTS: dict[FrameworkEnum, str] = {
    FrameworkEnum.DOTNET_EFCORE: (
        "MUST include the `SandboxDbContext` class (DbSet properties for every entity) — the "
        "generated entrypoint instantiates `new SandboxDbContext(...)`."
    ),
    FrameworkEnum.DOTNET_DAPPER: "Plain POCO classes (+ any projection records the queries need).",
    FrameworkEnum.DOTNET_NHIBERNATE: (
        "MUST include the `ClassMapping<T>` mapping classes named `<Entity>Map` — the generated "
        "entrypoint discovers them by the `Map` name suffix via reflection."
    ),
    FrameworkEnum.JAVA_SPRING_DATA_MONGODB: (
        "Entity classes with Spring Data MongoDB annotations (@Document/@Id/@Field) plus any "
        "projection records the queries need."
    ),
    FrameworkEnum.JAVA_SPRING_DATA_NEO4J: (
        "Entity classes with Spring Data Neo4j annotations (@Node/@Id/@Relationship) plus any "
        "projection records the queries need."
    ),
}


def generate_entrypoint_tail(
    framework: FrameworkEnum, entry_type_name: str, query_ids: tuple[int, ...]
) -> str:
    """Generate the deterministic harness-support + entrypoint code for the fragment contract."""
    if framework in _CS_BOOTSTRAPS:
        bootstrap, ctx_var = _CS_BOOTSTRAPS[framework]
        results_env, results_prefix = _CS_RESULTS[framework]
        entries = "\n".join(
            f"            ({qid}, () => Query{qid}.Harness({ctx_var}))," for qid in query_ids
        ).rstrip(",")
        main = _CS_MAIN_TEMPLATE.format(
            entry_name=entry_type_name,
            bootstrap=bootstrap.rstrip("\n"),
            harness_entries=entries,
            results_env=results_env,
            results_prefix=results_prefix,
        )
        return _CS_HARNESS_SUPPORT + "\n" + main
    if framework in _JAVA_CONFIG:
        cfg = _JAVA_CONFIG[framework]
        entries = ",\n".join(
            f"            new HarnessCase({qid}, {cfg['harness_call'].format(qid=qid)})"
            for qid in query_ids
        )
        return _JAVA_MAIN_TEMPLATE.format(
            entry_name=entry_type_name,
            bootstrap=cfg["bootstrap"].rstrip("\n"),
            harness_entries=entries,
            results_env=cfg["results_env"],
            results_prefix=cfg["results_prefix"],
            closing=cfg["closing"],
        )
    raise ValueError(f"No entrypoint template for framework {framework.value}")


def strip_entrypoint_class(content: str, entry_type_name: str) -> str:
    """Remove the entrypoint class block from a snippet body (for fragment-mode prompt examples).

    In the fragment contract the entrypoint `main` is GENERATED, so the structure reference shown
    to the model must not include it — otherwise the model imitates it and redeclares the class.
    """
    block = _extract_named_block(content, entry_type_name)
    return content.replace(block, "").strip() if block else content.strip()


def _drop_reserved_classes(body: str, entry_type_name: str) -> str:
    """Remove model-authored redeclarations of generated classes (entrypoint / HarnessSupport)."""
    for name in (entry_type_name, "HarnessSupport"):
        while True:
            block = _extract_named_block(body, name)
            if not block:
                break
            body = body.replace(block, "")
    return body


async def assemble_query_harness(
    framework: FrameworkEnum,
    schema_body: str,
    query_fragments: dict[int, str],
) -> tuple[str, str]:
    """Stitch a runnable query-validation file from per-query fragments (fragment contract).

    Layout: canonical prelude → seam → schema fragment → Query{N} fragments (ascending) →
    generated HarnessSupport + entrypoint ``main``. Model-authored imports are hoisted into the
    prelude; redeclared invariant/generated classes are dropped.

    Args:
        framework: The framework whose canonical snippet supplies the invariant prelude.
        schema_body: The model-authored schema fragment (entities + mapping/bootstrap types).
        query_fragments: ``{query_id: fragment}`` per-query harness fragments.

    Returns:
        tuple[str, str]: ``(assembled_code, entry_type_name)``.
    """
    snippet = await get_snippet_content(framework, is_schema=False)
    content = snippet["content"]
    entry_type_name = snippet["entry_type_name"]
    query_ids = tuple(sorted(query_fragments))

    prelude = _build_prelude(content, framework) if content else ""
    hoisted_all: list[str] = []

    cleaned_schema, hoisted = _strip_model_body(
        _drop_reserved_classes(schema_body, entry_type_name), framework
    )
    hoisted_all.extend(hoisted)

    cleaned_fragments: list[str] = []
    for qid in query_ids:
        cleaned, hoisted = _strip_model_body(
            _drop_reserved_classes(query_fragments[qid], entry_type_name), framework
        )
        hoisted_all.extend(hoisted)
        cleaned_fragments.append(cleaned)

    prelude = _hoist_imports(prelude, framework, hoisted_all)
    tail = generate_entrypoint_tail(framework, entry_type_name, query_ids)

    parts = [
        prelude.rstrip(),
        "",
        SCHEMA_MARKER,
        "",
        cleaned_schema,
        "",
        "// --- Query Harness Fragments ---",
        "",
        "\n\n".join(cleaned_fragments),
        "",
        "// --- Generated Entrypoint (do not edit) ---",
        "",
        tail.rstrip(),
        "",
    ]
    return "\n".join(parts), entry_type_name


__all__ = [
    "assemble_validation_code",
    "assemble_query_harness",
    "generate_entrypoint_tail",
    "FRAGMENT_SIGNATURES",
    "SCHEMA_FRAGMENT_HINTS",
    "SCHEMA_MARKER",
]
