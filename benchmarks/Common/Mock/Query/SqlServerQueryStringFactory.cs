using System;
using System.Data;
using System.Data.Common;
using System.Data.SqlTypes;
using System.Globalization;
using System.Text;
using Microsoft.Data.SqlClient;

namespace Common.Mock.Query;

public class SqlServerQueryStringFactory : IRelationalQueryStringFactory
{
    public SqlServerQueryStringFactory()
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
            var typeName = TypeNameBuilder.CreateTypeName(parameter);

            builder
                .Append("DECLARE ")
                .Append(parameter.ParameterName)
                .Append(' ')
                .Append(typeName)
                .Append(" = ");

            if (parameter.Value == DBNull.Value || parameter.Value is null)
            {
                builder.Append("NULL");
            }
            else
            {
                builder.Append(FormatParameterValue(parameter.Value));
            }

            builder.AppendLine(";");
        }

        return builder
            .AppendLine()
            .Append(command.CommandText).ToString();
    }

    private static string FormatParameterValue(object value)
    {
        if (value is SqlBytes sqlBytes)
        {
            return "0x" + BitConverter.ToString(sqlBytes.Value).Replace("-", "");
        }

        return FormatValue(value);
    }

    public static string FormatValue(object value)
    {
        if (value == null || value == DBNull.Value) return "NULL";

        return value switch
        {
            string s => $"N'{s.Replace("'", "''")}'",
            char c => $"N'{c.ToString().Replace("'", "''")}'",
            bool b => b ? "1" : "0",
            DateTime dt => $"'{dt:yyyy-MM-ddTHH:mm:ss.fff}'",
            DateTimeOffset dto => $"'{dto:yyyy-MM-ddTHH:mm:ss.fffzzz}'",
            DateOnly d => $"'{d:yyyy-MM-dd}'",
            TimeOnly t => $"'{t:HH:mm:ss.fff}'",
            TimeSpan ts => $"'{ts}'",
            Guid g => $"'{g}'",
            byte[] bytes => "0x" + BitConverter.ToString(bytes).Replace("-", ""),
            Enum e => Convert.ChangeType(e, Enum.GetUnderlyingType(e.GetType())).ToString(),
            IFormattable formattable => formattable.ToString(null, CultureInfo.InvariantCulture),
            _ => value.ToString() ?? "NULL"
        };
    }
}

internal static class TypeNameBuilder
{
    private static StringBuilder AppendSize(this StringBuilder builder, DbParameter parameter)
    {
        if (parameter.Size > 0)
        {
            builder
                .Append('(')
                .Append(parameter.Size.ToString(CultureInfo.InvariantCulture))
                .Append(')');
        }

        return builder;
    }

    private static StringBuilder AppendSizeOrMax(this StringBuilder builder, DbParameter parameter)
    {
        if (parameter.Size > 0)
        {
            builder.AppendSize(parameter);
        }
        else if (parameter.Size == -1)
        {
            builder.Append("(max)");
        }

        return builder;
    }

    private static StringBuilder AppendPrecision(this StringBuilder builder, DbParameter parameter)
    {
        if (parameter.Precision > 0)
        {
            builder
                .Append('(')
                .Append(parameter.Precision.ToString(CultureInfo.InvariantCulture))
                .Append(')');
        }

        return builder;
    }

    private static StringBuilder AppendScale(this StringBuilder builder, DbParameter parameter)
    {
        if (parameter.Scale > 0)
        {
            builder
                .Append('(')
                .Append(parameter.Scale.ToString(CultureInfo.InvariantCulture))
                .Append(')');
        }

        return builder;
    }

    private static StringBuilder AppendPrecisionAndScale(this StringBuilder builder, DbParameter parameter)
    {
        if (parameter is { Precision: > 0, Scale: > 0 })
        {
            return builder
                .Append('(')
                .Append(parameter.Precision.ToString(CultureInfo.InvariantCulture))
                .Append(',')
                .Append(parameter.Scale.ToString(CultureInfo.InvariantCulture))
                .Append(')');
        }

        return builder.AppendPrecision(parameter);
    }

