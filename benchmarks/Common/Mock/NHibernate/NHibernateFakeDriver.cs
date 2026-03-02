using System.Data;
using System.Data.Common;
using NHibernate.Driver;
using NHibernate.Engine;
using NHibernate.SqlCommand;
using NHibernate.SqlTypes;

namespace Common.Mock.NHibernate;

public partial class NHibernateFakeDriver : IDriver
{
    public static System.Type DriverClass { get; set; }

    private readonly IDriver _driverImplementation;

    public NHibernateFakeDriver()
    {
        _driverImplementation = (IDriver)global::NHibernate.Cfg.Environment.ObjectsFactory.CreateInstance(DriverClass);
    }

    DbCommand IDriver.GenerateCommand(CommandType type, SqlString sqlString, SqlType[] parameterTypes)
    {
        var cmd = _driverImplementation.GenerateCommand(type, sqlString, parameterTypes);
        return new SubstituteDbCommand(cmd);
    }

    #region Pure forwarding

    DbParameter IDriver.GenerateParameter(DbCommand command, string name, SqlType sqlType)
    {
        return _driverImplementation.GenerateParameter(command, name, sqlType);
    }

    void IDriver.Configure(IDictionary<string, string> settings)
    {
        _driverImplementation.Configure(settings);
    }

    DbConnection IDriver.CreateConnection()
    {
        return _driverImplementation.CreateConnection();
    }

    bool IDriver.SupportsMultipleOpenReaders => _driverImplementation.SupportsMultipleOpenReaders;

    void IDriver.PrepareCommand(DbCommand command)
    {
        _driverImplementation.PrepareCommand(command);
    }

    void IDriver.RemoveUnusedCommandParameters(DbCommand cmd, SqlString sqlString)
    {
        _driverImplementation.RemoveUnusedCommandParameters(cmd, sqlString);
    }

    void IDriver.ExpandQueryParameters(DbCommand cmd, SqlString sqlString, SqlType[] parameterTypes)
    {
        _driverImplementation.ExpandQueryParameters(cmd, sqlString, parameterTypes);
    }

    IResultSetsCommand IDriver.GetResultSetsCommand(ISessionImplementor session)
    {
        return _driverImplementation.GetResultSetsCommand(session);
    }

    bool IDriver.SupportsMultipleQueries => _driverImplementation.SupportsMultipleQueries;

    void IDriver.AdjustCommand(DbCommand command)
    {
        _driverImplementation.AdjustCommand(command);
    }

    bool IDriver.RequiresTimeSpanForTime => _driverImplementation.RequiresTimeSpanForTime;

    bool IDriver.SupportsSystemTransactions => _driverImplementation.SupportsSystemTransactions;

    bool IDriver.SupportsNullEnlistment => _driverImplementation.SupportsNullEnlistment;

    bool IDriver.SupportsEnlistmentWhenAutoEnlistmentIsDisabled =>
        _driverImplementation.SupportsEnlistmentWhenAutoEnlistmentIsDisabled;

    bool IDriver.HasDelayedDistributedTransactionCompletion =>
        _driverImplementation.HasDelayedDistributedTransactionCompletion;

    DateTime IDriver.MinDate => _driverImplementation.MinDate;

    #endregion

    private class SubstituteDbCommand : DbCommand
    {
        private readonly DbCommand _concreteCommand;
        private readonly BenchmarkCommandExecutor _commandExecutor;

        public SubstituteDbCommand(DbCommand concreteCommand, BenchmarkCommandExecutor? executor = null) 
        {
            _concreteCommand = concreteCommand;
            _commandExecutor = executor ?? BenchmarkCommandExecutor.Instance;
        }

        protected override DbDataReader ExecuteDbDataReader(CommandBehavior behavior)
        {
            if (RecordQueryInfoScope.Current != null)
            {
                RecordQueryInfoScope.Current.Record(QueryOutputInfoHelper.AnalyzeSqlCommand(this._concreteCommand));
                return new DataTable().CreateDataReader();
            }
            return _commandExecutor.ExecuteReader(this, behavior);
        }

        public override void Prepare()
        {
        }

        public override int ExecuteNonQuery()
        {
            if (RecordQueryInfoScope.Current != null)
                RecordQueryInfoScope.Current.Record(QueryOutputInfoHelper.AnalyzeSqlCommand(this._concreteCommand));
            return -1;
        }

        public override object ExecuteScalar()
        {
            if (RecordQueryInfoScope.Current != null)
                RecordQueryInfoScope.Current.Record(QueryOutputInfoHelper.AnalyzeSqlCommand(this._concreteCommand));
            return 1.00m;
        }

        protected override Task<DbDataReader> ExecuteDbDataReaderAsync(CommandBehavior behavior, CancellationToken cancellationToken)
        {
            if (RecordQueryInfoScope.Current != null)
            {
                RecordQueryInfoScope.Current.Record(QueryOutputInfoHelper.AnalyzeSqlCommand(this._concreteCommand));
                return Task.FromResult<DbDataReader>(new DataTable().CreateDataReader());
            }
            return _commandExecutor.ExecuteReaderAsync(this, behavior, cancellationToken);
        }

        public override Task<int> ExecuteNonQueryAsync(CancellationToken cancellationToken)
        {
            if (RecordQueryInfoScope.Current != null)
                RecordQueryInfoScope.Current.Record(QueryOutputInfoHelper.AnalyzeSqlCommand(this._concreteCommand));
            return Task.FromResult(-1);
        }

        public override Task<object?> ExecuteScalarAsync(CancellationToken cancellationToken)
        {
            if (RecordQueryInfoScope.Current != null)
                RecordQueryInfoScope.Current.Record(QueryOutputInfoHelper.AnalyzeSqlCommand(this._concreteCommand));
            return Task.FromResult<object?>(1.00m);
        }

        protected override void Dispose(bool disposing)
        {
            base.Dispose(disposing);
            if (disposing)
            {
                _concreteCommand.Dispose();
            }
        }

        #region Pure forwarding

        public override string CommandText
        {
            get => _concreteCommand.CommandText;
            set => _concreteCommand.CommandText = value;
        }

        public override int CommandTimeout
        {
            get => _concreteCommand.CommandTimeout;
            set => _concreteCommand.CommandTimeout = value;
        }

        public override CommandType CommandType
        {
            get => _concreteCommand.CommandType;
            set => _concreteCommand.CommandType = value;
        }

        public override UpdateRowSource UpdatedRowSource
        {
            get => _concreteCommand.UpdatedRowSource;
            set => _concreteCommand.UpdatedRowSource = value;
        }

        protected override DbConnection DbConnection
        {
            get => _concreteCommand.Connection;
            set => _concreteCommand.Connection = value;
        }

        protected override DbParameterCollection DbParameterCollection => _concreteCommand.Parameters;

        protected override DbTransaction DbTransaction
        {
            get => _concreteCommand.Transaction;
            set => _concreteCommand.Transaction = value;
        }

        public override bool DesignTimeVisible
        {
            get => _concreteCommand.DesignTimeVisible;
            set => _concreteCommand.DesignTimeVisible = value;
        }

        public override void Cancel()
        {
            _concreteCommand.Cancel();
        }

        protected override DbParameter CreateDbParameter()
        {
            return _concreteCommand.CreateParameter();
        }

        #endregion
    }
}
