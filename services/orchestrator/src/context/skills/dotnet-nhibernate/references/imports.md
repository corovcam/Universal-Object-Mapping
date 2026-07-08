# Canonical usings — NHibernate 5.5 / .NET 10 (source harness)

This is the source of truth for `using` directives in an NHibernate validation harness. The project
targets `net10.0` with `<ImplicitUsings>enable</ImplicitUsings>` and `<Nullable>enable</Nullable>`,
NHibernate 5.5.x and `Microsoft.Data.SqlClient` 7.0.x. NHibernate's API is spread across many small
namespaces, so a missing `using` is the most common "does not compile" cause.

The injected prelude already carries the full set below, and any `using` you write at the top of a
fragment is hoisted and de-duplicated. If a namespace is not listed here, look it up — do not guess.

## Already implicit (`ImplicitUsings`)

```csharp
// System, System.Linq, System.Collections.Generic, System.Threading.Tasks, System.IO, System.Text
```

## The canonical prelude usings (injected — present for your fragment)

```csharp
using NHibernate.Linq;                              // session.Query<T>() extension — REQUIRED for LINQ
using System;
using System.Linq;
using System.Text.Json;
using System.Text.Json.Serialization;               // [JsonPropertyName], JsonConverter
using System.Text.Encodings.Web;
using System.Globalization;
using System.Text.Json.Serialization.Metadata;
using System.Collections.Generic;
using NHibernate.Cfg;                               // Configuration, DataBaseIntegration
using NHibernate.Driver;                            // MicrosoftDataSqlClientDriver
using NHibernate.Mapping.ByCode;                    // ModelMapper, Generators, mapping DSL
using NHibernate.Mapping.ByCode.Conformist;         // ClassMapping<T>
using NHibernate.Dialect;                           // MsSql2012Dialect
using NHibernate.Transform;                         // Transformers.AliasToBean<T>()
```

`NHibernate.ISession` is referenced fully qualified in fragment signatures
(`Harness(NHibernate.ISession session)`) so you do not need `using NHibernate;` — but adding it is
harmless if you prefer the short `ISession`.

## Where each mapping/query type lives

| Type / member | Namespace |
|---|---|
| `ClassMapping<T>` | `NHibernate.Mapping.ByCode.Conformist` |
| `Generators` (`Generators.Identity`), `ModelMapper`, `Id`/`Property`/`Bag`/`ManyToOne` DSL | `NHibernate.Mapping.ByCode` |
| `session.Query<T>()` (LINQ) | `NHibernate.Linq` (extension method — **must** be imported) |
| `Transformers.AliasToBean<T>()` | `NHibernate.Transform` |
| `Configuration`, `.DataBaseIntegration(...)` | `NHibernate.Cfg` |
| `MsSql2012Dialect` | `NHibernate.Dialect` |
| `MicrosoftDataSqlClientDriver` | `NHibernate.Driver` |
| `ISession`, `ISessionFactory`, `CreateSQLQuery` | `NHibernate` (root) |
| `[JsonPropertyName]` | `System.Text.Json.Serialization` |

## Renamed / removed / do-not-use

| Wrong (other-stack / hallucinated) | Correct (NHibernate 5.5) |
|---|---|
| `session.Query<T>()` **without** `using NHibernate.Linq;` | add `using NHibernate.Linq;` (it is an extension method) |
| `Transformers` without `using NHibernate.Transform;` | add `using NHibernate.Transform;` |
| `FluentNHibernate.Mapping.ClassMap<T>` (Fluent NHibernate) | `NHibernate.Mapping.ByCode.Conformist.ClassMapping<T>` (mapping-by-code) |
| hbm.xml `<class>`/`<property>` files | the code `ClassMapping<T>` named `<Entity>Map` |
| `SqlServerDriver` / `Sql2008Driver` | `MicrosoftDataSqlClientDriver` (`NHibernate.Driver`) |
| `MsSql2008Dialect` | `MsSql2012Dialect` (`NHibernate.Dialect`) |
| naming the mapping class `EntityMapping`/`EntityConfig` | `<Entity>Map` (discovered by the `Map` suffix) |
| naming a helper `Query{N}` inside `class Query{N}` | name it `Rows`/`Build` (avoids `CS0542`/`CS1955`) |
| declaring a `namespace ...;` in your fragment | omit it — the prelude owns the namespace |
