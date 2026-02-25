using System.Data;
using System.Data.Common;
using System.Reflection;
using Microsoft.Data.SqlClient;
using Microsoft.EntityFrameworkCore.Diagnostics;
using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.EntityFrameworkCore.Internal;
using Microsoft.EntityFrameworkCore.Metadata.Internal;
using Microsoft.EntityFrameworkCore.Query;
using Microsoft.EntityFrameworkCore.SqlServer.Query.Internal;
using Microsoft.EntityFrameworkCore.Storage;
using static Microsoft.EntityFrameworkCore.DbLoggerCategory.Database;

namespace Common.Mock;

public class RecordCommandsInterceptor : DbCommandInterceptor
{
    public static RecordCommandsInterceptor Instance { get; } = new();

    private RecordCommandsInterceptor()
    {
    }

    public override InterceptionResult<DbCommand> CommandCreating(CommandCorrelatedEventData eventData, InterceptionResult<DbCommand> result)
    {
        if (RecordSqlQueryStringsScope.Current != null && eventData.IsAsync)
            throw new InvalidOperationException("Cannot use Async operation when recording a command");

        return base.CommandCreating(eventData, result);
    }

    public override InterceptionResult<int> NonQueryExecuting(DbCommand cmd, CommandEventData eventData, InterceptionResult<int> result)
        => this.Executing(cmd, eventData, result);

    public override InterceptionResult<DbDataReader> ReaderExecuting(DbCommand cmd, CommandEventData eventData,
        InterceptionResult<DbDataReader> result)
    {
        this.Executing(cmd, eventData, result);
        //var concreteReaderType = result.GetType().GetTypeInfo().GenericTypeArguments[0];
        //var concreteReader = (DbDataReader?)Activator.CreateInstance(concreteReaderType);
        return InterceptionResult<DbDataReader>.SuppressWithResult(new DataTable().CreateDataReader());
    }

    public override InterceptionResult<object> ScalarExecuting(DbCommand cmd, CommandEventData eventData, InterceptionResult<object> result)
        => this.Executing(cmd, eventData, result);


    private InterceptionResult<T> Executing<T>(DbCommand cmd, CommandEventData eventData, InterceptionResult<T> result)
    {
        if (RecordSqlQueryStringsScope.Current == null)
            return result;

        if (eventData.Context == null)
            return result;

        var queryStringFactory = eventData.Context.GetService<IRelationalQueryStringFactory>();
        var sqlQuery = queryStringFactory.Create(cmd);

        RecordSqlQueryStringsScope.Current.Record(sqlQuery);
        return InterceptionResult<T>.SuppressWithResult(default!);
    }
}
