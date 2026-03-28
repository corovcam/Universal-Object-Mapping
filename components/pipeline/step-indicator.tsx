"use client";

import { Check, Loader2 } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

interface StepIndicatorProps {
  label: string;
  description: string;
  status: "pending" | "active" | "completed";
  stepNumber: number;
}

export function StepIndicator({
  label,
  description,
  status,
  stepNumber,
}: StepIndicatorProps) {
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div className="flex items-center gap-2 min-w-0">
            <div
              className={cn(
                "flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-xs font-medium transition-all duration-300",
                status === "completed" && "bg-primary text-primary-foreground",
                status === "active" &&
                  "bg-primary/20 text-primary ring-2 ring-primary ring-offset-2 ring-offset-background",
                status === "pending" && "bg-muted text-muted-foreground"
              )}
            >
              {status === "completed" ? (
                <Check className="w-4 h-4" />
              ) : status === "active" ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                stepNumber
              )}
            </div>
            <span
              className={cn(
                "text-xs font-medium truncate hidden md:block",
                status === "active" && "text-primary",
                status === "completed" && "text-foreground",
                status === "pending" && "text-muted-foreground"
              )}
            >
              {label}
            </span>
          </div>
        </TooltipTrigger>
        <TooltipContent side="bottom" className="max-w-[200px]">
          <p className="font-medium">{label}</p>
          <p className="text-xs text-muted-foreground">{description}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
