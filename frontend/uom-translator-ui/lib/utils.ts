import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import {
	type FrameworkInfoType,
	FrameworkType,
	LanguageType,
	SandboxType,
} from "./types";

/**
 * Utility to merge Tailwind CSS classes dynamically without style conflicts.
 * Combines `clsx` for conditional class joining and `tailwind-merge` to handle overrides.
 *
 * @param {...ClassValue[]} inputs - List of class names, arrays, or conditional objects.
 * @returns {string} The resolved and merged class name string.
 */
export function cn(...inputs: ClassValue[]) {
	return twMerge(clsx(inputs));
}

/**
 * Metadata registry mapping each FrameworkType to its execution properties:
 * - Human-readable name
 * - Backend runtime environment (LanguageType)
 * - Required Daytona sandbox container image (SandboxType)
 * - Directionality flag (whether it acts as migration source or target)
 */
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
	},
};

/**
 * Helper function to retrieve a FrameworkType enum key by matching its human-readable name.
 * Useful for parsing responses from LangGraph agent state outputs.
 *
 * @param {string} name - The human-readable name of the framework (e.g. "Java Spring Data Neo4j").
 * @returns {FrameworkType | null} The corresponding FrameworkType enum value, or null if no match is found.
 */
export const getFrameworkTypeByName: (name: string) => FrameworkType | null = (
	name: string,
) => {
	return (
		(Object.entries(FrameworkInfo).find(
			([_, info]) => info.name === name,
		)?.[0] as FrameworkType) || null
	);
};
