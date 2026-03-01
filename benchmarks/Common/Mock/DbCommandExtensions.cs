using System.Data.Common;
using Common.Mock.Query;

namespace Common.Mock;

public static class DbCommandExtensions
{
    public static string ToQueryString(this DbCommand command)
    {
        var connectionTypeName = command.Connection?.GetType().Name ?? "";
        
        IRelationalQueryStringFactory factory;
        if (connectionTypeName.Contains("Sqlite"))
        {
            factory = new SqliteQueryStringFactory();
        }
        else if (connectionTypeName.Contains("SqlConnection") || connectionTypeName.Contains("SqlDbConnection"))
        {
            factory = new SqlServerQueryStringFactory();
        }
        else
        {
            factory = new RelationalQueryStringFactory();
        }

        return factory.Create(command);
    }
}
