using BenchmarkDotNet.Attributes;
using Common;
using Common.Mock;
using EFCoreEntities;
using EFCoreEntities.Models;
using Microsoft.Data.SqlClient;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Diagnostics;
using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.VSDiagnostics;

namespace EFCorePerformance
{
    [EventsDiagnoser]
    [CPUUsageDiagnoser]
    [DatabaseDiagnoser]
    [MemoryDiagnoser]
    [ExceptionDiagnoser]
    public class EFCoreBenchmarks
    {
        private PooledDbContextFactory<WWIContext> contextFactory = null!;
        private readonly BenchmarkCommandExecutor commandExecutor = BenchmarkCommandExecutor.Instance;
        private decimal counter = 0m;
        private Dictionary<string, QueryOutputInfoHelper.QueryInfo> queryInfoCache = new();

        [GlobalSetup]
        public void GlobalSetup()
        {
            var options = new DbContextOptionsBuilder<WWIContext>()
               .UseSqlServer(DatabaseConfig.MSSQLConnectionString)
               // We only test read queries, tracking is not needed and might slow down the tests
               .UseQueryTrackingBehavior(QueryTrackingBehavior.NoTracking)
               .ConfigureWarnings(warnings =>
               {
                   warnings.Ignore(CoreEventId.SensitiveDataLoggingEnabledWarning);
                   // we only read the values, so we don't need to worry about precision when saving
                   warnings.Ignore(SqlServerEventId.DecimalTypeDefaultWarning);
               })
               .AddInterceptors(RecordCommandsInterceptor.Instance)
               .LogTo(Console.WriteLine, new[] { RelationalEventId.CommandExecuted })
               .Options;

            contextFactory = new(options);

            ExtractQueryInfo();

            var fakeConnection = new FakeDbConnection(DatabaseConfig.MSSQLConnectionString, commandExecutor); 
            fakeConnection.Open();

            var benchmarkOptions = new DbContextOptionsBuilder<WWIContext>()
                .UseSqlServer(fakeConnection)
                // We only test read queries, tracking is not needed and might slow down the tests
                .UseQueryTrackingBehavior(QueryTrackingBehavior.NoTracking)
                .ConfigureWarnings(warnings =>
                {
                    warnings.Ignore(CoreEventId.SensitiveDataLoggingEnabledWarning);
                    // we only read the values, so we don't need to worry about precision when saving
                    warnings.Ignore(SqlServerEventId.DecimalTypeDefaultWarning);
                })
                //.LogTo(Console.WriteLine, new[] { RelationalEventId.CommandExecuted })
                .Options;

            contextFactory = new(benchmarkOptions);
        }

