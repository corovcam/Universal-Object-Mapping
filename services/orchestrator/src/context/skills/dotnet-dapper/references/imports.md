# Canonical usings — Dapper 2.1 / .NET 10 (source harness)

This is the source of truth for `using` directives in a Dapper validation harness. The project
targets `net10.0` with `<ImplicitUsings>enable</ImplicitUsings>` and `<Nullable>enable</Nullable>`,
Dapper 2.1.x and `Microsoft.Data.SqlClient` 7.0.x. Dapper's whole query surface is **extension
methods on `IDbConnection`**, so `using Dapper;` is load-bearing.

The injected prelude already carries the full set below, and any `using` you write at the top of a
fragment is hoisted and de-duplicated. If a namespace is not listed here, look it up — do not guess.

## Already implicit (`ImplicitUsings`)

```csharp
// System, System.Linq, System.Collections.Generic, System.Threading.Tasks, System.IO, System.Text
```

## The canonical prelude usings (injected — present for your fragment)

```csharp
using System;
using System.Linq;
using System.Text.Json;
using System.Text.Json.Serialization;               // [JsonPropertyName], JsonConverter
using System.Text.Encodings.Web;
using System.Globalization;
using System.Text.Json.Serialization.Metadata;
using System.Collections.Generic;
using Dapper;                                        // Query<T>, ExecuteScalar<T>, QueryMultiple — REQUIRED
using Microsoft.Data.SqlClient;                      // SqlConnection
```

## Where each type/method lives

| Type / method | Namespace |
|---|---|
| `SqlConnection` | `Microsoft.Data.SqlClient` |
| `conn.Query<T>(...)`, `conn.Query<T1,T2,TReturn>(...)`, `conn.ExecuteScalar<T>(...)`, `conn.Execute(...)` | `Dapper` (extension methods on `IDbConnection`) |
| `conn.QueryMultiple(...)` → `SqlMapper.GridReader` (`.Read<T>()`, `.ReadSingle<T>()`) | `Dapper` |
| `[JsonPropertyName]` | `System.Text.Json.Serialization` |

Dapper has **no mapping-attribute namespace** — there is nothing like EF Core's
`System.ComponentModel.DataAnnotations.Schema` to import, because Dapper matches columns to
properties by name, not by attribute.

## Renamed / removed / do-not-use

| Wrong (other-stack / hallucinated) | Correct (Dapper 2.1) |
|---|---|
| `System.Data.SqlClient.SqlConnection` | `Microsoft.Data.SqlClient.SqlConnection` (the project's provider) |
| `conn.Query<T>()` **without** `using Dapper;` | add `using Dapper;` (extension methods) |
| `[Table]`/`[Key]`/`[Column]` attributes to "map" a Dapper POCO | none — Dapper maps by column name; attributes are ignored |
| `IN (@Ids)` | `IN @Ids` (Dapper adds the parentheses) |
| building SQL by string concatenation of values | parameterize with `@name` + an anonymous object |
| `Newtonsoft.Json` for the harness serializer | it is injected as `System.Text.Json` — do not add another |
| naming a helper `Query{N}` inside `class Query{N}` | name it `Rows`/`MapRow`/`Build` (avoids `CS0542`/`CS1955`) |
| declaring a `namespace ...;` in your fragment | omit it — the prelude owns the namespace |
