using Microsoft.EntityFrameworkCore;

namespace Common.Mock.EFCore;

public static class DbContextExtensions
{
    public static IReadOnlyCollection<QueryOutputInfoHelper.QueryInfo> RecordQueryInfos<TContext, TResult>(this TContext dbCtx, params Func<TContext, TResult>[] getResults) where TContext : DbContext
    {
        using (RecordQueryInfoScope.StartNew())
        {
            foreach (var getResult in getResults)
            {
                try
                {
                    getResult(dbCtx);
                }
                catch (InvalidOperationException exception)
                {
                    // Ignore exceptions, we just want to record the SQL query strings.
                    Console.WriteLine(exception);
                }
            }
            return RecordQueryInfoScope.Current?.RecordedQueryInfos ?? Array.Empty<QueryOutputInfoHelper.QueryInfo>();
        }
    }
}
