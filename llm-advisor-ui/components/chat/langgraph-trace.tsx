"use client";

import { useState } from "react";
import { ChevronDown, Workflow, CheckCircle, Circle, Loader2, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import type { TraceStep } from "@/lib/types";

interface LangGraphTraceProps {
  steps: TraceStep[];
  defaultExpanded?: boolean;
  className?: string;
}

const stepStatusIcons = {
  pending: Circle,
  running: Loader2,
  complete: CheckCircle,
  error: AlertCircle,
};

const stepStatusStyles = {
  pending: "text-muted-foreground",
  running: "text-primary animate-spin",
  complete: "text-success",
  error: "text-destructive",
};

export function LangGraphTrace({ 
  steps, 
  defaultExpanded = false,
  className 
}: LangGraphTraceProps) {
  const [isOpen, setIsOpen] = useState(defaultExpanded);

  const completedSteps = steps.filter(s => s.status === "complete").length;
  const totalSteps = steps.length;
  const isRunning = steps.some(s => s.status === "running");

  return (
    <Collapsible 
      open={isOpen} 
      onOpenChange={setIsOpen}
      className={cn("w-full", className)}
    >
      <CollapsibleTrigger asChild>
        <button
          className={cn(
            "flex items-center justify-between w-full px-3 py-2 rounded-lg",
            "bg-muted/50 hover:bg-muted/80 transition-colors",
            "text-sm font-medium text-foreground"
          )}
        >
          <div className="flex items-center gap-2">
            <Workflow className="size-4 text-primary" />
            <span>Trace (LangGraph)</span>
            {isRunning && (
              <Loader2 className="size-3 text-primary animate-spin" />
            )}
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">
              {completedSteps}/{totalSteps} steps
            </span>
            <ChevronDown 
              className={cn(
                "size-4 text-muted-foreground transition-transform",
                isOpen && "rotate-180"
              )} 
            />
          </div>
        </button>
      </CollapsibleTrigger>

      <CollapsibleContent className="mt-2">
        <div className="relative pl-4 border-l-2 border-border ml-2 space-y-2">
          {steps.map((step, index) => {
            const StatusIcon = stepStatusIcons[step.status];
            const statusStyle = stepStatusStyles[step.status];

            return (
              <div 
                key={step.id}
                className={cn(
                  "relative flex items-start gap-3 py-2 px-3 rounded-md",
                  "bg-card/50 border border-border/50",
                  step.status === "running" && "border-primary/50 bg-primary/5"
                )}
              >
                {/* Timeline dot */}
                <div 
                  className={cn(
                    "absolute -left-[1.125rem] top-1/2 -translate-y-1/2",
                    "size-2.5 rounded-full border-2 border-background",
                    step.status === "complete" && "bg-success",
                    step.status === "running" && "bg-primary",
                    step.status === "error" && "bg-destructive",
                    step.status === "pending" && "bg-muted"
                  )}
                />

                <StatusIcon className={cn("size-4 mt-0.5 shrink-0", statusStyle)} />
                
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm font-medium truncate">{step.node}</span>
                    {step.endTime && step.startTime && (
                      <span className="text-xs text-muted-foreground shrink-0">
                        {((step.endTime - step.startTime) / 1000).toFixed(2)}s
                      </span>
                    )}
                  </div>
                  {step.details && (
                    <p className="text-xs text-muted-foreground mt-0.5 truncate">
                      {step.details}
                    </p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}
