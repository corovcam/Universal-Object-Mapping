using System.Data.Common;
using BenchmarkDotNet.Attributes;
using Common;
using Common.Mock;
using Common.Mock.NHibernate;
using Microsoft.Data.SqlClient;
using Microsoft.EntityFrameworkCore.Internal;
using NHibernate;
using NHibernate.Cfg;
using NHibernate.Dialect;
using NHibernate.Driver;
using NHibernate.Linq;
using NHibernate.Transform;
using NHibernateEntities;
using NHibernateEntities.Models;

namespace NHibernatePerformance
{
    [MemoryDiagnoser]
    [ExceptionDiagnoser]
    public class NHibernateBenchmarks
    {
        private ISessionFactory sessionFactory = null!;
        private readonly BenchmarkCommandExecutor commandExecutor = BenchmarkCommandExecutor.Instance;
        private Dictionary<string, QueryOutputInfoHelper.QueryInfo> queryInfoCache = new();

        [GlobalSetup]
        public void GlobalSetup()
        {
            NHibernateFakeDriver.DriverClass = typeof(SqlClientDriver);
            var configuration = new Configuration()
                .DataBaseIntegration(db =>
                {
                    db.ConnectionString = DatabaseConfig.MSSQLConnectionString;
                    db.Driver<NHibernateFakeDriver>();
                    db.Dialect<MsSql2012Dialect>();
                })
                .AddAssembly(typeof(PurchaseOrder).Assembly);

            sessionFactory = configuration.BuildSessionFactory();
            ExtractQueryInfo();
        }

