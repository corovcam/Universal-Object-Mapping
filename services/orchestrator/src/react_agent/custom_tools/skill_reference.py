"""On-demand access to the target-framework "skills" that live in ``src/context/skills``.

The translator's dominant *model* failure mode is hallucinated imports/APIs on the target side
(e.g. missing ``org.bson.types.Decimal128``, the wrong ``MongoTemplate.count`` overload, invalid
Cypher-DSL ``Statement`` usage). Those exact traps are already documented, per framework, in
``src/context/skills/<skill>/references/*.md`` — but nothing wired them into the agent, so the model
never saw them and instead leaned on the in-prompt EXAMPLES (which only covered the small test set).

This module closes that gap with a *hybrid* delivery:

* a short always-on orientation summary from ``SKILL.md`` (:func:`get_skill_overview`), injected into
  the translation system prompt, and
* a :func:`build_skill_reference_tool` factory that lets the agent pull the detailed reference files
  on demand — the same shape as the reference/detail split the skills were authored for.

Only the *target* framework has a skill (the production API the model must not hallucinate); the
source side is plain .NET and needs no such reference.
"""

from __future__ import annotations

import os

import aiofiles
from langchain_core.tools import BaseTool, StructuredTool

from react_agent.constants import FrameworkEnum
from react_agent.utils.utils import get_context_dir, logger

# Target framework -> skill directory under ``src/context/skills``. Source (.NET) frameworks have no
# skill: the skills teach the *target* production API surface, which is where hallucinations happen.
FRAMEWORK_TO_SKILL: dict[FrameworkEnum, str] = {
    FrameworkEnum.JAVA_SPRING_DATA_MONGODB: "spring-data-mongodb",
    FrameworkEnum.JAVA_SPRING_DATA_NEO4J: "spring-data-neo4j",
}


def _skill_dir(framework: FrameworkEnum) -> str | None:
    skill = FRAMEWORK_TO_SKILL.get(framework)
    if not skill:
        return None
    return os.path.join(get_context_dir(), "skills", skill)


def _available_references(framework: FrameworkEnum) -> list[str]:
    """List the reference topics available for a framework's skill (filenames without ``.md``)."""
    skill_dir = _skill_dir(framework)
    if not skill_dir:
        return []
    refs_dir = os.path.join(skill_dir, "references")
    try:
        return sorted(f[:-3] for f in os.listdir(refs_dir) if f.endswith(".md"))
    except OSError as e:
        logger.warning(f"Could not list skill references for {framework.value}: {e}")
        return []


async def get_skill_overview(framework: FrameworkEnum) -> str:
    """Return the target skill's ``SKILL.md`` orientation (YAML frontmatter stripped), or "".

    Injected always-on into the translation system prompt: the concise API/import rules and the
    "renamed since 3.x" traps. Detailed per-topic reference files are fetched on demand via the
    ``read_skill_reference`` tool built by :func:`build_skill_reference_tool`.
    """
    skill_dir = _skill_dir(framework)
    if not skill_dir:
        return ""
    path = os.path.join(skill_dir, "SKILL.md")
    try:
        async with aiofiles.open(path) as f:
            content = await f.read()
    except OSError as e:
        logger.warning(f"Could not read SKILL.md for {framework.value}: {e}")
        return ""

    # Strip a leading YAML frontmatter block (--- ... ---) — it is retrieval metadata for the host,
    # not guidance the model needs.
    if content.startswith("---"):
        end = content.find("\n---", 3)
        if end != -1:
            nl = content.find("\n", end + 1)
            content = content[nl + 1 :] if nl != -1 else ""
    return content.strip()


def build_skill_reference_tool(target_framework: FrameworkEnum) -> BaseTool | None:
    """Build the ``read_skill_reference`` tool scoped to the target framework's skill.

    Returns ``None`` when the target framework has no skill (nothing to expose), so the caller can
    simply skip appending it to the tool list.
    """
    available = _available_references(target_framework)
    if not available:
        return None

    skill_dir = _skill_dir(target_framework)
    assert skill_dir is not None  # guaranteed by non-empty ``available``
    refs_dir = os.path.join(skill_dir, "references")
    available_list = ", ".join(available)

    async def _read_skill_reference(reference: str) -> str:
        """Read one detailed reference file for the target framework's skill."""
        name = reference.strip().lower()
        if name.endswith(".md"):
            name = name[:-3]
        if name not in available:
            return (
                f"Unknown reference '{reference}'. Available references: {available_list}."
            )
        path = os.path.join(refs_dir, f"{name}.md")
        try:
            async with aiofiles.open(path) as f:
                return await f.read()
        except OSError as e:
            logger.warning(f"Could not read skill reference {path}: {e}")
            return f"Could not read reference '{name}': {e}"

    return StructuredTool.from_function(
        coroutine=_read_skill_reference,
        name="read_skill_reference",
        description=(
            f"Look up the EXACT, non-hallucinated imports and API surface for the target framework "
            f"({target_framework.value}) before writing target code. Use it whenever you are unsure "
            f"of a package, class, annotation, or method signature — a single wrong import fails the "
            f"whole compile. Pass `reference` as ONE of: {available_list}. "
            f"('imports' = the canonical allowed import list + renamed/removed traps; "
            f"'schema-mapping' = @Document/@Node entity mapping and type conversions; "
            f"'queries' = the read/query API; and the rest are per-topic detail.)"
        ),
    )


__all__ = [
    "FRAMEWORK_TO_SKILL",
    "build_skill_reference_tool",
    "get_skill_overview",
]
