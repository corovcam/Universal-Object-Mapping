using Microsoft.EntityFrameworkCore;

namespace Common.Mock;

public static class DbContextExtensions
{
    public static IReadOnlyCollection<string> RecordSqlQueryStrings<TContext, TResult>(this TContext dbCtx, params Func<TContext, TResult>[] getResults) where TContext : DbContext
    {
        using (RecordSqlQueryStringsScope.StartNew())
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
            return RecordSqlQueryStringsScope.Current.RecordedSqlQueries;
        }
    }
}
