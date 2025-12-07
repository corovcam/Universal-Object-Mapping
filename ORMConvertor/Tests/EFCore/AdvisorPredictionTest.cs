using AbstractWrappers;
using EFCoreWrappers;
using Microsoft.VisualStudio.TestPlatform.ObjectModel;
using Model;
using SampleData;
using System.Linq;
using Tests.Fixtures;

[assembly: CaptureConsole]
namespace Tests.EFCore;

public class AdvisorPredictionTest
{
    [Fact]
    public void EFCoreSqlExtraction1()
    {
        EfCoreSqlExtractor_ca48d48729fb42baaf9f71957a84092e extractor = new();
        string sqlQuery;
        try
        {
            extractor.Setup();
            sqlQuery = extractor.GetSqlQuery();
        }
        finally
        {
            extractor.Cleanup();
        }

        Console.WriteLine("SQL: ", sqlQuery);

        Assert.NotNull(sqlQuery);
    }
}
