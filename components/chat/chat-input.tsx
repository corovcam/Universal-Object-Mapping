"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Loader2, ArrowRightLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { FrameworkSelector } from "./framework-selector";
import { cn } from "@/lib/utils";
import type { FrameworkType } from "@/lib/types";

interface ChatInputProps {
  onSubmit: (
    message: string,
    sourceFramework: FrameworkType,
    targetFramework: FrameworkType
  ) => void;
  isLoading?: boolean;
  disabled?: boolean;
}

export function ChatInput({
  onSubmit,
  isLoading = false,
  disabled = false,
}: ChatInputProps) {
  const [message, setMessage] = useState("");
  const [sourceFramework, setSourceFramework] = useState<FrameworkType | undefined>();
  const [targetFramework, setTargetFramework] = useState<FrameworkType | undefined>();
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [message]);

  const handleSubmit = () => {
    if (!message.trim() || !sourceFramework || !targetFramework || isLoading) {
      return;
    }
    onSubmit(message, sourceFramework, targetFramework);
    setMessage("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const swapFrameworks = () => {
    const temp = sourceFramework;
    setSourceFramework(targetFramework);
    setTargetFramework(temp);
  };

  const isValid = message.trim() && sourceFramework && targetFramework;

  return (
    <div className="border-t bg-background p-4 space-y-3">
      {/* Framework selectors */}
      <div className="flex items-end gap-2 flex-wrap">
        <FrameworkSelector
          value={sourceFramework}
          onChange={setSourceFramework}
          label="Source Framework"
          placeholder="Select source"
          disabled={disabled || isLoading}
          excludeFramework={targetFramework}
        />
        <Button
          variant="ghost"
          size="icon"
          onClick={swapFrameworks}
          disabled={!sourceFramework || !targetFramework || disabled || isLoading}
          className="h-9 w-9 mb-0.5"
        >
          <ArrowRightLeft className="h-4 w-4" />
          <span className="sr-only">Swap frameworks</span>
        </Button>
        <FrameworkSelector
          value={targetFramework}
          onChange={setTargetFramework}
          label="Target Framework"
          placeholder="Select target"
          disabled={disabled || isLoading}
          excludeFramework={sourceFramework}
        />
      </div>

      {/* Message input */}
      <div className="flex gap-2 items-end">
        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Paste your code here or describe what you want to translate..."
            disabled={disabled || isLoading}
            className={cn(
              "w-full resize-none rounded-lg border bg-background px-4 py-3 text-sm",
              "placeholder:text-muted-foreground",
              "focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
              "disabled:cursor-not-allowed disabled:opacity-50",
              "min-h-[48px] max-h-[200px]"
            )}
            rows={1}
          />
        </div>
        <Button
          onClick={handleSubmit}
          disabled={!isValid || disabled || isLoading}
          size="icon"
          className="h-12 w-12 shrink-0"
        >
          {isLoading ? (
            <Loader2 className="h-5 w-5 animate-spin" />
          ) : (
            <Send className="h-5 w-5" />
          )}
          <span className="sr-only">Send message</span>
        </Button>
      </div>

      {/* Helper text */}
      <p className="text-xs text-muted-foreground text-center">
        Press Enter to send, Shift+Enter for new line
      </p>
    </div>
  );
}