        private void ExtractQueryInfo()
        {
            using var context = contextFactory.CreateDbContext();
            using var sqlConn = new SqlConnection(DatabaseConfig.MSSQLConnectionString);
            sqlConn.Open();

            queryInfoCache.Add("A1_EntityIdenticalToTable", QueryOutputInfoHelper.AnalyzeSqlQuery(
                context.RecordSqlQueryStrings(
                    ctx => ctx.PurchaseOrders.Find(25)
                ).First(),
                sqlConnection: sqlConn));

            queryInfoCache.Add("A2_LimitedEntity", QueryOutputInfoHelper.AnalyzeSqlQuery(
                context.RecordSqlQueryStrings(
                    ctx => ctx.Suppliers
                        .Where(s => s.SupplierID == 10)
                        .Select(s => new SupplierContactInfo
                        {
                            SupplierID = s.SupplierID,
                            SupplierName = s.SupplierName,
                            PhoneNumber = s.PhoneNumber,
                            FaxNumber = s.FaxNumber,
                            WebsiteURL = s.WebsiteURL,
                            ValidFrom = s.ValidFrom,
                            ValidTo = s.ValidTo
                        })
                        .SingleOrDefault()
                ).First(), sqlConnection: sqlConn));

            queryInfoCache.Add("A3_MultipleEntitiesFromOneResult", QueryOutputInfoHelper.AnalyzeSqlQuery(
                context.RecordSqlQueryStrings(
                    ctx => ctx.Suppliers
                        .Where(s => s.SupplierID == 10)
                        .Select(s => new
                        {
                            ContactInfo = new SupplierContactInfo
                            {
                                SupplierID = s.SupplierID,
                                SupplierName = s.SupplierName,
                                PhoneNumber = s.PhoneNumber,
                                FaxNumber = s.FaxNumber,
                                WebsiteURL = s.WebsiteURL,
                                ValidFrom = s.ValidFrom,
                                ValidTo = s.ValidTo
                            },
                            BankAccount = new SupplierBankAccount
                            {
                                SupplierID = s.SupplierID,
                                BankAccountName = s.BankAccountName,
                                BankAccountBranch = s.BankAccountBranch,
                                BankAccountCode = s.BankAccountCode,
                                BankAccountNumber = s.BankAccountNumber,
                                BankInternationalCode = s.BankInternationalCode
                            }
                        })
                        .Select(result => new { result.ContactInfo, result.BankAccount })
                        .SingleOrDefault()
                ).First(), sqlConnection: sqlConn));

            var spFrom = new SqlParameter("@p0", new DateTime(2014, 1, 1));
            var spTo = new SqlParameter("@p1", new DateTime(2015, 1, 1));
            queryInfoCache.Add("A4_StoredProcedureToEntity", QueryOutputInfoHelper.AnalyzeSqlQuery(
                context.RecordSqlQueryStrings(
                    ctx => ctx.Set<PurchaseOrderUpdate>()
                        .FromSqlInterpolated($"EXEC WideWorldImporters.Integration.GetOrderUpdates @LastCutoff = {spFrom}, @NewCutoff = {spTo}")
                        .ToList()
                ).First(), sqlConnection: sqlConn));

            int orderId = 26866;
            queryInfoCache.Add("B1_SelectionOverIndexedColumn", QueryOutputInfoHelper.AnalyzeSqlQuery(
                context.RecordSqlQueryStrings(
                    ctx => ctx.OrderLines
                        .Where(ol => ol.OrderID == orderId)
                        .ToList()
                ).First(), sqlConnection: sqlConn));

            decimal unitPrice = 25m;
            queryInfoCache.Add("B2_SelectionOverNonIndexedColumn", QueryOutputInfoHelper.AnalyzeSqlQuery(
                context.RecordSqlQueryStrings(
                    ctx => ctx.OrderLines
                        .Where(ol => ol.UnitPrice == unitPrice)
                        .ToList()
                ).First(), sqlConnection: sqlConn));

            var rangeFrom = new DateTime(2014, 12, 20);
            var rangeTo = new DateTime(2014, 12, 31);
            queryInfoCache.Add("B3_RangeQuery", QueryOutputInfoHelper.AnalyzeSqlQuery(
                context.RecordSqlQueryStrings(
                    ctx => ctx.OrderLines
                        .Where(ol => ol.PickingCompletedWhen >= rangeFrom && ol.PickingCompletedWhen <= rangeTo)
                        .ToList()
                ).First(), sqlConnection: sqlConn));

            var orderIds = new[] { 1, 10, 100, 1000, 10000 };
            queryInfoCache.Add("B4_InQuery", QueryOutputInfoHelper.AnalyzeSqlQuery(
                context.RecordSqlQueryStrings(
                    ctx => ctx.OrderLines
                        .Where(ol => orderIds.Contains(ol.OrderID))
                        .ToList()
                ).First(), sqlConnection: sqlConn));

            string text = "C++";
            queryInfoCache.Add("B5_TextSearch", QueryOutputInfoHelper.AnalyzeSqlQuery(
                context.RecordSqlQueryStrings(
                    ctx => ctx.OrderLines
                        .Where(ol => ol.Description.Contains(text))
                        .ToList()
                ).First(), sqlConnection: sqlConn));

            int skip = 1000;
            int take = 50;
            queryInfoCache.Add("B6_PagingQuery", QueryOutputInfoHelper.AnalyzeSqlQuery(
                context.RecordSqlQueryStrings(
                    ctx => ctx.OrderLines
                        .OrderBy(ol => ol.OrderLineID)
                        .Skip(skip)
                        .Take(take)
                        .ToList()
                ).First(), sqlConnection: sqlConn));

            queryInfoCache.Add("C1_AggregationCount", QueryOutputInfoHelper.AnalyzeSqlQuery(
                context.RecordSqlQueryStrings(
                    ctx => ctx.OrderLines
                        .GroupBy(ol => ol.TaxRate)
                        .Select(g => new { TaxRate = g.Key, Count = g.Count() })
                        .OrderByDescending(x => x.Count)
                        .ToDictionary(x => x.TaxRate, x => x.Count)
                ).First(), sqlConnection: sqlConn));

            queryInfoCache.Add("C2_AggregationMax", QueryOutputInfoHelper.AnalyzeSqlQuery(
                context.RecordSqlQueryStrings(
                    ctx => ctx.OrderLines.Max(ol => ol.UnitPrice)
                ).First(), sqlConnection: sqlConn));

            queryInfoCache.Add("C3_AggregationSum", QueryOutputInfoHelper.AnalyzeSqlQuery(
                context.RecordSqlQueryStrings(
                    ctx => ctx.OrderLines.Sum(ol => ol.Quantity * ol.UnitPrice)
                ).First(), sqlConnection: sqlConn));

            queryInfoCache.Add("D1_OneToManyRelationship", QueryOutputInfoHelper.AnalyzeSqlQuery(
                context.RecordSqlQueryStrings(
                    ctx => ctx.Orders
                        .Include(o => o.OrderLines)
                        .SingleOrDefault(o => o.OrderID == 530)
                ).First(), sqlConnection: sqlConn));

            queryInfoCache.Add("D2_StockItems", QueryOutputInfoHelper.AnalyzeSqlQuery(
                context.RecordSqlQueryStrings(
                    ctx => ctx.StockItems
                        .Include(si => si.StockGroups)
                        .OrderBy(si => si.StockItemID)
                        .ToList()
                ).First(), sqlConnection: sqlConn));

            queryInfoCache.Add("D2_StockGroups", QueryOutputInfoHelper.AnalyzeSqlQuery(
                context.RecordSqlQueryStrings(
                    ctx => ctx.StockGroups
                        .Include(sg => sg.StockItems)
                        .OrderBy(sg => sg.StockGroupID)
                        .ToList()
                ).First(), sqlConnection: sqlConn));

            queryInfoCache.Add("D3_OptionalRelationship", QueryOutputInfoHelper.AnalyzeSqlQuery(
                context.RecordSqlQueryStrings(
                    ctx => ctx.Customers
                        .Include(c => c.Transactions)
                        .OrderBy(c => c.CustomerID)
                        .ToList()
                ).First(), sqlConnection: sqlConn));

            queryInfoCache.Add("E1_ColumnSorting", QueryOutputInfoHelper.AnalyzeSqlQuery(
                context.RecordSqlQueryStrings(
                    ctx => ctx.PurchaseOrders
                        .OrderBy(po => po.ExpectedDeliveryDate)
                        .Take(1000)
                        .ToList()
                ).First(), sqlConnection: sqlConn));

            queryInfoCache.Add("E2_Distinct", QueryOutputInfoHelper.AnalyzeSqlQuery(
                context.RecordSqlQueryStrings(
                    ctx => ctx.PurchaseOrders
                        .Select(po => po.SupplierReference)
                        .Distinct()
                        .ToList()
                ).First(), sqlConnection: sqlConn));

            queryInfoCache.Add("F1_JSONObjectQuery", QueryOutputInfoHelper.AnalyzeSqlQuery(
                context.RecordSqlQueryStrings(
                    ctx => ctx.People
                        .Where(p => p.CustomFields!.Title == "Team Member")
                        .OrderBy(p => p.PersonID)
                        .ToList()
                ).First(), sqlConnection: sqlConn));

            queryInfoCache.Add("F2_JSONArrayQuery", QueryOutputInfoHelper.AnalyzeSqlQuery(
                context.RecordSqlQueryStrings(
                    ctx => ctx.People
                        .Where(p => p.OtherLanguages!.Contains("Slovak"))
                        .OrderBy(p => p.PersonID)
                        .ToList()
                ).First(), sqlConnection: sqlConn));

            var g1SqlStrings = context.RecordSqlQueryStrings(ctx =>
                {
                    var first = context.Suppliers
                        .Where(s => s.SupplierID < 5)
                        .Select(s => s.SupplierID)
                        .ToList();

                    var last = context.Suppliers
                        .Where(s => s.SupplierID >= 5 && s.SupplierID <= 10)
                        .Select(s => s.SupplierID)
                        .ToList();

                    var suppliers = first
                        .Union(last)
                        .OrderBy(s => s)
                        .ToList();

                    return suppliers;
                }
            );
            queryInfoCache.Add("G1_Union_1", QueryOutputInfoHelper.AnalyzeSqlQuery(g1SqlStrings.ElementAt(0), sqlConnection: sqlConn));
            queryInfoCache.Add("G1_Union_2", QueryOutputInfoHelper.AnalyzeSqlQuery(g1SqlStrings.ElementAt(1), sqlConnection: sqlConn));

            var g2SqlStrings = context.RecordSqlQueryStrings(ctx =>
                {
                    var first = context.Suppliers
                        .Where(s => s.SupplierID < 10)
                        .Select(s => s.SupplierID)
                        .ToList();

                    var last = context.Suppliers
                        .Where(s => s.SupplierID >= 5 && s.SupplierID <= 15)
                        .Select(s => s.SupplierID)
                        .ToList();

                    var suppliers = first
                        .Intersect(last)
                        .OrderBy(s => s)
                        .ToList();

                    return suppliers;
                }
            );
            queryInfoCache.Add("G2_Intersection_1", QueryOutputInfoHelper.AnalyzeSqlQuery(g2SqlStrings.ElementAt(0), sqlConnection: sqlConn));
            queryInfoCache.Add("G2_Intersection_2", QueryOutputInfoHelper.AnalyzeSqlQuery(g2SqlStrings.ElementAt(1), sqlConnection: sqlConn));

            queryInfoCache.Add("H1_Metadata", QueryOutputInfoHelper.AnalyzeSqlQuery(
                context.RecordSqlQueryStrings(
                    ctx => ctx.Database.SqlQueryRaw<string>(
                        """
                            SELECT DATA_TYPE AS Value FROM INFORMATION_SCHEMA.COLUMNS 
                                WHERE TABLE_SCHEMA = 'Purchasing'
                                AND TABLE_NAME = 'Suppliers'
                                AND COLUMN_NAME = 'SupplierReference'
                        """
                    ).SingleOrDefault()
                ).First(), sqlConnection: sqlConn));
        }

