#!/usr/bin/env python3
"""plot_final.py — the FINAL thesis figures for the UOM evaluation.

Built for the 2026-07-09/10 canonical run (tag 20260709-150203: 6 pairs x full-15-query bundled
prompt x 10 repetitions, generator einfra/kimi-k2.7), with the SOTA external arms (claude_code /
antigravity) and the run-generation history (single-rep runs of 07-08 and 07-09) overlaid where
they exist.

Headline metric everywhere: STRICT execution equivalence — queries_equivalent / queries_expected
from the deterministic checker (count + first/last sample DeepDiff against the live source DB).
The pipeline's own `passed`/`accepted` flags fold in judge acceptances and carry-forwards; they are
shown only inside the outcome-decomposition figure, clearly labelled — never as the headline.

Figures (PNG 300dpi + PDF, light mode; palette follows the validated dataviz reference):
  fig1_equivalence      — strict equivalence per pair: mean bar + one dot per repetition.
  fig2_decomposition    — per pair, all 150 query outcomes split into: deterministically
                          equivalent / accepted-but-not-equivalent (judge or carry) / not
                          accepted / run crashed.
  fig3_pass_at_k        — strict pass@k (all 15 equivalent) per pair, k = 1,2,3,5.
  fig4_arms             — head-to-head strict equivalence vs every scored external arm
                          (claude_code, antigravity, per explicit model + effort) on the two
                          pairs all arms completed: dapper-mongo + efcore-mongo.
  fig5_cost             — mean tokens / cost / wall-clock per pair (min-max whiskers).
  fig6_judge            — graded LLM-judge scores vs strict equivalence, with Pearson r.
  fig8_arms_resources   — tokens (ours: translation loop only) / price / wall vs the SOTA arms.
  fig9_codebleu         — CodeBLEU + its components (n-gram/AST/data-flow) per artifact per arm.
  fig10_query_heatmap   — per-query strict-equivalence rate, pair x query (needs node_tokens.csv).
  fig11_stage_tokens    — mean LLM tokens per pipeline stage per pair (needs node_tokens.csv).
  fig12_baseline_prior_design — the PRIOR pipeline design (main branch): set A
                          (qwen3.5, small variant, 15 reps): mean equivalence + pass@k.

Usage:
  uv run --project evaluation python evaluation/scripts/plot_final.py \
      --traces evaluation/traces/10-7-2026 --out evaluation/out/charts-final
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

csv.field_size_limit(10**9)

# ---------------------------------------------------------------------------
# Palette — the validated dataviz reference instance (light mode).
# Arms set [#2a78d6, #4a3aa7, #eb6834] and outcome set [#2a78d6, #eda100, #e34948, #74736e]
# were run through validate_palette.js: arms PASS all checks; in the outcome set the yellow's
# 2.11:1 contrast WARN is relieved by direct segment labels and the gray "crashed" slot is a
# deliberate non-category (absence of data) carried by a hatch + label, not by hue.
# ---------------------------------------------------------------------------
C_OURS = "#2a78d6"      # categorical slot 1 (blue)   — our approach / equivalent
C_CLAUDE = "#4a3aa7"    # categorical slot 5 (violet) — claude_code arm
C_AGY = "#eb6834"       # categorical slot 8 (orange) — antigravity arm
C_JUDGE = "#eda100"     # categorical slot 3 (yellow) — accepted, not strictly equivalent
C_FAIL = "#e34948"      # categorical slot 6 (red)    — not accepted
C_CRASH = "#74736e"     # neutral                     — run crashed (hatched, labelled)
INK = "#0b0b0b"
INK_2 = "#52514e"
GRID = "#e4e3df"
SURFACE = "#fcfcfb"

PAIR_ORDER = ["dapper-mongo", "efcore-mongo", "nhib-mongo",
              "dapper-neo4j", "efcore-neo4j", "nhib-neo4j"]
PAIR_LABEL = {
    "dapper-mongo": "Dapper\n→ Mongo", "efcore-mongo": "EF Core\n→ Mongo",
    "nhib-mongo": "NHibernate\n→ Mongo", "dapper-neo4j": "Dapper\n→ Neo4j",
    "efcore-neo4j": "EF Core\n→ Neo4j", "nhib-neo4j": "NHibernate\n→ Neo4j",
}
# The dataset pair-slug spellings used by results.csv / codebleu.csv for the pairs where
# external arms were actually run (mongo targets; the neo4j arms died on the SOTA side —
# claude-sonnet-5 hit the 64k output-token ceiling, antigravity failed to compile).
PAIR_SLUG = {
    "dapper-mongo": "net-dapper__java-spring-data-mongodb",
    "efcore-mongo": "net-entity-framework-core__java-spring-data-mongodb",
    "nhib-mongo": "net-nhibernate__java-spring-data-mongodb",
}
ARM_PAIRS = ["dapper-mongo", "efcore-mongo"]  # pairs shown in the head-to-head figures

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "text.color": INK, "axes.labelcolor": INK_2, "xtick.color": INK_2, "ytick.color": INK_2,
    "axes.edgecolor": GRID, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.axisbelow": True, "font.size": 10.5, "axes.titlesize": 12, "axes.titleweight": "bold",
    "axes.spines.top": False, "axes.spines.right": False,
    "svg.fonttype": "none",
})


def _f(x, d=None):
    try:
        return float(x)
    except (TypeError, ValueError):
        return d


def _pair_of(fname: str) -> str | None:
    for p in PAIR_ORDER:
        if p in fname:
            return p
    return None


def load_run(traces: Path) -> dict[str, list[dict]]:
    """Per-pair rows of one exported run (flat dir of per-pair CSVs)."""
    per_pair: dict[str, list[dict]] = defaultdict(list)
    for cf in sorted(traces.glob("*.csv")):
        pair = _pair_of(cf.name)
        if not pair:
            continue
        for r in csv.DictReader(open(cf, newline="")):
            eq = _f(r.get("queries_equivalent"), 0.0) or 0.0
            exp = _f(r.get("queries_expected"), 15.0) or 15.0
            acc = _f(r.get("queries_accepted"), 0.0) or 0.0
            out = {}
            try:
                out = json.loads(r["outputs"]) if r.get("outputs") else {}
            except Exception:
                out = {}
            per_pair[pair].append({
                "rep": int(_f(r.get("repetition"), 0) or 0),
                "eq": eq, "exp": exp, "acc": acc,
                "strict": eq >= exp,
                "crashed": (acc == 0 and eq == 0
                            and (_f(r.get("compile_pass"), 0.0) or 0.0) < 1.0),
                "loops": _f(r.get("translation_loops"), 0.0) or 0.0,
                "tokens": _f(r.get("tokens"), 0.0) or 0.0,
                "cost": _f(r.get("total_cost"), 0.0) or 0.0,
                "wall": _f(r.get("wall_clock_s"), 0.0) or 0.0,
                "judge_te": _f(r.get("translation_equivalence")),
                "judge_cc": _f(r.get("code_correctness")),
                "judge_fa": _f(r.get("faithfulness")),
                "error": (out or {}).get("error"),
            })
    return per_pair


def pass_at_k(n: int, c: int, k: int) -> float | None:
    """Unbiased pass@k estimator (Chen et al. 2021): 1 - C(n-c, k)/C(n, k)."""
    if n < k:
        return None
    if n - c < k:
        return 1.0
    return 1.0 - math.comb(n - c, k) / math.comb(n, k)


def _label_bars(ax, bars, fmt="{:.2f}", dy=0.012, fs=9.5):
    for b in bars:
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + dy, fmt.format(b.get_height()),
                ha="center", va="bottom", fontsize=fs, color=INK)


def _finish(ax, ylab, ymax=1.06):
    ax.set_ylim(0, ymax)
    ax.set_ylabel(ylab)
    ax.grid(axis="x", visible=False)


def fig1_equivalence(per_pair, out: Path):
    fig, ax = plt.subplots(figsize=(8.0, 4.2))
    xs = range(len(PAIR_ORDER))
    means = []
    for i, p in enumerate(PAIR_ORDER):
        fr = [r["eq"] / r["exp"] for r in per_pair[p]]
        means.append(sum(fr) / len(fr))
    bars = ax.bar(xs, means, width=0.62, color=C_OURS, zorder=2)
    # one dot per repetition, jittered — the distribution is the story (bimodal on Neo4j)
    for i, p in enumerate(PAIR_ORDER):
        fr = [r["eq"] / r["exp"] for r in per_pair[p]]
        off = [(-0.14 + 0.28 * j / max(1, len(fr) - 1)) for j in range(len(fr))]
        ax.scatter([i + o for o in off], fr, s=26, facecolor=SURFACE, edgecolor=INK_2,
                   linewidth=1.1, zorder=3)
    for b in bars:  # value INSIDE the bar so it never collides with the rep dots
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() - 0.05,
                f"{b.get_height():.2f}", ha="center", va="top", fontsize=10,
                color=SURFACE, fontweight="bold", zorder=4)
    ax.set_xticks(list(xs), [PAIR_LABEL[p] for p in PAIR_ORDER])
    _finish(ax, "Strict execution equivalence")
    n = len(per_pair[PAIR_ORDER[0]])
    ax.set_title(f"Strict execution equivalence — mean of {n} reps (dots = runs)")
    fig.tight_layout()
    fig.savefig(out / "fig1_equivalence.png", dpi=300)
    fig.savefig(out / "fig1_equivalence.pdf")
    plt.close(fig)


def fig2_decomposition(per_pair, out: Path):
    fig, ax = plt.subplots(figsize=(8.0, 4.4))
    cats = {  # per pair: query counts over all reps
        p: {"equiv": 0, "accepted_not_equiv": 0, "not_accepted": 0, "crashed": 0}
        for p in PAIR_ORDER
    }
    for p in PAIR_ORDER:
        for r in per_pair[p]:
            if r["crashed"]:
                cats[p]["crashed"] += int(r["exp"])
                continue
            cats[p]["equiv"] += int(r["eq"])
            cats[p]["accepted_not_equiv"] += int(max(0, r["acc"] - r["eq"]))
            cats[p]["not_accepted"] += int(max(0, r["exp"] - max(r["acc"], r["eq"])))
    total = {p: sum(cats[p].values()) for p in PAIR_ORDER}
    xs = range(len(PAIR_ORDER))
    layers = [
        ("equiv", "Deterministically equivalent", C_OURS, None),
        ("accepted_not_equiv", "Accepted, not strictly equivalent (judge / carry-forward)",
         C_JUDGE, None),
        ("not_accepted", "Not accepted", C_FAIL, None),
        ("crashed", "Run crashed (infrastructure)", C_CRASH, "///"),
    ]
    bottoms = [0.0] * len(PAIR_ORDER)
    for key, label, color, hatch in layers:
        vals = [cats[p][key] / total[p] for p in PAIR_ORDER]
        bars = ax.bar(xs, vals, bottom=bottoms, width=0.62, color=color, hatch=hatch,
                      edgecolor=SURFACE, linewidth=1.6, label=label, zorder=2)
        for i, (b, v) in enumerate(zip(bars, vals)):
            cnt = cats[PAIR_ORDER[i]][key]
            if v >= 0.045:  # direct label every visible segment (relief rule for the yellow)
                ax.text(b.get_x() + b.get_width() / 2, bottoms[i] + v / 2, str(cnt),
                        ha="center", va="center", fontsize=9,
                        color=SURFACE if color in (C_OURS, C_FAIL) else INK)
        bottoms = [b + v for b, v in zip(bottoms, vals)]
    ax.set_xticks(list(xs), [PAIR_LABEL[p] for p in PAIR_ORDER])
    _finish(ax, "Share of all query outcomes", ymax=1.0)
    n = len(per_pair[PAIR_ORDER[0]])
    tq = total[PAIR_ORDER[0]]
    ax.set_title(f"Outcome decomposition — {tq} query slots per pair ({n} reps × 15 queries)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=2, frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(out / "fig2_decomposition.png", dpi=300)
    fig.savefig(out / "fig2_decomposition.pdf")
    plt.close(fig)


def fig3_pass_at_k(per_pair, out: Path):
    ks = [1, 2, 3, 5]
    seq = ["#9ec5f4", "#6da7ec", "#3987e5", "#1c5cab"]  # ordinal steps of the blue ramp
    fig, ax = plt.subplots(figsize=(8.6, 4.2))
    w = 0.19
    for j, k in enumerate(ks):
        vals = []
        for p in PAIR_ORDER:
            n = len(per_pair[p])
            c = sum(1 for r in per_pair[p] if r["strict"])
            vals.append(pass_at_k(n, c, k) or 0.0)
        bars = ax.bar([i + (j - 1.5) * w for i in range(len(PAIR_ORDER))], vals, width=w - 0.02,
                      color=seq[j], label=f"pass@{k}", zorder=2)
        if k in (1, 5):
            _label_bars(ax, bars, fs=8)
    ax.set_xticks(range(len(PAIR_ORDER)), [PAIR_LABEL[p] for p in PAIR_ORDER])
    _finish(ax, "P(≥1 of k runs strictly passes)")
    ax.set_title("Strict pass@k per pair (all 15 queries execution-equivalent)", pad=28)
    ax.legend(frameon=False, ncol=4, loc="lower left", bbox_to_anchor=(0.0, 1.0), fontsize=9)
    fig.tight_layout()
    fig.savefig(out / "fig3_pass_at_k.png", dpi=300)
    fig.savefig(out / "fig3_pass_at_k.pdf")
    plt.close(fig)


def _arm_defs(per_pair, ext_runs, pair: str = "dapper-mongo") -> list[dict]:
    """The chart-order arm list FOR ONE PAIR: our pipeline first, then each (approach, model)
    external arm in first-seen order, with effort-bracketed model labels and per-run fractions.
    External runs are filtered to the pair — the arms were re-run per pair on 2026-07-11."""
    ours = [r["eq"] / r["exp"] for r in per_pair[pair]]
    arms = [{"key": "ours", "title": "Our pipeline\neinfra/kimi-k2.7",
             "color": C_OURS, "fracs": ours, "runs": None}]
    pair_runs = [r for r in ext_runs if r["pair_slug"] == PAIR_SLUG.get(pair)]
    idx: dict[str, int] = defaultdict(int)
    for approach, model, runs in group_arms(pair_runs):
        color = _arm_color(approach, idx[approach])
        idx[approach] += 1
        arms.append({"key": f"{approach}:{model}",
                     "title": f"{_ARM_TITLE[approach]}\n{_pretty_model(model)}",
                     "color": color, "fracs": [r["frac"] for r in runs], "runs": runs})
    return arms


def _arm_equiv_panel(ax, arms: list[dict], title: str):
    xs = range(len(arms))
    bars = ax.bar(xs, [sum(a["fracs"]) / len(a["fracs"]) for a in arms], width=0.6,
                  color=[a["color"] for a in arms], zorder=2)
    for i, a in enumerate(arms):  # per-run dots wherever n > 1
        if len(a["fracs"]) > 1:
            ax.scatter([i] * len(a["fracs"]), a["fracs"], s=26, facecolor=SURFACE,
                       edgecolor=INK_2, linewidth=1.1, zorder=3)
    for b, a in zip(bars, arms):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.012,
                f"{b.get_height():.2f} (n={len(a['fracs'])})", ha="center", va="bottom",
                fontsize=8.5, color=INK)
    ax.set_xticks(list(xs), [a["title"] for a in arms], fontsize=7.5,
                  rotation=16, ha="right")
    _finish(ax, "Strict execution equivalence")
    ax.set_title(title)


def fig4_arms(per_pair, ext_runs: list[dict], out: Path):
    """Strict equivalence head-to-head on the two pairs every arm actually completed:
    dapper→mongo (all arms incl. claude-opus-4-8) and efcore→mongo (all but opus).
    CodeBLEU per arm lives in fig9."""
    fig, axes = plt.subplots(1, 2, figsize=(12.0, 4.4))
    for ax, pair in zip(axes, ARM_PAIRS):
        arms = _arm_defs(per_pair, ext_runs, pair)
        _arm_equiv_panel(ax, arms, f"{PAIR_LABEL[pair].replace(chr(10), ' ')}: "
                                   "strict equivalence")
    fig.suptitle("Head-to-head vs SOTA coding agents — same task, same checker "
                 "(bars = mean, dots = individual runs)", y=1.0,
                 fontsize=12, fontweight="bold")
    fig.tight_layout()
    fig.savefig(out / "fig4_arms.png", dpi=300)
    fig.savefig(out / "fig4_arms.pdf")
    plt.close(fig)


_EFFORTS = {"low", "medium", "high", "xhigh", "max"}
C_AGY2 = "#b34d17"     # second antigravity model: darker step of the orange slot
C_CLAUDE2 = "#8a7fd6"  # second claude_code model: lighter step of the violet slot


def _pretty_model(label: str) -> str:
    """'claude-opus-4-8-high' -> 'claude-opus-4-8 (high)' — reasoning effort in brackets."""
    base, _, eff = label.rpartition("-")
    if eff in _EFFORTS and base:
        return f"{base} ({eff})"
    return label


def load_external_runs() -> list[dict]:
    """One dict per scored external-arm run (results.csv is one appended row per scoring)."""
    runs = []
    for approach in ("claude_code", "antigravity"):
        p = Path(f"evaluation/out/external/{approach}/results.csv")
        if not p.exists():
            continue
        for r in csv.DictReader(open(p)):
            runs.append({
                "approach": approach,
                "model": r["model"],
                "pair_slug": r.get("pair_slug") or "",
                "run8": (r.get("run_id") or "")[:8],
                "frac": ((_f(r["queries_equivalent"], 0) or 0)
                         / (_f(r["queries_expected"], 15) or 15)),
                "wall_val": _f(r.get("wall_clock_validation_s"), 0.0) or 0.0,
            })
    return runs


def group_arms(runs: list[dict]) -> list[tuple[str, str, list[dict]]]:
    """[(approach, model, runs)] in first-seen (chronological) order."""
    order: list[tuple[str, str]] = []
    bykey: dict[tuple[str, str], list[dict]] = {}
    for r in runs:
        k = (r["approach"], r["model"])
        if k not in bykey:
            bykey[k] = []
            order.append(k)
        bykey[k].append(r)
    return [(a, m, bykey[(a, m)]) for a, m in order]


_ARM_TITLE = {"claude_code": "Claude Code", "antigravity": "Antigravity"}


def _arm_color(approach: str, model_idx: int) -> str:
    if approach == "claude_code":
        return C_CLAUDE if model_idx == 0 else C_CLAUDE2
    return C_AGY if model_idx == 0 else C_AGY2


# Per-run generation resources of the external arms, keyed by run_id[:8] from results.csv.
# NOTHING here is estimated (user rule: never invent token counts/prices):
#   * c8ed97f3 (claude_code, opus-4.8 high, dapper-mongo) — API-reported usage from the arm's
#     own session transcript (persisted as conversation-claude_code-*.jsonl next to the
#     capture); single call, output includes extended thinking. Wall from transcript timestamps.
#   * b714e55b / 9d86b0ea (claude_code, sonnet-5 high, dapper-mongo / efcore-mongo,
#     2026-07-11) — API-reported usage from usage-claude_code-claude-sonnet-5-high.json
#     (single call each). Priced at the sonnet-5 INTRODUCTORY list price in effect on the
#     run date ($2/MTok in, $10/MTok out through 2026-08-31; standard list $3/$15) —
#     cache write 1.25x in, cache read 0.1x in.
#   * e81060db (antigravity, gemini-3.5-flash rep1, 2026-07-09) — the agy CLI exposes NO usage
#     (no OTEL export; /context is interactive-only). Wall from capture birth -> mtime.
#   * a5b1ac97 (flash rep2, 2026-07-10) — the re-run overwrote the capture file in place, so
#     even the generation wall is unrecoverable: everything "not reported".
#   * 262a930a (antigravity, gemini-3.1-pro, 2026-07-10) — wall from prompt mtime -> capture
#     mtime (1783721268 -> 1783721491); no usage.
#   * All 2026-07-11 antigravity re-runs (f9c11e14, d6f3891b, 8c33034c, 53194d8a, efcore/nhib
#     runs) — no usage, and the in-place capture overwrites make even the generation wall
#     unmeasurable: everything "not reported".
# Opus price: verified list price 2026-07-10 (claude-api skill / platform.claude.com):
# claude-opus-4-8 $5/MTok in, $25/MTok out; cache write 1.25x in, cache read 0.1x in.
_EXT_GEN: dict[str, dict] = {
    "c8ed97f3": {
        "wall_s": 1309.0,
        "tokens": {"input": 4, "cache_write": 109_929, "cache_read": 54_784, "output": 87_972},
        "price": {"input": 5.0, "cache_write": 6.25, "cache_read": 0.50, "output": 25.0},
    },
    "b714e55b": {  # sonnet-5 (high), dapper-mongo
        "wall_s": 506.0,
        "tokens": {"input": 2, "cache_write": 62_800, "cache_read": 0, "output": 58_922},
        "price": {"input": 2.0, "cache_write": 2.50, "cache_read": 0.20, "output": 10.0},
    },
    "9d86b0ea": {  # sonnet-5 (high), efcore-mongo
        "wall_s": 450.0,
        "tokens": {"input": 2, "cache_write": 59_050, "cache_read": 4_697, "output": 59_991},
        "price": {"input": 2.0, "cache_write": 2.50, "cache_read": 0.20, "output": 10.0},
    },
    "e81060db": {"wall_s": 73.0, "tokens": None, "price": None},
    "a5b1ac97": {"wall_s": None, "tokens": None, "price": None},
    "262a930a": {"wall_s": 223.0, "tokens": None, "price": None},
}


def load_loop_tokens(path: Path = Path("evaluation/out/node_tokens.csv"),
                     pair: str = "dapper-mongo") -> list[float]:
    """Per-rep translation-loop token totals (generate_translation_node onward, all loop
    iterations) harvested from LangSmith by harvest_node_tokens.py. Empty if not harvested."""
    if not path.exists():
        return []
    return [float(r["loop_tokens"]) for r in csv.DictReader(open(path))
            if pair in (r.get("session") or "")]


def _reference_runs(ref_root: Path = Path("evaluation/reference/wwi/full")) -> set[str]:
    """Prediction-dir names frozen as the CodeBLEU reference (score 1.0 by construction) —
    excluded from their own arm's aggregates. See freeze_reference.py / provenance.json."""
    prov = ref_root / "provenance.json"
    if not prov.exists():
        return set()
    data = json.loads(prov.read_text(encoding="utf-8"))
    return {v["pred_dir"].split("/")[-1] for v in data.values()}


