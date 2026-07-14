"""Unit tests for the per-framework skills wired into the translation system prompt.

Every supported framework — the Java (target) frameworks AND the .NET (source) frameworks — has a
skill under ``src/context/skills``. Both the source and the target skill of a pair are injected in
full into the translation system prompt; only the two relevant to the current pair appear, and the
source skill precedes the target skill. These tests pin that contract.
"""

import os

import pytest

from react_agent.constants import FrameworkEnum, TranslationType
from react_agent.custom_tools.skill_reference import (
    FRAMEWORK_TO_SKILL,
    _skill_dir,
    get_skill_overview,
    get_skill_references,
)
from react_agent.prompts import build_system_prompt
from react_agent.state import State

_ALL = list(FrameworkEnum)

# SKILL.md `# <title>` used to prove a specific skill is (or is not) present in an assembled prompt.
_SKILL_TITLE_MARKER: dict[FrameworkEnum, str] = {
    FrameworkEnum.DOTNET_EFCORE: ".NET Entity Framework Core 10 Expert (source side)",
    FrameworkEnum.DOTNET_DAPPER: ".NET Dapper 2.1 Expert (source side)",
    FrameworkEnum.DOTNET_NHIBERNATE: ".NET NHibernate 5.5 Expert (source side)",
    FrameworkEnum.JAVA_SPRING_DATA_MONGODB: "Spring Data MongoDB 5.0 Expert",
    FrameworkEnum.JAVA_SPRING_DATA_NEO4J: "Spring Data Neo4j 8.0 Expert",
}


def test_every_framework_has_a_skill():
    """FRAMEWORK_TO_SKILL covers every framework and each skill dir has SKILL.md + references."""
    assert set(FRAMEWORK_TO_SKILL) == set(FrameworkEnum)
    for fw in FrameworkEnum:
        skill_dir = _skill_dir(fw)
        assert skill_dir is not None and os.path.isdir(skill_dir), fw
        assert os.path.isfile(os.path.join(skill_dir, "SKILL.md")), fw
        refs = os.path.join(skill_dir, "references")
        assert os.path.isdir(refs) and any(f.endswith(".md") for f in os.listdir(refs)), fw


@pytest.mark.asyncio
@pytest.mark.parametrize("framework", _ALL)
async def test_skill_overview_and_references_load(framework):
    overview = await get_skill_overview(framework)
    references = await get_skill_references(framework)
    assert overview, f"empty overview for {framework.value}"
    assert references, f"empty references for {framework.value}"
    # YAML frontmatter is stripped from the overview (it is host retrieval metadata, not guidance).
    assert not overview.lstrip().startswith("---"), framework
    assert f"name: {FRAMEWORK_TO_SKILL[framework]}" not in overview, framework
    # References are concatenated with the per-topic section header.
    assert "### Reference:" in references, framework


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "source_fw, target_fw",
    [
        (FrameworkEnum.DOTNET_EFCORE, FrameworkEnum.JAVA_SPRING_DATA_NEO4J),
        (FrameworkEnum.DOTNET_DAPPER, FrameworkEnum.JAVA_SPRING_DATA_MONGODB),
        (FrameworkEnum.DOTNET_NHIBERNATE, FrameworkEnum.JAVA_SPRING_DATA_MONGODB),
    ],
)
async def test_build_system_prompt_injects_only_the_pair_skills(source_fw, target_fw):
    state = State(
        source_schema_code="",
        source_query_code=(
            "public static class Query1 { public static object Query1() { return null; } }"
        ),
        translation_type=TranslationType.QUERY,
        source_target=source_fw,
        destination_target=target_fw,
    )
    prompt = await build_system_prompt(state)

    # Both relevant sections are present, source before target.
    src_header = f"--- SOURCE FRAMEWORK SKILL: {source_fw.value} ---"
    tgt_header = f"--- TARGET FRAMEWORK SKILL: {target_fw.value} ---"
    assert src_header in prompt
    assert tgt_header in prompt
    assert prompt.index(src_header) < prompt.index(tgt_header)

    # The source and target skill bodies are present; the three uninvolved skills are not.
    for fw, title in _SKILL_TITLE_MARKER.items():
        if fw in (source_fw, target_fw):
            assert title in prompt, f"{title} should be injected for {source_fw}->{target_fw}"
        else:
            assert title not in prompt, f"{title} should NOT be injected for {source_fw}->{target_fw}"