        [GlobalCleanup]
        public void GlobalCleanup() {}

        [Benchmark]
        public PurchaseOrder? A1_EntityIdenticalToTable()
        {
            commandExecutor.Configure(queryInfoCache["A1_EntityIdenticalToTable"]);
            using var context = contextFactory.CreateDbContext();

            var order = context.PurchaseOrders.Find(25);

            return order;
        }

        [Benchmark]
        public SupplierContactInfo A2_LimitedEntity()
        {
            commandExecutor.Configure(queryInfoCache["A2_LimitedEntity"]);
            using var context = contextFactory.CreateDbContext();

            var contactInfo = context.Suppliers
            .Where(s => s.SupplierID == 10)
            .Select(s => new SupplierContactInfo
            {
                SupplierID = s.SupplierID,
                SupplierName = s.SupplierName,
                PhoneNumber = s.PhoneNumber,
                FaxNumber = s.FaxNumber,
                WebsiteURL = s.WebsiteURL,
                ValidFrom = s.ValidFrom,
                ValidTo = s.ValidTo
            })
            .Single();

            return contactInfo;
        }

        [Benchmark]
        public (SupplierContactInfo ContactInfo, SupplierBankAccount BankAccount) A3_MultipleEntitiesFromOneResult()
        {
            commandExecutor.Configure(queryInfoCache["A3_MultipleEntitiesFromOneResult"]);
            using var context = contextFactory.CreateDbContext();

            var result = context.Suppliers
            .Where(s => s.SupplierID == 10)
            .Select(s => new
            {
                ContactInfo = new SupplierContactInfo
                {
                    SupplierID = s.SupplierID,
                    SupplierName = s.SupplierName,
                    PhoneNumber = s.PhoneNumber,
                    FaxNumber = s.FaxNumber,
                    WebsiteURL = s.WebsiteURL,
                    ValidFrom = s.ValidFrom,
                    ValidTo = s.ValidTo
                },
                BankAccount = new SupplierBankAccount
                {
                    SupplierID = s.SupplierID,
                    BankAccountName = s.BankAccountName,
                    BankAccountBranch = s.BankAccountBranch,
                    BankAccountCode = s.BankAccountCode,
                    BankAccountNumber = s.BankAccountNumber,
                    BankInternationalCode = s.BankInternationalCode
                }
            })
            .Select(result => new { result.ContactInfo, result.BankAccount })
            .Single();

            return (result.ContactInfo, result.BankAccount);
        }

