#!/usr/bin/env python3
"""
metrics.py — E3: generated-vs-ground-truth comparators (weakest -> strongest).

Lead with execution-equivalence (the gold standard you already have via Layer 3).
Use CodeBLEU / exact-match only as secondary, well-caveated similarity numbers --
they do NOT prove functional correctness (state this in the thesis).

Functions:
  normalized_exact_match(a, b)      -> bool   (whitespace/identifier-insensitive)
  token_overlap(a, b)               -> float  (cheap Jaccard, no deps)
  codebleu_score(refs, hyps, lang)  -> dict   (optional: pip install codebleu)
  execution_equivalent(src, tgt)    -> bool   (reuse your DeepDiff Layer-3 config)

Usage as a library; or `python metrics.py demo` for a smoke test.
"""
from __future__ import annotations

import re
from typing import Any


# --- weakest: normalized exact / token overlap ---------------------------------------------
def _normalize(code: str) -> str:
    code = re.sub(r"//.*?$|/\*.*?\*/|#.*?$", "", code, flags=re.M | re.S)  # strip comments
    code = re.sub(r"\s+", " ", code)                                        # collapse whitespace
    return code.strip()


def normalized_exact_match(a: str, b: str) -> bool:
    return _normalize(a) == _normalize(b)


def token_overlap(a: str, b: str) -> float:
    ta = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", _normalize(a)))
    tb = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", _normalize(b)))
    if not ta and not tb:
        return 1.0
    return len(ta & tb) / len(ta | tb or {1})


# --- middling: CodeBLEU (syntax + AST + data-flow) -----------------------------------------
def codebleu_score(references: list[str], hypotheses: list[str], lang: str = "java") -> dict[str, float]:
    """Wrapper over the `codebleu` package. lang in {java, c_sharp, python, ...}.

    Returns the component breakdown. CAVEAT: CodeBLEU measures similarity, not
    functional correctness -- report it as secondary evidence only.
    """
    try:
        from codebleu import calc_codebleu  # pip install codebleu
    except ImportError as e:
        raise SystemExit("pip install codebleu  (and a tree-sitter grammar for the language)") from e
    return calc_codebleu(references, hypotheses, lang=lang,
                         weights=(0.25, 0.25, 0.25, 0.25))


# --- strongest: execution-equivalence (reuse Layer-3 tolerant diff) ------------------------
def execution_equivalent(source_summary: dict[str, Any], target_summary: dict[str, Any],
                         sig_digits: int = 4) -> bool:
    """Tolerant equivalence on the {count, firstSample, lastSample} summaries the
    harnesses emit (see ch_validation.tex, Listing equiv-json). Ignores field
    order, rounds floats, and applies the swapped-sorting robustness check.

    This mirrors the orchestrator's check_query_equivalence so E3 scoring matches
    what the pipeline itself decides. Prefer importing the real implementation:

        from react_agent.custom_tools... import check_query_equivalence  # if importable

    The standalone version below uses DeepDiff with the same tolerances.
    """
    try:
        from deepdiff import DeepDiff
    except ImportError as e:
        raise SystemExit("pip install deepdiff") from e

    def diff(x: Any, y: Any) -> bool:
        d = DeepDiff(x, y, ignore_order=True, significant_digits=sig_digits,
                     ignore_numeric_type_changes=True)
        return not d  # True == equal

    if source_summary.get("count") != target_summary.get("count"):
        return False
    s_first, s_last = source_summary.get("firstSample"), source_summary.get("lastSample")
    t_first, t_last = target_summary.get("firstSample"), target_summary.get("lastSample")
    if diff(s_first, t_first) and diff(s_last, t_last):
        return True                       # same order
    if diff(s_first, t_last) and diff(s_last, t_first):
        return True                       # reversed order (swap test)
    return False


def _demo() -> None:
    a = "var q = ctx.Orders.Where(o => o.Total > 100).OrderBy(o => o.Id).ToList();"
    b = "var  q = ctx.Orders.Where(o=>o.Total>100).OrderBy(o=>o.Id).ToList();"
    print("normalized_exact_match:", normalized_exact_match(a, b))
    print("token_overlap:", round(token_overlap(a, b), 3))
    src = {"count": 142, "firstSample": {"Id": 1001, "Price": 48.50},
           "lastSample": {"Id": 1143, "Price": 12.00}}
    tgt = {"count": 142, "lastSample": {"Price": 12.0, "Id": 1143},
           "firstSample": {"Price": 48.5000, "Id": 1001}}
    print("execution_equivalent:", execution_equivalent(src, tgt))


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        _demo()
    else:
        print(__doc__)
