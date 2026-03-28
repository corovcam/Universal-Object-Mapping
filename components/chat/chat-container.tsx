"use client";

import { useState, useEffect } from "react";
import { MessageList } from "./message-list";
import { ChatInput } from "./chat-input";
import { PipelineVisualizer } from "@/components/pipeline/pipeline-visualizer";
import { ConversationSidebar } from "./conversation-sidebar";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme-toggle";
import { Menu, X, Plus, AlertCircle } from "lucide-react";
import { useChatStream } from "@/hooks/use-chat-stream";
import { useChatHistory } from "@/hooks/use-chat-history";
import { cn } from "@/lib/utils";
import type { FrameworkType, ChatMessage } from "@/lib/types";
import { generateId } from "@/lib/utils";

export function ChatContainer() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [targetFramework, setTargetFramework] = useState<FrameworkType | undefined>();

  const {
    messages: streamMessages,
    isStreaming,
    pipeline,
    error,
    sendMessage,
    clearMessages,
    stopStream,
  } = useChatStream();

  const {
    conversations,
    activeConversation,
    isLoaded,
    startNewConversation,
    selectConversation,
    removeConversation,
    clearAll,
  } = useChatHistory();

  // Use stream messages or fall back to conversation history
  const displayMessages = streamMessages.length > 0 
    ? streamMessages 
    : (activeConversation?.messages || []);

  const handleSubmit = async (
    message: string,
    sourceFramework: FrameworkType,
    targetFw: FrameworkType
  ) => {
    setTargetFramework(targetFw);
    
    // Create a new conversation if needed
    if (!activeConversation) {
      startNewConversation();
    }
    
    await sendMessage(message, sourceFramework, targetFw);
  };

  const handleNewChat = () => {
    clearMessages();
    startNewConversation();
    setSidebarOpen(false);
  };

  const handleSelectConversation = (id: string) => {
    clearMessages();
    selectConversation(id);
    setSidebarOpen(false);
  };

  return (
    <div className="flex h-dvh bg-background">
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-background/80 backdrop-blur-sm z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 w-72 bg-card border-r transform transition-transform duration-200 lg:relative lg:translate-x-0",
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="font-semibold">Conversations</h2>
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="icon"
              onClick={handleNewChat}
              className="h-8 w-8"
            >
              <Plus className="h-4 w-4" />
              <span className="sr-only">New chat</span>
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setSidebarOpen(false)}
              className="h-8 w-8 lg:hidden"
            >
              <X className="h-4 w-4" />
              <span className="sr-only">Close sidebar</span>
            </Button>
          </div>
        </div>
        <ConversationSidebar
          conversations={conversations}
          activeId={activeConversation?.id}
          onSelect={handleSelectConversation}
          onDelete={removeConversation}
          onClearAll={clearAll}
        />
      </aside>

      {/* Main chat area */}
      <main className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="flex items-center justify-between px-4 py-3 border-b bg-card/50 backdrop-blur-sm">
          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setSidebarOpen(true)}
              className="h-9 w-9 lg:hidden"
            >
              <Menu className="h-5 w-5" />
              <span className="sr-only">Open sidebar</span>
            </Button>
            <div>
              <h1 className="text-lg font-semibold">Code Translator</h1>
              <p className="text-xs text-muted-foreground hidden sm:block">
                Universal Object Mapping
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {isStreaming && (
              <Button
                variant="outline"
                size="sm"
                onClick={stopStream}
                className="text-destructive"
              >
                Stop
              </Button>
            )}
            <ThemeToggle />
          </div>
        </header>

        {/* Pipeline visualizer */}
        {pipeline.currentStep !== "idle" && (
          <PipelineVisualizer
            currentStep={pipeline.currentStep}
            completedSteps={pipeline.completedSteps}
          />
        )}

        {/* Error display */}
        {error && (
          <div className="mx-4 mt-4 p-4 rounded-lg bg-destructive/10 border border-destructive/20 flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-destructive shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm font-medium text-destructive">
                Connection Error
              </p>
              <p className="text-sm text-muted-foreground mt-1">
                {error.message || "Failed to connect to the translation service. Please check if the orchestrator is running."}
              </p>
            </div>
          </div>
        )}

        {/* Messages */}
        <MessageList
          messages={displayMessages}
          targetFramework={targetFramework}
          isStreaming={isStreaming}
        />

        {/* Input */}
        <ChatInput
          onSubmit={handleSubmit}
          isLoading={isStreaming}
          disabled={!isLoaded}
        />
      </main>
    </div>
  );
}
