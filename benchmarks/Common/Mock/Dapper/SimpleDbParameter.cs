using System.Data;
using System.Data.Common;

namespace Common.Mock.Dapper;

public partial class FakeDbCommand
{
	// Minimal stubs required by DbCommand's abstract contract.
	// DbCommand.CreateDbParameter() must return a concrete DbParameter,
	// and DbCommand.DbParameterCollection must return a concrete collection.
	// No built-in concrete types exist in System.Data.Common.

	private sealed class SimpleDbParameter : DbParameter
	{
		public override DbType DbType { get; set; }
		public override ParameterDirection Direction { get; set; }
		public override bool IsNullable { get; set; }
		public override string ParameterName { get; set; } = "";
		public override int Size { get; set; }
		public override string SourceColumn { get; set; } = "";
		public override bool SourceColumnNullMapping { get; set; }
		public override object Value { get; set; }
		public override void ResetDbType() { }
	}
}
