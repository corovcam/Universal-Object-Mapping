#!/bin/bash

snippets_dir="src/context/snippets"

# in orchestrator directory

cp -f ../java-services/mongo_sandbox/src/main/java/uom/services/MongoQueryEntrypoint.java $snippets_dir
cp -f ../java-services/mongo_sandbox/src/main/java/uom/services/MongoSchemaValidationEntrypoint.java $snippets_dir

cp -f ../java-services/neo4j_sandbox/src/main/java/uom/services/Neo4jQueryEntrypoint.java $snippets_dir
cp -f ../java-services/neo4j_sandbox/src/main/java/uom/services/Neo4jSchemaValidationEntrypoint.java $snippets_dir

cp -f ../dotnet-service/efcore-sandbox/EFCoreQueryEntrypoint.cs $snippets_dir
cp -f ../dotnet-service/efcore-sandbox/EFCoreSchemaValidationEntrypoint.cs $snippets_dir

cp -f ../dotnet-service/nhibernate-sandbox/NHibernateQueryEntrypoint.cs $snippets_dir
cp -f ../dotnet-service/nhibernate-sandbox/NHibernateSchemaValidationEntrypoint.cs $snippets_dir

cp -f ../dotnet-service/dapper-sandbox/DapperQueryEntrypoint.cs $snippets_dir
cp -f ../dotnet-service/dapper-sandbox/DapperSchemaValidationEntrypoint.cs $snippets_dir
