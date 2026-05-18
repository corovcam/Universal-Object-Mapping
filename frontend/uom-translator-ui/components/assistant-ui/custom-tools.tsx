"use client";

import { makeAssistantToolUI } from "@assistant-ui/react";
import {
	CheckCircle2Icon,
	Code2Icon,
	FileJsonIcon,
	GitCompareArrowsIcon,
	Loader2Icon,
	XCircleIcon,
} from "lucide-react";
import { useState } from "react";

export const ExtractInputToolUI = makeAssistantToolUI({
	toolName: "extract_input",
	render: ({ args, result, status }) => {
		return (
			<ToolCard
				title="Extracting Requirements"
				icon={<FileJsonIcon className="w-4 h-4 text-green-500" />}
				status={status.type}
				args={args}
				result={result}
			/>
		);
	},
});

export const SchemaInspectionToolUI = makeAssistantToolUI({
	toolName: "schema_inspection",
	render: ({ args, result, status }) => {
		return (
			<ToolCard
				title="Inspecting Database Schemas"
				icon={<Loader2Icon className="w-4 h-4 text-yellow-500" />}
				status={status.type}
				args={args}
				result={result}
			/>
		);
	},
});

export const ValidateDotnetToolUI = makeAssistantToolUI({
	toolName: "validate_dotnet_code",
	render: ({ args, result, status }) => {
		return (
			<ToolCard
				title="Validating .NET Code"
				icon={<Code2Icon className="w-4 h-4 text-blue-500" />}
				status={status.type}
				args={args}
				result={result}
			/>
		);
	},
});

export const ValidateJavaToolUI = makeAssistantToolUI({
	toolName: "validate_java_code",
	render: ({ args, result, status }) => {
		return (
			<ToolCard
				title="Validating Java Code"
				icon={<Code2Icon className="w-4 h-4 text-orange-500" />}
				status={status.type}
				args={args}
				result={result}
			/>
		);
	},
});

export const CheckEquivalenceToolUI = makeAssistantToolUI({
	toolName: "check_query_equivalence",
	render: ({ args, result, status }) => {
		return (
			<ToolCard
				title="Checking Query Equivalence"
				icon={<GitCompareArrowsIcon className="w-4 h-4 text-purple-500" />}
				status={status.type}
				args={args}
				result={result}
			/>
		);
	},
});

function ToolCard({
	title,
	icon,
	status,
	args,
	result,
}: {
	title: string;
	icon: React.ReactNode;
	status: string;
	args: unknown;
	result: unknown;
}) {
	const [expanded, setExpanded] = useState(false);

	// Determine if there was an error in the validation result
	const isComplete = status === "complete";
	let hasError = false;

	if (isComplete && typeof result === "string") {
		hasError = result.includes("Failed]") || result.includes("Error");
	} else if (isComplete && result && typeof result === "object") {
		// If it's a parsed JSON response containing an error
		hasError =
			JSON.stringify(result).includes("Failed]") ||
			JSON.stringify(result).includes("Error");
	}

	return (
		<div className="flex flex-col gap-2 rounded-lg border bg-card text-card-foreground shadow-sm my-2 overflow-hidden w-full max-w-full">
			<button
				type="button"
				onClick={() => setExpanded(!expanded)}
				className="flex items-center justify-between p-3 bg-muted/30 hover:bg-muted/50 transition-colors w-full text-left"
			>
				<div className="flex items-center gap-2">
					{icon}
					<span className="font-medium text-sm">{title}</span>
				</div>
				<div className="flex items-center gap-2">
					{status === "running" && (
						<div className="flex items-center gap-1.5 text-xs text-muted-foreground">
							<Loader2Icon className="w-3.5 h-3.5 animate-spin" />
							<span>Running...</span>
						</div>
					)}
					{isComplete && hasError && (
						<div className="flex items-center gap-1.5 text-xs text-destructive">
							<XCircleIcon className="w-3.5 h-3.5" />
							<span>Failed</span>
						</div>
					)}
					{isComplete && !hasError && (
						<div className="flex items-center gap-1.5 text-xs text-green-600 dark:text-green-500">
							<CheckCircle2Icon className="w-3.5 h-3.5" />
							<span>Passed</span>
						</div>
					)}
				</div>
			</button>

			{expanded && (
				<div className="p-3 border-t bg-muted/10 text-xs overflow-x-auto max-w-full">
					<div className="mb-3">
						<p className="font-medium text-muted-foreground mb-1">Arguments:</p>
						<pre className="bg-muted p-2 rounded-md overflow-x-auto whitespace-pre-wrap max-w-full">
							{JSON.stringify(args, null, 2)}
						</pre>
					</div>

					{isComplete && (
						<div>
							<p className="font-medium text-muted-foreground mb-1 flex items-center gap-1">
								<FileJsonIcon className="w-3.5 h-3.5" /> Result:
							</p>
							<pre className="bg-muted p-2 rounded-md overflow-x-auto whitespace-pre-wrap max-w-full">
								{typeof result === "string"
									? result
									: JSON.stringify(result, null, 2)}
							</pre>
						</div>
					)}
				</div>
			)}
		</div>
	);
}
