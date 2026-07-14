# Reference provenance

- frozen: 2026-07-11
- source run tag: `20260709-150203` (our pipeline, variant `full`)
- source run id: `2889b5e7-c243-4d7d-904f-c989315ed124` (predictions dir `einfra-kimi-k2-7/our_approach-2889b5e7`)
- evidence: final deterministic equivalence check = 15/15
  strictly `Equivalent` against the live WWI stores (count + first/last-sample
  DeepDiff), reconstructed from the aimock recording `our_approach-full-1793cbec`.
- files: schema.java, queries.java

No human-written Java gold exists for this pair; this execution-verified translation
is the frozen structural-similarity reference. When comparing arms with CodeBLEU,
exclude this run id from its own arm's aggregate (see provenance.json).
