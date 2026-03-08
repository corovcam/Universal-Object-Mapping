using System.Data.Common;

namespace Common.Mock.Query;

public interface IRelationalQueryStringFactory
{
    string Create(DbCommand command);
}
