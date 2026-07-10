#!/usr/bin/env python3
"""build_eval_dataset.py — generate the bundled per-pair examples for the "UOM Final Experiments"
LangSmith dataset, to test how the translation graph GENERALIZES across source frameworks, target
stores, and a broader query set drawn from the .NET ORM benchmarks.

Design (confirmed with the user — "bundle per pair"):
  * The ~15 queries are derived from the `.NET` ORM `benchmarks/` (EFCorePerformance / DapperPerformance
    / NHibernatePerformance) and span the benchmark categories: indexed/non-indexed selection, range,
    IN, text search, paging, grouped aggregation, one-to-many / optional relationships, sorting,
    distinct, projection, and compound filters. Each is expressed in its SOURCE framework's OWN idiom
    (EFCore LINQ, Dapper raw SQL, NHibernate LINQ-over-ISession) so the source harness is realistic.
  * They operate over the SAME self-contained 4-entity WideWorldImporters subset the existing
    `tests/fixtures/input-*.txt` use (Customer / CustomerTransaction / Order / OrderLine), so the full
    schema is sent ONCE per prompt — no per-query "minimal entity subset" assembly is needed.
  * For each (source_framework, target_store) PAIR we build bundled prompts = header + full schema +
    the variant's queries. The DEFAULT variants are three 5-query batches (batch1 = Query1-5,
    batch2 = Query6-10, batch3 = Query11-15 — original numbering kept) covering 15 queries total:
    the 2026-07-02 traces showed accuracy degrading with the number of queries per prompt, and 5 at
    a time is the size the pipeline handled reliably. `small` (alias of the first 5) and `full`
    (all 15 in one prompt) remain available for comparison runs. Query16 (G2 intersect) is dropped —
    G1 already covers set operations and dropping the LAST query keeps numbering stable.
  * Six pairs: {EFCore, NHibernate, Dapper} x {Spring Data MongoDB, Spring Data Neo4j}. Each example is
    tagged in `metadata` with {pair, variant, source_fw, target_fw} so the runner can filter per pair
    client-side (no splits API) and so "15 iterations" maps to `num_repetitions=15` per pair.

The example shape matches the dataset / graph input the runner consumes:
``{"messages": [{"role": "user", "content": "<header>\\n\\n<schema>\\n\\n<queries>"}]}``.

Idempotent: examples are keyed by (pair, variant) in metadata; a re-run UPDATES the existing example
rather than duplicating. Use ``--dry-run`` to print the prompts (and a token-ish size) without touching
LangSmith; ``--pairs`` / ``--frameworks`` to restrict what is built.

    uv run python evaluation/scripts/build_eval_dataset.py --dry-run
    uv run python evaluation/scripts/build_eval_dataset.py --env ../.env        # upsert for real
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))  # so the sibling eval_inputs package imports when run as a script
sys.path.insert(0, str(_HERE.parents[1] / "src"))  # services/orchestrator/src

# The bulky per-framework C# inputs (schema + query bodies) live in their own files under
# eval_inputs/ — see eval_inputs/{efcore,dapper,nhibernate}.py — and are imported here.
from eval_inputs import QUERIES, SCHEMAS  # noqa: E402

DATASET_ID = "56708f08-2697-4af2-b3b7-9172c0e68b4b"  # "UOM Final Experiments"
DATASET_NAME = "UOM Final Experiments"

# Source-framework header label (what the extraction node maps to a SourceFramework) and the
# normalized slug used in metadata (mirrors react_agent.constants.FRAMEWORK_TO_NORMALIZED_NAME).
SOURCES = {
    "efcore": {"label": "EFCore 10", "slug": "dotnet_efcore"},
    "nhibernate": {"label": "NHibernate", "slug": "dotnet_nhibernate"},
    "dapper": {"label": "Dapper", "slug": "dotnet_dapper"},
}
TARGETS = {
    "mongodb": {"label": "Spring Data MongoDB 5.0", "slug": "java_spring_data_mongodb"},
    "neo4j": {"label": "Spring Data Neo4j 8.0.0", "slug": "java_spring_data_neo4j"},
}

# Variant -> [start, end) slice of the 40-query workload. The batches are the experiment default
# (5 queries per prompt — the size the pipeline translates reliably); "small" is the legacy fast
# gate (same content as batch1); "full" bundles the original 15 into one prompt for comparison;
# batch4-8 slice the 2026-07-10 EXTENDED workload (Query16-40: A1-A3, G2-G3, D2/D3/D4/D6, B7-B11,
# C4-C9, E3-E5, F3 — every answerable benchmark FEATURE category, see eval_inputs/efcore.py);
# "xl" bundles the ENTIRE 40-query workload (original 15 + extended 25) into ONE prompt — the
# user-selected shape for the extended experiments (2026-07-10: "not batched, fully bundled").
VARIANT_SLICES: dict[str, tuple[int, int]] = {
    "small": (0, 5),
    "batch1": (0, 5),
    "batch2": (5, 10),
    "batch3": (10, 15),
    "batch4": (15, 20),
    "batch5": (20, 25),
    "batch6": (25, 30),
    "batch7": (30, 35),
    "batch8": (35, 40),
    "full": (0, 15),
    "xl": (0, 40),
}
BATCH_VARIANTS = ["batch1", "batch2", "batch3", "batch4", "batch5", "batch6", "batch7", "batch8"]


def build_prompt(source: str, target: str, variant: str) -> str:
    """Assemble one bundled translate-prompt (header + full schema + the variant's queries)."""
    start, end = VARIANT_SLICES[variant]
    header = f"Translate {SOURCES[source]['label']} to {TARGETS[target]['label']}:"
    queries = "\n\n".join(QUERIES[source][start:end])
    return f"{header}\n\n{SCHEMAS[source]}\n\n{queries}\n"


def iter_examples(sources: list[str], targets: list[str], variants: list[str]):
    """Yield (metadata, prompt) for every requested (source, target, variant)."""
    for source in sources:
        for target in targets:
            for variant in variants:
                start, end = VARIANT_SLICES[variant]
                pair = f"{SOURCES[source]['slug']}->{TARGETS[target]['slug']}"
                meta = {
                    "pair": pair,
                    "variant": variant,
                    "source_fw": SOURCES[source]["slug"],
                    "target_fw": TARGETS[target]["slug"],
                    "n_queries": end - start,
                    # Original benchmark numbering (Query6 stays "Query6" inside batch2).
                    "query_ids": list(range(start + 1, end + 1)),
                }
                yield meta, build_prompt(source, target, variant)


def _matches(ex_meta: dict, meta: dict) -> bool:
    return (ex_meta or {}).get("pair") == meta["pair"] and (ex_meta or {}).get("variant") == meta["variant"]


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--frameworks", nargs="+", default=list(SOURCES), choices=list(SOURCES))
    ap.add_argument("--targets", nargs="+", default=list(TARGETS), choices=list(TARGETS))
    ap.add_argument("--variants", nargs="+", default=BATCH_VARIANTS,
                    choices=list(VARIANT_SLICES))
    ap.add_argument("--dry-run", action="store_true",
                    help="print prompts + sizes; do NOT touch LangSmith")
    ap.add_argument("--env", default="../.env", help="path to .env with LANGSMITH_* keys")
    args = ap.parse_args()

    examples = list(iter_examples(args.frameworks, args.targets, args.variants))
    print(f"=== {len(examples)} example(s): {len(args.frameworks)} src x {len(args.targets)} tgt "
          f"x {len(args.variants)} variant ===")

    if args.dry_run:
        for meta, prompt in examples:
            print(f"\n----- {meta['pair']} [{meta['variant']}] "
                  f"({meta['n_queries']} queries, {len(prompt)} chars, ~{len(prompt)//4} tok) -----")
            print(prompt[:600] + ("\n... [truncated]" if len(prompt) > 600 else ""))
        print("\n(dry-run: nothing uploaded)")
        return

    try:
        from dotenv import load_dotenv
        load_dotenv(args.env)
    except Exception:
        pass
    if not os.environ.get("LANGSMITH_API_KEY"):
        raise SystemExit("LANGSMITH_API_KEY not set (load it via --env); aborting upsert.")

    from langsmith import Client

    client = Client()
    existing = list(client.list_examples(dataset_id=DATASET_ID))
    created = updated = 0
    for meta, prompt in examples:
        inputs = {"messages": [{"role": "user", "content": prompt}]}
        match = next((e for e in existing if _matches(getattr(e, "metadata", {}) or {}, meta)), None)
        if match is not None:
            client.update_example(example_id=match.id, inputs=inputs, metadata=meta)
            updated += 1
        else:
            client.create_example(inputs=inputs, metadata=meta, dataset_id=DATASET_ID)
            created += 1
        print(f"  {'updated' if match else 'created'}  {meta['pair']} [{meta['variant']}]")

    print(f"\nDone: {created} created, {updated} updated in {DATASET_NAME!r} ({DATASET_ID}).")


if __name__ == "__main__":
    main()
