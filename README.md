# Universal Object Mapping

[![ORMConvertor tests](https://github.com/corovcam/Universal-Object-Mapping/actions/workflows/ormconvertor-tests.yml/badge.svg)](https://github.com/corovcam/Universal-Object-Mapping/actions/workflows/ormconvertor-tests.yml)

## Repository structure

The repository is structured into several directories. The `diagrams` directory holds diagrams created using [draw.io](https://www.drawio.com/). Experimental comparisons, including unit tests and benchmarks, are located in the `benchmarks` directory. The `ORMConvertor` folder includes a prototype tool for translating between different .NET ORM frameworks.

## ORMConvertor

The translation and advisor tool are currently hosted at [http://116.203.208.55/orm/home](http://116.203.208.55/orm/home).

## Frameworks and ORM/OGM/ODMs compared

The compared ORMs are:

- [Dapper](https://github.com/DapperLib/Dapper)
- [NHibernate](https://github.com/nhibernate)
- [Entity Framework Core](https://github.com/dotnet/efcore)

The compared OGMs are:

- [Spring Data Neo4j](https://github.com/spring-projects/spring-data-neo4j)

The compared ODMs are:

- [Spring Data MongoDB](https://github.com/spring-projects/spring-data-mongodb)

## Acknowledgements

Part of the `ORMConvertor` and the `benchmarks` source code, including some workflows and diagrams, were developed by Milan Abrahám as part of his Master thesis titled _Framework-Agnostic Query Adaptation: Ensuring SQL Compatibility Across .NET Database Frameworks_. The thesis is available at http://hdl.handle.net/20.500.11956/203083, and the source code is available at https://github.com/milan252525/orm-convertor.