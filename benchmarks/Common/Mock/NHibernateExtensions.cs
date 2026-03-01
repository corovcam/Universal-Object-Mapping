using System;
using System.Collections.Generic;
using System.Data.Common;
using NHibernate;
using NHibernate.Driver;
using NHibernate.Engine;
using NHibernate.Multi;
using static Microsoft.EntityFrameworkCore.DbLoggerCategory;

namespace Common.Mock;

public static class NHibernateExtensions
{
    // Source - https://stackoverflow.com/a/55517893
    // Posted by Roman Artiukhin, modified by community. See post 'Timeline' for change history
    // Retrieved 2026-02-23, License - CC BY-SA 4.0

    //For LINQ
    public static IEnumerable<DbCommand> GetDbCommands<T>(this IQueryable<T> query, ISession s)
    {
        return GetDbCommands(LinqBatchItem.Create(query), s);
    }

    //For HQL
    public static IEnumerable<DbCommand> GetDbCommands(this IQuery query, ISession s)
    {
        return GetDbCommands(new QueryBatchItem<object>(query), s);
    }

    //For QueryOver
    public static IEnumerable<DbCommand> GetDbCommands(this IQueryOver query, ISession s)
    {
        return GetDbCommands(query.RootCriteria, s);
    }

    //For Criteria (needs to be called for root criteria)
    public static IEnumerable<DbCommand> GetDbCommands(this ICriteria rootCriteria, ISession s)
    {
        return GetDbCommands(new CriteriaBatchItem<object>(rootCriteria), s);
    }

    //Adapted from Loader.PrepareQueryCommand
    private static IEnumerable<DbCommand> GetDbCommands(IQueryBatchItem item, ISession s)
    {
        var si = s.GetSessionImplementation();
        item.Init(si);
        var commands = item.GetCommands();
        foreach (var sqlCommand in commands)
        {
            var sqlString = sqlCommand.Query;
            sqlCommand.ResetParametersIndexesForTheCommand(0);
            var command = si.Batcher.PrepareQueryCommand(System.Data.CommandType.Text, sqlString, sqlCommand.ParameterTypes);
            RowSelection selection = sqlCommand.QueryParameters.RowSelection;
            if (selection != null && selection.Timeout != RowSelection.NoValue)
            {
                command.CommandTimeout = selection.Timeout;
            }

            sqlCommand.Bind(command, si);

            IDriver driver = si.Factory.ConnectionProvider.Driver;
            driver.RemoveUnusedCommandParameters(command, sqlString);
            driver.ExpandQueryParameters(command, sqlString, sqlCommand.ParameterTypes);

            yield return command;
        }
    }
}
