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
  * For each (source_framework, target_store) PAIR we build ONE bundled prompt = header + full schema +
    every chosen query. A **full** variant (~15 queries) and a **small** variant (first 5) are emitted,
    so a fast small-query gate can run before the full overnight matrix.
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
sys.path.insert(0, str(_HERE.parents[1] / "src"))  # services/orchestrator/src

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

# --------------------------------------------------------------------------------------------------
# Schemas — verbatim from tests/fixtures/input-*.txt (the schema portion only; queries appended below
# from QUERIES). Kept per-framework so each source harness compiles in its own sandbox idiom.
# --------------------------------------------------------------------------------------------------

EFCORE_SCHEMA = """\
[Table("Customers", Schema = "Sales")]
public class Customer
{
  [Key]
  public required int CustomerID { get; set; }
  [MaxLength(200)]
  public required string CustomerName { get; set; }
  [Column(TypeName = "datetime2")]
  [Precision(7)]
  public required DateTime AccountOpenedDate { get; set; }
  [Column(TypeName = "decimal")]
  [Precision(18, 2)]
  public decimal? CreditLimit { get; set; }
  public List<CustomerTransaction> CustomerTransactions { get; set; } = [];
}

[Table("CustomerTransactions", Schema = "Sales")]
public class CustomerTransaction
{
  [Key]
  public int CustomerTransactionID { get; set; }
  [ForeignKey(nameof(Customer))]
  public int CustomerID { get; set; }
  public DateTime TransactionDate { get; set; }
  public decimal TransactionAmount { get; set; }
}

[Table("Orders", Schema = "Sales")]
public class Order
{
  [Key]
  public int OrderID { get; set; }
  [ForeignKey(nameof(Customer))]
  public int CustomerID { get; set; }
  public Customer Customer { get; set; } = null!;
  public List<OrderLine> OrderLines { get; set; } = [];
}

[Table("OrderLines", Schema = "Sales")]
public class OrderLine
{
  [Key]
  public int OrderLineID { get; set; }
  [ForeignKey(nameof(Order))]
  public int OrderID { get; set; }
  public required string Description { get; set; }
  public int PackageTypeID { get; set; }
  public int Quantity { get; set; }
  public decimal? UnitPrice { get; set; }
  public decimal TaxRate { get; set; }
  public int PickedQuantity { get; set; }
  public DateTime? PickingCompletedWhen { get; set; }
  public int LastEditedBy { get; set; }
  public DateTime LastEditedWhen { get; set; }
}

public class SandboxDbContext(DbContextOptions<SandboxDbContext> options) : DbContext(options)
{
  public DbSet<Customer> Customers => Set<Customer>();
  public DbSet<Order> Orders => Set<Order>();
  public DbSet<CustomerTransaction> CustomerTransactions => Set<CustomerTransaction>();
  public DbSet<OrderLine> OrderLines => Set<OrderLine>();
}"""

DAPPER_SCHEMA = """\
public class Customer
{
    public required int CustomerID { get; set; }
    public required string CustomerName { get; set; }
    public required DateTime AccountOpenedDate { get; set; }
    public decimal? CreditLimit { get; set; }
    public List<CustomerTransaction> CustomerTransactions { get; set; } = [];
}
public class CustomerTransaction
{
    public int CustomerTransactionID { get; set; }
    public int CustomerID { get; set; }
    public DateTime TransactionDate { get; set; }
    public decimal TransactionAmount { get; set; }
}
public class Order
{
    public int OrderID { get; set; }
    public int CustomerID { get; set; }
    public Customer Customer { get; set; } = null!;
    public List<OrderLine> OrderLines { get; set; } = [];
}
public class OrderLine
{
    public int OrderLineID { get; set; }
    public int OrderID { get; set; }
    public required string Description { get; set; }
    public int PackageTypeID { get; set; }
    public int Quantity { get; set; }
    public decimal? UnitPrice { get; set; }
    public decimal TaxRate { get; set; }
    public int PickedQuantity { get; set; }
    public DateTime? PickingCompletedWhen { get; set; }
    public int LastEditedBy { get; set; }
    public DateTime LastEditedWhen { get; set; }
}"""

