using System.Data.Common;
using System.Collections.Generic;

namespace Common.Mock;

public class RecordQueryInfoScope : AmbientScopeBase<RecordQueryInfoScope>
{
    private List<QueryOutputInfoHelper.QueryInfo> _recordedQueryInfos = new();

    public IReadOnlyCollection<QueryOutputInfoHelper.QueryInfo> RecordedQueryInfos => _recordedQueryInfos.AsReadOnly();

    public static RecordQueryInfoScope StartNew()
    {
        return StartNew(new RecordQueryInfoScope());
    }

    private RecordQueryInfoScope()
    {
    }

    public void Record(QueryOutputInfoHelper.QueryInfo queryInfo)
    {
        this._recordedQueryInfos.Add(queryInfo);
    }
}
