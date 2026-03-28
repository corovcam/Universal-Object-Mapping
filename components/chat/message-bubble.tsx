"use client";

import { useMemo } from "react";
import { Bot, User } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { CodeBlock } from "./code-block";
import { cn } from "@/lib/utils";
import { formatTimestamp } from "@/lib/utils";
import { getFramework, getShikiLanguage } from "@/lib/frameworks";
import type { ChatMessage, FrameworkType } from "@/lib/types";

interface MessageBubbleProps {
  message: ChatMessage;
  targetFramework?: FrameworkType;
}

export function MessageBubble({ message, targetFramework }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const framework = targetFramework ? getFramework(targetFramework) : undefined;

  const codeBlocks = useMemo(() => {
    const regex = /```(\w+)?\n([\s\S]*?)```/g;
    const blocks: { language: string; code: string }[] = [];
    let match;
    while ((match = regex.exec(message.content)) !== null) {
      blocks.push({
        language: match[1] || "plaintext",
        code: match[2].trim(),
      });
    }
    return blocks;
  }, [message.content]);

  const textContent = useMemo(() => {
    return message.content.replace(/```(\w+)?\n[\s\S]*?```/g, "").trim();
  }, [message.content]);

  return (
    <div
      className={cn(
        "flex gap-3 px-4 py-4",
        isUser ? "bg-transparent" : "bg-muted/30"
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          "flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center",
          isUser ? "bg-primary text-primary-foreground" : "bg-secondary"
        )}
      >
        {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0 space-y-3">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">
            {isUser ? "You" : "AI Translator"}
          </span>
          <span className="text-xs text-muted-foreground">
            {formatTimestamp(message.timestamp)}
          </span>
          {framework && !isUser && (
            <span
              className="text-xs px-2 py-0.5 rounded-full"
              style={{
                backgroundColor: `${framework.color}20`,
                color: framework.color,
              }}
            >
              {framework.name}
            </span>
          )}
        </div>

        {/* Text content */}
        {textContent && (
          <div className="message-content prose prose-sm dark:prose-invert max-w-none">
            <ReactMarkdown>{textContent}</ReactMarkdown>
          </div>
        )}

        {/* Code blocks */}
        {codeBlocks.map((block, index) => {
          const lang = mapLanguage(block.language, targetFramework);
          return (
            <CodeBlock
              key={index}
              code={block.code}
              language={lang}
              title={
                block.language !== "plaintext" ? block.language : undefined
              }
              collapsible={block.code.split("\n").length > 20}
            />
          );
        })}

        {/* Streaming indicator */}
        {message.isStreaming && (
          <div className="flex items-center gap-1 text-muted-foreground">
            <div className="typing-dot w-1.5 h-1.5 rounded-full bg-current" />
            <div className="typing-dot w-1.5 h-1.5 rounded-full bg-current" />
            <div className="typing-dot w-1.5 h-1.5 rounded-full bg-current" />
          </div>
        )}
      </div>
    </div>
  );
}

function mapLanguage(
  lang: string,
  targetFramework?: FrameworkType
): "csharp" | "java" | "sql" | "typescript" | "json" {
  const normalized = lang.toLowerCase();
  if (normalized === "csharp" || normalized === "cs" || normalized === "c#") {
    return "csharp";
  }
  if (normalized === "java") {
    return "java";
  }
  if (normalized === "sql" || normalized === "mssql" || normalized === "tsql") {
    return "sql";
  }
  if (normalized === "json") {
    return "json";
  }
  if (
    normalized === "typescript" ||
    normalized === "ts" ||
    normalized === "javascript" ||
    normalized === "js"
  ) {
    return "typescript";
  }
  // Fallback to target framework language
  if (targetFramework) {
    return getShikiLanguage(targetFramework);
  }
  return "sql";
}
