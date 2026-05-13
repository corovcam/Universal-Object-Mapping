"use client";

import { cn } from "@/lib/utils";
import { 
  FileText, 
  CheckCircle, 
  Loader2, 
  AlertCircle, 
  Sparkles,
  Code,
  Lightbulb
} from "lucide-react";
import type { AgentStatus } from "@/lib/types";

interface StatusBadgeProps {
  status: AgentStatus;
  label: string;
  isActive?: boolean;
  className?: string;
}

const statusConfig: Record<AgentStatus, {
  icon: React.ComponentType<{ className?: string }>;
  bgClass: string;
  textClass: string;
  iconClass: string;
}> = {
  fetching_docs: {
    icon: FileText,
    bgClass: "bg-info/15 border-info/30",
    textClass: "text-info",
    iconClass: "text-info",
  },
  validating_java: {
    icon: Code,
    bgClass: "bg-warning/15 border-warning/30",
    textClass: "text-warning",
    iconClass: "text-warning",
  },
  validating_dotnet: {
    icon: Code,
    bgClass: "bg-warning/15 border-warning/30",
    textClass: "text-warning",
    iconClass: "text-warning",
  },
  generating: {
    icon: Sparkles,
    bgClass: "bg-primary/15 border-primary/30",
    textClass: "text-primary",
    iconClass: "text-primary",
  },
  thinking: {
    icon: Lightbulb,
    bgClass: "bg-accent border-border",
    textClass: "text-foreground",
    iconClass: "text-muted-foreground",
  },
  complete: {
    icon: CheckCircle,
    bgClass: "bg-success/15 border-success/30",
    textClass: "text-success",
    iconClass: "text-success",
  },
  error: {
    icon: AlertCircle,
    bgClass: "bg-destructive/15 border-destructive/30",
    textClass: "text-destructive",
    iconClass: "text-destructive",
  },
};

export function StatusBadge({ 
  status, 
  label, 
  isActive = false,
  className 
}: StatusBadgeProps) {
  const config = statusConfig[status];
  const Icon = config.icon;

  return (
    <div
      className={cn(
        "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border text-xs font-medium transition-all",
        config.bgClass,
        config.textClass,
        className
      )}
    >
      {isActive ? (
        <Loader2 className={cn("size-3 animate-spin", config.iconClass)} />
      ) : (
        <Icon className={cn("size-3", config.iconClass)} />
      )}
      <span>{label}</span>
    </div>
  );
}

interface StatusBadgeGroupProps {
  activities: Array<{
    id: string;
    status: AgentStatus;
    label: string;
    endTime?: number;
  }>;
  className?: string;
}

export function StatusBadgeGroup({ activities, className }: StatusBadgeGroupProps) {
  return (
    <div className={cn("flex flex-wrap items-center gap-2", className)}>
      {activities.map((activity) => (
        <StatusBadge
          key={activity.id}
          status={activity.status}
          label={activity.label}
          isActive={!activity.endTime}
        />
      ))}
    </div>
  );
}