def fig8_arms_resources(per_pair, ext_runs: list[dict], out: Path):
    """Tokens / price / wall-clock, our pipeline vs the single-shot SOTA arms.

    Fairness note: the external arms only ever perform the TRANSLATION step (they receive the
    pipeline's exported prompt), so our token bar counts only the translation loop
    (generate_translation_node onward, all iterations — harvested per-node from LangSmith),
    not intent extraction / schema inspection. Price and wall clock remain whole-run (the
    loop dominates both; per-node prices are not itemizable in LiteLLM's cost tracking)."""
    arms = _arm_defs(per_pair, ext_runs)
    ours = per_pair["dapper-mongo"]
    loop_tokens = load_loop_tokens()
    our_tok = [t / 1e6 for t in loop_tokens] or [r["tokens"] / 1e6 for r in ours]
    tok_label = ("LLM tokens (millions) — translation loop only" if loop_tokens
                 else "LLM tokens (millions)")

    def gen(run8: str) -> dict:
        return _EXT_GEN.get(run8, {"wall_s": None, "tokens": None, "price": None})

    def ext_tokens(runs) -> float | None:
        vals = [sum(g["tokens"].values()) / 1e6 for r in runs
                if (g := gen(r["run8"]))["tokens"]]
        return sum(vals) / len(vals) if vals else None

    def ext_cost(runs) -> float | None:
        vals = []
        for r in runs:
            g = gen(r["run8"])
            if g["tokens"] and g["price"]:
                vals.append(sum(g["tokens"][k] / 1e6 * g["price"][k] for k in g["tokens"]))
        return sum(vals) / len(vals) if vals else None

    def ext_wall(runs) -> float | None:
        vals = [(g["wall_s"] + r["wall_val"]) / 60.0 for r in runs
                if (g := gen(r["run8"]))["wall_s"] is not None]
        return sum(vals) / len(vals) if vals else None

    panels = [
        (tok_label, our_tok, ext_tokens),
        ("Price (USD) — whole run", [r["cost"] for r in ours], ext_cost),
        ("Wall clock (minutes) — whole run", [r["wall"] / 60.0 for r in ours], ext_wall),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(12.5, 4.7))
    for ax, (ylab, our_vals, ext_fn) in zip(axes, panels):
        mean_ours = sum(our_vals) / len(our_vals)
        vals = [mean_ours] + [ext_fn(a["runs"]) for a in arms[1:]]
        drawn = [v if v is not None else 0.0 for v in vals]
        ax.bar(range(len(arms)), drawn, width=0.6, color=[a["color"] for a in arms],
               edgecolor=SURFACE, linewidth=1.2, zorder=2)
        # our min-max whiskers (10 reps); externals are means of their measured runs
        ax.errorbar([0], [mean_ours],
                    yerr=[[mean_ours - min(our_vals)], [max(our_vals) - mean_ours]],
                    fmt="none", ecolor=INK_2, elinewidth=1.2, capsize=3, zorder=3)
        top = max(max(drawn), max(our_vals))
        for i, v in enumerate(vals):
            if v is None:
                ax.text(i, top * 0.04, "not\nreported", ha="center", va="bottom",
                        fontsize=8.5, color=INK_2, style="italic")
                continue
            lbl = f"{v:,.2f}" if v < 10 else f"{v:,.0f}"
            y = (max(our_vals) if i == 0 else v) + top * 0.03
            ax.text(i, y, lbl, ha="center", va="bottom", fontsize=9, color=INK)
        ax.set_xticks(range(len(arms)), [a["title"] for a in arms], fontsize=7,
                      rotation=16, ha="right")
        ax.set_ylabel(ylab)
        ax.grid(axis="x", visible=False)
        ax.set_ylim(0, top * 1.22)
    fig.suptitle("Dapper → Mongo resources — our pipeline (n=10, whiskers = min–max; tokens = "
                 "translation loop only)\nvs single-shot SOTA arms (API-reported usage; the "
                 "Antigravity CLI exposes none)", fontsize=11.5, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.subplots_adjust(wspace=0.32)
    fig.savefig(out / "fig8_arms_resources.png", dpi=300)
    fig.savefig(out / "fig8_arms_resources.pdf")
    plt.close(fig)


def fig9_codebleu(codebleu_csv: Path, per_pair, ext_runs: list[dict], out: Path):
    """CodeBLEU per artifact (schema / queries) with its three stored components, per arm."""
    arms = _arm_defs(per_pair, ext_runs)
    ref_runs = _reference_runs()
    metrics = [("codebleu", "CodeBLEU"), ("ngram", "n-gram match"),
               ("syntax", "syntax (AST) match"), ("dataflow", "data-flow match")]
    # arm key -> artifact -> metric -> [values]
    data: dict[str, dict[str, dict[str, list[float]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list)))
    for r in csv.DictReader(open(codebleu_csv)):
        if r["pair"] != "net-dapper__java-spring-data-mongodb":
            continue
        if r["run"] in ref_runs:
            continue  # the frozen reference itself (scores 1.0 by construction)
        tag = r.get("run_tag") or ""
        if tag == "20260709-150203":
            key = "ours"
        elif tag.startswith("external-"):
            key = f"{tag.removeprefix('external-')}:{r['model']}"
        else:
            continue
        for mkey, _ in metrics:
            v = _f(r[mkey])
            if v is not None:
                data[key][r["artifact"]][mkey].append(v)

    arms = [a for a in arms if data.get(a["key"])]
    fig, axes = plt.subplots(1, 2, figsize=(12.0, 4.6), sharey=True)
    group_w = 0.82
    w = group_w / max(3, len(arms))
    for ax, artifact in zip(axes, ("schema", "queries")):
        for j, a in enumerate(arms):
            means, spans = [], []
            for mkey, _ in metrics:
                vs = data[a["key"]][artifact][mkey]
                m = sum(vs) / len(vs) if vs else 0.0
                means.append(m)
                spans.append((m - min(vs), max(vs) - m) if len(vs) > 1 else (0, 0))
            n = len(data[a["key"]][artifact]["codebleu"])
            label = (f"{a['title'].replace(chr(10), ' · ')} (n={n}"
                     + (", reference rep excluded" if a["key"] == "ours" else "") + ")")
            xpos = [i + (j - (len(arms) - 1) / 2) * w for i in range(len(metrics))]
            ax.bar(xpos, means, width=w - 0.03, color=a["color"],
                   label=label if artifact == "schema" else None, zorder=2)
            ax.errorbar(xpos, means, yerr=list(zip(*spans)), fmt="none", ecolor=INK_2,
                        elinewidth=1.0, capsize=2.5, zorder=3)
            for x, m, (_, hi) in zip(xpos, means, spans):
                ax.text(x, m + hi + 0.02, f"{m:.2f}", ha="center", va="bottom",
                        fontsize=7, color=INK_2, rotation=90)
        ax.set_xticks(range(len(metrics)), [lbl for _, lbl in metrics], fontsize=9)
        ax.set_title(f"{artifact} artifact")
        ax.set_ylim(0, 1.12)
        ax.grid(axis="x", visible=False)
    axes[0].set_ylabel("Score vs shared frozen reference")
    fig.suptitle("Dapper → Mongo CodeBLEU and its components per arm — vs the shared "
                 "execution-verified reference", fontsize=12, fontweight="bold")
    fig.legend(loc="lower center", bbox_to_anchor=(0.5, -0.02), ncol=2, frameon=False,
               fontsize=8.5)
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    fig.savefig(out / "fig9_codebleu.png", dpi=300)
    fig.savefig(out / "fig9_codebleu.pdf")
    plt.close(fig)


def fig5_cost(per_pair, out: Path):
    fig, axes = plt.subplots(1, 3, figsize=(11.0, 3.8))
    metrics = [("tokens", 1e6, "LLM tokens (millions)"), ("cost", 1.0, "Cost (USD)"),
               ("wall", 3600.0, "Wall clock (hours)")]
    for ax, (key, div, ylab) in zip(axes, metrics):
        means, los, his = [], [], []
        for p in PAIR_ORDER:
            vs = [r[key] / div for r in per_pair[p]]
            means.append(sum(vs) / len(vs))
            los.append(means[-1] - min(vs))
            his.append(max(vs) - means[-1])
        bars = ax.bar(range(len(PAIR_ORDER)), means, width=0.62, color=C_OURS, zorder=2)
        ax.errorbar(range(len(PAIR_ORDER)), means, yerr=[los, his], fmt="none",
                    ecolor=INK_2, elinewidth=1.2, capsize=3, zorder=3)
        pad = max(m + h for m, h in zip(means, his)) * 0.03
        for i, (m, h) in enumerate(zip(means, his)):  # above the whisker cap, never through it
            ax.text(i, m + h + pad, f"{m:.1f}", ha="center", va="bottom", fontsize=9, color=INK)
        ax.set_xticks(range(len(PAIR_ORDER)),
                      [PAIR_LABEL[p].replace("\n", " ") for p in PAIR_ORDER],
                      rotation=35, ha="right", fontsize=8)
        ax.set_ylabel(ylab)
        ax.grid(axis="x", visible=False)
        ax.set_ylim(0, max(m + h for m, h in zip(means, his)) * 1.24)
    n = len(per_pair[PAIR_ORDER[0]])
    fig.suptitle(f"Resource use per translation run — mean of {n} reps (whiskers = min–max)",
                 fontsize=12, fontweight="bold")
    fig.tight_layout()
    fig.savefig(out / "fig5_cost.png", dpi=300)
    fig.savefig(out / "fig5_cost.pdf")
    plt.close(fig)


def _pearson(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx == 0 or syy == 0:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / math.sqrt(sxx * syy)


def fig6_judge(per_pair, out: Path):
    judges = [("judge_te", "translation_equivalence", C_OURS),
              ("judge_cc", "code_correctness", C_CLAUDE),
              ("judge_fa", "faithfulness", C_AGY)]
    fig, axes = plt.subplots(1, 3, figsize=(11.0, 3.8), sharey=True)
    for ax, (key, label, color) in zip(axes, judges):
        xs, ys = [], []
        for p in PAIR_ORDER:
            for r in per_pair[p]:
                if r[key] is None:
                    continue
                xs.append(r["eq"] / r["exp"])
                ys.append(r[key])
        ax.scatter(xs, ys, s=30, facecolor=color, edgecolor=SURFACE, linewidth=1.0,
                   alpha=0.85, zorder=2)
        r_ = _pearson(xs, ys)
        ax.plot([0, 1], [0, 1], color=GRID, linewidth=1.2, zorder=1)
        ax.set_title(f"{label}\nPearson r = {r_:.2f} (n={len(xs)})", fontsize=10)
        ax.set_xlabel("Strict execution equivalence")
        ax.set_xlim(-0.04, 1.04)
        ax.set_ylim(-0.04, 1.04)
        ax.grid(axis="x", visible=False)
    axes[0].set_ylabel("Graded judge score")
    fig.suptitle("Graded LLM judges track deterministic ground truth", fontsize=12,
                 fontweight="bold")
    fig.tight_layout()
    fig.savefig(out / "fig6_judge.png", dpi=300)
    fig.savefig(out / "fig6_judge.pdf")
    plt.close(fig)


def _load_node_rows(path: Path = Path("evaluation/out/node_tokens.csv")) -> list[dict]:
    if not path.exists():
        return []
    return list(csv.DictReader(open(path)))


def fig10_query_heatmap(node_rows: list[dict], out: Path):
    """Per-query strict-equivalence rate: pair x query over all repetitions. A run that never
    reached the final equivalence check counts as NOT equivalent for every query (same
    denominator convention as fig1)."""
    if not node_rows:
        print("[fig10] node_tokens.csv missing — run harvest_node_tokens.py first")
        return
    nq = 15
    counts = {p: [0] * nq for p in PAIR_ORDER}
    denom = {p: 0 for p in PAIR_ORDER}
    for r in node_rows:
        pair = _pair_of(r.get("session") or "")
        if not pair:
            continue
        denom[pair] += 1
        eq = json.loads(r.get("query_equivalence") or "{}")
        for q, ok in eq.items():
            qid = int(str(q).removeprefix("query"))
            if 1 <= qid <= nq and ok:
                counts[pair][qid - 1] += 1

    mat = [[counts[p][j] / denom[p] if denom[p] else 0.0 for j in range(nq)]
           for p in PAIR_ORDER]
    fig, ax = plt.subplots(figsize=(9.6, 3.9))
    im = ax.imshow(mat, cmap="Blues", vmin=0, vmax=1, aspect="auto")
    for i, p in enumerate(PAIR_ORDER):
        for j in range(nq):
            v = counts[p][j]
            ax.text(j, i, str(v), ha="center", va="center", fontsize=8,
                    color=SURFACE if mat[i][j] > 0.55 else INK)
    ax.set_xticks(range(nq), [f"q{j + 1}" for j in range(nq)], fontsize=8.5)
    ax.set_yticks(range(len(PAIR_ORDER)),
                  [PAIR_LABEL[p].replace("\n", " ") for p in PAIR_ORDER], fontsize=8.5)
    ax.grid(visible=False)
    n = denom[PAIR_ORDER[0]]
    ax.set_title(f"Per-query strict equivalence — repetitions equivalent (of {n})", pad=10)
    cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.015)
    cb.set_label("equivalence rate", fontsize=9)
    fig.tight_layout()
    fig.savefig(out / "fig10_query_heatmap.png", dpi=300)
    fig.savefig(out / "fig10_query_heatmap.pdf")
    plt.close(fig)


def fig11_stage_tokens(node_rows: list[dict], out: Path):
    """Where the pipeline spends LLM tokens: mean per-run tokens per stage, per pair.
    Motivates the fig8 fairness cut: pre-loop stages are excluded from the arm comparison."""
    if not node_rows:
        print("[fig11] node_tokens.csv missing — run harvest_node_tokens.py first")
        return
    stages = [
        ("Intent extraction", ["extract_input"], "#9ec5f4"),
        ("Schema inspection", ["schema_inspection"], "#5598e7"),
        ("Generation (translation loop)", ["generate_translation_node"], C_OURS),
        ("Validation + equivalence", ["prep_schema_validation", "validate_schema_node",
                                      "prep_query_validation", "validate_query_node",
                                      "prep_query_equivalence", "check_query_equivalence_node"],
         "#1c5cab"),
        ("Judge + finalize", ["evaluation_node", "finalize_translation_node",
                              "human_intervention_node"], "#eda100"),
    ]
    tok: dict[str, dict[str, list[float]]] = {p: {s[0]: [] for s in stages} for p in PAIR_ORDER}
    sec: dict[str, dict[str, list[float]]] = {p: {s[0]: [] for s in stages} for p in PAIR_ORDER}
    for r in node_rows:
        pair = _pair_of(r.get("session") or "")
        if not pair:
            continue
        for label, nodes, _ in stages:
            tok[pair][label].append(sum(
                float(r.get(f"{n}_in") or 0) + float(r.get(f"{n}_out") or 0)
                for n in nodes) / 1e6)
            sec[pair][label].append(sum(float(r.get(f"{n}_s") or 0) for n in nodes) / 60.0)

    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.6))
    panels = [(axes[0], tok, "Mean LLM tokens per run (millions)", "{:.2f}"),
              (axes[1], sec, "Mean minutes per run", "{:.0f}")]
    xs = range(len(PAIR_ORDER))
    for ax, data, ylab, fmt in panels:
        bottoms = [0.0] * len(PAIR_ORDER)
        for label, _, color in stages:
            vals = [sum(data[p][label]) / max(1, len(data[p][label])) for p in PAIR_ORDER]
            ax.bar(xs, vals, bottom=bottoms, width=0.62, color=color,
                   label=label if ax is axes[0] else None,
                   edgecolor=SURFACE, linewidth=1.0, zorder=2)
            bottoms = [b + v for b, v in zip(bottoms, vals)]
        for i, b in enumerate(bottoms):
            ax.text(i, b + max(bottoms) * 0.015, fmt.format(b), ha="center", va="bottom",
                    fontsize=8.5, color=INK)
        ax.set_xticks(list(xs), [PAIR_LABEL[p] for p in PAIR_ORDER], fontsize=8)
        ax.set_ylabel(ylab)
        ax.set_ylim(0, max(bottoms) * 1.16)
        ax.grid(axis="x", visible=False)
    n = max(len(v) for p in PAIR_ORDER for v in tok[p].values())
    fig.suptitle(f"Pipeline resources by stage — mean of up to {n} reps "
                 "(LLM tokens left, wall time right)", fontsize=12, fontweight="bold")
    fig.legend(loc="lower center", bbox_to_anchor=(0.5, -0.02), ncol=5, frameon=False,
               fontsize=8.5)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(out / "fig11_stage_tokens.png", dpi=300)
    fig.savefig(out / "fig11_stage_tokens.pdf")
    plt.close(fig)