NHIBERNATE_SCHEMA = """\
public class Customer
{
    public virtual int CustomerID { get; set; }
    public virtual required string CustomerName { get; set; }
    public virtual DateTime AccountOpenedDate { get; set; }
    public virtual decimal? CreditLimit { get; set; }
    public virtual IList<CustomerTransaction> CustomerTransactions { get; set; } = [];
}
public class CustomerTransaction
{
    public virtual int CustomerTransactionID { get; set; }
    public virtual int CustomerID { get; set; }
    public virtual DateTime TransactionDate { get; set; }
    public virtual decimal TransactionAmount { get; set; }
}
public class Order
{
    public virtual int OrderID { get; set; }
    public virtual int CustomerID { get; set; }
    public virtual Customer Customer { get; set; } = null!;
    public virtual IList<OrderLine> OrderLines { get; set; } = [];
}
public class OrderLine
{
    public virtual int OrderLineID { get; set; }
    public virtual int OrderID { get; set; }
    public virtual required string Description { get; set; }
    public virtual int PackageTypeID { get; set; }
    public virtual int Quantity { get; set; }
    public virtual decimal? UnitPrice { get; set; }
    public virtual decimal TaxRate { get; set; }
    public virtual int PickedQuantity { get; set; }
    public virtual DateTime? PickingCompletedWhen { get; set; }
    public virtual int LastEditedBy { get; set; }
    public virtual DateTime LastEditedWhen { get; set; }
}
public class CustomerMap : ClassMapping<Customer> {
    public CustomerMap() {
        Table("Customers"); Schema("Sales");
        Id(x => x.CustomerID, m => m.Generator(Generators.Identity));
        Property(x => x.CustomerName);
        Property(x => x.AccountOpenedDate);
        Property(x => x.CreditLimit);
        Bag(x => x.CustomerTransactions, map => { map.Key(k => k.Column("CustomerID")); map.Inverse(true); }, rel => rel.OneToMany());
    }
}
public class CustomerTransactionMap : ClassMapping<CustomerTransaction> {
    public CustomerTransactionMap() {
        Table("CustomerTransactions"); Schema("Sales");
        Id(x => x.CustomerTransactionID, m => m.Generator(Generators.Identity));
        Property(x => x.CustomerID, m => { m.Insert(false); m.Update(false); });
        Property(x => x.TransactionDate);
        Property(x => x.TransactionAmount);
    }
}
public class OrderMap : ClassMapping<Order> {
    public OrderMap() {
        Table("Orders"); Schema("Sales");
        Id(x => x.OrderID, m => m.Generator(Generators.Identity));
        Property(x => x.CustomerID, m => { m.Insert(false); m.Update(false); });
        ManyToOne(x => x.Customer, m => m.Column("CustomerID"));
        Bag(x => x.OrderLines, map => { map.Key(k => k.Column("OrderID")); map.Inverse(true); }, rel => rel.OneToMany());
    }
}
public class OrderLineMap : ClassMapping<OrderLine> {
    public OrderLineMap() {
        Table("OrderLines"); Schema("Sales");
        Id(x => x.OrderLineID, m => m.Generator(Generators.Identity));
        Property(x => x.OrderID, m => { m.Insert(false); m.Update(false); });
        Property(x => x.Description);
        Property(x => x.PackageTypeID);
        Property(x => x.Quantity);
        Property(x => x.UnitPrice);
        Property(x => x.TaxRate);
        Property(x => x.PickedQuantity);
        Property(x => x.PickingCompletedWhen);
        Property(x => x.LastEditedBy);
        Property(x => x.LastEditedWhen);
    }
}
public record TaxRateCount { public decimal TaxRate { get; set; } public long Count { get; set; } }
public record PackageQtySum { public int PackageTypeID { get; set; } public int TotalQuantity { get; set; } }
public record LineQtyProjection { public int OrderLineID { get; set; } public int Quantity { get; set; } }"""

# --------------------------------------------------------------------------------------------------
# Query bodies — same logical set across frameworks (categories from EFCoreBenchmarks.cs etc.),
# expressed in each framework's native idiom. All return a sequence so the deterministic execution
# harness can run + serialize each one uniformly.
# --------------------------------------------------------------------------------------------------

