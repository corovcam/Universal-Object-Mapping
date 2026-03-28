import type { Framework, FrameworkType } from "./types";

export const FRAMEWORKS: Framework[] = [
  {
    id: "ms_sql_native",
    name: "MS SQL Native",
    language: "sql",
    description: "Native Microsoft SQL Server queries",
    color: "#CC2927",
  },
  {
    id: "csharp_efcore_linq",
    name: "C# EF Core LINQ",
    language: "csharp",
    description: "Entity Framework Core with LINQ queries",
    color: "#512BD4",
  },
  {
    id: "csharp_dapper",
    name: "C# Dapper",
    language: "csharp",
    description: "Micro ORM for .NET with raw SQL",
    color: "#68217A",
  },
  {
    id: "csharp_nhibernate_hql",
    name: "C# NHibernate HQL",
    language: "csharp",
    description: "NHibernate with Hibernate Query Language",
    color: "#59666C",
  },
  {
    id: "java_spring_data_jpa",
    name: "Java Spring Data JPA",
    language: "java",
    description: "Spring Data JPA repositories",
    color: "#6DB33F",
  },
  {
    id: "java_spring_data_mongodb",
    name: "Java Spring Data MongoDB",
    language: "java",
    description: "Spring Data MongoDB repositories",
    color: "#47A248",
  },
  {
    id: "java_spring_data_neo4j",
    name: "Java Spring Data Neo4j",
    language: "java",
    description: "Spring Data Neo4j for graph databases",
    color: "#008CC1",
  },
];

export function getFramework(id: FrameworkType): Framework | undefined {
  return FRAMEWORKS.find((f) => f.id === id);
}

export function getLanguageFromFramework(
  frameworkId: FrameworkType
): "csharp" | "java" | "sql" {
  const framework = getFramework(frameworkId);
  return framework?.language ?? "sql";
}

export function getShikiLanguage(
  frameworkId: FrameworkType
): "csharp" | "java" | "sql" {
  return getLanguageFromFramework(frameworkId);
}
