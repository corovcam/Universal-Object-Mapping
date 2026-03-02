using System.Data;
using System.Data.Common;
using Microsoft.EntityFrameworkCore.Diagnostics;

namespace Common.Mock.EFCore;

public class RecordCommandsInterceptor : DbCommandInterceptor
{
    public static RecordCommandsInterceptor Instance { get; } = new();

    private RecordCommandsInterceptor()
    {
    }

    public override InterceptionResult<DbCommand> CommandCreating(CommandCorrelatedEventData eventData, InterceptionResult<DbCommand> result)
    {
        if (RecordQueryInfoScope.Current != null && eventData.IsAsync)
            throw new InvalidOperationException("Cannot use Async operation when recording a command");

        return base.CommandCreating(eventData, result);
    }

    public override InterceptionResult<int> NonQueryExecuting(DbCommand cmd, CommandEventData eventData, InterceptionResult<int> result)
        => this.Executing(cmd, eventData, result);

    public override InterceptionResult<DbDataReader> ReaderExecuting(DbCommand cmd, CommandEventData eventData,
        InterceptionResult<DbDataReader> result)
    {
        this.Executing(cmd, eventData, result);
        return InterceptionResult<DbDataReader>.SuppressWithResult(new DataTable().CreateDataReader());
    }

    public override InterceptionResult<object> ScalarExecuting(DbCommand cmd, CommandEventData eventData, InterceptionResult<object> result)
        => this.Executing(cmd, eventData, result);

    private InterceptionResult<T> Executing<T>(DbCommand cmd, CommandEventData eventData, InterceptionResult<T> result)
    {
        if (RecordQueryInfoScope.Current == null)
            return result;

        var queryInfo = QueryOutputInfoHelper.AnalyzeSqlCommand(cmd);

        RecordQueryInfoScope.Current.Record(queryInfo);
        return InterceptionResult<T>.SuppressWithResult(default!);
    }
}