        private void ExtractQueryInfo()
        {
            using var session = sessionFactory.OpenSession();
            using var sqlConn = new SqlConnection(DatabaseConfig.MSSQLConnectionString);
            sqlConn.Open();

            queryInfoCache.Add("A1_EntityIdenticalToTable", 
                session.RecordQueryInfos(s => s.Get<PurchaseOrder>(25)).First());

            queryInfoCache.Add("A2_LimitedEntity", 
                session.RecordQueryInfos(s => s.Query<Supplier>()
                    .Where(sup => sup.SupplierID == 10)
                    .Select(sup => new SupplierContactInfo
                    {
                        SupplierID = sup.SupplierID,
                        SupplierName = sup.SupplierName,
                        PhoneNumber = sup.PhoneNumber,
                        FaxNumber = sup.FaxNumber,
                        WebsiteURL = sup.WebsiteURL,
                        ValidFrom = sup.ValidFrom,
                        ValidTo = sup.ValidTo
                    })
                    .SingleOrDefault()).First());

            queryInfoCache.Add("A3_MultipleEntitiesFromOneResult", 
                session.RecordQueryInfos(s => s.Query<Supplier>()
                    .Where(sup => sup.SupplierID == 10)
                    .Select(sup => new
                    {
                        ContactInfo = new SupplierContactInfo
                        {
                            SupplierID = sup.SupplierID,
                            SupplierName = sup.SupplierName,
                            PhoneNumber = sup.PhoneNumber,
                            FaxNumber = sup.FaxNumber,
                            WebsiteURL = sup.WebsiteURL,
                            ValidFrom = sup.ValidFrom,
                            ValidTo = sup.ValidTo
                        },
                        BankAccount = new SupplierBankAccount
                        {
                            SupplierID = sup.SupplierID,
                            BankAccountName = sup.BankAccountName,
                            BankAccountBranch = sup.BankAccountBranch,
                            BankAccountCode = sup.BankAccountCode,
                            BankAccountNumber = sup.BankAccountNumber,
                            BankInternationalCode = sup.BankInternationalCode
                        }
                    })
                    .Select(result => new { result.ContactInfo, result.BankAccount })
                    .SingleOrDefault()).First());

            var from = new DateTime(2014, 1, 1);
            var to = new DateTime(2015, 1, 1);
            queryInfoCache.Add("A4_StoredProcedureToEntity", 
                session.RecordQueryInfos(s => s.GetNamedQuery("GetOrderUpdates")
                    .SetDateTime("from", from)
                    .SetDateTime("to", to)
                    .SetResultTransformer(Transformers.AliasToEntityMap)
                    .List<System.Collections.Hashtable>()).First());

            int orderId = 26866;
            queryInfoCache.Add("B1_SelectionOverIndexedColumn", 
                session.RecordQueryInfos(s => s.Query<OrderLine>()
                    .Where(ol => ol.OrderID == orderId)
                    .ToList()).First());

            decimal unitPrice = 25m;
            queryInfoCache.Add("B2_SelectionOverNonIndexedColumn", 
                session.RecordQueryInfos(s => s.Query<OrderLine>()
                    .Where(ol => ol.UnitPrice == unitPrice)
                    .ToList()).First());

            var rangeFrom = new DateTime(2014, 12, 20);
            var rangeTo = new DateTime(2014, 12, 31);
            queryInfoCache.Add("B3_RangeQuery", 
                session.RecordQueryInfos(s => s.Query<OrderLine>()
                    .Where(ol => ol.PickingCompletedWhen >= rangeFrom && ol.PickingCompletedWhen <= rangeTo)
                    .ToList()).First());

            var orderIds = new[] { 1, 10, 100, 1000, 10000 };
            queryInfoCache.Add("B4_InQuery", 
                session.RecordQueryInfos(s => s.Query<OrderLine>()
                    .Where(ol => orderIds.Contains(ol.OrderID))
                    .ToList()).First());

            string text = "C++";
            queryInfoCache.Add("B5_TextSearch", 
                session.RecordQueryInfos(s => s.Query<OrderLine>()
                    .Where(ol => ol.Description.Contains(text))
                    .ToList()).First());

            int skip = 1000;
            int take = 50;
            queryInfoCache.Add("B6_PagingQuery", 
                session.RecordQueryInfos(s => s.Query<OrderLine>()
                    .OrderBy(ol => ol.OrderLineID)
                    .Skip(skip)
                    .Take(take)
                    .ToList()).First());

            queryInfoCache.Add("C1_AggregationCount", 
                session.RecordQueryInfos(s => s.Query<OrderLine>()
                    .GroupBy(ol => ol.TaxRate)
                    .Select(g => new { TaxRate = g.Key, Count = g.Count() })
                    .OrderByDescending(x => x.Count)
                    .ToList()).First());

            queryInfoCache.Add("C2_AggregationMax", 
                session.RecordQueryInfos(s => s.CreateQuery("SELECT MAX(ol.UnitPrice) FROM OrderLine ol")
                    .UniqueResult<decimal?>()).First());

            queryInfoCache.Add("C3_AggregationSum", 
                session.RecordQueryInfos(s => s
                    .CreateQuery("SELECT SUM(ol.Quantity * ol.UnitPrice) FROM OrderLine ol")
                    .UniqueResult<decimal?>()).First());

            queryInfoCache.Add("D1_OneToManyRelationship", 
                session.RecordQueryInfos(s => s.Query<Order>()
                    .Fetch(o => o.OrderLines)
                    .SingleOrDefault(o => o.OrderID == 530)).First());

            queryInfoCache.Add("D2_StockItems", 
                session.RecordQueryInfos(s => s.Query<StockItem>()
                    .Fetch(si => si.StockGroups)
                    .OrderBy(si => si.StockItemID)
                    .ToList()).First());

            queryInfoCache.Add("D2_StockGroups", 
                session.RecordQueryInfos(s => s.Query<StockGroup>()
                    .Fetch(sg => sg.StockItems)
                    .OrderBy(sg => sg.StockGroupID)
                    .ToList()).First());

            queryInfoCache.Add("D3_OptionalRelationship", 
                session.RecordQueryInfos(s => s.Query<Customer>()
                    .Fetch(c => c.Transactions)
                    .OrderBy(c => c.CustomerID)
                    .ToList()).First());

            queryInfoCache.Add("E1_ColumnSorting", 
                session.RecordQueryInfos(s => s.Query<PurchaseOrder>()
                    .OrderBy(po => po.ExpectedDeliveryDate)
                    .Take(1000)
                    .ToList()).First());

            queryInfoCache.Add("E2_Distinct", 
                session.RecordQueryInfos(s => s.Query<PurchaseOrder>()
                    .Select(po => po.SupplierReference)
                    .Distinct()
                    .ToList()).First());

            var f1Sql = """
                            SELECT PersonID, FullName, PreferredName, EmailAddress, CustomFields, OtherLanguages 
                            FROM WideWorldImporters.Application.People 
                            WHERE JSON_VALUE(CustomFields, '$.Title') = :title
                        """;
            queryInfoCache.Add("F1_JSONObjectQuery", 
                session.RecordQueryInfos(s => s.CreateSQLQuery(f1Sql)
                    .SetParameter("title", "Team Member")
                    .SetResultTransformer(Transformers.AliasToBean<Person>())
                    .List<Person>()).First());

            var f2Sql = """
                            SELECT PersonID, FullName, PreferredName, EmailAddress, CustomFields, OtherLanguages 
                            FROM WideWorldImporters.Application.People 
                            WHERE EXISTS (
                                SELECT 1 FROM OPENJSON(OtherLanguages) 
                                WHERE value = :lang
                            )
                        """;
            queryInfoCache.Add("F2_JSONArrayQuery", 
                session.RecordQueryInfos(s => s.CreateSQLQuery(f2Sql)
                    .SetParameter("lang", "Slovak")
                    .SetResultTransformer(Transformers.AliasToBean<Person>())
                    .List<Person>()).First());

            var g1SqlStrings = session.RecordQueryInfos(s =>
            {
                var first = s.Query<Supplier>()
                    .Where(sup => sup.SupplierID < 5)
                    .Select(sup => sup.SupplierID)
                    .ToList();

                var last = s.Query<Supplier>()
                    .Where(sup => sup.SupplierID >= 5 && sup.SupplierID <= 10)
                    .Select(sup => sup.SupplierID)
                    .ToList();

                return first.Union(last).OrderBy(sup => sup).ToList();
            });
            queryInfoCache.Add("G1_Union_1", g1SqlStrings.ElementAt(0));
            queryInfoCache.Add("G1_Union_2", g1SqlStrings.ElementAt(1));

            var g2SqlStrings = session.RecordQueryInfos(s =>
            {
                var first = s.Query<Supplier>()
                    .Where(sup => sup.SupplierID < 10)
                    .Select(sup => sup.SupplierID)
                    .ToList();

                var last = s.Query<Supplier>()
                    .Where(sup => sup.SupplierID >= 5 && sup.SupplierID <= 15)
                    .Select(sup => sup.SupplierID)
                    .ToList();

                return first.Intersect(last).OrderBy(sup => sup).ToList();
            });
            queryInfoCache.Add("G2_Intersection_1", g2SqlStrings.ElementAt(0));
            queryInfoCache.Add("G2_Intersection_2", g2SqlStrings.ElementAt(1));

            queryInfoCache.Add("H1_Metadata", 
                session.RecordQueryInfos(s => s.CreateSQLQuery(
                    """
                        SELECT DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS 
                            WHERE TABLE_SCHEMA = 'Purchasing'
                            AND TABLE_NAME = 'Suppliers'
                            AND COLUMN_NAME = 'SupplierReference'
                    """
                ).UniqueResult<string>()).First());
        }