def fig12_baseline(out: Path,
                   root: Path = Path("evaluation/out/final/A-baseline-qwen35-small-15rep")):
    """The PRIOR pipeline design (main branch, direct harness injection, no skills/save-tools),
    canonical set A: qwen3.5 generator, small 5-query variant, 15 repetitions per pair.
    Left: mean strict equivalence per pair with per-rep dots. Right: strict pass@k.
    This is the baseline the redesigned pipeline (fig1/fig3, full 15-query variant) is
    measured against — note the variants differ (5 vs 15 queries), so compare shapes, not
    absolute numbers."""
    rows_csv = root / "rows.csv"
    if not rows_csv.exists():
        print(f"[fig12] {rows_csv} missing — skipped")
        return
    per: dict[str, list[float]] = defaultdict(list)
    for r in csv.DictReader(open(rows_csv)):
        p = r["_pair"]
        eq = _f(r.get("queries_equivalent"), 0.0) or 0.0
        exp = _f(r.get("queries_expected")) or 5.0  # small variant = 5 queries
        per[p].append(eq / exp)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.5, 4.3),
                                   gridspec_kw={"width_ratios": [1.15, 1]})
    xs = range(len(PAIR_ORDER))
    means = [sum(per[p]) / max(1, len(per[p])) for p in PAIR_ORDER]
    bars = ax1.bar(xs, means, width=0.62, color=C_OURS, zorder=2)
    for i, p in enumerate(PAIR_ORDER):
        ax1.scatter([i] * len(per[p]), per[p], s=22, facecolor=SURFACE,
                    edgecolor=INK_2, linewidth=1.0, zorder=3)
    _label_bars(ax1, bars)
    ax1.set_xticks(list(xs), [PAIR_LABEL[p] for p in PAIR_ORDER], fontsize=8)
    _finish(ax1, "Strict execution equivalence")
    ax1.set_title("Prior design: mean equivalence (dots = 15 reps)")

    ks = [1, 2, 3, 5]
    for p in PAIR_ORDER:
        n = len(per[p])
        c = sum(1 for f in per[p] if f >= 1.0)
        ys = [pass_at_k(n, c, k) or 0.0 for k in ks]
        ax2.plot(ks, ys, marker="o", markersize=5, linewidth=1.8,
                 label=PAIR_LABEL[p].replace("\n", " "))
    ax2.set_xticks(ks, [f"k={k}" for k in ks])
    ax2.set_ylim(0, 1.06)
    ax2.set_ylabel("Strict pass@k (all queries equivalent)")
    ax2.set_title("Prior design: strict pass@k")
    ax2.legend(fontsize=7.5, frameon=False, loc="upper left")
    fig.suptitle("Prior pipeline design (main branch) — qwen3.5, small 5-query variant, "
                 "15 repetitions per pair", y=1.0, fontsize=12, fontweight="bold")
    fig.tight_layout()
    fig.savefig(out / "fig12_baseline_prior_design.png", dpi=300)
    fig.savefig(out / "fig12_baseline_prior_design.pdf")
    plt.close(fig)


