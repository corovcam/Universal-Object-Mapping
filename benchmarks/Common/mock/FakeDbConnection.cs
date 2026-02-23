using Microsoft.Data.SqlClient;
using System;
using System.Data;
using System.Data.Common;
using System.Threading;
using System.Threading.Tasks;

namespace Common.mock;

/// <summary>
/// A fake DbConnection that uses BenchmarkCommandExecutor to return mock data.
/// Can be used with any ADO.NET-based ORM (EF Core, Dapper, NHibernate).
/// Configure the executor with query plan info before each benchmark iteration.
/// </summary>
public class FakeDbConnection : DbConnection
{
	private readonly BenchmarkCommandExecutor _commandExecutor;
	private ConnectionState _state;

	public SqlConnection SqlConnection { get; init; }

	public FakeDbConnection(string connectionString, BenchmarkCommandExecutor? commandExecutor = null)
	{
		ConnectionString = connectionString;
		SqlConnection = new SqlConnection(connectionString);
		_commandExecutor = commandExecutor ?? new BenchmarkCommandExecutor();
		_state = ConnectionState.Closed;
	}

	/// <summary>
	/// Gets the command executor for configuring mock data before benchmark iterations.
	/// </summary>
	public BenchmarkCommandExecutor CommandExecutor => _commandExecutor;

	public override ConnectionState State => _state;

	public override string ConnectionString { get; set; }

	public override string Database { get; } = "Fake Database";

	public override string DataSource { get; } = "Fake DataSource";

	public override string ServerVersion => "16.0.0";

	public override void ChangeDatabase(string databaseName) { }

	public override void Open() {
		SqlConnection.Open();
		_state = ConnectionState.Open;
	}

	public override Task OpenAsync(CancellationToken cancellationToken)
	{
		var task = SqlConnection.OpenAsync(cancellationToken);
		_state = ConnectionState.Open;
		return task;
	}

	public override void Close() {
		SqlConnection.Close();
		_state = ConnectionState.Closed;
	}

	protected override DbCommand CreateDbCommand()
		=> new FakeDbCommand(this, _commandExecutor);

	protected override DbTransaction BeginDbTransaction(IsolationLevel isolationLevel)
		=> throw new NotSupportedException("FakeDbConnection does not support transactions.");

	protected override void Dispose(bool disposing)
	{
		if (disposing)
		{
			_state = ConnectionState.Closed;
		}
		SqlConnection.Dispose();
		base.Dispose(disposing);
	}
}