        [GlobalCleanup]
        public void GlobalCleanup()
        {
            sessionFactory.Dispose();
        }

        [Benchmark]
        public PurchaseOrder A1_EntityIdenticalToTable()
        {
            commandExecutor.Configure(queryInfoCache["A1_EntityIdenticalToTable"]);
            using var session = sessionFactory.OpenSession();

            var order = session.Get<PurchaseOrder>(25);

            return order;
        }

        [Benchmark]
        public SupplierContactInfo A2_LimitedEntity()
        {
            commandExecutor.Configure(queryInfoCache["A2_LimitedEntity"]);
            using var session = sessionFactory.OpenSession();

            var contactInfo = session.Query<Supplier>()
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
            using var session = sessionFactory.OpenSession();

            var result = session.Query<Supplier>()
                .Where(s => s.SupplierID == 10)
                .Select(s => new
                {
                    ContactInfo =
                        new SupplierContactInfo
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
        public IList<System.Collections.Hashtable> A4_StoredProcedureToEntity()
        {
            commandExecutor.Configure(queryInfoCache["A4_StoredProcedureToEntity"]);
            using var session = sessionFactory.OpenSession();

            var from = new DateTime(2014, 1, 1);
            var to = new DateTime(2015, 1, 1);

            // Can't map to entity directly, NHibernate throws internal error
            // It can't process the spaces in column names
            var orders = session.GetNamedQuery("GetOrderUpdates")
                .SetDateTime("from", from)
                .SetDateTime("to", to)
                .SetResultTransformer(Transformers.AliasToEntityMap)
                .List<System.Collections.Hashtable>();

            return orders;
        }

        [Benchmark]
        public List<OrderLine> B1_SelectionOverIndexedColumn()
        {
            commandExecutor.Configure(queryInfoCache["B1_SelectionOverIndexedColumn"]);
            using var session = sessionFactory.OpenSession();

            int orderId = 26866;

            var orderLines = session.Query<OrderLine>()
                .Where(ol => ol.OrderID == orderId)
                .ToList();

            return orderLines;
        }

        [Benchmark]
        public List<OrderLine> B2_SelectionOverNonIndexedColumn()
        {
            commandExecutor.Configure(queryInfoCache["B2_SelectionOverNonIndexedColumn"]);
            using var session = sessionFactory.OpenSession();

            decimal unitPrice = 25m;

            var orderLines = session.Query<OrderLine>()
                .Where(ol => ol.UnitPrice == unitPrice)
                .ToList();

            return orderLines;
        }

        [Benchmark]
        public List<OrderLine> B3_RangeQuery()
        {
            commandExecutor.Configure(queryInfoCache["B3_RangeQuery"]);
            using var session = sessionFactory.OpenSession();

            var from = new DateTime(2014, 12, 20);
            var to = new DateTime(2014, 12, 31);

            var orderLines = session.Query<OrderLine>()
                .Where(ol => ol.PickingCompletedWhen >= from && ol.PickingCompletedWhen <= to)
                .ToList();

            return orderLines;
        }

        [Benchmark]
        public List<OrderLine> B4_InQuery()
        {
            commandExecutor.Configure(queryInfoCache["B4_InQuery"]);
            using var session = sessionFactory.OpenSession();

            var orderIds = new[] { 1, 10, 100, 1000, 10000 };

            var orderLines = session.Query<OrderLine>()
                .Where(ol => orderIds.Contains(ol.OrderID))
                .ToList();

            return orderLines;
        }

        [Benchmark]
        public List<OrderLine> B5_TextSearch()
        {
            commandExecutor.Configure(queryInfoCache["B5_TextSearch"]);
            using var session = sessionFactory.OpenSession();

            string text = "C++";

            var orderLines = session.Query<OrderLine>()
                .Where(ol => ol.Description.Contains(text))
                .ToList();

            return orderLines;
        }

        [Benchmark]
        public List<OrderLine> B6_PagingQuery()
        {
            commandExecutor.Configure(queryInfoCache["B6_PagingQuery"]);
            using var session = sessionFactory.OpenSession();

            int skip = 1000;
            int take = 50;

            var orderLines = session.Query<OrderLine>()
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
            using var session = sessionFactory.OpenSession();

            var taxRates = session.Query<OrderLine>()
                .GroupBy(ol => ol.TaxRate)
                .Select(g => new { TaxRate = g.Key, Count = g.Count() })
                .OrderByDescending(x => x.Count)
                .ToDictionary(x => x.TaxRate, x => x.Count);

            return taxRates;
        }

        [Benchmark]
        public decimal? C2_AggregationMax()
        {
            commandExecutor.Configure(queryInfoCache["C2_AggregationMax"]);
            using var session = sessionFactory.OpenSession();

            var maxUnitPrice = session.Query<OrderLine>()
                .Max(ol => ol.UnitPrice);

            return maxUnitPrice;
        }

        [Benchmark]
        public decimal? C3_AggregationSum()
        {
            commandExecutor.Configure(queryInfoCache["C3_AggregationSum"]);
            using var session = sessionFactory.OpenSession();

            var totalSales = session.Query<OrderLine>()
                .Sum(ol => ol.Quantity * ol.UnitPrice);

            return totalSales;
        }

        [Benchmark]
        public Order D1_OneToManyRelationship()
        {
            commandExecutor.Configure(queryInfoCache["D1_OneToManyRelationship"]);
            using var session = sessionFactory.OpenSession();

            var order = session.Query<Order>()
                .Fetch(o => o.OrderLines)
                .Single(o => o.OrderID == 530);

            return order;
        }

        [Benchmark]
        public (List<StockItem> stockItems, List<StockGroup> stockGroups) D2_ManyToManyRelationship()
        {
            using var session = sessionFactory.OpenSession();

            commandExecutor.Configure(queryInfoCache["D2_StockItems"]);
            var stockItems = session.Query<StockItem>()
                .Fetch(si => si.StockGroups)
                .OrderBy(si => si.StockItemID)
                .ToList();

            commandExecutor.Configure(queryInfoCache["D2_StockGroups"]);
            var stockGroups = session.Query<StockGroup>()
                .Fetch(sg => sg.StockItems)
                .OrderBy(sg => sg.StockGroupID)
                .ToList();

            return (stockItems, stockGroups);
        }

        [Benchmark]
        public List<Customer> D3_OptionalRelationship()
        {
            commandExecutor.Configure(queryInfoCache["D3_OptionalRelationship"]);
            using var session = sessionFactory.OpenSession();

            var result = session.Query<Customer>()
                .Fetch(c => c.Transactions)
                .OrderBy(c => c.CustomerID)
                .ToList();

            return result;
        }

        [Benchmark]
        public List<PurchaseOrder> E1_ColumnSorting()
        {
            commandExecutor.Configure(queryInfoCache["E1_ColumnSorting"]);
            using var session = sessionFactory.OpenSession();

            var orders = session.Query<PurchaseOrder>()
                .OrderBy(po => po.ExpectedDeliveryDate)
                .Take(1000)
                .ToList();

            return orders;
        }

        [Benchmark]
        public List<string?> E2_Distinct()
        {
            commandExecutor.Configure(queryInfoCache["E2_Distinct"]);
            using var session = sessionFactory.OpenSession();

            var supplierReferences = session.Query<PurchaseOrder>()
                .Select(po => po.SupplierReference)
                .Distinct()
                .ToList();

            return supplierReferences;
        }

        [Benchmark]
        public IList<Person> F1_JSONObjectQuery()
        {
            commandExecutor.Configure(queryInfoCache["F1_JSONObjectQuery"]);
            using var session = sessionFactory.OpenSession();

            var sql = """
                          SELECT PersonID, FullName, PreferredName, EmailAddress, CustomFields, OtherLanguages 
                          FROM WideWorldImporters.Application.People 
                          WHERE JSON_VALUE(CustomFields, '$.Title') = :title
                      """;

            var people = session.CreateSQLQuery(sql)
                .SetParameter("title", "Team Member")
                .SetResultTransformer(Transformers.AliasToBean<Person>())
                .List<Person>();

            return people;
        }

        [Benchmark]
        public IList<Person> F2_JSONArrayQuery()
        {
            commandExecutor.Configure(queryInfoCache["F2_JSONArrayQuery"]);
            using var session = sessionFactory.OpenSession();

            var sql = """
                          SELECT PersonID, FullName, PreferredName, EmailAddress, CustomFields, OtherLanguages 
                          FROM WideWorldImporters.Application.People 
                          WHERE EXISTS (
                              SELECT 1 FROM OPENJSON(OtherLanguages) 
                              WHERE value = :lang
                          )
                      """;

            var people = session.CreateSQLQuery(sql)
                .SetParameter("lang", "Slovak")
                .SetResultTransformer(Transformers.AliasToBean<Person>())
                .List<Person>();

            return people;
        }

        [Benchmark]
        public List<int> G1_Union()
        {
            using var session = sessionFactory.OpenSession();

            commandExecutor.Configure(queryInfoCache["G1_Union_1"]);
            var first = session.Query<Supplier>()
                .Where(s => s.SupplierID < 5)
                .Select(s => s.SupplierID)
                .ToList();

            commandExecutor.Configure(queryInfoCache["G1_Union_2"]);
            var last = session.Query<Supplier>()
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
            using var session = sessionFactory.OpenSession();

            commandExecutor.Configure(queryInfoCache["G2_Intersection_1"]);
            var first = session.Query<Supplier>()
                .Where(s => s.SupplierID < 10)
                .Select(s => s.SupplierID)
                .ToList();

            commandExecutor.Configure(queryInfoCache["G2_Intersection_2"]);
            var last = session.Query<Supplier>()
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
            using var session = sessionFactory.OpenSession();

            var datatype = session.CreateSQLQuery(
                    """
                        SELECT DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS 
                            WHERE TABLE_SCHEMA = 'Purchasing'
                            AND TABLE_NAME = 'Suppliers'
                            AND COLUMN_NAME = 'SupplierReference'
                    """
                )
                .UniqueResult<string>();

            return datatype;
        }
    }
}