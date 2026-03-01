using System.Data.Common;
using System.Text;

namespace Common.Mock.Query;

public class RelationalQueryStringFactory : IRelationalQueryStringFactory
{
    public virtual string Create(DbCommand command)
    {
        if (command.Parameters.Count == 0)
        {
            return command.CommandText;
        }

        var builder = new StringBuilder();
        foreach (DbParameter parameter in command.Parameters)
        {
            builder.Append("-- ").Append(parameter.ParameterName).Append(" = ").AppendLine(parameter.Value?.ToString() ?? "NULL");
        }

        return builder.Append(command.CommandText).ToString();
    }
}
