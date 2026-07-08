# Canonical usings — EF Core 10 / .NET 10 (source harness)

This is the source of truth for `using` directives in an EF Core validation harness. The project
targets `net10.0` with `<ImplicitUsings>enable</ImplicitUsings>` and `<Nullable>enable</Nullable>`,
EF Core 10.0.x (`Microsoft.EntityFrameworkCore.SqlServer`) and `Microsoft.Data.SqlClient` 7.0.x.

You rarely need to add usings yourself: the injected prelude already carries the full set below, and
any `using` you *do* write at the top of a fragment is hoisted and de-duplicated into the header. If
a namespace is not listed here, look it up before using it — do not guess.

## Already implicit (do NOT add — `ImplicitUsings` provides them)

```csharp
// System, System.Linq, System.Collections.Generic, System.Threading, System.Threading.Tasks,
// System.IO, System.Text — all in scope automatically. Writing them is harmless but unnecessary.
```

## The canonical prelude usings (injected — present for your fragment)

```csharp
using System;
using System.Linq;
using Microsoft.EntityFrameworkCore;                              // DbContext, DbSet, Include, ToQueryString, UseSqlServer
using System.ComponentModel.DataAnnotations;                      // [Key], [MaxLength], [Required]
using System.ComponentModel.DataAnnotations.Schema;               // [Table], [Column], [ForeignKey], [NotMapped]
using System.Text.Json;
using System.Text.Json.Serialization;                             // [JsonPropertyName], JsonConverter
using System.Text.Encodings.Web;
using System.Globalization;
using System.Text.Json.Serialization.Metadata;
using Microsoft.EntityFrameworkCore.Diagnostics;                  // DbContextLoggerOptions
using Microsoft.Extensions.Logging;                               // LogLevel
```

`Microsoft.Data.SqlClient` (the `SqlConnection`) is used only by the *generated* `Main` bootstrap,
not by your EF Core query fragments — your fragments receive a ready `SandboxDbContext`.

## Mapping namespaces you reference in a schema fragment

| Attribute / type | Namespace |
|---|---|
| `[Table]`, `[Column]`, `[ForeignKey]`, `[NotMapped]`, `[DatabaseGenerated]` | `System.ComponentModel.DataAnnotations.Schema` |
| `[Key]`, `[MaxLength]`, `[Required]`, `[StringLength]` | `System.ComponentModel.DataAnnotations` |
| `[Precision(p, s)]` | `Microsoft.EntityFrameworkCore` |
| `[JsonPropertyName]` | `System.Text.Json.Serialization` |
| `DbContext`, `DbSet<T>`, `DbContextOptions<T>`, `ModelBuilder` | `Microsoft.EntityFrameworkCore` |

## Query namespaces you reference in a query fragment

| Operator / type | Where it comes from |
|---|---|
| `Where`, `OrderBy`, `Select`, `GroupBy`, `Distinct`, `Skip`, `Take`, `Count`, `Max`, `Sum`, `Union`, `Intersect`, `ToList`, `ToDictionary` | `System.Linq` (implicit) |
| `Include`, `ThenInclude`, `AsSplitQuery`, `AsNoTracking`, `ToQueryString`, `SingleOrDefault`/`FirstOrDefault` (EF async variants) | `Microsoft.EntityFrameworkCore` |
| `IQueryable<T>`, `IEnumerable<T>` | `System.Linq` / `System.Collections.Generic` (implicit) |

## Renamed / removed / do-not-use

| Wrong (old / other-stack / hallucinated) | Correct (EF Core 10) |
|---|---|
| `System.Data.Entity.*` (EF6 / EF Classic) | `Microsoft.EntityFrameworkCore.*` |
| `[Table]` from `System.ComponentModel.DataAnnotations` | `System.ComponentModel.DataAnnotations.Schema` |
| `modelBuilder.Entity<T>().Property(x => x.P).HasColumnType("json")` for a POCO | `OwnsOne(p => p.Owned, cb => cb.ToJson())` for an owned type |
| `DbSet<T> X { get; set; }` mutable auto-property | `DbSet<T> X => Set<T>();` (the project convention; both compile) |
| Naming a helper `Query{N}` inside `class Query{N}` | name it `Rows`/`Build` (avoids `CS0542`/`CS1955`) |
| `Newtonsoft.Json` for the harness serializer | it is injected as `System.Text.Json` — do not add another |
| declaring a `namespace ...;` in your fragment | omit it — the prelude owns the namespace |
