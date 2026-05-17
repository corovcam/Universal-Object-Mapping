"use client";

import { Sun, Moon, History, Maximize2, Minimize2, X, Boxes } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import type { ThemeMode } from "@/lib/types";

interface ChatHeaderProps {
  theme: ThemeMode;
  isMaximized: boolean;
  onThemeToggle: () => void;
  onHistoryToggle: () => void;
  onMaximizeToggle: () => void;
  onClose: () => void;
  className?: string;
}

export function ChatHeader({
  theme,
  isMaximized,
  onThemeToggle,
  onHistoryToggle,
  onMaximizeToggle,
  onClose,
  className,
}: ChatHeaderProps) {
  return (
    <header
      className={cn(
        "flex items-center justify-between px-4 py-3 border-b border-border bg-card/80 backdrop-blur-sm",
        className
      )}
    >
      {/* Logo and Title */}
      <div className="flex items-center gap-3">
        <div className="flex items-center justify-center size-8 rounded-lg bg-primary/10 border border-primary/20">
          <Boxes className="size-4 text-primary" />
        </div>
        <div className="flex flex-col">
          <h1 className="text-sm font-semibold text-foreground leading-tight">
            Universal Object
          </h1>
          <h2 className="text-sm font-semibold text-primary leading-tight">
            Framework Translation
          </h2>
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-1">
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              onClick={onThemeToggle}
              className="size-8 p-0 text-muted-foreground hover:text-foreground"
            >
              {theme === "dark" ? (
                <Sun className="size-4" />
              ) : (
                <Moon className="size-4" />
              )}
              <span className="sr-only">Toggle theme</span>
            </Button>
          </TooltipTrigger>
          <TooltipContent side="bottom">
            <p>Toggle theme</p>
          </TooltipContent>
        </Tooltip>

        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              onClick={onHistoryToggle}
              className="size-8 p-0 text-muted-foreground hover:text-foreground"
            >
              <History className="size-4" />
              <span className="sr-only">View history</span>
            </Button>
          </TooltipTrigger>
          <TooltipContent side="bottom">
            <p>View history</p>
          </TooltipContent>
        </Tooltip>

        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              onClick={onMaximizeToggle}
              className="size-8 p-0 text-muted-foreground hover:text-foreground"
            >
              {isMaximized ? (
                <Minimize2 className="size-4" />
              ) : (
                <Maximize2 className="size-4" />
              )}
              <span className="sr-only">
                {isMaximized ? "Minimize" : "Maximize"}
              </span>
            </Button>
          </TooltipTrigger>
          <TooltipContent side="bottom">
            <p>{isMaximized ? "Minimize" : "Maximize"}</p>
          </TooltipContent>
        </Tooltip>

        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
              className="size-8 p-0 text-muted-foreground hover:text-foreground"
            >
              <X className="size-4" />
              <span className="sr-only">Close</span>
            </Button>
          </TooltipTrigger>
          <TooltipContent side="bottom">
            <p>Close</p>
          </TooltipContent>
        </Tooltip>
      </div>
    </header>
  );
}
