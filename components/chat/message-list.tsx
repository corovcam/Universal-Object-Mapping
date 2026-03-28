"use client";

import { useEffect, useRef } from "react";
import { MessageBubble } from "./message-bubble";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { ChatMessage, FrameworkType } from "@/lib/types";

interface MessageListProps {
  messages: ChatMessage[];
  targetFramework?: FrameworkType;
  isStreaming?: boolean;
}

export function MessageList({
  messages,
  targetFramework,
  isStreaming,
}: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isStreaming]);

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="text-center max-w-md space-y-4">
          <div className="w-16 h-16 mx-auto rounded-2xl bg-primary/10 flex items-center justify-center">
            <svg
              className="w-8 h-8 text-primary"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
              />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-balance">
            Universal Object Mapping
          </h3>
          <p className="text-sm text-muted-foreground text-balance">
            Translate code between ORM frameworks. Paste your source code, select
            the source and target frameworks, and let AI handle the translation.
          </p>
          <div className="flex flex-wrap justify-center gap-2 pt-2">
            {[
              "EF Core",
              "Dapper",
              "NHibernate",
              "Spring Data JPA",
              "MongoDB",
              "Neo4j",
            ].map((fw) => (
              <span
                key={fw}
                className="px-2 py-1 text-xs rounded-full bg-secondary text-secondary-foreground"
              >
                {fw}
              </span>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <ScrollArea className="flex-1">
      <div className="divide-y divide-border">
        {messages.map((message) => (
          <MessageBubble
            key={message.id}
            message={message}
            targetFramework={targetFramework}
          />
        ))}
      </div>
      <div ref={bottomRef} className="h-4" />
    </ScrollArea>
  );
}
