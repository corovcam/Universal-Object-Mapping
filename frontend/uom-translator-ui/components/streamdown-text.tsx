"use client";

import {
	type SyntaxHighlighterProps,
	useIsStreamdownCodeBlock,
} from "@assistant-ui/react-streamdown";
import { code } from "@streamdown/code";
import { mermaid } from "@streamdown/mermaid";
import dynamic from "next/dynamic";
import { Allow, parse as parsePartialJson } from "partial-json";
import { memo } from "react";
import {
	CodeBlock,
	CodeBlockContainer,
	CodeBlockHeader,
	type CustomRendererProps,
	Streamdown,
	type StreamdownProps,
} from "streamdown";
import { AutoScrollJsonViewer } from "@/components/json-viewer";

const StreamdownTextPrimitive = dynamic(
	() =>
		import("@assistant-ui/react-streamdown").then(
			(mod) => mod.StreamdownTextPrimitive,
		),
	{ ssr: false },
);

/**
 * React Component to render streaming Markdown text with typing animations and carets.
 * Plugs into `@assistant-ui/react-streamdown` and supports code syntax highlighting
 * (using Shiki) and Mermaid diagram parsing dynamically.
 *
 * @param {object} props - Pass-through props.
 * @returns {React.JSX.Element} The streaming Markdown rendering primitive.
 */
export const StreamdownText = ({ ...props }) => {
	"use-client";

	return (
		<StreamdownTextPrimitive
			plugins={{ code, mermaid }}
			shikiTheme={["github-light", "github-dark"]}
			caret="circle"
			linkSafety={{
				enabled: true,
			}}
			containerProps={{
				suppressHydrationWarning: true,
			}}
			animated
		/>
	);
};

/**
 * Custom renderer for syntax highlighted inline code and code blocks.
 * Determines block-level vs inline presentation using the `useIsStreamdownCodeBlock` hook.
 */
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

/**
 * Custom code block renderer specialized for JSON formatting.
 * Intercepts text strings in JSON blocks, uses partial JSON decoding to process
 * incomplete/streaming payloads, and renders them inside an AutoScrollJsonViewer tree.
 */
export const JsonCodeComponent = ({
	node,
	components,
	language,
	code,
}: SyntaxHighlighterProps) => {
	console.debug("Parsing JSON code block:", code);
	try {
		code = code.trim().replace(/^"|"$/g, "");
		console.debug("Parsing JSON code block:", code);
		const parsed = parsePartialJson(code, Allow.ALL);
		return (
			<AutoScrollJsonViewer
				value={parsed}
				containerClassName="border p-4 mt-2 mb-2 max-h-[500px] w-full overflow-y-auto custom-scrollbar"
			/>
		);
	} catch (_e) {
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

/**
 * React Component for static, non-animated markdown document presentations.
 * Normalizes carriage returns and processes custom json blocks on-the-fly.
 *
 * @param {Omit<StreamdownProps, "children"> & { markdownText: string }} props - Wrapper parameters.
 * @returns {React.JSX.Element} Static markdown document element.
 */
export const StaticStreamdownWrapper = ({
	markdownText,
	...props
}: Omit<StreamdownProps, "children"> & { markdownText: string }) => {
	const processedText = markdownText.replace(/\r\n/g, "\n");
	const renderers = [{ language: "json", component: JsonRenderer }];

	return (
		<Streamdown
			mode="static"
			caret="circle"
			linkSafety={{
				enabled: true,
			}}
			plugins={{ code, mermaid, renderers }}
			shikiTheme={["github-light", "github-dark"]}
			{...props}
		>
			{processedText}
		</Streamdown>
	);
};

/**
 * Internal custom JSON renderer plugin implementation.
 */
const JsonRendererImpl = ({
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
			<AutoScrollJsonViewer
				value={parsed}
				containerClassName="border p-4 mt-2 mb-2 max-h-[500px] w-full overflow-y-auto custom-scrollbar"
			/>
		</CodeBlockContainer>
	) : (
		<CodeBlock code={code} language={language} isIncomplete={isIncomplete} />
	);
};

export const JsonRenderer = memo(JsonRendererImpl);
