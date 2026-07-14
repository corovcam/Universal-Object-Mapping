# Reference provenance

- frozen: 2026-07-11
- source run tag: `20260709-150203` (our pipeline, variant `full`)
- source run id: `43ceba37-23d4-41f8-865e-ed32517aae3d` (predictions dir `einfra-kimi-k2-7/our_approach-43ceba37`)
- evidence: final deterministic equivalence check = 15/15
  strictly `Equivalent` against the live WWI stores (count + first/last-sample
  DeepDiff), reconstructed from the aimock recording `our_approach-full-3b40a0c4`.
- files: schema.java, queries.java

No human-written Java gold exists for this pair; this execution-verified translation
is the frozen structural-similarity reference. When comparing arms with CodeBLEU,
exclude this run id from its own arm's aggregate (see provenance.json).
