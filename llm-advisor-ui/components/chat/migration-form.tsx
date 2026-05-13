"use client";

import { useState } from "react";
import { ChevronDown, Settings2 } from "lucide-react";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { SOURCE_FRAMEWORKS, TARGET_FRAMEWORKS, type MigrationConfig } from "@/lib/types";

interface MigrationFormProps {
  config: MigrationConfig;
  onConfigChange: (config: MigrationConfig) => void;
  defaultExpanded?: boolean;
  className?: string;
}

export function MigrationForm({
  config,
  onConfigChange,
  defaultExpanded = false,
  className,
}: MigrationFormProps) {
  const [isOpen, setIsOpen] = useState(defaultExpanded);

  const handleChange = <K extends keyof MigrationConfig>(
    key: K,
    value: MigrationConfig[K]
  ) => {
    onConfigChange({ ...config, [key]: value });
  };

  const selectedSource = SOURCE_FRAMEWORKS.find(f => f.id === config.sourceFramework);
  const selectedTarget = TARGET_FRAMEWORKS.find(f => f.id === config.destinationFramework);

  return (
    <Collapsible
      open={isOpen}
      onOpenChange={setIsOpen}
      className={cn("w-full", className)}
    >
      <CollapsibleTrigger asChild>
        <button
          className={cn(
            "flex items-center justify-between w-full px-4 py-3",
            "bg-muted/50 hover:bg-muted/80 transition-colors",
            "border-y border-border text-sm font-medium text-foreground"
          )}
        >
          <div className="flex items-center gap-2">
            <Settings2 className="size-4 text-muted-foreground" />
            <span>Structured Migration</span>
          </div>
          <ChevronDown
            className={cn(
              "size-4 text-muted-foreground transition-transform",
              isOpen && "rotate-180"
            )}
          />
        </button>
      </CollapsibleTrigger>

      <CollapsibleContent>
        <div className="p-4 space-y-4 bg-card/50 border-b border-border">
          {/* Translation Type */}
          <div className="space-y-2">
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Translation Type
            </label>
            <Select
              value={config.translationType}
              onValueChange={(value) => handleChange("translationType", value as MigrationConfig["translationType"])}
            >
              <SelectTrigger className="w-full bg-input border-border">
                <SelectValue placeholder="Select type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="schema">Schema</SelectItem>
                <SelectItem value="query">Query</SelectItem>
                <SelectItem value="both">Both</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Source Framework Row */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                Source Framework
              </label>
              <Select
                value={config.sourceFramework}
                onValueChange={(value) => handleChange("sourceFramework", value)}
              >
                <SelectTrigger className="w-full bg-input border-border">
                  <SelectValue placeholder="Select framework" />
                </SelectTrigger>
                <SelectContent>
                  {SOURCE_FRAMEWORKS.map((framework) => (
                    <SelectItem key={framework.id} value={framework.id}>
                      {framework.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                Version
              </label>
              <Input
                value={config.sourceVersion}
                onChange={(e) => handleChange("sourceVersion", e.target.value)}
                placeholder="e.g. 7.0"
                className="bg-input border-border"
              />
            </div>
          </div>

          {/* Destination Framework Row */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <label className="text-xs font-medium text-primary uppercase tracking-wide">
                Destination Framework
              </label>
              <Select
                value={config.destinationFramework}
                onValueChange={(value) => handleChange("destinationFramework", value)}
              >
                <SelectTrigger className="w-full bg-input border-border">
                  <SelectValue placeholder="Select framework" />
                </SelectTrigger>
                <SelectContent>
                  {TARGET_FRAMEWORKS.map((framework) => (
                    <SelectItem key={framework.id} value={framework.id}>
                      {framework.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                Version
              </label>
              <Input
                value={config.destinationVersion}
                onChange={(e) => handleChange("destinationVersion", e.target.value)}
                placeholder="e.g. 3.1"
                className="bg-input border-border"
              />
            </div>
          </div>

          {/* Source Schema Code */}
          {(config.translationType === "schema" || config.translationType === "both") && (
            <div className="space-y-2">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                Source Schema Code
              </label>
              <Textarea
                value={config.sourceSchemaCode || ""}
                onChange={(e) => handleChange("sourceSchemaCode", e.target.value)}
                placeholder="Paste schema here..."
                rows={5}
                className="bg-input border-border font-mono text-sm resize-y"
              />
            </div>
          )}

          {/* Source Query Code */}
          {(config.translationType === "query" || config.translationType === "both") && (
            <div className="space-y-2">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                Source Query Code
              </label>
              <Textarea
                value={config.sourceQueryCode || ""}
                onChange={(e) => handleChange("sourceQueryCode", e.target.value)}
                placeholder="Paste query here..."
                rows={5}
                className="bg-input border-border font-mono text-sm resize-y"
              />
            </div>
          )}

          {/* Summary Badge */}
          {selectedSource && selectedTarget && (
            <div className="flex items-center gap-2 pt-2">
              <span className="text-xs text-muted-foreground">Migration:</span>
              <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded bg-primary/10 border border-primary/20 text-xs font-medium text-primary">
                {selectedSource.name.split(" ").pop()} 
                <span className="text-muted-foreground">{"→"}</span>
                {selectedTarget.name.split(" ").pop()}
              </span>
            </div>
          )}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}
