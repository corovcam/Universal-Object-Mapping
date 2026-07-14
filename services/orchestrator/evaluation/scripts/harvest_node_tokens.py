#!/usr/bin/env python3
"""harvest_node_tokens.py — per-node LLM token/time attribution for exported experiment runs.

Why: the `tokens` column of an exported experiment CSV is the WHOLE pipeline run (intent
extraction + schema inspection + the translation loop). The SOTA external arms only ever do the
"translation" part (they receive the already-exported prompt), so a fair resource comparison
(fig8) needs our tokens restricted to the translation loop: every node from
generate_translation_node onward (generation, validation, equivalence, judge, finalize),
across ALL loop iterations.

Reads each exported experiment CSV under --traces, resolves the root run id from the `run`
blob, fetches the trace's child runs from LangSmith once, attributes every llm span to its
nearest ancestor graph node (same walk as aggregate_traces.py), and writes one row per run:

  run_id, session, pair, rep, total_tokens_in/out, loop_tokens_in/out, loop_tokens,
  loop_seconds, unattributed_tokens, per-node in/out columns.

The result is cached as a CSV so plot_final.py never needs LangSmith at plot time:

  uv run python evaluation/scripts/harvest_node_tokens.py \
      --traces evaluation/traces/10-7-2026 --out evaluation/out/node_tokens.csv --env .env.dev
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aggregate_traces import (  # noqa: E402
    NODE_NAMES, _scrape_equivalence, _seconds, _tokens,
)

# The translation loop = everything from the generation node onward (all iterations).
PRE_LOOP_NODES = {"extract_input", "schema_inspection"}
LOOP_NODES = NODE_NAMES - PRE_LOOP_NODES

csv.field_size_limit(10**9)


def load_env(path: str) -> None:
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _retry(fn, tries: int = 4, wait: float = 20.0):
    """LangSmith EU intermittently 502s under load — retry with a flat backoff."""
    import time
    for attempt in range(tries):
        try:
            return fn()
        except Exception as e:
            if attempt == tries - 1:
                raise
            print(f"  [retry {attempt + 1}/{tries}] {e}", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError("unreachable")


def harvest_run(client, run_id: str) -> dict | None:
    try:
        root = _retry(lambda: client.read_run(run_id))
        children = _retry(lambda: list(
            client.list_runs(trace_id=str(root.trace_id), is_root=False)))
    except Exception as e:  # trace evicted / quota gap — report, don't die
        print(f"  [warn] {run_id}: {e}", file=sys.stderr)
        return None
    byid = {str(c.id): c for c in children}
    byid[str(root.id)] = root

    def nearest_node(run) -> str | None:
        cur, hops = run, 0
        while cur is not None and hops < 40:
            if cur.name in NODE_NAMES:
                return cur.name
            pid = getattr(cur, "parent_run_id", None)
            cur = byid.get(str(pid)) if pid else None
            hops += 1
        return None

    tin: dict[str, int] = defaultdict(int)
    tout: dict[str, int] = defaultdict(int)
    secs: dict[str, float] = defaultdict(float)
    stray_in = stray_out = 0
    for c in children:
        if c.name in NODE_NAMES:
            secs[c.name] += _seconds(c)
        if c.run_type == "llm":
            i, o = _tokens(c)
            owner = nearest_node(c)
            if owner:
                tin[owner] += i
                tout[owner] += o
            else:
                stray_in += i
                stray_out += o

    row: dict = {
        "total_tokens_in": sum(tin.values()) + stray_in,
        "total_tokens_out": sum(tout.values()) + stray_out,
        "loop_tokens_in": sum(v for k, v in tin.items() if k in LOOP_NODES),
        "loop_tokens_out": sum(v for k, v in tout.items() if k in LOOP_NODES),
        "loop_seconds": round(sum(v for k, v in secs.items() if k in LOOP_NODES), 1),
        "unattributed_tokens": stray_in + stray_out,
    }
    row["loop_tokens"] = row["loop_tokens_in"] + row["loop_tokens_out"]
    # per-query final equivalence (LAST check_query_equivalence span wins) — feeds the
    # per-query difficulty heatmap without relying on the recordings' escaping quirks
    row["query_equivalence"] = json.dumps(_scrape_equivalence(children), sort_keys=True)
    for n in sorted(NODE_NAMES):
        row[f"{n}_in"] = tin.get(n, 0)
        row[f"{n}_out"] = tout.get(n, 0)
        row[f"{n}_s"] = round(secs.get(n, 0.0), 1)
    return row


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--traces", default="evaluation/traces/10-7-2026")
    ap.add_argument("--out", default="evaluation/out/node_tokens.csv")
    ap.add_argument("--env", default=".env.dev")
    ap.add_argument("--workers", type=int, default=3,
                    help="parallel trace fetches (LangSmith EU 502s under load — keep modest)")
    args = ap.parse_args()
    load_env(args.env)

    import threading
    from concurrent.futures import ThreadPoolExecutor

    from langsmith import Client
    client = Client()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    done: set[str] = set()
    if out.exists():  # resume: skip runs already harvested
        done = {r["run_id"] for r in csv.DictReader(open(out, newline=""))}
        print(f"resuming — {len(done)} runs already in {out}")

    todo: list[dict] = []
    for cf in sorted(Path(args.traces).glob("*.csv")):
        for r in csv.DictReader(open(cf, newline="")):
            try:
                rid = json.loads(r["run"])["id"]
            except Exception:
                continue
            if rid in done:
                continue
            todo.append({"rid": rid, "session": cf.stem, "rep": r.get("repetition"),
                         "pair": (json.loads(r["outputs"] or "{}") or {}).get("pair", ""),
                         "csv_tokens": r.get("tokens")})

    lock = threading.Lock()
    new_file = not out.exists()
    fh = out.open("a", newline="", encoding="utf-8")
    writer: list = [None]  # DictWriter created on first row (needs fieldnames)

    def work(t: dict) -> None:
        nonlocal new_file
        h = harvest_run(client, t["rid"])
        if h is None:
            return
        row = {"run_id": t["rid"], "session": t["session"], "pair": t["pair"],
               "rep": t["rep"], "csv_tokens": t["csv_tokens"], **h}
        with lock:
            if writer[0] is None:
                writer[0] = csv.DictWriter(fh, fieldnames=list(row))
                if new_file:
                    writer[0].writeheader()
                    new_file = False
            writer[0].writerow(row)
            fh.flush()
            print(f"{t['session']} rep={t['rep']} loop={row['loop_tokens'] / 1e6:.2f}M "
                  f"total={(row['total_tokens_in'] + row['total_tokens_out']) / 1e6:.2f}M",
                  flush=True)

    print(f"harvesting {len(todo)} runs with {args.workers} workers ...", flush=True)
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        list(ex.map(work, todo))
    fh.close()

    rows = list(csv.DictReader(open(out, newline="")))
    if not rows:
        sys.exit("no runs harvested")
    loops = [float(r["loop_tokens"]) for r in rows]
    tot = [float(r["total_tokens_in"]) + float(r["total_tokens_out"]) for r in rows]
    print(f"\n{out}: {len(rows)} rows")
    print(f"loop tokens mean {sum(loops)/len(loops)/1e6:.2f}M of total mean "
          f"{sum(tot)/len(tot)/1e6:.2f}M ({sum(loops)/max(1,sum(tot)):.0%})")


if __name__ == "__main__":
    main()
