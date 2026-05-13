"use client";

import { useState } from "react";
import { History, Layers, Settings, ArrowRight } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { Card, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import type { ConversationHistoryItem } from "@/lib/types";

interface HistoryItemCardProps {
  item: ConversationHistoryItem;
  onClick: () => void;
  isActive?: boolean;
}

function formatRelativeTime(timestamp: number): string {
  const now = Date.now();
  const diff = now - timestamp;
  
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);

  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  if (days === 1) return "Yesterday";
  return `${days}d ago`;
}

function HistoryItemCard({ item, onClick, isActive }: HistoryItemCardProps) {
  return (
    <Card
      className={cn(
        "cursor-pointer transition-all hover:bg-accent/50",
        isActive && "border-primary/50 bg-primary/5"
      )}
      onClick={onClick}
    >
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-2">
          <h3 className="font-medium text-sm text-foreground line-clamp-2">
            {item.title}
          </h3>
          <span className="text-xs text-muted-foreground shrink-0">
            {formatRelativeTime(item.timestamp)}
          </span>
        </div>
        
        {item.migrationBadge && (
          <div className="mt-2">
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-primary/10 border border-primary/20 text-primary">
              {item.migrationBadge.source}
              <ArrowRight className="size-3" />
              {item.migrationBadge.target}
            </span>
          </div>
        )}
        
        {item.preview && (
          <p className="mt-2 text-xs text-muted-foreground line-clamp-2">
            {item.preview}
          </p>
        )}
      </CardContent>
    </Card>
  );
}

interface WorkflowStepProps {
  number: number;
  title: string;
  description?: string;
  status?: "pending" | "active" | "complete";
  children?: React.ReactNode;
}

function WorkflowStep({ number, title, description, status = "pending", children }: WorkflowStepProps) {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <span className="text-xs font-mono text-muted-foreground uppercase tracking-wider">
          {number}. {title}
        </span>
      </div>
      <div
        className={cn(
          "rounded-lg border p-4 bg-card/50",
          status === "active" && "border-primary/50",
          status === "complete" && "border-success/50"
        )}
      >
        {children || (
          <div className="space-y-2">
            <div className="h-8 rounded bg-muted/50" />
            <div className="flex justify-end">
              <div className="size-8 rounded bg-primary/20" />
            </div>
          </div>
        )}
      </div>
      {description && (
        <p className="text-xs text-muted-foreground">{description}</p>
      )}
    </div>
  );
}

interface HistorySidebarProps {
  history: ConversationHistoryItem[];
  activeConversationId?: string;
  onSelectConversation: (id: string) => void;
  onClose?: () => void;
  className?: string;
}

export function HistorySidebar({
  history,
  activeConversationId,
  onSelectConversation,
  onClose,
  className,
}: HistorySidebarProps) {
  const [activeTab, setActiveTab] = useState<"history" | "states">("history");

  return (
    <div
      className={cn(
        "flex flex-col h-full bg-card border-l border-border",
        className
      )}
    >
      {/* Header with Tabs */}
      <div className="p-4 border-b border-border">
        <Tabs
          value={activeTab}
          onValueChange={(v) => setActiveTab(v as "history" | "states")}
          className="w-full"
        >
          <div className="flex items-center justify-between">
            <TabsList className="h-9 bg-muted/50">
              <TabsTrigger value="history" className="text-xs gap-1.5">
                <History className="size-3.5" />
                History
              </TabsTrigger>
              <TabsTrigger value="states" className="text-xs gap-1.5">
                <Layers className="size-3.5" />
                States
              </TabsTrigger>
            </TabsList>
            
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="sm"
                  className="size-8 p-0 text-muted-foreground"
                >
                  <Settings className="size-4" />
                  <span className="sr-only">Settings</span>
                </Button>
              </TooltipTrigger>
              <TooltipContent side="left">
                <p>Settings</p>
              </TooltipContent>
            </Tooltip>
          </div>
        </Tabs>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {activeTab === "history" ? (
          <ScrollArea className="h-full">
            <div className="p-4 space-y-3">
              {history.length === 0 ? (
                <div className="text-center py-8">
                  <History className="size-8 mx-auto text-muted-foreground/50 mb-2" />
                  <p className="text-sm text-muted-foreground">No conversation history</p>
                </div>
              ) : (
                history.map((item) => (
                  <HistoryItemCard
                    key={item.id}
                    item={item}
                    isActive={item.id === activeConversationId}
                    onClick={() => onSelectConversation(item.id)}
                  />
                ))
              )}
            </div>
          </ScrollArea>
        ) : (
          <ScrollArea className="h-full">
            <div className="p-4 space-y-6">
              <WorkflowStep
                number={1}
                title="INITIAL INPUT"
                status="complete"
              />
              
              <WorkflowStep
                number={2}
                title="PROCESSING & TRACE"
                status="active"
              >
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded text-xs bg-muted text-muted-foreground">
                      Parsing
                    </span>
                    <span className="px-2 py-0.5 rounded text-xs bg-primary/10 text-primary">
                      Translating
                    </span>
                  </div>
                  <div className="h-2 rounded-full bg-muted overflow-hidden">
                    <div className="h-full w-2/3 bg-primary rounded-full animate-pulse" />
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="size-2 rounded-full bg-success animate-pulse" />
                    <span className="text-xs text-muted-foreground">Processing step 2/3</span>
                  </div>
                </div>
              </WorkflowStep>
              
              <WorkflowStep
                number={3}
                title="RESULT OUTPUT"
                status="pending"
              >
                <div className="space-y-2">
                  <div className="h-3 w-full rounded bg-muted/50" />
                  <div className="h-3 w-3/4 rounded bg-muted/50" />
                  <Separator className="my-3" />
                  <div className="h-16 rounded bg-muted/30 border border-dashed border-border" />
                </div>
              </WorkflowStep>
            </div>
          </ScrollArea>
        )}
      </div>
    </div>
  );
}
