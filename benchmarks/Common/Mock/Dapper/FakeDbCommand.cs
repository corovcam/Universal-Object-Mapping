using System.Data;
using System.Data.Common;
using Microsoft.Data.SqlClient;

namespace Common.Mock.Dapper;

public partial class FakeDbCommand : DbCommand
{
	private readonly BenchmarkCommandExecutor _commandExecutor;

	public FakeDbCommand()
	{
	}

	public FakeDbCommand(
		FakeDbConnection connection,
		BenchmarkCommandExecutor commandExecutor)
	{
		DbConnection = connection;
		_commandExecutor = commandExecutor;
	}

	protected override DbConnection DbConnection { get; set; }

	protected override DbTransaction DbTransaction { get; set; }

	public override void Cancel() { }

	public override string CommandText { get; set; }

	public override int CommandTimeout { get; set; } = 30;

	public override CommandType CommandType { get; set; }

	protected override DbParameter CreateDbParameter()
		=> new SqlParameter();

	protected override DbParameterCollection DbParameterCollection { get; }
		= new SimpleDbParameterCollection();

	public override void Prepare() { }

	public override int ExecuteNonQuery()
		=> _commandExecutor.ExecuteNonQuery(this);

	public override object ExecuteScalar()
		=> _commandExecutor.ExecuteScalar(this);

    protected override DbDataReader ExecuteDbDataReader(CommandBehavior behavior)
		=> _commandExecutor.ExecuteReader(this, behavior);

	public override Task<int> ExecuteNonQueryAsync(CancellationToken cancellationToken)
		=> _commandExecutor.ExecuteNonQueryAsync(this, cancellationToken);

	public override Task<object> ExecuteScalarAsync(CancellationToken cancellationToken)
		=> _commandExecutor.ExecuteScalarAsync(this, cancellationToken);

	protected override Task<DbDataReader> ExecuteDbDataReaderAsync(CommandBehavior behavior, CancellationToken cancellationToken)
		=> _commandExecutor.ExecuteReaderAsync(this, behavior, cancellationToken);

	public override bool DesignTimeVisible
	{
		get => false;
		set { }
	}

	public override UpdateRowSource UpdatedRowSource
	{
		get => UpdateRowSource.None;
		set { }
	}
}
