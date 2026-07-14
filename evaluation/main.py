from pathlib import Path
from codebleu import calc_codebleu


def main():
    base_dir = Path(__file__).parent / "predictions" / "wideworldimporters" / "dapper-mongo"

    # Load schema files
    valid_schema_path = base_dir / "valid" / "schema.java"
    invalid_schema_path = base_dir / "invalid" / "schema.java"

    # Load query files
    valid_queries_path = base_dir / "valid" / "queries.java"
    invalid_queries_path = base_dir / "invalid" / "queries.java"

    # Read contents
    ref_schema = valid_schema_path.read_text(encoding="utf-8")
    pred_schema = invalid_schema_path.read_text(encoding="utf-8")

    ref_queries = valid_queries_path.read_text(encoding="utf-8")
    pred_queries = invalid_queries_path.read_text(encoding="utf-8")

    print("--- Schema Comparison ---")
    schema_result = calc_codebleu([ref_schema], [pred_schema], lang="java")
    for k, v in schema_result.items():
        print(f"{k}: {v:.4f}")

    print("\n--- Queries Comparison ---")
    queries_result = calc_codebleu([ref_queries], [pred_queries], lang="java")
    for k, v in queries_result.items():
        print(f"{k}: {v:.4f}")


if __name__ == "__main__":
    main()

