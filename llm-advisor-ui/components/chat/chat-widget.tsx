"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { MessageSquare } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import { ChatHeader } from "./chat-header";
import { ChatInput } from "./chat-input";
import { ChatMessagesList } from "./chat-message";
import { MigrationForm } from "./migration-form";
import { HistorySidebar } from "./history-sidebar";
import type {
  ChatMessage,
  MigrationConfig,
  ConversationHistoryItem,
  ThemeMode,
} from "@/lib/types";

// Sample data for demonstration
const SAMPLE_HISTORY: ConversationHistoryItem[] = [
  {
    id: "1",
    title: "User Entity Translation",
    migrationBadge: { source: "EF Core", target: "MongoDB" },
    timestamp: Date.now() - 120000,
    preview: "Translated User entity with all properties...",
  },
  {
    id: "2",
    title: "Order Service Migration",
    migrationBadge: { source: "Dapper", target: "Hibernate" },
    timestamp: Date.now() - 3600000,
    preview: "Complex query migration with joins...",
  },
  {
    id: "3",
    title: "Auth Schema Update",
    migrationBadge: { source: "EF Core", target: "MongoDB" },
    timestamp: Date.now() - 86400000,
  },
];

const SAMPLE_MESSAGES: ChatMessage[] = [
  {
    id: "1",
    role: "user",
    content: `Translate EF Core to Spring Data MongoDB for the User entity.

[Table("Customers", Schema = "Sales")]
public class Customer
{
    ...
    public List<OrderLine> Query1 ...
    ...
    public List<Customer> Query2...
    ...
}`,
    timestamp: Date.now() - 60000,
  },
  {
    id: "2",
    role: "assistant",
    content: "Here is the translated `User` entity for Spring Data MongoDB.",
    timestamp: Date.now() - 55000,
    activities: [
      { id: "a1", status: "complete", label: "Fetching Docs", startTime: Date.now() - 58000, endTime: Date.now() - 56000 },
      { id: "a2", status: "complete", label: "Validating Java", startTime: Date.now() - 56000, endTime: Date.now() - 54000 },
    ],
    trace: {
      id: "t1",
      isExpanded: false,
      steps: [
        { id: "s1", node: "Parse Input", status: "complete", startTime: Date.now() - 58000, endTime: Date.now() - 57500, details: "EF Core entity parsed" },
        { id: "s2", node: "Schema Analysis", status: "complete", startTime: Date.now() - 57500, endTime: Date.now() - 56500, details: "Identified 5 properties" },
        { id: "s3", node: "Generate Translation", status: "complete", startTime: Date.now() - 56500, endTime: Date.now() - 55500, details: "Spring Data MongoDB" },
        { id: "s4", node: "Validate Output", status: "complete", startTime: Date.now() - 55500, endTime: Date.now() - 55000, details: "Compilation successful" },
      ],
    },
    codeBlocks: [
      {
        language: "java",
        code: `import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

@Document(collection = "users")
public class User {

    @Id
    private String id;

    private String username;
    
    private String email;
    
    private LocalDateTime createdAt;
}`,
      },
    ],
  },
];

interface ChatWidgetProps {
  className?: string;
}

export function ChatWidget({ className }: ChatWidgetProps) {
  const [isOpen, setIsOpen] = useState(true);
  const [isMaximized, setIsMaximized] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [theme, setTheme] = useState<ThemeMode>("dark");
  const [messages, setMessages] = useState<ChatMessage[]>(SAMPLE_MESSAGES);
  const [history] = useState<ConversationHistoryItem[]>(SAMPLE_HISTORY);
  const [activeConversationId, setActiveConversationId] = useState<string>("1");
  const [isLoading, setIsLoading] = useState(false);
  const [config, setConfig] = useState<MigrationConfig>({
    translationType: "schema",
    sourceFramework: "efcore",
    sourceVersion: "7.0",
    destinationFramework: "spring-mongodb",
    destinationVersion: "3.1",
    sourceSchemaCode: "",
    sourceQueryCode: "",
  });

  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  // Handle theme toggle
  const handleThemeToggle = useCallback(() => {
    const newTheme = theme === "dark" ? "light" : "dark";
    setTheme(newTheme);
    document.documentElement.classList.toggle("dark", newTheme === "dark");
  }, [theme]);

  // Handle send message
  const handleSendMessage = useCallback(async (content: string) => {
    const userMessage: ChatMessage = {
      id: `msg-${Date.now()}`,
      role: "user",
      content,
      timestamp: Date.now(),
    };
    
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    // Simulate AI response
    setTimeout(() => {
      const assistantMessage: ChatMessage = {
        id: `msg-${Date.now()}-response`,
        role: "assistant",
        content: "I'll help you with that translation. Let me analyze the code...",
        timestamp: Date.now(),
        activities: [
          { id: `a-${Date.now()}`, status: "generating", label: "Generating", startTime: Date.now() },
        ],
        isStreaming: true,
      };
      setMessages((prev) => [...prev, assistantMessage]);
      setIsLoading(false);
    }, 1000);
  }, []);

  // Handle conversation selection from history
  const handleSelectConversation = useCallback((id: string) => {
    setActiveConversationId(id);
    // In a real app, this would load the conversation messages
  }, []);

  // Floating button when widget is closed
  if (!isOpen) {
    return (
      <Button
        onClick={() => setIsOpen(true)}
        className={cn(
          "fixed bottom-6 right-6 size-14 rounded-full shadow-lg",
          "bg-primary hover:bg-primary/90 text-primary-foreground",
          className
        )}
      >
        <MessageSquare className="size-6" />
        <span className="sr-only">Open LLM Advisor</span>
      </Button>
    );
  }

  return (
    <div
      className={cn(
        "fixed flex flex-col bg-background border border-border shadow-2xl overflow-hidden transition-all duration-300",
        isMaximized
          ? "inset-4 rounded-xl"
          : "bottom-6 right-6 w-[440px] h-[680px] rounded-xl",
        className
      )}
    >
      <div className="flex flex-1 overflow-hidden">
        {/* Main Chat Area */}
        <div className="flex flex-col flex-1 min-w-0">
          {/* Header */}
          <ChatHeader
            theme={theme}
            isMaximized={isMaximized}
            onThemeToggle={handleThemeToggle}
            onHistoryToggle={() => setShowHistory(!showHistory)}
            onMaximizeToggle={() => setIsMaximized(!isMaximized)}
            onClose={() => setIsOpen(false)}
          />

          {/* Messages Area */}
          <ScrollArea className="flex-1" ref={scrollRef}>
            <div className="px-4">
              <ChatMessagesList messages={messages} />
            </div>
          </ScrollArea>

          {/* Migration Form */}
          <MigrationForm
            config={config}
            onConfigChange={setConfig}
            defaultExpanded={false}
          />

          {/* Input Area */}
          <div className="p-4 border-t border-border bg-background">
            <ChatInput onSend={handleSendMessage} isLoading={isLoading} />
          </div>
        </div>

        {/* History Sidebar - only visible when toggled */}
        {showHistory && (
          <div className={cn("w-80 shrink-0", !isMaximized && "hidden lg:block")}>
            <HistorySidebar
              history={history}
              activeConversationId={activeConversationId}
              onSelectConversation={handleSelectConversation}
              onClose={() => setShowHistory(false)}
            />
          </div>
        )}
      </div>
    </div>
  );
}