    public static string CreateTypeName(DbParameter parameter)
    {
        if (parameter is SqlParameter sqlParameter)
        {
            var builder = new StringBuilder();
            return (sqlParameter.SqlDbType switch
            {
                SqlDbType.BigInt => builder.Append("bigint"),
                SqlDbType.Binary => builder.Append("binary").AppendSize(parameter),
                SqlDbType.Bit => builder.Append("bit"),
                SqlDbType.Char => builder.Append("char").AppendSize(parameter),
                SqlDbType.Date => builder.Append("date"),
                SqlDbType.DateTime => builder.Append("datetime"),
                SqlDbType.DateTime2 => builder.Append("datetime2").AppendPrecision(parameter),
                SqlDbType.DateTimeOffset => builder.Append("datetimeoffset").AppendPrecision(parameter),
                SqlDbType.Decimal => builder.Append("decimal").AppendPrecisionAndScale(parameter),
                SqlDbType.Float => builder.Append("float").AppendSize(parameter),
                SqlDbType.Image => builder.Append("image"),
                SqlDbType.Int => builder.Append("int"),
                SqlDbType.Money => builder.Append("money"),
                SqlDbType.NChar => builder.Append("nchar").AppendSize(parameter),
                SqlDbType.NText => builder.Append("ntext"),
                SqlDbType.NVarChar => builder.Append("nvarchar").AppendSizeOrMax(parameter),
                SqlDbType.Real => builder.Append("real"),
                SqlDbType.SmallDateTime => builder.Append("smalldatetime"),
                SqlDbType.SmallInt => builder.Append("smallint"),
                SqlDbType.SmallMoney => builder.Append("smallmoney"),
                SqlDbType.Structured => builder.Append("structured"),
                SqlDbType.Text => builder.Append("text"),
                SqlDbType.Time => builder.Append("time").AppendScale(parameter),
                SqlDbType.Timestamp => builder.Append("rowversion"),
                SqlDbType.TinyInt => builder.Append("tinyint"),
                SqlDbType.Udt => builder.Append(sqlParameter.UdtTypeName),
                SqlDbType.UniqueIdentifier => builder.Append("uniqueIdentifier"),
                SqlDbType.VarBinary => builder.Append("varbinary").AppendSizeOrMax(parameter),
                SqlDbType.VarChar => builder.Append("varchar").AppendSizeOrMax(parameter),
                SqlDbType.Variant => builder.Append("sql_variant"),
                SqlDbType.Xml => builder.Append("xml"),
                _ => builder.Append("sql_variant")
            }).ToString();
        }
        else
        {
            var builder = new StringBuilder();
            return (parameter.DbType switch
            {
                DbType.Int64 => builder.Append("bigint"),
                DbType.Binary => builder.Append("varbinary").AppendSizeOrMax(parameter),
                DbType.Boolean => builder.Append("bit"),
                DbType.AnsiStringFixedLength => builder.Append("char").AppendSize(parameter),
                DbType.Date => builder.Append("date"),
                DbType.DateTime => builder.Append("datetime"),
                DbType.DateTime2 => builder.Append("datetime2").AppendPrecision(parameter),
                DbType.DateTimeOffset => builder.Append("datetimeoffset").AppendPrecision(parameter),
                DbType.Decimal => builder.Append("decimal").AppendPrecisionAndScale(parameter),
                DbType.Double => builder.Append("float"),
                DbType.Int32 => builder.Append("int"),
                DbType.Currency => builder.Append("money"),
                DbType.StringFixedLength => builder.Append("nchar").AppendSize(parameter),
                DbType.String => builder.Append("nvarchar").AppendSizeOrMax(parameter),
                DbType.Single => builder.Append("real"),
                DbType.Int16 => builder.Append("smallint"),
                DbType.Time => builder.Append("time").AppendScale(parameter),
                DbType.Byte => builder.Append("tinyint"),
                DbType.Guid => builder.Append("uniqueidentifier"),
                DbType.AnsiString => builder.Append("varchar").AppendSizeOrMax(parameter),
                DbType.Xml => builder.Append("xml"),
                _ => builder.Append("sql_variant")
            }).ToString();
        }
    }
}
