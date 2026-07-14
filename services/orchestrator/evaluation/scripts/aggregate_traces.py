#!/usr/bin/env python3
"""aggregate_traces.py — E1 (stage funnel), E4 (internal stats), and the judge-vs-execution
confusion matrix, harvested from LangSmith traces.

This reconstructs, per translation run, the pipeline stage reached, per-node wall-clock and token
usage, and the verifier's ACCEPT/REJECT decision against the execution-equivalence ground truth.
Everything is derived from the *current* graph (post finalize-split) — it does not depend on the
old structured-output generation contract.

What it reads from the LangSmith trace tree (verified against project "LLM orchestrator service"):
  - Node spans are `chain` runs named exactly after the graph nodes (extract_input,
    schema_inspection, generate_translation_node, validate_query_node, check_query_equivalence_node,
    evaluation_node, finalize_translation_node, human_intervention_node, ...).
  - Token usage lives on `ChatLiteLLM` (run_type="llm") spans as prompt_tokens/completion_tokens;
    each is attributed to the nearest node-named ancestor via parent_run_id.
  - The translation pair + type come from extract_input's output
    (source_target / destination_target / translation_type).
  - Per-query equivalence comes from the `check_query_equivalence` tool span's
    "[Query Equivalence Results]" JSON ({"query1": {"status": "Equivalent"}, ...}).
  - ACCEPT is signalled structurally: finalize_translation_node only runs on an accept path
    (route_post_evaluation ACCEPT, route_post_schema_validation pass, or human accept).

Usage:
  pip install langsmith pandas python-dotenv        # langsmith + dotenv already in the orchestrator venv
  # LANGSMITH_API_KEY / LANGSMITH_PROJECT / LANGSMITH_ENDPOINT are read from ../.env by default
  python aggregate_traces.py --limit 50 --out ./out
  python aggregate_traces.py --project "LLM orchestrator service" --dataset wwi --out ./out
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

# --- the graph's node names (chain spans we care about) -------------------------------------
NODE_NAMES = {
    "extract_input",
    "schema_inspection",
    "generate_translation_node",
    "human_intervention_node",
    "prep_schema_validation",
    "validate_schema_node",
    "prep_query_validation",
    "validate_query_node",
    "prep_query_equivalence",
    "check_query_equivalence_node",
    "evaluation_node",
    "finalize_translation_node",
}

# --- ordered funnel stages (each is "this run reached/passed the stage") ---------------------
# Reconstructed from node-reached + the equivalence scrape, NOT from any structured-output flag
# (generation no longer emits structured output; clean code is derived later by finalize).
STAGES = [
    "extract_input",            # intent extracted
    "schema_inspection",        # DB schema inspected
    "generate_translation",     # generation node ran (authored validation bodies)
    "compiled_executed",        # harnesses compiled + ran (reached query equivalence / schema pass)
    "equivalent",               # every query equivalent (exec-equivalence holds)
    "accepted",                 # judge ACCEPT -> finalize ran -> clean code emitted
]
TERMINALS = ["accepted", "human_intervention", "incomplete"]

_EQUIV_BLOCK_RE = re.compile(r"\[Query Equivalence Results\]\s*```json\s*(\{.*?\})\s*```", re.S)
# Markers the judge (evaluation_node) writes: ACCEPT emits the "Finalizing…" message, REJECT emits
# "[REJECT] …", and structured-output/eval failures emit their own tags (treated as non-verdicts).
_ACCEPT_MARK = "accepted by automated evaluation"
_REJECT_MARK = "[REJECT]"
_ERROR_MARKS = ("[Structured Output Error]", "[Evaluation Failed]", "[Evaluation Error]")


@dataclass
class RunSummary:
    run_id: str
    trace_id: str = ""
    dataset: str = "wwi"
    pair: str = "unknown"               # e.g. ".NET Dapper -> Java Spring Data MongoDB"
    translation_type: str = "unknown"   # schema | query | both
    model: str = "unknown"
    reached: dict[str, bool] = field(default_factory=lambda: {s: False for s in STAGES})
    terminal: str = "incomplete"
    translation_loops: int = 0          # number of generate_translation_node visits
    e2e_seconds: float = 0.0
    node_seconds: dict[str, float] = field(default_factory=dict)
    node_tokens_in: dict[str, int] = field(default_factory=dict)
    node_tokens_out: dict[str, int] = field(default_factory=dict)
    queries_total: int = 0
    queries_equivalent: int = 0
    judge_verdict: str = "none"         # ACCEPT | REJECT | accept_schema | error | none
    judge_accept: bool = False          # judge said ACCEPT (not merely "finalize reached")
    finalize_reached: bool = False
    completed: bool = True              # root run has an end_time (not in-progress)
    single_pass: bool = False           # baseline arm (stamped via metadata.single_pass)
    all_equivalent: bool | None = None  # exec-equivalence ground-truth label (None if no queries)


# --- LangSmith ingestion --------------------------------------------------------------------
def fetch_root_runs(project: str, limit: int | None, graph_name: str | None) -> Iterable[Any]:
    from langsmith import Client

    client = Client()
    # The project also logs stray top-level spans (ChatLiteLLM, save_translation) as "roots";
    # restrict to the actual graph invocation by name so the funnel denominator is clean.
    kwargs: dict[str, Any] = {"project_name": project, "is_root": True, "limit": limit}
    if graph_name:
        kwargs["filter"] = f'eq(name, "{graph_name}")'
    for r in client.list_runs(**kwargs):
        yield r, client


def iter_child_runs(client: Any, trace_id: str) -> list[Any]:
    return list(client.list_runs(trace_id=trace_id, is_root=False))


# --- per-run reconstruction -----------------------------------------------------------------
def _seconds(run: Any) -> float:
    start, end = getattr(run, "start_time", None), getattr(run, "end_time", None)
    if start and end:
        try:
            return (end - start).total_seconds()
        except Exception:
            return 0.0
    return 0.0


def _tokens(run: Any) -> tuple[int, int]:
    """(in, out) tokens for an llm span. Prefer the flat attrs LangSmith fills for ChatLiteLLM."""
    pin = getattr(run, "prompt_tokens", None)
    pout = getattr(run, "completion_tokens", None)
    if pin is not None or pout is not None:
        return int(pin or 0), int(pout or 0)
    meta = getattr(run, "usage_metadata", None) or {}
    if isinstance(meta, dict):
        return int(meta.get("input_tokens", 0) or 0), int(meta.get("output_tokens", 0) or 0)
    return 0, 0


def _outputs_dict(run: Any) -> dict:
    out = getattr(run, "outputs", None) or {}
    return out if isinstance(out, dict) else {}


def _scrape_equivalence(children: list[Any]) -> dict[str, bool]:
    """Per-query equivalence from the check_query_equivalence tool span(s).

    Returns {query_name: is_equivalent}. If the loop retried, the LAST equivalence span wins.
    """
    def iter_strings(obj: Any) -> Iterable[str]:
        if isinstance(obj, str):
            yield obj
        elif isinstance(obj, dict):
            for v in obj.values():
                yield from iter_strings(v)
        elif isinstance(obj, (list, tuple)):
            for v in obj:
                yield from iter_strings(v)

    result: dict[str, bool] = {}
    eq_runs = [c for c in children if c.name == "check_query_equivalence"]
    eq_runs.sort(key=lambda c: getattr(c, "start_time", None) or 0)
    for c in eq_runs:
        # Walk the (unescaped) string values in the tool output and regex the real content; the
        # "[Query Equivalence Results]" block lives in messages[].content. The LAST span wins.
        for s in iter_strings(_outputs_dict(c)):
            m = _EQUIV_BLOCK_RE.search(s)
            if not m:
                continue
            try:
                payload = json.loads(m.group(1))
            except Exception:
                continue
            for q, v in payload.items():
                status = (v or {}).get("status", "") if isinstance(v, dict) else str(v)
                result[q] = status.strip().lower() == "equivalent"
    return result


def _scrape_verdict(children: list[Any]) -> str:
    """The judge's final ACCEPT/REJECT, read from the LAST evaluation_node span.

    Returns ACCEPT | REJECT | error | none. This is the real classifier signal — NOT
    "finalize reached", which can't distinguish a REJECT from an aborted/in-progress trace.
    """
    ev = [c for c in children if c.name == "evaluation_node"]
    if not ev:
        return "none"
    ev.sort(key=lambda c: getattr(c, "start_time", None) or 0)

    def strings(obj: Any) -> Iterable[str]:
        if isinstance(obj, str):
            yield obj
        elif isinstance(obj, dict):
            for v in obj.values():
                yield from strings(v)
        elif isinstance(obj, (list, tuple)):
            for v in obj:
                yield from strings(v)

    blob = "\n".join(strings(_outputs_dict(ev[-1])))
    if _ACCEPT_MARK in blob:
        return "ACCEPT"
    if _REJECT_MARK in blob:
        return "REJECT"
    if any(t in blob for t in _ERROR_MARKS):
        return "error"
    return "none"


def summarize_run(root: Any, client: Any, dataset: str) -> RunSummary:
    rs = RunSummary(run_id=str(root.id), trace_id=str(getattr(root, "trace_id", root.id)),
                    dataset=dataset)
    rs.e2e_seconds = _seconds(root)
    rs.completed = getattr(root, "end_time", None) is not None
    meta = (getattr(root, "extra", {}) or {}).get("metadata", {}) or {}
    rs.model = meta.get("model", rs.model)
    rs.single_pass = bool(meta.get("single_pass", False)) or meta.get("approach") == "baseline"

    children = iter_child_runs(client, rs.trace_id)
    byid: dict[str, Any] = {str(c.id): c for c in children}
    byid[str(root.id)] = root

    def nearest_node(run: Any) -> str | None:
        cur, hops = run, 0
        while cur is not None and hops < 40:
            if cur.name in NODE_NAMES:
                return cur.name
            pid = getattr(cur, "parent_run_id", None)
            cur = byid.get(str(pid)) if pid else None
            hops += 1
        return None

    node_seconds: dict[str, float] = defaultdict(float)
    tin: dict[str, int] = defaultdict(int)
    tout: dict[str, int] = defaultdict(int)
    reached_nodes: set[str] = set()

    for c in children:
        if c.name in NODE_NAMES:
            reached_nodes.add(c.name)
            node_seconds[c.name] += _seconds(c)
            if c.name == "generate_translation_node":
                rs.translation_loops += 1
        if c.run_type == "llm":
            owner = nearest_node(c)
            if owner:
                i, o = _tokens(c)
                tin[owner] += i
                tout[owner] += o

    rs.node_seconds = dict(node_seconds)
    rs.node_tokens_in = dict(tin)
    rs.node_tokens_out = dict(tout)

    # pair + translation_type from extract_input output
    ei = next((c for c in children if c.name == "extract_input"), None)
    if ei:
        o = _outputs_dict(ei)
        src, dst = o.get("source_target"), o.get("destination_target")
        if src and dst:
            rs.pair = f"{src} -> {dst}"
        rs.translation_type = str(o.get("translation_type") or rs.translation_type)

    # per-query equivalence (execution-equivalence ground truth)
    per_query = _scrape_equivalence(children)
    rs.queries_total = len(per_query)
    rs.queries_equivalent = sum(1 for v in per_query.values() if v)
    rs.all_equivalent = (rs.queries_total > 0 and all(per_query.values())) if per_query else None

    # --- funnel (node-reached driven) ---
    rs.reached["extract_input"] = "extract_input" in reached_nodes
    rs.reached["schema_inspection"] = "schema_inspection" in reached_nodes
    rs.reached["generate_translation"] = "generate_translation_node" in reached_nodes
    # reaching equivalence (queries) or finalize after a schema-only validation pass means the
    # harnesses compiled and executed.
    rs.reached["compiled_executed"] = (
        "check_query_equivalence_node" in reached_nodes
        or ("finalize_translation_node" in reached_nodes and rs.translation_type == "schema")
    )
    if rs.all_equivalent is not None:
        rs.reached["equivalent"] = rs.all_equivalent
    else:  # schema-only: no query equivalence; compile/exec pass stands in
        rs.reached["equivalent"] = rs.reached["compiled_executed"]

    # Judge verdict from the real ACCEPT/REJECT signal. Schema-only runs auto-accept via
    # route_post_schema_validation (no evaluation_node) — label them accept_schema so they don't
    # masquerade as a judge decision in the confusion matrix.
    rs.finalize_reached = "finalize_translation_node" in reached_nodes
    verdict = _scrape_verdict(children)
    if verdict == "none" and rs.finalize_reached and "evaluation_node" not in reached_nodes:
        verdict = "accept_schema"
    rs.judge_verdict = verdict
    rs.judge_accept = verdict in ("ACCEPT", "accept_schema")
    rs.reached["accepted"] = rs.finalize_reached

    # terminal
    if rs.finalize_reached:
        rs.terminal = "accepted"
    elif "human_intervention_node" in reached_nodes:
        rs.terminal = "human_intervention"
    elif verdict == "REJECT":
        rs.terminal = "rejected"
    elif not rs.completed:
        rs.terminal = "in_progress"
    elif rs.single_pass:
        # A single-pass BASELINE that ended (`__end__`) without finalize is a DECIDED outcome —
        # "single-shot couldn't produce an accepted translation" is a primary baseline finding, not
        # trace flakiness. (For full-loop runs the same shape is genuine flakiness → "incomplete".)
        rs.terminal = "failed"
    else:
        rs.terminal = "incomplete"
    return rs


# --- aggregation ----------------------------------------------------------------------------
# A run is "decided" once it reaches a pipeline-controlled terminal. incomplete/in_progress traces
# (aborted, errored, or unparseable-verdict) are excluded from the funnel so every conditional rate
# is a real P(pass | reached previous) and not depressed by trace flakiness.
DECIDED_TERMINALS = ("accepted", "rejected", "human_intervention", "failed")


def funnel_table(rows: list[RunSummary]) -> list[dict[str, Any]]:
    n = len(rows) or 1
    out, prev = [], n
    for s in STAGES:
        k = sum(1 for r in rows if r.reached[s])
        out.append({
            "stage": s,
            "passed": k,
            "of_total_pct": round(100 * k / n, 1),
            "conditional_pct": round(100 * k / prev, 1) if prev else 0.0,
        })
        prev = k or prev
    return out


def per_node_cost(rows: list[RunSummary]) -> list[dict[str, Any]]:
    names: set[str] = set()
    for r in rows:
        names |= set(r.node_seconds) | set(r.node_tokens_in)
    total_time = sum(sum(r.node_seconds.values()) for r in rows) or 1.0
    out = []
    for name in names:
        s = sum(r.node_seconds.get(name, 0.0) for r in rows)
        out.append({
            "node": name,
            "mean_s": round(s / (len(rows) or 1), 2),
            "total_s": round(s, 1),
            "pct_of_total_time": round(100 * s / total_time, 1),
            "tokens_in": sum(r.node_tokens_in.get(name, 0) for r in rows),
            "tokens_out": sum(r.node_tokens_out.get(name, 0) for r in rows),
        })
    return sorted(out, key=lambda d: -d["pct_of_total_time"])


def confusion_matrix(rows: list[RunSummary]) -> dict[str, Any]:
    """Judge ACCEPT/REJECT vs execution-equivalence ground truth (precision/recall/accuracy).

    Positive = judge ACCEPT; truth-positive = all queries equivalent. Only runs with a DEFINITE
    LLM-judge verdict (ACCEPT or REJECT) AND a ground-truth equivalence label are counted —
    schema-only auto-accepts, error verdicts, and in-progress/aborted traces are excluded so the
    FP/TN cells (the judge-quality cells) can populate honestly.
    """
    tp = fp = fn = tn = 0
    for r in rows:
        if r.judge_verdict not in ("ACCEPT", "REJECT") or r.all_equivalent is None:
            continue
        if r.judge_accept and r.all_equivalent:
            tp += 1
        elif r.judge_accept and not r.all_equivalent:
            fp += 1
        elif not r.judge_accept and r.all_equivalent:
            fn += 1
        else:
            tn += 1
    total = tp + fp + fn + tn
    prec = tp / (tp + fp) if (tp + fp) else None
    rec = tp / (tp + fn) if (tp + fn) else None
    acc = (tp + tn) / total if total else None
    far = fp / (fp + tn) if (fp + tn) else None   # false-accept rate
    frr = fn / (fn + tp) if (fn + tp) else None   # false-reject rate
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "n": total,
            "precision": prec, "recall": rec, "accuracy": acc,
            "false_accept_rate": far, "false_reject_rate": frr}


def computational_accuracy(rows: list[RunSummary]) -> dict[str, Any]:
    q = sum(r.queries_total for r in rows)
    eq = sum(r.queries_equivalent for r in rows)
    return {"queries_total": q, "queries_equivalent": eq,
            "pass_at_1": round(eq / q, 4) if q else None}


def _round(x: Any, n: int = 4) -> Any:
    return round(x, n) if isinstance(x, float) else x


# --- output ---------------------------------------------------------------------------------
def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", default=None, help="LangSmith project (default: $LANGSMITH_PROJECT)")
    ap.add_argument("--dataset", default="wwi", help="dataset label stamped on every run")
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--graph-name", default="Universal Object Mapping Translator",
                    help="root span name of the graph invocation (filters out stray roots); "
                         "pass '' to disable filtering")
    ap.add_argument("--env", default="../.env", help="path to .env with LANGSMITH_* (relative to cwd)")
    ap.add_argument("--out", default="./out")
    ap.add_argument("--stratify", action="store_true", help="also emit per-(pair) funnel/cost")
    args = ap.parse_args()

    try:
        from dotenv import load_dotenv
        load_dotenv(args.env)
    except Exception:
        pass
    project = args.project or os.environ.get("LANGSMITH_PROJECT")
    if not project:
        raise SystemExit("set --project or LANGSMITH_PROJECT")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows: list[RunSummary] = []
    for root, client in fetch_root_runs(project, args.limit, args.graph_name or None):
        try:
            rows.append(summarize_run(root, client, args.dataset))
        except Exception as e:
            print(f"[warn] run {getattr(root, 'id', '?')}: {e}")

    if not rows:
        print("no runs found")
        return

    decided = [r for r in rows if r.terminal in DECIDED_TERMINALS]
    excluded = [r for r in rows if r.terminal not in DECIDED_TERMINALS]
    # The linear funnel's "equivalent" stage only applies to query-bearing runs (query/both).
    # Schema-only (and unclassified) runs take a different path (validate_schema -> finalize, no
    # query equivalence) — funnelling them linearly makes "accepted" exceed "equivalent". Run the
    # funnel over query-bearing decided runs and report the other-path accepts separately.
    query_runs = [r for r in decided if r.translation_type in ("query", "both")]
    other_runs = [r for r in decided if r.translation_type not in ("query", "both")]
    other_accepted = sum(1 for r in other_runs if r.terminal == "accepted")
    funnel = funnel_table(query_runs)
    cost = per_node_cost(rows)
    cm = confusion_matrix(rows)
    comp = computational_accuracy(rows)

    print(f"\n=== {len(rows)} runs  (project: {project}, dataset: {args.dataset}) ===")
    print(f"\n-- E1 funnel (over {len(query_runs)} query-bearing decided runs; "
          f"{len(excluded)} excluded incomplete/in-progress, "
          f"{len(other_runs)} schema/other-path [{other_accepted} accepted]) --")
    for r in funnel:
        print(f"{r['stage']:<20} {r['passed']:>3}  ({r['of_total_pct']:>5}% total, "
              f"{r['conditional_pct']:>5}% conditional)")

    print("\n-- terminals --")
    for k, v in Counter(r.terminal for r in rows).most_common():
        print(f"{k:<20} {v}")
    in_progress = sum(1 for r in rows if not r.completed)
    print(f"\n-- judge verdicts --")
    for k, v in Counter(r.judge_verdict for r in rows).most_common():
        print(f"{k:<20} {v}")
    hi = sum(1 for r in rows if r.terminal == "human_intervention")
    print(f"\nhuman-intervention rate: {hi}/{len(rows)}   in-progress (not ended): {in_progress}")
    print(f"mean translation loops:  {sum(r.translation_loops for r in rows) / len(rows):.2f}")
    print(f"mean e2e seconds:        {sum(r.e2e_seconds for r in rows) / len(rows):.1f}")

    print("\n-- E4 per-node cost --")
    for r in cost:
        print(f"{r['node']:<28} {r['mean_s']:>7}s  {r['pct_of_total_time']:>5}%  "
              f"in={r['tokens_in']} out={r['tokens_out']}")

    print("\n-- computational accuracy (pass@1, per-query exec-equivalence) --")
    print(f"  {comp['queries_equivalent']}/{comp['queries_total']} queries equivalent  "
          f"pass@1={comp['pass_at_1']}")

    print("\n-- judge vs execution-equivalence (verifier confusion matrix) --")
    print(f"  TP={cm['tp']} FP={cm['fp']} FN={cm['fn']} TN={cm['tn']}  (n={cm['n']})")
    print(f"  precision={_round(cm['precision'])} recall={_round(cm['recall'])} "
          f"accuracy={_round(cm['accuracy'])} FAR={_round(cm['false_accept_rate'])} "
          f"FRR={_round(cm['false_reject_rate'])}")

    write_csv(out_dir / "funnel.csv", funnel)
    write_csv(out_dir / "per_node_cost.csv", cost)
    write_csv(out_dir / "runs.csv",
              [{k: v for k, v in asdict(r).items() if not isinstance(v, dict)} for r in rows])
    (out_dir / "summary.json").write_text(json.dumps(
        {"n_runs": len(rows), "n_decided": len(decided), "n_excluded": len(excluded),
         "n_query_funnel": len(query_runs), "n_other_path": len(other_runs),
         "other_path_accepted": other_accepted,
         "project": project, "dataset": args.dataset,
         "funnel": funnel, "per_node_cost": cost,
         "confusion_matrix": cm, "computational_accuracy": comp,
         "terminals": dict(Counter(r.terminal for r in rows))}, indent=2))

    if args.stratify:
        by_pair: dict[str, list[RunSummary]] = defaultdict(list)
        for r in rows:
            by_pair[r.pair].append(r)
        strat = []
        for pair, prs in sorted(by_pair.items()):
            cmp = confusion_matrix(prs)
            comp_p = computational_accuracy(prs)
            strat.append({"pair": pair, "n": len(prs),
                          "accepted": sum(1 for r in prs if r.terminal == "accepted"),
                          "pass_at_1": comp_p["pass_at_1"],
                          "precision": _round(cmp["precision"]), "recall": _round(cmp["recall"])})
        write_csv(out_dir / "by_pair.csv", strat)
        print("\n-- by pair --")
        for s in strat:
            print(f"  {s['pair']:<45} n={s['n']} accepted={s['accepted']} "
                  f"pass@1={s['pass_at_1']} P={s['precision']} R={s['recall']}")

    print(f"\nwrote CSVs + summary.json to {out_dir}")


if __name__ == "__main__":
    main()
