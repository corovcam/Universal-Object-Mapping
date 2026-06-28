#!/usr/bin/env python3
"""
fault_injection.py — E2: verifier-efficacy via mutation / fault injection.

Goal: evaluate the VERIFICATION GRAPH independently of the (currently flaky)
generator. We take ground-truth target translations we KNOW are correct
(positives), derive faulty variants by applying mutation operators (negatives),
push each through the validation sub-graph by SEEDING graph state (so
generate_translation_node is bypassed), and compare the pipeline verdict
(ACCEPT/REJECT) against the ground-truth label.

Outputs: precision / recall / accuracy / FAR / FRR of the verifier, plus a
breakdown of WHICH layer killed each mutant (compile vs equivalence vs judge) —
evidence that the four layers are complementary (ch_validation.tex claim).

This is the highest-leverage experiment under time pressure: deterministic,
re-runnable, and statistically powerful (hundreds of cheap mutants), and it does
NOT depend on the generator succeeding.

This is a SKELETON. Fill in:
  (a) load_ground_truth(): your known-good (schema, query, harness) translations
  (b) run_validation_subgraph(): seed State and invoke from prep_*_validation
      onward (see services/orchestrator integration tests for how to drive it)

Usage:
  python fault_injection.py --gt ./ground_truth --out ./out --per-op 5
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
from dataclasses import dataclass, field
from typing import Callable

# ----------------------------------------------------------------------------------
# Mutation operators. Each takes target code and returns a (mutated_code, op_name)
# or None if not applicable. These mirror real translation faults the verifier
# must catch. Keep them small & language-agnostic-ish (regex on emitted Java/C#).
# ----------------------------------------------------------------------------------
Mutator = Callable[[str], str | None]


def drop_filter_predicate(code: str) -> str | None:
    # remove a .filter(...) / .where(...) / WHERE ... clause  -> changes cardinality
    for pat in (r"\.where\([^;]*?\)", r"\.filter\([^;]*?\)", r"(?i)\bWHERE\b[^\n;]*"):
        m = re.search(pat, code)
        if m:
            return code[:m.start()] + code[m.end():]
    return None


def swap_aggregation(code: str) -> str | None:
    pairs = [("Sum", "Count"), ("sum", "count"), ("Max", "Min"), ("max", "min"),
             ("Average", "Sum"), ("avg", "sum")]
    for a, b in pairs:
        if re.search(rf"\b{a}\b", code):
            return re.sub(rf"\b{a}\b", b, code, count=1)
    return None


def reverse_sort(code: str) -> str | None:
    if "Descending" in code or "DESC" in code:
        return code.replace("Descending", "Ascending", 1).replace("DESC", "ASC", 1)
    if "Ascending" in code or "ASC" in code:
        return code.replace("Ascending", "Descending", 1).replace("ASC", "DESC", 1)
    if ".OrderBy(" in code:
        return code.replace(".OrderBy(", ".OrderByDescending(", 1)
    return None


def rename_mapped_field(code: str) -> str | None:
    # corrupt one field/property name -> compile error OR wrong projection
    m = re.search(r'(?<![\w."])([A-Z][a-zA-Z0-9]{3,})(?=\s*[,)\.])', code)
    if m:
        bad = m.group(1) + "_X"
        return code[:m.start()] + bad + code[m.end():]
    return None


def change_join_direction(code: str) -> str | None:
    # flip a relationship/join order -> wrong result for non-symmetric joins
    m = re.search(r"\.(hasMany|hasOne|WithMany|WithOne|belongsTo)\(", code)
    if m:
        flip = {"hasMany": "hasOne", "hasOne": "hasMany",
                "WithMany": "WithOne", "WithOne": "WithMany",
                "belongsTo": "hasMany"}[m.group(1)]
        return code[:m.start(1)] + flip + code[m.end(1):]
    return None


def wrong_numeric_type(code: str) -> str | None:
    for a, b in [("decimal", "int"), ("BigDecimal", "Integer"), ("double", "int"), ("long", "int")]:
        if re.search(rf"\b{a}\b", code):
            return re.sub(rf"\b{a}\b", b, code, count=1)
    return None


MUTATORS: dict[str, Mutator] = {
    "drop_filter": drop_filter_predicate,
    "swap_agg": swap_aggregation,
    "reverse_sort": reverse_sort,
    "rename_field": rename_mapped_field,
    "flip_join": change_join_direction,
    "wrong_type": wrong_numeric_type,
}


# ----------------------------------------------------------------------------------
@dataclass
class GroundTruth:
    name: str
    pair: str                 # "efcore->mongo"
    translation_type: str     # "SCHEMA" | "QUERY" | "BOTH"
    schema_code: str = ""
    query_code: str = ""
    harness_code: str = ""
    schema_context: str = ""  # the inspected-schema context the validators need


@dataclass
class Case:
    gt_name: str
    label: str                # "correct" (positive) or "faulty" (negative)
    op: str                   # mutation op name, or "none"
    code: str
    verdict: str = ""         # filled by the verifier: "ACCEPT" / "REJECT" / "ERROR"
    killed_by: str = ""       # "compile" | "equivalence" | "judge" | ""


# --- TODO (a): load your known-good translations ----------------------------------
def load_ground_truth(path: str) -> list[GroundTruth]:
    """Load known-good target translations from JSON files in `path`.

    Each JSON: {name, pair, translation_type, schema_code, query_code,
                harness_code, schema_context}. These MUST compile and be
                data-equivalent against your live target DBs (verify once by
                running them through the pipeline before mutating).
    """
    gts: list[GroundTruth] = []
    for fn in sorted(os.listdir(path)):
        if fn.endswith(".json"):
            with open(os.path.join(path, fn), encoding="utf-8") as f:
                d = json.load(f)
            gts.append(GroundTruth(**d))
    if not gts:
        raise SystemExit(f"No ground-truth JSON found in {path}. See docstring for format.")
    return gts


def make_cases(gts: list[GroundTruth], per_op: int, seed: int = 0) -> list[Case]:
    random.seed(seed)
    cases: list[Case] = []
    for gt in gts:
        base = gt.query_code or gt.schema_code
        cases.append(Case(gt.name, "correct", "none", base))  # positive
        for op_name, op in MUTATORS.items():
            made = 0
            for _ in range(per_op):
                mutated = op(base)
                if mutated and mutated != base:
                    cases.append(Case(gt.name, "faulty", op_name, mutated))
                    made += 1
                if made >= 1:  # one distinct mutant per op per gt is enough for many ops
                    break
    return cases


# --- TODO (b): drive the real validation sub-graph --------------------------------
async def run_validation_subgraph(gt: GroundTruth, code: str) -> tuple[str, str]:
    """Seed State with `code` as the translated output and run from validation onward.

    Return (verdict, killed_by) where verdict in {ACCEPT, REJECT, ERROR} and
    killed_by in {compile, equivalence, judge, ""}.

    Implementation outline (see tests/integration_tests/test_sandboxed_validation.py
    and test_deepdiff_validator.py for working snippets):

        from react_agent.graph import (
            prep_query_validation, validate_query_node,
            prep_query_equivalence, check_query_equivalence_node, evaluation_node,
        )
        from react_agent.state import State

        state = State(
            translation_type=...,            # from gt.translation_type
            source_target=..., destination_target=...,
            schema_context=gt.schema_context,
            translated_query_code=code,      # <-- the (possibly mutated) translation
            target_validation_harness_code=gt.harness_code,
            ...                              # seed any source-side fields once, reuse
        )
        # call prep -> validate (Daytona compile+run) -> equivalence -> evaluation,
        # threading the returned state updates, then read the judge decision and
        # which stage first emitted a "Failed]" / drift to set killed_by.

    NOTE: source-side validation results can be cached/seeded once per gt so each
    mutant only re-runs the target side -> fast.
    """
    raise NotImplementedError("Wire to react_agent.graph nodes; see docstring + integration tests.")


def score(cases: list[Case]) -> dict:
    # positive = correct (should ACCEPT); negative = faulty (should REJECT)
    tp = sum(1 for c in cases if c.label == "faulty" and c.verdict == "REJECT")   # correctly rejected
    fn = sum(1 for c in cases if c.label == "faulty" and c.verdict == "ACCEPT")   # missed fault (false accept)
    tn = sum(1 for c in cases if c.label == "correct" and c.verdict == "ACCEPT")  # correctly accepted
    fp = sum(1 for c in cases if c.label == "correct" and c.verdict == "REJECT")  # false reject
    n = tp + fn + tn + fp or 1
    prec = tp / (tp + fp) if (tp + fp) else float("nan")   # of all rejects, how many were truly faulty
    rec = tp / (tp + fn) if (tp + fn) else float("nan")    # mutant-kill rate
    killed = {}
    for c in cases:
        if c.label == "faulty" and c.verdict == "REJECT" and c.killed_by:
            killed[c.killed_by] = killed.get(c.killed_by, 0) + 1
    return {
        "n": n, "tp_killed": tp, "fn_missed": fn, "tn": tn, "fp_false_reject": fp,
        "accuracy": round((tp + tn) / n, 3),
        "precision": round(prec, 3), "recall_mutant_kill": round(rec, 3),
        "false_accept_rate": round(fn / (tp + fn), 3) if (tp + fn) else None,
        "false_reject_rate": round(fp / (fp + tn), 3) if (fp + tn) else None,
        "killed_by_layer": killed,
    }


def main() -> None:
    import asyncio
    ap = argparse.ArgumentParser()
    ap.add_argument("--gt", required=True, help="dir of ground-truth JSON files")
    ap.add_argument("--per-op", type=int, default=1, help="mutants per operator per gt")
    ap.add_argument("--out", default="./out")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    gts = load_ground_truth(args.gt)
    gt_by_name = {g.name: g for g in gts}
    cases = make_cases(gts, args.per_op)
    print(f"{len(gts)} ground-truths -> {len(cases)} cases "
          f"({sum(c.label=='correct' for c in cases)} pos / {sum(c.label=='faulty' for c in cases)} neg)")

    async def run_all():
        for c in cases:
            try:
                c.verdict, c.killed_by = await run_validation_subgraph(gt_by_name[c.gt_name], c.code)
            except NotImplementedError:
                raise
            except Exception as e:
                c.verdict, c.killed_by = "ERROR", ""
                print(f"[warn] {c.gt_name}/{c.op}: {e}")

    asyncio.run(run_all())

    result = score(cases)
    print("\n=== verifier efficacy (E2) ===")
    print(json.dumps(result, indent=2))
    with open(os.path.join(args.out, "e2_result.json"), "w", encoding="utf-8") as f:
        json.dump({"summary": result,
                   "cases": [vars(c) for c in cases]}, f, indent=2)
    print(f"wrote {args.out}/e2_result.json")


if __name__ == "__main__":
    main()
