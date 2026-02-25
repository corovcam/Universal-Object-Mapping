using System.Data.Common;

namespace Common.Mock;

//An ambient scope similar to TransactionScope
//The base class is not provided but there are a number of implementations, which usually leverage AsyncLocal<T>
public class RecordSqlQueryStringsScope : AmbientScopeBase<RecordSqlQueryStringsScope>
{
    private List<string> _recordedSqlQueries = new();

    public IReadOnlyCollection<string> RecordedSqlQueries => _recordedSqlQueries.AsReadOnly();

    public static RecordSqlQueryStringsScope StartNew()
    {
        return StartNew(new RecordSqlQueryStringsScope());
    }

    private RecordSqlQueryStringsScope()
    {
    }

    public void Record(string sqlQuery)
    {
        this._recordedSqlQueries.Add(sqlQuery);
    }
}
