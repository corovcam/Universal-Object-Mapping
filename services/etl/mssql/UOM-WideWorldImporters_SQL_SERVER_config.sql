/*
* Relational Migrator needs source database to allow change data capture.
* The following scripts must be executed on MS-SQL source database before starting migration to enable change data capture.
* See https://docs.microsoft.com/en-us/sql/relational-databases/track-changes/about-change-data-capture-sql-server?view=sql-server-ver16 for more details on CDC.
*
* Prerequisites for running this script:
* You are a member of the sysadmin fixed server role for the SQL Server.
* You are a db_owner of the database.
*/

/*
* Set up CDC for the database WideWorldImporters.
*/
USE WideWorldImporters
GO
IF (N'WideWorldImporters') NOT in (SELECT name FROM sys.databases WHERE is_cdc_enabled = 1)
EXEC sys.sp_cdc_enable_db;
GO



/* On SQL Server, parameters that control the behavior of the capture job agent are defined in the SQL Server table msdb.dbo.cdc_jobs.
* If you experience performance issues while running the capture job agent, adjust capture jobs settings to reduce CPU load by running the sys.sp_cdc_change_job stored procedure and supplying new values.
* See https://debezium.io/documentation/reference/stable/connectors/sqlserver.html#_sql_server_capture_job_agent_configuration_parameters for more details
*/