EFCORE_QUERIES = [
    # 1 range (PickingCompletedWhen) — B3
    """public static IQueryable<OrderLine> Query1(SandboxDbContext ctx)
{
  var from = new DateTime(2014, 12, 20);
  var to = new DateTime(2014, 12, 31);
  return ctx.OrderLines.Where(ol => ol.PickingCompletedWhen >= from && ol.PickingCompletedWhen <= to);
}""",
    # 2 selection over indexed column (OrderID) — B1
    """public static IQueryable<OrderLine> Query2(SandboxDbContext ctx)
{
  return ctx.OrderLines.Where(ol => ol.OrderID == 26866);
}""",
    # 3 selection over non-indexed column (UnitPrice) — B2
    """public static IQueryable<OrderLine> Query3(SandboxDbContext ctx)
{
  return ctx.OrderLines.Where(ol => ol.UnitPrice == 25m);
}""",
    # 4 IN query — B4
    """public static IQueryable<OrderLine> Query4(SandboxDbContext ctx)
{
  var ids = new[] { 1, 10, 100, 1000, 10000 };
  return ctx.OrderLines.Where(ol => ids.Contains(ol.OrderID));
}""",
    # 5 text search — B5
    """public static IQueryable<OrderLine> Query5(SandboxDbContext ctx)
{
  return ctx.OrderLines.Where(ol => ol.Description.Contains("C++"));
}""",
    # 6 paging — B6
    """public static IQueryable<OrderLine> Query6(SandboxDbContext ctx)
{
  return ctx.OrderLines.OrderBy(ol => ol.OrderLineID).Skip(1000).Take(50);
}""",
    # 7 grouped aggregation count — C1
    """public static IQueryable<dynamic> Query7(SandboxDbContext ctx)
{
  return ctx.OrderLines.GroupBy(ol => ol.TaxRate)
    .Select(g => new { TaxRate = g.Key, Count = g.Count() })
    .OrderByDescending(x => x.Count);
}""",
    # 8 grouped aggregation sum — C3
    """public static IQueryable<dynamic> Query8(SandboxDbContext ctx)
{
  return ctx.OrderLines.GroupBy(ol => ol.PackageTypeID)
    .Select(g => new { PackageTypeID = g.Key, TotalQuantity = g.Sum(ol => ol.Quantity) });
}""",
    # 9 one-to-many include — D1
    """public static IQueryable<Order> Query9(SandboxDbContext ctx)
{
  return ctx.Orders.Include(o => o.OrderLines).Where(o => o.OrderID == 530);
}""",
    # 10 optional relationship include + order — D3
    """public static IQueryable<Customer> Query10(SandboxDbContext ctx)
{
  return ctx.Customers.Include(c => c.CustomerTransactions).OrderBy(c => c.CustomerID);
}""",
    # 11 sorting + top-N — E1
    """public static IQueryable<OrderLine> Query11(SandboxDbContext ctx)
{
  return ctx.OrderLines.OrderByDescending(ol => ol.Quantity).Take(50);
}""",
    # 12 distinct — E2
    """public static IQueryable<string> Query12(SandboxDbContext ctx)
{
  return ctx.OrderLines.Select(ol => ol.Description).Distinct();
}""",
    # 13 projection
    """public static IQueryable<dynamic> Query13(SandboxDbContext ctx)
{
  return ctx.OrderLines.Select(ol => new { ol.OrderLineID, ol.Quantity });
}""",
    # 14 nullable-decimal filter + order
    """public static IQueryable<Customer> Query14(SandboxDbContext ctx)
{
  return ctx.Customers.Where(c => c.CreditLimit > 1000m).OrderByDescending(c => c.CreditLimit);
}""",
    # 15 compound filter
    """public static IQueryable<OrderLine> Query15(SandboxDbContext ctx)
{
  return ctx.OrderLines.Where(ol => ol.Quantity > 10 && ol.TaxRate == 15m);
}""",
]

