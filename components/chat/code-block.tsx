"use client";

import { useEffect, useState } from "react";
import { Check, Copy, ChevronDown, ChevronUp } from "lucide-react";
import { codeToHtml } from "shiki";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

interface CodeBlockProps {
  code: string;
  language?: "csharp" | "java" | "sql" | "typescript" | "json";
  title?: string;
  showLineNumbers?: boolean;
  collapsible?: boolean;
  maxHeight?: number;
}

export function CodeBlock({
  code,
  language = "sql",
  title,
  showLineNumbers = true,
  collapsible = false,
  maxHeight = 400,
}: CodeBlockProps) {
  const [copied, setCopied] = useState(false);
  const [expanded, setExpanded] = useState(!collapsible);
  const [highlightedCode, setHighlightedCode] = useState<string>("");

  useEffect(() => {
    async function highlight() {
      try {
        const html = await codeToHtml(code, {
          lang: language,
          themes: {
            light: "github-light",
            dark: "github-dark",
          },
        });
        setHighlightedCode(html);
      } catch {
        // Fallback for unsupported languages
        setHighlightedCode(
          `<pre class="shiki"><code>${escapeHtml(code)}</code></pre>`
        );
      }
    }
    highlight();
  }, [code, language]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      toast.success("Code copied to clipboard");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("Failed to copy code");
    }
  };

  const lineCount = code.split("\n").length;
  const shouldCollapse = collapsible && lineCount > 15;

  return (
    <div className="group relative rounded-lg border bg-card overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-muted/50 border-b">
        <div className="flex items-center gap-2">
          <div className="flex gap-1.5">
            <div className="w-3 h-3 rounded-full bg-destructive/60" />
            <div className="w-3 h-3 rounded-full bg-warning/60" />
            <div className="w-3 h-3 rounded-full bg-success/60" />
          </div>
          {title && (
            <span className="text-sm font-medium text-muted-foreground ml-2">
              {title}
            </span>
          )}
          <span className="text-xs text-muted-foreground/60 uppercase">
            {language}
          </span>
        </div>
        <div className="flex items-center gap-1">
          {shouldCollapse && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setExpanded(!expanded)}
              className="h-7 px-2 text-xs"
            >
              {expanded ? (
                <>
                  <ChevronUp className="h-3 w-3 mr-1" />
                  Collapse
                </>
              ) : (
                <>
                  <ChevronDown className="h-3 w-3 mr-1" />
                  Expand ({lineCount} lines)
                </>
              )}
            </Button>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={handleCopy}
            className="h-7 px-2"
          >
            {copied ? (
              <Check className="h-4 w-4 text-success" />
            ) : (
              <Copy className="h-4 w-4" />
            )}
          </Button>
        </div>
      </div>

      {/* Code content */}
      <div
        className={cn(
          "code-block overflow-auto transition-all duration-200",
          !showLineNumbers && "[&_.line::before]:hidden",
          !expanded && "max-h-32"
        )}
        style={{ maxHeight: expanded ? maxHeight : undefined }}
      >
        {highlightedCode ? (
          <div
            dangerouslySetInnerHTML={{ __html: highlightedCode }}
            className="[&_.shiki]:!bg-transparent dark:[&_.shiki]:!bg-transparent"
          />
        ) : (
          <pre className="p-4 text-sm font-mono">
            <code>{code}</code>
          </pre>
        )}
      </div>

      {/* Gradient overlay for collapsed state */}
      {!expanded && shouldCollapse && (
        <div className="absolute bottom-0 left-0 right-0 h-12 bg-gradient-to-t from-card to-transparent pointer-events-none" />
      )}
    </div>
  );
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