        [Benchmark]
        public List<PurchaseOrderUpdate> A4_StoredProcedureToEntity()
        {
            commandExecutor.Configure(queryInfoCache["A4_StoredProcedureToEntity"]);
            using var context = contextFactory.CreateDbContext();

            var from = new DateTime(2014, 1, 1);
            var to = new DateTime(2015, 1, 1);

            var orders = context.Set<PurchaseOrderUpdate>()
                .FromSqlInterpolated($"EXEC WideWorldImporters.Integration.GetOrderUpdates @LastCutoff = {from}, @NewCutoff = {to}")
                .ToList();

            return orders;
        }

        [Benchmark]
        public List<OrderLine> B1_SelectionOverIndexedColumn()
        {
            commandExecutor.Configure(queryInfoCache["B1_SelectionOverIndexedColumn"]);
            using var context = contextFactory.CreateDbContext();

            int orderId = 26866;

            var orderLines = context.OrderLines
                .Where(ol => ol.OrderID == orderId)
                .ToList();

            return orderLines;
        }

        [Benchmark]
        public List<OrderLine> B2_SelectionOverNonIndexedColumn()
        {
            commandExecutor.Configure(queryInfoCache["B2_SelectionOverNonIndexedColumn"]);
            using var context = contextFactory.CreateDbContext();

            decimal unitPrice = 25m;

            var orderLines = context.OrderLines
                .Where(ol => ol.UnitPrice == unitPrice)
                .ToList();

            return orderLines;
        }

