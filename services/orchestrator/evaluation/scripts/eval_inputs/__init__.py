"""Per-framework source inputs (schema + queries) for the UOM eval dataset."""
from . import dapper, efcore, nhibernate

SCHEMAS = {"efcore": efcore.SCHEMA, "dapper": dapper.SCHEMA, "nhibernate": nhibernate.SCHEMA}
QUERIES = {"efcore": efcore.QUERIES, "dapper": dapper.QUERIES, "nhibernate": nhibernate.QUERIES}

__all__ = ["SCHEMAS", "QUERIES"]
