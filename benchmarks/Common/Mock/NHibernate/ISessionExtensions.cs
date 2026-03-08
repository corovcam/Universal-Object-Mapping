using NHibernate;

namespace Common.Mock.NHibernate;

public static class ISessionExtensions
{
    public static IReadOnlyCollection<QueryOutputInfoHelper.QueryInfo> RecordQueryInfos<TResult>(this ISession session, params Func<ISession, TResult>[] getResults)
    {
        using (RecordQueryInfoScope.StartNew())
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
            return RecordQueryInfoScope.Current?.RecordedQueryInfos ?? Array.Empty<QueryOutputInfoHelper.QueryInfo>();
        }
    }
}
