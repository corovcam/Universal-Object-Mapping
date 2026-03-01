using System;
using System.Data.Common;
using System.Globalization;
using System.Text;

namespace Common.Mock.Query;

public class SqliteQueryStringFactory : IRelationalQueryStringFactory
{
    public SqliteQueryStringFactory()
    {
    }

    public virtual string Create(DbCommand command)
    {
        if (command.Parameters.Count == 0)
        {
            return command.CommandText;
        }

        var builder = new StringBuilder();
        foreach (DbParameter parameter in command.Parameters)
        {
            var value = parameter.Value;
            builder
                .Append("-- .param set ")
                .Append(parameter.ParameterName)
                .Append(' ')
                .AppendLine(
                    value == null || value == DBNull.Value
                        ? "NULL"
                        : FormatValue(value));
        }

        return builder
            .AppendLine()
            .Append(command.CommandText).ToString();
    }

    private static string FormatValue(object value)
    {
        return value switch
        {
            string s => $"'{s.Replace("'", "''")}'",
            char c => $"'{c.ToString().Replace("'", "''")}'",
            bool b => b ? "1" : "0",
            DateTime dt => $"'{dt:yyyy-MM-dd HH:mm:ss.FFFFFFF}'",
            DateTimeOffset dto => $"'{dto:yyyy-MM-dd HH:mm:ss.FFFFFFFzzz}'",
            DateOnly d => $"'{d:yyyy-MM-dd}'",
            TimeOnly t => $"'{t:HH:mm:ss.FFFFFFF}'",
            TimeSpan ts => $"'{ts}'",
            Guid g => $"'{g}'",
            byte[] bytes => "X'" + BitConverter.ToString(bytes).Replace("-", "") + "'",
            Enum e => Convert.ChangeType(e, Enum.GetUnderlyingType(e.GetType())).ToString(),
            IFormattable formattable => formattable.ToString(null, CultureInfo.InvariantCulture),
            _ => value.ToString() ?? "NULL"
        };
    }
}
