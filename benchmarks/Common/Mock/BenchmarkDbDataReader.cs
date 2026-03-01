using System;
using System.Collections;
using System.Collections.Generic;
using System.Data;
using System.Data.Common;

namespace Common.Mock;

public class BenchmarkDbDataReader : DbDataReader
{
    private readonly IReadOnlyList<QueryOutputInfoHelper.ColumnInfo> _columns;
    private readonly int _rowCount;
    private readonly bool _useUniqueColumnNames;
    private int _currentRow = -1;
    private readonly object[] _rowValues;
    private readonly string[] _columnNames;

    public BenchmarkDbDataReader(IReadOnlyList<QueryOutputInfoHelper.ColumnInfo> columns, int rowCount, bool useUniqueColumnNames = false)
    {
        _columns = columns;
        _rowCount = rowCount;
        _useUniqueColumnNames = useUniqueColumnNames;

        _rowValues = new object[_columns.Count];
        _columnNames = new string[_columns.Count];

        for (int i = 0; i < _columns.Count; i++)
        {
            var col = _columns[i];
            _rowValues[i] = QueryOutputInfoHelper.GetDefaultValue(col.ClrType) ?? DBNull.Value;
            _columnNames[i] = _useUniqueColumnNames ? $"{col.Ordinal}__{col.Name}" : col.Name;
        }
    }

    public static BenchmarkDbDataReader CreateScalar(object value)
    {
        var cols = new List<QueryOutputInfoHelper.ColumnInfo>
        {
            new QueryOutputInfoHelper.ColumnInfo { Name = "Value", ClrType = value?.GetType() ?? typeof(object) }
        };
        var reader = new BenchmarkDbDataReader(cols, 1);
        reader._rowValues[0] = value ?? DBNull.Value;
        return reader;
    }

    public override bool Read()
    {
        _currentRow++;
        return _currentRow < _rowCount;
    }

    public override bool NextResult() => false;

    public override bool HasRows => _rowCount > 0;
    
    public override bool IsClosed => false;

    public override int Depth => 0;

    public override int FieldCount => _columns.Count;

    public override int RecordsAffected => -1;

    public override object this[string name] => GetValue(GetOrdinal(name));

    public override object this[int ordinal] => GetValue(ordinal);

    public override bool GetBoolean(int ordinal) => (bool)GetValue(ordinal);

    public override byte GetByte(int ordinal) => (byte)GetValue(ordinal);

    public override long GetBytes(int ordinal, long dataOffset, byte[] buffer, int bufferOffset, int length) => 0;

    public override char GetChar(int ordinal) => (char)GetValue(ordinal);

    public override long GetChars(int ordinal, long dataOffset, char[] buffer, int bufferOffset, int length) => 0;

    public override string GetDataTypeName(int ordinal) => _columns[ordinal].ClrType.Name;

    public override DateTime GetDateTime(int ordinal) => (DateTime)GetValue(ordinal);

    public override decimal GetDecimal(int ordinal) => (decimal)GetValue(ordinal);

    public override double GetDouble(int ordinal) => (double)GetValue(ordinal);

    public override Type GetFieldType(int ordinal) => _columns[ordinal].ClrType;

    public override float GetFloat(int ordinal) => (float)GetValue(ordinal);

    public override Guid GetGuid(int ordinal) => (Guid)GetValue(ordinal);

    public override short GetInt16(int ordinal) => (short)GetValue(ordinal);

    public override int GetInt32(int ordinal) => (int)GetValue(ordinal);

    public override long GetInt64(int ordinal) => (long)GetValue(ordinal);

    public override string GetName(int ordinal) => _columnNames[ordinal];

    public override int GetOrdinal(string name)
    {
        for (int i = 0; i < _columnNames.Length; i++)
        {
            if (string.Equals(_columnNames[i], name, StringComparison.OrdinalIgnoreCase))
                return i;
        }
        return -1;
    }

    public override string GetString(int ordinal) => (string)GetValue(ordinal);

    public override object GetValue(int ordinal) => _rowValues[ordinal];

    public override int GetValues(object[] values)
    {
        int count = Math.Min(values.Length, _rowValues.Length);
        Array.Copy(_rowValues, values, count);
        return count;
    }

    public override bool IsDBNull(int ordinal) => _rowValues[ordinal] == DBNull.Value;

    public override IEnumerator GetEnumerator() => new DbEnumerator(this, false);
}
