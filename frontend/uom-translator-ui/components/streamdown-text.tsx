"use client";

import {
	type SyntaxHighlighterProps,
	useIsStreamdownCodeBlock,
} from "@assistant-ui/react-streamdown";
import { code } from "@streamdown/code";
import { mermaid } from "@streamdown/mermaid";
import dynamic from "next/dynamic";
import { Allow, parse as parsePartialJson } from "partial-json";
import {
	CodeBlock,
	CodeBlockContainer,
	CodeBlockHeader,
	type CustomRendererProps,
	Streamdown,
	type StreamdownProps,
} from "streamdown";
import { JsonViewer } from "@/components/json-viewer";

const StreamdownTextPrimitive = dynamic(
	() =>
		import("@assistant-ui/react-streamdown").then(
			(mod) => mod.StreamdownTextPrimitive,
		),
	{ ssr: false },
);

export const StreamdownText = ({ ...props }) => {
	"use-client";

	const renderers = [{ language: "json", component: JsonRenderer }];

	return (
		<StreamdownTextPrimitive
			plugins={{ code, mermaid }}
			shikiTheme={["github-light", "github-dark"]}
			caret="circle"
			linkSafety={{
				enabled: true,
			}}
			componentsByLanguage={{
				json: {
					SyntaxHighlighter: JsonCodeComponent,
				},
			}}
			containerProps={{
				suppressHydrationWarning: true,
			}}
			animated
		/>
	);
};

export const CodeComponent = ({
	components,
	node,
	children,
	...props
}: {
	components: SyntaxHighlighterProps["components"];
	node?: any;
	children?: React.ReactNode;
} & React.HTMLAttributes<HTMLElement>) => {
	const isCodeBlock = useIsStreamdownCodeBlock();
	const CodeComp = components?.Code || "code";

	if (!isCodeBlock) {
		return (
			<CodeComp className="code-block" {...props}>
				{children}
			</CodeComp>
		);
	}

	const PreComp = components?.Pre || "pre";
	return (
		<PreComp node={node}>
			<CodeComp className="code-block" {...props}>
				{children}
			</CodeComp>
		</PreComp>
	);
};

export const JsonCodeComponent = ({
	node,
	components,
	language,
	code,
}: SyntaxHighlighterProps) => {
	console.log("Parsing JSON code block:", code);
	try {
		code = code.trim().replace(/^"|"$/g, "");
		console.log("Parsing JSON code block:", code);
		const parsed = parsePartialJson(code, Allow.ALL);
		return (
			<div className="border p-4 mt-2 mb-2 max-h-[500px] w-full overflow-y-auto custom-scrollbar">
				<JsonViewer value={parsed} />
			</div>
		);
	} catch (e) {
		// Fall back to default rendering if parsing exception occurs
	}
	return (
		<CodeComponent
			components={components}
			node={node}
			className="language-json"
		>
			{code}
		</CodeComponent>
	);
};

export const StaticStreamdownWrapper = ({
	markdownText,
	...props
}: Omit<StreamdownProps, "children"> & { markdownText: string }) => {
	const processedText = markdownText.replace(/\r\n/g, "\n");

	return (
		<Streamdown
			mode="static"
			caret="circle"
			linkSafety={{
				enabled: true,
			}}
			plugins={{ code, mermaid }}
			shikiTheme={["github-light", "github-dark"]}
			{...props}
		>
			{processedText}
		</Streamdown>
	);
};

export const JsonRenderer = ({
	code,
	language,
	isIncomplete,
}: CustomRendererProps) => {
	let parsed: any = null;
	try {
		parsed = parsePartialJson(code, Allow.ALL);
	} catch {
		// Fall back to default rendering if parsing exception occurs
	}

	return parsed ? (
		<CodeBlockContainer isIncomplete={isIncomplete} language={language}>
			<CodeBlockHeader language={language} />
			<div className="border p-4 mt-2 mb-2 max-h-[500px] w-full overflow-y-auto custom-scrollbar">
				<JsonViewer value={parsed} />
			</div>
		</CodeBlockContainer>
	) : (
		<CodeBlock code={code} language={language} isIncomplete={isIncomplete} />
	);
};
