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


__all__ = ["assemble_validation_code", "SCHEMA_MARKER"]
