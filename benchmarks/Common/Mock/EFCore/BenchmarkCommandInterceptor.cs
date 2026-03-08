using System.Data.Common;
using Microsoft.EntityFrameworkCore.Diagnostics;

namespace Common.Mock.EFCore;

public class BenchmarkCommandInterceptor : DbCommandInterceptor
{
    private readonly BenchmarkCommandExecutor _executor;

    public BenchmarkCommandInterceptor(BenchmarkCommandExecutor executor)
    {
        _executor = executor;
    }

    public override InterceptionResult<int> NonQueryExecuting(DbCommand command, CommandEventData eventData, InterceptionResult<int> result)
    {
        return InterceptionResult<int>.SuppressWithResult(_executor.ExecuteNonQuery(command));
    }

    public override ValueTask<InterceptionResult<int>> NonQueryExecutingAsync(DbCommand command, CommandEventData eventData, InterceptionResult<int> result, CancellationToken cancellationToken = default)
    {
        return new ValueTask<InterceptionResult<int>>(InterceptionResult<int>.SuppressWithResult(_executor.ExecuteNonQueryAsync(command, cancellationToken).GetAwaiter().GetResult()));
    }

    public override InterceptionResult<DbDataReader> ReaderExecuting(DbCommand command, CommandEventData eventData, InterceptionResult<DbDataReader> result)
    {
        return InterceptionResult<DbDataReader>.SuppressWithResult(_executor.ExecuteReader(command, System.Data.CommandBehavior.Default));
    }

    public override ValueTask<InterceptionResult<DbDataReader>> ReaderExecutingAsync(DbCommand command, CommandEventData eventData, InterceptionResult<DbDataReader> result, CancellationToken cancellationToken = default)
    {
        return new ValueTask<InterceptionResult<DbDataReader>>(InterceptionResult<DbDataReader>.SuppressWithResult(_executor.ExecuteReaderAsync(command, System.Data.CommandBehavior.Default, cancellationToken).GetAwaiter().GetResult()));
    }

    public override InterceptionResult<object> ScalarExecuting(DbCommand command, CommandEventData eventData, InterceptionResult<object> result)
    {
        return InterceptionResult<object>.SuppressWithResult(_executor.ExecuteScalar(command));
    }

    public override ValueTask<InterceptionResult<object>> ScalarExecutingAsync(DbCommand command, CommandEventData eventData, InterceptionResult<object> result, CancellationToken cancellationToken = default)
    {
        return new ValueTask<InterceptionResult<object>>(InterceptionResult<object>.SuppressWithResult(_executor.ExecuteScalarAsync(command, cancellationToken).GetAwaiter().GetResult()));
    }
}