        [Benchmark]
        public List<OrderLine> B3_RangeQuery()
        {
            commandExecutor.Configure(queryInfoCache["B3_RangeQuery"]);
            using var context = contextFactory.CreateDbContext();

            var from = new DateTime(2014, 12, 20);
            var to = new DateTime(2014, 12, 31);

            var orderLines = context.OrderLines
                .Where(ol => ol.PickingCompletedWhen >= from && ol.PickingCompletedWhen <= to)
                .ToList();

            return orderLines;
        }

        [Benchmark]
        public List<OrderLine> B4_InQuery()
        {
            commandExecutor.Configure(queryInfoCache["B4_InQuery"]);
            using var context = contextFactory.CreateDbContext();

            var orderIds = new[] { 1, 10, 100, 1000, 10000 };

            var orderLines = context.OrderLines
                .Where(ol => orderIds.Contains(ol.OrderID))
                .ToList();

            return orderLines;
        }

        [Benchmark]
        public List<OrderLine> B5_TextSearch()
        {
            commandExecutor.Configure(queryInfoCache["B5_TextSearch"]);
            using var context = contextFactory.CreateDbContext();

            string text = "C++";

            var orderLines = context.OrderLines
                //.Where(ol => EF.Functions.Like(ol.Description, $"%{text}%"))
                .Where(ol => ol.Description.Contains(text))
                .ToList();

            return orderLines;
        }

        [Benchmark]
        public List<OrderLine> B6_PagingQuery()
        {
            commandExecutor.Configure(queryInfoCache["B6_PagingQuery"]);
            using var context = contextFactory.CreateDbContext();

            int skip = 1000;
            int take = 50;

            var orderLines = context.OrderLines
                .OrderBy(ol => ol.OrderLineID)
                .Skip(skip)
                .Take(take)
                .ToList();

            return orderLines;
        }

        [Benchmark]
        public Dictionary<decimal, int> C1_AggregationCount()
        {
            commandExecutor.Configure(queryInfoCache["C1_AggregationCount"]);
            using var context = contextFactory.CreateDbContext();

            var taxRates = context.OrderLines
                .GroupBy(ol => ol.TaxRate)
                .Select(g => new { TaxRate = g.Key, Count = g.Count() })
                .OrderByDescending(x => x.Count)
                .ToDictionary(x => x.TaxRate + ++counter, x => x.Count);

            return taxRates;
        }

        [Benchmark]
        public decimal? C2_AggregationMax()
        {
            commandExecutor.Configure(queryInfoCache["C2_AggregationMax"]);
            using var context = contextFactory.CreateDbContext();

            var maxUnitPrice = context.OrderLines.Max(ol => ol.UnitPrice);

            return maxUnitPrice;
        }

        [Benchmark]
        public decimal? C3_AggregationSum()
        {
            commandExecutor.Configure(queryInfoCache["C3_AggregationSum"]);
            using var context = contextFactory.CreateDbContext();

            var totalSales = context.OrderLines
                .Sum(ol => ol.Quantity * ol.UnitPrice);

            return totalSales;
        }

        [Benchmark]
        public Order D1_OneToManyRelationship()
        {
            commandExecutor.Configure(queryInfoCache["D1_OneToManyRelationship"]);
            using var context = contextFactory.CreateDbContext();

            var order = context.Orders
                .Include(o => o.OrderLines)
                .Single(o => o.OrderID == 530);

            return order;
        }