DAPPER_QUERIES = [
    """public static IEnumerable<OrderLine> Query1(SqlConnection conn)
{
    var from = new DateTime(2014, 12, 20);
    var to = new DateTime(2014, 12, 31);
    string sql = @"SELECT * FROM Sales.OrderLines WHERE PickingCompletedWhen >= @From AND PickingCompletedWhen <= @To";
    return conn.Query<OrderLine>(sql, new { From = from, To = to });
}""",
    """public static IEnumerable<OrderLine> Query2(SqlConnection conn)
{
    string sql = @"SELECT * FROM Sales.OrderLines WHERE OrderID = @OrderID";
    return conn.Query<OrderLine>(sql, new { OrderID = 26866 });
}""",
    """public static IEnumerable<OrderLine> Query3(SqlConnection conn)
{
    string sql = @"SELECT * FROM Sales.OrderLines WHERE UnitPrice = @UnitPrice";
    return conn.Query<OrderLine>(sql, new { UnitPrice = 25m });
}""",
    """public static IEnumerable<OrderLine> Query4(SqlConnection conn)
{
    var ids = new[] { 1, 10, 100, 1000, 10000 };
    string sql = @"SELECT * FROM Sales.OrderLines WHERE OrderID IN @Ids";
    return conn.Query<OrderLine>(sql, new { Ids = ids });
}""",
    """public static IEnumerable<OrderLine> Query5(SqlConnection conn)
{
    string sql = @"SELECT * FROM Sales.OrderLines WHERE Description LIKE @Pattern";
    return conn.Query<OrderLine>(sql, new { Pattern = "%C++%" });
}""",
    """public static IEnumerable<OrderLine> Query6(SqlConnection conn)
{
    string sql = @"SELECT * FROM Sales.OrderLines ORDER BY OrderLineID OFFSET 1000 ROWS FETCH NEXT 50 ROWS ONLY";
    return conn.Query<OrderLine>(sql);
}""",
    """public static IEnumerable<(decimal TaxRate, int Count)> Query7(SqlConnection conn)
{
    string sql = @"SELECT TaxRate, COUNT(*) AS Count FROM Sales.OrderLines GROUP BY TaxRate ORDER BY Count DESC";
    return conn.Query<(decimal TaxRate, int Count)>(sql);
}""",
    """public static IEnumerable<(int PackageTypeID, int TotalQuantity)> Query8(SqlConnection conn)
{
    string sql = @"SELECT PackageTypeID, SUM(Quantity) AS TotalQuantity FROM Sales.OrderLines GROUP BY PackageTypeID";
    return conn.Query<(int PackageTypeID, int TotalQuantity)>(sql);
}""",
    """static Order Query9mapRow(Order o, OrderLine ol)
{
    o.OrderLines.Add(ol);
    return o;
}
public static IEnumerable<Order> Query9(SqlConnection conn)
{
    string sql = @"
        SELECT o.*, ol.*
        FROM Sales.Orders o
        LEFT JOIN Sales.OrderLines ol ON o.OrderID = ol.OrderID
        WHERE o.OrderID = 530";
    var rows = conn.Query<Order, OrderLine, Order>(sql, Query9mapRow, splitOn: "OrderLineID");
    return rows.GroupBy(o => o.OrderID).Select(g => {
        var order = g.First();
        order.OrderLines = g.SelectMany(o => o.OrderLines).Where(ol => ol != null).ToList();
        return order;
    });
}""",
    """static Customer Query10mapRow(Customer c, CustomerTransaction t)
{
    if (t != null) c.CustomerTransactions.Add(t);
    return c;
}
public static IEnumerable<Customer> Query10(SqlConnection conn)
{
    string sql = @"
        SELECT c.*, t.*
        FROM Sales.Customers c
        LEFT JOIN Sales.CustomerTransactions t ON c.CustomerID = t.CustomerID
        ORDER BY c.CustomerID";
    var rows = conn.Query<Customer, CustomerTransaction, Customer>(sql, Query10mapRow, splitOn: "CustomerTransactionID");
    return rows.GroupBy(c => c.CustomerID).Select(g => {
        var customer = g.First();
        customer.CustomerTransactions = g.SelectMany(c => c.CustomerTransactions).Where(t => t != null).ToList();
        return customer;
    });
}""",
    """public static IEnumerable<OrderLine> Query11(SqlConnection conn)
{
    string sql = @"SELECT TOP 50 * FROM Sales.OrderLines ORDER BY Quantity DESC";
    return conn.Query<OrderLine>(sql);
}""",
    """public static IEnumerable<string> Query12(SqlConnection conn)
{
    string sql = @"SELECT DISTINCT Description FROM Sales.OrderLines";
    return conn.Query<string>(sql);
}""",
    """public static IEnumerable<(int OrderLineID, int Quantity)> Query13(SqlConnection conn)
{
    string sql = @"SELECT OrderLineID, Quantity FROM Sales.OrderLines";
    return conn.Query<(int OrderLineID, int Quantity)>(sql);
}""",
    """public static IEnumerable<Customer> Query14(SqlConnection conn)
{
    string sql = @"SELECT * FROM Sales.Customers WHERE CreditLimit > @Limit ORDER BY CreditLimit DESC";
    return conn.Query<Customer>(sql, new { Limit = 1000m });
}""",
    """public static IEnumerable<OrderLine> Query15(SqlConnection conn)
{
    string sql = @"SELECT * FROM Sales.OrderLines WHERE Quantity > @Qty AND TaxRate = @Tax";
    return conn.Query<OrderLine>(sql, new { Qty = 10, Tax = 15m });
}""",
]

