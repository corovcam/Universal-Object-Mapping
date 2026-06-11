import fs from "node:fs";
import { Assistant } from "./assistant";
import type { UOMGraphContext } from "@/lib/types";

/**
 * Default configuration values for the UOM Translator application, with environment variable overrides.
 * This includes settings for Ollama, OpenAI, database connection strings, Daytona API, and more.
 * Environment variables allow for secure and flexible configuration in different deployment contexts.
 */
export const DEFAULT_UOM_GRAPH_CONTEXT: UOMGraphContext = {
	ollamaHost: process.env.OLLAMA_HOST || "http://localhost:11434",
	model: process.env.MODEL || "einfra/kimi-k2.6",
	openaiApiUrl: process.env.OPENAI_API_URL || "https://llm.ai.e-infra.cz/v1",
	openaiApiKey: "",
	mssqlConnectionString: process.env.MSSQL_CONNECTION_STRING || "Server=localhost,1333;Database=WideWorldImporters;User Id=sa;Password=Testingorms123;TrustServerCertificate=True",
	mongodbUri: process.env.MONGODB_URI || "mongodb://localhost:27027",
	neo4jUri: process.env.NEO4J_URI || "neo4j://localhost:7697",
	neo4jPassword: process.env.NEO4J_PASSWORD || "password",
	daytonaTimeout: process.env.DAYTONA_TIMEOUT ? parseInt(process.env.DAYTONA_TIMEOUT) : 480,
	dbToolboxUri: process.env.DB_TOOLBOX_URI || "http://localhost:5010",
	daytonaApiUrl: process.env.DAYTONA_API_URL || "http://localhost:3000/api",
	daytonaApiKey: "",
	daytonaTarget: (process.env.DAYTONA_TARGET as "us" | "eu") || "us",
	mongodbMcpUri: process.env.MONGODB_MCP_URI || "http://localhost:3010/mcp",
};

export default function Home() {
	let efcoreToMongoInput: string | null = null;
	let efcoreToNeo4jInput: string | null = null;
	let dapperToMongoInput: string | null = null;
	let nhibernateToMongoInput: string | null = null;

	const cwd = process.cwd();
	try {
		// TODO: use getStaticProps
		efcoreToMongoInput = fs.readFileSync(
			`${cwd}/app/data/input-efcore-mongodb.txt`,
			"utf-8",
		);
		efcoreToNeo4jInput = fs.readFileSync(
			`${cwd}/app/data/input-efcore-neo4j.txt`,
			"utf-8",
		);
		dapperToMongoInput = fs.readFileSync(
			`${cwd}/app/data/input-dapper-mongodb.txt`,
			"utf-8",
		);
		nhibernateToMongoInput = fs.readFileSync(
			`${cwd}/app/data/input-nhibernate-mongodb.txt`,
			"utf-8",
		);
	} catch (error) {
		console.error(error);
	}

	const inputSuggestions = [];

	if (efcoreToMongoInput) {
		inputSuggestions.push({
			title: "EF Core to Spring Data MongoDB",
			label: "Sample translation from EF Core 10 to Spring Data MongoDB 5.0",
			prompt: efcoreToMongoInput,
		});
	}
	if (efcoreToNeo4jInput) {
		inputSuggestions.push({
			title: "EF Core to Spring Data Neo4j",
			label: "Sample translation from EF Core 10 to Spring Data Neo4j 8.0",
			prompt: efcoreToNeo4jInput,
		});
	}
	if (dapperToMongoInput) {
		inputSuggestions.push({
			title: "Dapper to Spring Data MongoDB",
			label: "Sample translation from Dapper to Spring Data MongoDB",
			prompt: dapperToMongoInput,
		});
	}
	if (nhibernateToMongoInput) {
		inputSuggestions.push({
			title: "NHibernate to Spring Data MongoDB",
			label: "Sample translation from NHibernate to Spring Data MongoDB",
			prompt: nhibernateToMongoInput,
		});
	}

	return (
		<main className="h-dvh w-screen overflow-hidden">
			<Assistant inputData={{ defaultUomGraphContext: DEFAULT_UOM_GRAPH_CONTEXT, inputSuggestions }} />
		</main>
	);
}
