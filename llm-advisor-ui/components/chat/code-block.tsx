"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { Check, Copy } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import hljs from "highlight.js/lib/core";
import java from "highlight.js/lib/languages/java";
import csharp from "highlight.js/lib/languages/csharp";
import sql from "highlight.js/lib/languages/sql";
import json from "highlight.js/lib/languages/json";
import xml from "highlight.js/lib/languages/xml";

// Register languages
hljs.registerLanguage("java", java);
hljs.registerLanguage("csharp", csharp);
hljs.registerLanguage("cs", csharp);
hljs.registerLanguage("sql", sql);
hljs.registerLanguage("json", json);
hljs.registerLanguage("xml", xml);

interface CodeBlockProps {
  code: string;
  language: string;
  filename?: string;
  isStreaming?: boolean;
  className?: string;
}

export function CodeBlock({
  code,
  language,
  filename,
  isStreaming = false,
  className,
}: CodeBlockProps) {
  const [copied, setCopied] = useState(false);
  const [highlightedCode, setHighlightedCode] = useState<string>("");
  const codeRef = useRef<HTMLElement>(null);

  const displayLanguage = language.toUpperCase() === "CS" ? "C#" : language.toUpperCase();

  useEffect(() => {
    if (code) {
      try {
        const langMap: Record<string, string> = {
          "c#": "csharp",
          "cs": "csharp",
        };
        const normalizedLang = langMap[language.toLowerCase()] || language.toLowerCase();
        
        if (hljs.getLanguage(normalizedLang)) {
          const result = hljs.highlight(code, { language: normalizedLang });
          setHighlightedCode(result.value);
        } else {
          setHighlightedCode(code);
        }
      } catch {
        setHighlightedCode(code);
      }
    }
  }, [code, language]);

  const copyToClipboard = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy code:", err);
    }
  }, [code]);

  return (
    <div className={cn("rounded-lg border border-border overflow-hidden", className)}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-muted/50 border-b border-border">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-primary">
            {displayLanguage}
          </span>
          {filename && (
            <>
              <span className="text-muted-foreground text-xs">-</span>
              <span className="text-xs text-muted-foreground font-mono">{filename}</span>
            </>
          )}
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={copyToClipboard}
          className="h-7 px-2 text-xs gap-1.5 text-muted-foreground hover:text-foreground"
        >
          {copied ? (
            <>
              <Check className="size-3.5" data-icon="inline-start" />
              Copied
            </>
          ) : (
            <>
              <Copy className="size-3.5" data-icon="inline-start" />
              Copy
            </>
          )}
        </Button>
      </div>

      {/* Code content */}
      <div className="relative overflow-x-auto bg-card">
        <pre className="p-4 text-sm leading-relaxed">
          <code
            ref={codeRef}
            className={cn("font-mono text-foreground", `language-${language}`)}
            dangerouslySetInnerHTML={{ __html: highlightedCode || code }}
          />
        </pre>
        
        {/* Streaming indicator */}
        {isStreaming && (
          <div className="absolute bottom-2 right-2 flex items-center gap-1.5">
            <span className="size-1.5 rounded-full bg-primary animate-pulse" />
            <span className="text-xs text-muted-foreground">Generating...</span>
          </div>
        )}
      </div>
    </div>
  );
}