def write_summary(per_pair, out: Path, ext_runs: list[dict] | None = None,
                  node_rows: list[dict] | None = None):
    loop_by_pair: dict[str, list[float]] = defaultdict(list)
    for r in node_rows or []:
        p = _pair_of(r.get("session") or "")
        if p:
            loop_by_pair[p].append(float(r["loop_tokens"]) / 1e6)
    lines = ["| pair | mean equiv | strict pass@1 | pass@5 | 15/15 reps | mean loops | "
             "mean Mtok | loop Mtok | mean $ | mean wall h |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    tidy = [("pair,rep,queries_equivalent,queries_expected,queries_accepted,strict_pass,"
             "crashed,loops,tokens,cost_usd,wall_s,judge_translation_equivalence,"
             "judge_code_correctness,judge_faithfulness")]
    for p in PAIR_ORDER:
        rows = per_pair[p]
        n = len(rows)
        c = sum(1 for r in rows if r["strict"])
        eqm = sum(r["eq"] / r["exp"] for r in rows) / n
        lt = loop_by_pair.get(p) or []
        loop_mtok = f"{sum(lt) / len(lt):.2f}" if lt else "n/a"
        lines.append(
            f"| {p} | {eqm:.3f} | {c / n:.2f} | {pass_at_k(n, c, 5) or 0:.2f} | {c}/{n} | "
            f"{sum(r['loops'] for r in rows) / n:.1f} | "
            f"{sum(r['tokens'] for r in rows) / n / 1e6:.2f} | {loop_mtok} | "
            f"{sum(r['cost'] for r in rows) / n:.2f} | "
            f"{sum(r['wall'] for r in rows) / n / 3600:.2f} |")
        for r in rows:
            tidy.append(",".join(str(x) for x in (
                p, r["rep"], int(r["eq"]), int(r["exp"]), int(r["acc"]), int(r["strict"]),
                int(r["crashed"]), int(r["loops"]), int(r["tokens"]), round(r["cost"], 4),
                r["wall"], r["judge_te"], r["judge_cc"], r["judge_fa"])))
    if ext_runs:
        for pair, slug in PAIR_SLUG.items():
            pair_runs = [r for r in ext_runs if r["pair_slug"] == slug]
            if not pair_runs:
                continue
            lines += ["", f"## External SOTA arms ({pair}, full variant)", "",
                      "| arm | model (effort) | n | mean strict equiv | runs |",
                      "|---|---|---|---|---|"]
            for approach, model, runs in group_arms(pair_runs):
                fr = [r["frac"] for r in runs]
                ids = ", ".join(f"{r['run8']} ({r['frac']:.2f})" for r in runs)
                lines.append(f"| {_ARM_TITLE[approach]} | {_pretty_model(model)} | "
                             f"{len(runs)} | {sum(fr) / len(fr):.3f} | {ids} |")
    (out / "summary.md").write_text("\n".join(lines) + "\n")
    (out / "per_rep.csv").write_text("\n".join(tidy) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--traces", default="evaluation/traces/10-7-2026")
    ap.add_argument("--out", default="evaluation/out/charts-final")
    ap.add_argument("--codebleu", default="evaluation/out/codebleu.csv")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    per_pair = load_run(Path(args.traces))
    if not per_pair:
        sys.exit(f"no CSVs under {args.traces}")

    ext_runs = load_external_runs()
    fig1_equivalence(per_pair, out)
    fig2_decomposition(per_pair, out)
    fig3_pass_at_k(per_pair, out)
    fig4_arms(per_pair, ext_runs, out)
    fig5_cost(per_pair, out)
    fig6_judge(per_pair, out)
    fig8_arms_resources(per_pair, ext_runs, out)
    fig9_codebleu(Path(args.codebleu), per_pair, ext_runs, out)
    node_rows = _load_node_rows()
    fig10_query_heatmap(node_rows, out)
    fig11_stage_tokens(node_rows, out)
    fig12_baseline(out)
    write_summary(per_pair, out, ext_runs, node_rows)
    print(f"wrote figures + summary -> {out}")


if __name__ == "__main__":
    main()