        [Benchmark]
        public (List<StockItem> stockItems, List<StockGroup> stockGroups) D2_ManyToManyRelationship()
        {
            using var context = contextFactory.CreateDbContext();

            commandExecutor.Configure(queryInfoCache["D2_StockItems"]);
            var stockItems = context.StockItems
                .Include(si => si.StockGroups)
                .OrderBy(si => si.StockItemID)
                .ToList();

            commandExecutor.Configure(queryInfoCache["D2_StockGroups"]);
            var stockGroups = context.StockGroups
                .Include(sg => sg.StockItems)
                .OrderBy(si => si.StockGroupID)
                .ToList();

            return (stockItems, stockGroups);
        }

        [Benchmark]
        public List<Customer> D3_OptionalRelationship()
        {
            commandExecutor.Configure(queryInfoCache["D3_OptionalRelationship"]);
            using var context = contextFactory.CreateDbContext();

            var result = context.Customers
            .Include(c => c.Transactions)
            .OrderBy(c => c.CustomerID)
            .ToList();

            return result;
        }

        [Benchmark]
        public List<PurchaseOrder> E1_ColumnSorting()
        {
            commandExecutor.Configure(queryInfoCache["E1_ColumnSorting"]);
            using var context = contextFactory.CreateDbContext();

            var orders = context.PurchaseOrders
                .OrderBy(po => po.ExpectedDeliveryDate)
                .Take(1000)
                .ToList();

            return orders;
        }

        [Benchmark]
        public List<string?> E2_Distinct()
        {
            commandExecutor.Configure(queryInfoCache["E2_Distinct"]);
            using var context = contextFactory.CreateDbContext();

            var supplierReferences = context.PurchaseOrders
                .Select(po => po.SupplierReference)
                .Distinct()
                .ToList();

            return supplierReferences;
        }

        [Benchmark]
        public List<Person> F1_JSONObjectQuery()
        {
            commandExecutor.Configure(queryInfoCache["F1_JSONObjectQuery"]);
            using var context = contextFactory.CreateDbContext();

            var people = context.People
                .Where(p => p.CustomFields!.Title == "Team Member")
                .OrderBy(p => p.PersonID)
                .ToList();

            return people;
        }

        [Benchmark]
        public List<Person> F2_JSONArrayQuery()
        {
            commandExecutor.Configure(queryInfoCache["F2_JSONArrayQuery"]);
            using var context = contextFactory.CreateDbContext();

            var people = context.People
                .Where(p => p.OtherLanguages!.Contains("Slovak"))
                .OrderBy(p => p.PersonID)
                .ToList();

            return people;
        }

        [Benchmark]
        public List<int> G1_Union()
        {
            using var context = contextFactory.CreateDbContext();

            commandExecutor.Configure(queryInfoCache["G1_Union_1"]);
            var first = context.Suppliers
                .Where(s => s.SupplierID < 5)
                .Select(s => s.SupplierID)
                .ToList();

            commandExecutor.Configure(queryInfoCache["G1_Union_2"]);
            var last = context.Suppliers
                .Where(s => s.SupplierID >= 5 && s.SupplierID <= 10)
                .Select(s => s.SupplierID)
                .ToList();

            var suppliers = first
                .Union(last)
                .OrderBy(s => s)
                .ToList();

            return suppliers;
        }

        [Benchmark]
        public List<int> G2_Intersection()
        {
            using var context = contextFactory.CreateDbContext();

            commandExecutor.Configure(queryInfoCache["G2_Intersection_1"]);
            var first = context.Suppliers
                .Where(s => s.SupplierID < 10)
                .Select(s => s.SupplierID)
                .ToList();

            commandExecutor.Configure(queryInfoCache["G2_Intersection_2"]);
            var last = context.Suppliers
                .Where(s => s.SupplierID >= 5 && s.SupplierID <= 15)
                .Select(s => s.SupplierID)
                .ToList();

            var suppliers = first
                .Intersect(last)
                .OrderBy(s => s)
                .ToList();

            return suppliers;
        }

        [Benchmark]
        public string H1_Metadata()
        {
            commandExecutor.Configure(queryInfoCache["H1_Metadata"]);
            using var context = contextFactory.CreateDbContext();

            var datatype = context.Database.SqlQueryRaw<string>(
                """
                    SELECT DATA_TYPE AS Value FROM INFORMATION_SCHEMA.COLUMNS 
                        WHERE TABLE_SCHEMA = 'Purchasing'
                        AND TABLE_NAME = 'Suppliers'
                        AND COLUMN_NAME = 'SupplierReference'
                """
            ).Single();

            return datatype;
        }
    }
}
