"use client";

import {
	type SyntaxHighlighterProps,
	useIsStreamdownCodeBlock,
} from "@assistant-ui/react-streamdown";
import { code } from "@streamdown/code";
import { mermaid } from "@streamdown/mermaid";
import dynamic from "next/dynamic";
import { Allow, parse as parsePartialJson } from "partial-json";
import { Streamdown, type StreamdownProps } from "streamdown";
import { JsonViewer } from "@/components/json-viewer";
import { useTheme } from "@/components/theme-provider";

const StreamdownTextPrimitive = dynamic(
	() =>
		import("@assistant-ui/react-streamdown").then(
			(mod) => mod.StreamdownTextPrimitive,
		),
	{ ssr: false },
);

export const StreamdownText = ({ ...props }) => (
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
	/>
);

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
	try {
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

// export const VegaLiteRenderer = ({
//   code,
//   language,
//   isIncomplete,
// }: CustomRendererProps) => {
//   const containerRef = useRef<HTMLDivElement>(null);
//   useEffect(() => {
//     if (isIncomplete || !containerRef.current) {
//       return;
//     }
//     let cancelled = false;
//     const render = async () => {
//       const spec = JSON.parse(code);
//       const vegaEmbed = (await import("vega-embed")).default;
//       if (cancelled || !containerRef.current) {
//         return;
//       }
//       containerRef.current.innerHTML = "";
//       await vegaEmbed(containerRef.current, spec, {
//         actions: false,
//         renderer: "svg",
//       });
//     };
//     render();
//     return () => {
//       cancelled = true;
//     };
//   }, [code, isIncomplete]);
//   return (
//     <CodeBlockContainer isIncomplete={isIncomplete} language={language}>
//       <CodeBlockHeader language={language} />
//       {isIncomplete ? (
//         <div className="flex h-48 items-center justify-center rounded-md bg-muted">
//           <span className="text-muted-foreground text-sm">
//             Loading chart...
//           </span>
//         </div>
//       ) : (
//         <div ref={containerRef} className="overflow-hidden rounded-md p-4" />
//       )}
//     </CodeBlockContainer>
//   );
// };
