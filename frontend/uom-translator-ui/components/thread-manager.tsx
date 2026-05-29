"use client";

import React, { useState } from "react";
import { MessageSquare, Plus, Trash2, FolderGit, ChevronLeft, ChevronRight, Terminal } from "lucide-react";
import { Button } from "@/components/ui/button";

export interface ThreadItem {
  id: string;
  title: string;
  createdAt: string;
}

interface ThreadManagerProps {
  currentThreadId: string | null;
  onSelectThread: (threadId: string) => void;
  onNewThread: () => Promise<void>;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  threads: ThreadItem[];
  onDeleteThread: (id: string) => void;
  serverActive: boolean;
}

export function ThreadManager({
  currentThreadId,
  onSelectThread,
  onNewThread,
  isCollapsed,
  onToggleCollapse,
  threads,
  onDeleteThread,
  serverActive,
}: ThreadManagerProps) {
  const [loading, setLoading] = useState(false);

  const handleCreateNew = async () => {
    setLoading(true);
    try {
      await onNewThread();
    } catch (e) {
      console.error("Error launching thread", e);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    onDeleteThread(id);
  };

  return (
    <div 
      className={`bg-slate-950 border-r border-slate-850 flex flex-col justify-between transition-all duration-300 ease-in-out h-full shrink-0 select-none overflow-hidden ${
        isCollapsed ? "w-16" : "w-64"
      }`}
    >
      <div className="flex-1 flex flex-col min-h-0">
        {/* Header */}
        <div className={`p-4 border-b border-slate-850 flex items-center shrink-0 ${
          isCollapsed ? "justify-center" : "justify-between"
        }`}>
          {!isCollapsed && (
            <div className="flex items-center gap-2">
              <FolderGit className="size-4.5 text-indigo-400" />
              <span className="font-semibold text-xs text-slate-200 tracking-wider uppercase">Sessions</span>
            </div>
          )}
          <Button
            size="icon"
            variant="ghost"
            onClick={onToggleCollapse}
            className={`size-7 text-slate-500 hover:bg-slate-900 hover:text-slate-300 ${
              isCollapsed ? "mx-auto" : ""
            }`}
            title={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {isCollapsed ? <ChevronRight className="size-4" /> : <ChevronLeft className="size-4" />}
          </Button>
        </div>

        {/* Start New Thread Button */}
        <div className="p-3 shrink-0">
          <Button
            onClick={handleCreateNew}
            disabled={loading}
            className={`bg-slate-900 hover:bg-slate-850 border border-slate-800 text-slate-200 font-semibold h-9 rounded-lg shadow-sm flex items-center transition-all duration-300 ${
              isCollapsed 
                ? "w-9 h-9 p-0 mx-auto justify-center" 
                : "w-full justify-start gap-2 text-xs px-3"
            }`}
            title="New Translation"
          >
            <Plus className="size-4 text-indigo-400 shrink-0" />
            {!isCollapsed && <span>New Translation</span>}
          </Button>
        </div>

        {/* Sessions List */}
        <div className="flex-1 overflow-y-auto px-2 py-1 space-y-1 custom-scrollbar min-h-0">
          {threads.length === 0 ? (
            <div className="text-center py-8 px-4">
              <MessageSquare className="size-6 text-slate-650 mx-auto mb-2 opacity-40" />
              {!isCollapsed && <p className="text-[10px] text-slate-500">No past migrations.</p>}
            </div>
          ) : (
            threads.map((t) => {
              const isActive = t.id === currentThreadId;
              return (
                <div
                  key={t.id}
                  onClick={() => onSelectThread(t.id)}
                  className={`group w-full flex items-center rounded-lg cursor-pointer text-xs transition-all border border-transparent ${
                    isActive
                      ? "bg-indigo-600/15 border border-indigo-500/25 text-slate-100 font-semibold"
                      : "text-slate-400 hover:bg-slate-900/60 hover:text-slate-200"
                  } ${
                    isCollapsed 
                      ? "justify-center p-2.5" 
                      : "justify-between px-3 py-2 gap-2"
                  }`}
                  title={t.title}
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <MessageSquare className={`size-3.5 shrink-0 ${isActive ? "text-indigo-400" : "text-slate-500"}`} />
                    {!isCollapsed && <span className="truncate font-medium">{t.title}</span>}
                  </div>
                  {!isCollapsed && (
                    <button
                      type="button"
                      onClick={(e) => handleDelete(t.id, e)}
                      className="size-5 rounded flex items-center justify-center text-slate-500 hover:bg-slate-800 hover:text-rose-400 opacity-0 group-hover:opacity-100 transition-opacity"
                      title="Delete session"
                    >
                      <Trash2 className="size-3" />
                    </button>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Footer Connection Status Info */}
      <div className="p-3 bg-slate-950 border-t border-slate-900 shrink-0">
        <div className={`p-2.5 bg-slate-900/60 rounded-lg border border-slate-850/60 flex items-center transition-all duration-300 ${
          isCollapsed ? "justify-center" : "gap-2.5"
        }`}>
          <Terminal className={`size-4 shrink-0 ${serverActive ? "text-emerald-400" : "text-rose-500 animate-pulse"}`} />
          {!isCollapsed && (
            <div className="min-w-0">
              <span className="text-[9px] text-slate-500 block uppercase font-bold tracking-wider leading-none">Connection</span>
              <span className={`text-[10px] font-semibold truncate block mt-0.5 ${serverActive ? "text-emerald-400" : "text-rose-500"}`}>
                {serverActive ? "LangGraph Active" : "Server Offline"}
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
