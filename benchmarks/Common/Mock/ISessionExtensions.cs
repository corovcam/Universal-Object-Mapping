using NHibernate;
using System;
using System.Collections.Generic;

namespace Common.Mock;

public static class ISessionExtensions
{
    public static IReadOnlyCollection<string> RecordSqlQueryStrings<TResult>(this ISession session, params Func<ISession, TResult>[] getResults)
    {
        using (RecordSqlQueryStringsScope.StartNew())
        {
            foreach (var getResult in getResults)
            {
                try
                {
                    getResult(session);
                }
                catch (Exception exception)
                {
                    Console.WriteLine(exception);
                }
            }
            return RecordSqlQueryStringsScope.Current.RecordedSqlQueries;
        }
    }
}
