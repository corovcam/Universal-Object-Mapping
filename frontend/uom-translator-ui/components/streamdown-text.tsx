import { JsonViewer } from "@/components/json-viewer";
import { StreamdownTextPrimitive, SyntaxHighlighterProps, useIsStreamdownCodeBlock } from "@assistant-ui/react-streamdown";
import { code } from "@streamdown/code";
import { mermaid } from "@streamdown/mermaid";

export const StreamdownText = ({...props}) => (
  <StreamdownTextPrimitive
    plugins={{ code, mermaid }}
    shikiTheme={["github-light", "github-dark"]}
    caret="circle"
    linkSafety={{
      enabled: true,
    }}
    componentsByLanguage={{
      "json": { 
        SyntaxHighlighter: JsonCodeComponent
      },
    }}
  />
);

export const CodeComponent = ({ children, ...props }: { children?: React.ReactNode, props?: any[] }) => {
  const isCodeBlock = useIsStreamdownCodeBlock();

  if (!isCodeBlock) {
    return <code className="code-block" {...props}>{children}</code>;
  }

  return <pre><code {...props}>{children}</code></pre>;
}

export const JsonCodeComponent = ({ node, components, language, code }: SyntaxHighlighterProps) => {
  try {
    const parsed = JSON.parse(code);
    return (
      <div className="border border-slate-800/80 rounded-lg bg-slate-950/80 p-4 mt-2 max-h-[500px] overflow-y-auto custom-scrollbar select-text">
        <JsonViewer data={parsed} maxDepth={2} />
      </div>
    );
  } catch (e) {
    // Fall back to default rendering if not yet fully formed JSON
  }
  return (
    <CodeComponent className="language-json">{code}</CodeComponent>
  );
}


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