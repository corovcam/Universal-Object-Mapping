import fs from "fs";
import { Assistant } from "./assistant";

export default function Home() {
	let efcoreToMongoInput: string | null = null;
	let efcoreToNeo4jInput: string | null = null;
	let dapperToMongoInput: string | null = null;
	let nhibernateToMongoInput: string | null = null;

	const cwd = process.cwd();
	try {
		// TODO: use getStaticProps
		efcoreToMongoInput = fs.readFileSync(
			cwd + "/app/data/input-efcore-mongodb.txt",
			"utf-8",
		);
		efcoreToNeo4jInput = fs.readFileSync(
			cwd + "/app/data/input-efcore-neo4j.txt",
			"utf-8",
		);
		dapperToMongoInput = fs.readFileSync(
			cwd + "/app/data/input-dapper-mongodb.txt",
			"utf-8",
		);
		nhibernateToMongoInput = fs.readFileSync(
			cwd + "/app/data/input-nhibernate-mongodb.txt",
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
			<Assistant inputData={{ inputSuggestions }} />
		</main>
	);
}