NHIBERNATE_QUERIES = [
    """public static IQueryable<OrderLine> Query1(NHibernate.ISession session)
{
    var from = new DateTime(2014, 12, 20);
    var to = new DateTime(2014, 12, 31);
    return session.Query<OrderLine>().Where(ol => ol.PickingCompletedWhen >= from && ol.PickingCompletedWhen <= to);
}""",
    """public static IQueryable<OrderLine> Query2(NHibernate.ISession session)
{
    return session.Query<OrderLine>().Where(ol => ol.OrderID == 26866);
}""",
    """public static IQueryable<OrderLine> Query3(NHibernate.ISession session)
{
    return session.Query<OrderLine>().Where(ol => ol.UnitPrice == 25m);
}""",
    """public static IQueryable<OrderLine> Query4(NHibernate.ISession session)
{
    var ids = new[] { 1, 10, 100, 1000, 10000 };
    return session.Query<OrderLine>().Where(ol => ids.Contains(ol.OrderID));
}""",
    """public static IQueryable<OrderLine> Query5(NHibernate.ISession session)
{
    return session.Query<OrderLine>().Where(ol => ol.Description.Contains("C++"));
}""",
    """public static IQueryable<OrderLine> Query6(NHibernate.ISession session)
{
    return session.Query<OrderLine>().OrderBy(ol => ol.OrderLineID).Skip(1000).Take(50);
}""",
    """public static IQueryable<TaxRateCount> Query7(NHibernate.ISession session)
{
    return session.Query<OrderLine>().GroupBy(ol => ol.TaxRate)
        .Select(g => new TaxRateCount { TaxRate = g.Key, Count = g.Count() })
        .OrderByDescending(x => x.Count);
}""",
    """public static IQueryable<PackageQtySum> Query8(NHibernate.ISession session)
{
    return session.Query<OrderLine>().GroupBy(ol => ol.PackageTypeID)
        .Select(g => new PackageQtySum { PackageTypeID = g.Key, TotalQuantity = g.Sum(ol => ol.Quantity) });
}""",
    """public static IQueryable<Order> Query9(NHibernate.ISession session)
{
    return session.Query<Order>().Where(o => o.OrderID == 530).Fetch(o => o.OrderLines);
}""",
    """public static IQueryable<Customer> Query10(NHibernate.ISession session)
{
    return session.Query<Customer>().FetchMany(c => c.CustomerTransactions).OrderBy(c => c.CustomerID);
}""",
    """public static IQueryable<OrderLine> Query11(NHibernate.ISession session)
{
    return session.Query<OrderLine>().OrderByDescending(ol => ol.Quantity).Take(50);
}""",
    """public static IQueryable<string> Query12(NHibernate.ISession session)
{
    return session.Query<OrderLine>().Select(ol => ol.Description).Distinct();
}""",
    """public static IQueryable<LineQtyProjection> Query13(NHibernate.ISession session)
{
    return session.Query<OrderLine>().Select(ol => new LineQtyProjection { OrderLineID = ol.OrderLineID, Quantity = ol.Quantity });
}""",
    """public static IQueryable<Customer> Query14(NHibernate.ISession session)
{
    return session.Query<Customer>().Where(c => c.CreditLimit > 1000m).OrderByDescending(c => c.CreditLimit);
}""",
    """public static IQueryable<OrderLine> Query15(NHibernate.ISession session)
{
    return session.Query<OrderLine>().Where(ol => ol.Quantity > 10 && ol.TaxRate == 15m);
}""",
]

SCHEMAS = {"efcore": EFCORE_SCHEMA, "dapper": DAPPER_SCHEMA, "nhibernate": NHIBERNATE_SCHEMA}
QUERIES = {"efcore": EFCORE_QUERIES, "dapper": DAPPER_QUERIES, "nhibernate": NHIBERNATE_QUERIES}
SMALL_N = 5  # the "small" gate variant keeps the first 5 queries


def build_prompt(source: str, target: str, variant: str) -> str:
    """Assemble one bundled translate-prompt (header + full schema + chosen queries)."""
    n = SMALL_N if variant == "small" else len(QUERIES[source])
    header = f"Translate {SOURCES[source]['label']} to {TARGETS[target]['label']}:"
    queries = "\n\n".join(QUERIES[source][:n])
    return f"{header}\n\n{SCHEMAS[source]}\n\n{queries}\n"


def iter_examples(sources: list[str], targets: list[str], variants: list[str]):
    """Yield (metadata, prompt) for every requested (source, target, variant)."""
    for source in sources:
        for target in targets:
            for variant in variants:
                pair = f"{SOURCES[source]['slug']}->{TARGETS[target]['slug']}"
                meta = {
                    "pair": pair,
                    "variant": variant,
                    "source_fw": SOURCES[source]["slug"],
                    "target_fw": TARGETS[target]["slug"],
                    "n_queries": SMALL_N if variant == "small" else len(QUERIES[source]),
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
    ap.add_argument("--variants", nargs="+", default=["small", "full"], choices=["small", "full"])
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
