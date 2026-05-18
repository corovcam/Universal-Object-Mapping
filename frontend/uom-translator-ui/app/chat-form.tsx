"use client";

import { useAui, useAuiState } from "@assistant-ui/react";
import { useState } from "react";
import { Button } from "@/components/ui/button";

export function ChatForm() {
	const api = useAui();
	const isRunning = useAuiState((s) => s.thread.isRunning);

	const [sourceFramework, setSourceFramework] = useState(
		".NET Entity Framework Core",
	);
	const [targetFramework, setTargetFramework] = useState(
		"Java Spring Data MongoDB",
	);
	const [translationType, setTranslationType] = useState("schema");
	const [schemaCode, setSchemaCode] = useState("");
	const [queryCode, setQueryCode] = useState("");

	const handleSubmit = (e: React.FormEvent) => {
		e.preventDefault();

		let content = `Translate the following code from ${sourceFramework} to ${targetFramework}. Translation type is ${translationType}.\n\n`;
		if (schemaCode) {
			content += `### Source Schema Code:\n\`\`\`csharp\n${schemaCode}\n\`\`\`\n\n`;
		}
		if (queryCode) {
			content += `### Source Query Code:\n\`\`\`csharp\n${queryCode}\n\`\`\`\n\n`;
		}

		api.thread().append({
			role: "user",
			content: [{ type: "text", text: content }],
		});
	};

	return (
		<form onSubmit={handleSubmit} className="flex flex-col gap-4 text-sm pb-6">
			<div className="flex flex-col gap-1.5">
				<label
					htmlFor="sourceFramework"
					className="font-medium text-foreground"
				>
					Source Framework
				</label>
				<select
					id="sourceFramework"
					value={sourceFramework}
					onChange={(e) => setSourceFramework(e.target.value)}
					className="border rounded-md px-3 py-2 bg-background"
				>
					<option value=".NET Entity Framework Core">
						.NET Entity Framework Core
					</option>
					<option value=".NET Dapper">.NET Dapper</option>
					<option value=".NET NHibernate">.NET NHibernate</option>
				</select>
			</div>

			<div className="flex flex-col gap-1.5">
				<label
					htmlFor="targetFramework"
					className="font-medium text-foreground"
				>
					Target Framework
				</label>
				<select
					id="targetFramework"
					value={targetFramework}
					onChange={(e) => setTargetFramework(e.target.value)}
					className="border rounded-md px-3 py-2 bg-background"
				>
					<option value="Java Spring Data MongoDB">
						Java Spring Data MongoDB
					</option>
					<option value="Java Spring Data Neo4j">Java Spring Data Neo4j</option>
				</select>
			</div>

			<div className="flex flex-col gap-1.5">
				<label
					htmlFor="translationType"
					className="font-medium text-foreground"
				>
					Translation Type
				</label>
				<select
					id="translationType"
					value={translationType}
					onChange={(e) => setTranslationType(e.target.value)}
					className="border rounded-md px-3 py-2 bg-background"
				>
					<option value="schema">Schema Only</option>
					<option value="query">Query Only</option>
					<option value="both">Schema & Query</option>
				</select>
			</div>

			<div className="flex flex-col gap-1.5">
			  <label htmlFor="schemaCode" className="font-medium text-foreground">Source Schema Code</label>
			  <textarea 
			    id="schemaCode"
			    value={schemaCode} 
			    onChange={(e) => setSchemaCode(e.target.value)}
			    className="border rounded-md px-3 py-2 bg-background min-h-[150px] font-mono text-xs"
			    placeholder="public class Customer { ... }"
			  />
			</div>

			<div className="flex flex-col gap-1.5">
			  <label htmlFor="queryCode" className="font-medium text-foreground">Source Query Code</label>
			  <textarea 
			    id="queryCode"
			    value={queryCode} 
			    onChange={(e) => setQueryCode(e.target.value)}
			    className="border rounded-md px-3 py-2 bg-background min-h-[150px] font-mono text-xs"
			    placeholder={`public static IEnumerable<OrderLine> Query1(SqlConnection conn)
			{
			var from = new DateTime(2014, 12, 20);
			var to = new DateTime(2014, 12, 31);
			string sql = @"SELECT * FROM Sales.OrderLines WHERE PickingCompletedWhen >= @From AND PickingCompletedWhen <= @To";
			return conn.Query<OrderLine>(sql, new { From = from, To = to });
			}`}
			  />
			</div>

			<Button type="submit" disabled={isRunning} className="w-full mt-2">
				{isRunning ? "Running..." : "Start Translation"}
			</Button>
		</form>
	);
}
