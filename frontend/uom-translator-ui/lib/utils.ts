import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { FrameworkInfoType, FrameworkType, LanguageType, SandboxType } from "./types";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const FrameworkInfo: Record<FrameworkType, FrameworkInfoType> = {
  [FrameworkType.DOTNET_EFCORE]: {
    name: ".NET Entity Framework Core",
    language: LanguageType.DOTNET,
    sandbox: SandboxType.DOTNET_10_SANDBOX,
    is_source: true,
    is_target: false,
  },
  [FrameworkType.DOTNET_NHIBERNATE]: {
    name: ".NET NHibernate",
    language: LanguageType.DOTNET,
    sandbox: SandboxType.DOTNET_10_SANDBOX,
    is_source: true,
    is_target: false,
  },
  [FrameworkType.DOTNET_DAPPER]: {
    name: ".NET Dapper",
    language: LanguageType.DOTNET,
    sandbox: SandboxType.DOTNET_10_SANDBOX,
    is_source: true,
    is_target: false,
  },
  [FrameworkType.JAVA_SPRING_DATA_MONGODB]: {
    name: "Java Spring Data MongoDB",
    language: LanguageType.JAVA,
    sandbox: SandboxType.JAVA_25_SANDBOX,
    is_source: false,
    is_target: true,
  },
  [FrameworkType.JAVA_SPRING_DATA_NEO4J]: {
    name: "Java Spring Data Neo4j",
    language: LanguageType.JAVA,
    sandbox: SandboxType.JAVA_25_SANDBOX,
    is_source: false,
    is_target: true,
  }
}

export const getFrameworkTypeByName: (name: string) => FrameworkType | null = (name: string) => {
  return Object.entries(FrameworkInfo).find(([_, info]) => info.name == name)?.[0] as FrameworkType || null;
}
