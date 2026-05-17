"use client";

import { cn } from "@/lib/utils";
import { Bot, User } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { CodeBlock } from "./code-block";
import { StatusBadgeGroup } from "./status-badge";
import { LangGraphTrace } from "./langgraph-trace";
import type { ChatMessage as ChatMessageType } from "@/lib/types";

interface ChatMessageProps {
  message: ChatMessageType;
  className?: string;
}

export function ChatMessage({ message, className }: ChatMessageProps) {
  const isUser = message.role === "user";
  const isAssistant = message.role === "assistant";

  return (
    <div className={cn("flex gap-3 py-4", className)}>
      {/* Avatar */}
      <div className="shrink-0">
        {isUser ? (
          <Avatar className="size-8 border border-border">
            <AvatarFallback className="bg-muted text-muted-foreground">
              <User className="size-4" />
            </AvatarFallback>
          </Avatar>
        ) : (
          <Avatar className="size-8 bg-primary/10 border border-primary/20">
            <AvatarFallback className="bg-transparent text-primary">
              <Bot className="size-4" />
            </AvatarFallback>
          </Avatar>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0 space-y-3">
        {/* User message content - styled as a bubble */}
        {isUser && (
          <div className="inline-block max-w-[85%]">
            <div className="px-4 py-3 rounded-2xl rounded-tl-sm bg-muted text-foreground">
              <pre className="whitespace-pre-wrap font-mono text-sm leading-relaxed">
                {message.content}
              </pre>
            </div>
          </div>
        )}

        {/* Assistant message */}
        {isAssistant && (
          <div className="space-y-4">
            {/* Agent activities/status badges */}
            {message.activities && message.activities.length > 0 && (
              <StatusBadgeGroup activities={message.activities} />
            )}

            {/* LangGraph trace */}
            {message.trace && message.trace.steps.length > 0 && (
              <LangGraphTrace 
                steps={message.trace.steps} 
                defaultExpanded={message.trace.isExpanded}
              />
            )}

            {/* Text content */}
            {message.content && (
              <div className="prose prose-sm dark:prose-invert max-w-none">
                <p className="text-foreground leading-relaxed whitespace-pre-wrap">
                  {message.content}
                </p>
              </div>
            )}

            {/* Code blocks */}
            {message.codeBlocks && message.codeBlocks.length > 0 && (
              <div className="space-y-3">
                {message.codeBlocks.map((block, index) => (
                  <CodeBlock
                    key={`${message.id}-code-${index}`}
                    code={block.code}
                    language={block.language}
                    filename={block.filename}
                    isStreaming={message.isStreaming && index === message.codeBlocks!.length - 1}
                  />
                ))}
              </div>
            )}

            {/* Streaming indicator */}
            {message.isStreaming && !message.codeBlocks?.length && (
              <div className="flex items-center gap-2 text-muted-foreground">
                <span className="size-1.5 rounded-full bg-primary animate-pulse" />
                <span className="text-sm">AI is generating...</span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

interface ChatMessagesListProps {
  messages: ChatMessageType[];
  className?: string;
}

export function ChatMessagesList({ messages, className }: ChatMessagesListProps) {
  return (
    <div className={cn("divide-y divide-border/50", className)}>
      {messages.map((message) => (
        <ChatMessage key={message.id} message={message} />
      ))}
    </div>
  );
}
