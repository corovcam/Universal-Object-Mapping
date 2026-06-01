"use client";

import { ConfigModal } from "@/components/config-modal";
import { IdeLink } from "@/components/ide-link";
import { Button } from "@/components/ui/button";
import { FolderGit, Settings } from "lucide-react";
import type { FC } from "react";
import { useState } from "react";
import { ThreadList } from "./thread-list";

export const ThreadListSidebar: FC = () => {
  const [isConfigOpen, setIsConfigOpen] = useState(false);

  return (
    <aside className="flex w-64 flex-col border-r bg-background text-foreground">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-3 border-b">
        <div className="flex items-center gap-2">
          <FolderGit className="size-4 text-primary" />
          <span className="text-xs font-semibold uppercase tracking-wider">Sessions</span>
        </div>
      </div>

      {/* Thread list */}
      <div className="flex-1 overflow-y-auto px-2 py-2 min-h-0">
        <ThreadList />
      </div>

      {/* Footer: Settings + IDE Link */}
      <div className="flex flex-col gap-2 border-t p-3">
        <IdeLink />
        <Button
          variant="outline"
          size="sm"
          onClick={() => setIsConfigOpen(true)}
          className="w-full justify-start gap-2 text-xs"
        >
          <Settings className="size-3.5" />
          Settings
        </Button>
      </div>

      <ConfigModal
        isOpen={isConfigOpen}
        onClose={() => setIsConfigOpen(false)}
        onSave={() => setIsConfigOpen(false)}
      />
    </aside>
  );
};
