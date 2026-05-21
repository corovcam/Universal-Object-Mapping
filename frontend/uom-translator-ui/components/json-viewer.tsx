"use client";

import React, { useState } from "react";
import { ChevronRight, ChevronDown } from "lucide-react";

interface JsonViewerProps {
  data: any;
  depth?: number;
  maxDepth?: number;
}

export function JsonViewer({ data, depth = 0, maxDepth = 2 }: JsonViewerProps) {
  const [isExpanded, setIsExpanded] = useState(depth < maxDepth);

  const isObject = data !== null && typeof data === "object";
  
  if (!isObject) {
    // Render primitive value
    if (typeof data === "string") {
      // Check if it contains newlines (like code snippets)
      if (data.includes("\n")) {
        return (
          <span className="text-emerald-400 font-mono whitespace-pre-wrap break-words select-text selection:bg-emerald-500/25">
            "{data}"
          </span>
        );
      }
      return <span className="text-emerald-400 font-mono select-text">"{data}"</span>;
    }
    if (typeof data === "number") {
      return <span className="text-amber-400 font-mono font-semibold select-text">{data}</span>;
    }
    if (typeof data === "boolean") {
      return <span className="text-purple-400 font-mono font-semibold select-text">{String(data)}</span>;
    }
    if (data === null) {
      return <span className="text-red-400 font-mono font-semibold select-text">null</span>;
    }
    return <span className="text-slate-350 font-mono select-text">{String(data)}</span>;
  }

  const isArray = Array.isArray(data);
  const keys = Object.keys(data);
  
  if (keys.length === 0) {
    return <span className="text-slate-500 font-mono">{isArray ? "[]" : "{}"}</span>;
  }

  const toggle = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsExpanded(!isExpanded);
  };

  return (
    <div className="font-mono text-xs select-text">
      {/* Trigger */}
      <span 
        onClick={toggle} 
        className="inline-flex items-center gap-1 cursor-pointer select-none text-slate-400 hover:text-slate-200"
      >
        {isExpanded ? (
          <ChevronDown className="size-3.5 text-slate-500 shrink-0" />
        ) : (
          <ChevronRight className="size-3.5 text-slate-500 shrink-0" />
        )}
        <span className="text-slate-500 font-semibold">{isArray ? `Array(${keys.length})` : "Object"}</span>
        <span className="text-slate-650 text-[10px]">
          {isExpanded ? "" : isArray ? "[...]" : "{...}"}
        </span>
      </span>

      {/* Children rendered lazily */}
      {isExpanded && (
        <div className="pl-4 border-l border-slate-800/85 my-1 space-y-1">
          {keys.map((key) => {
            const val = data[key];
            return (
              <div key={key} className="flex flex-col md:flex-row items-start gap-1 py-0.5">
                <span 
                  className="text-indigo-400 font-semibold shrink-0 cursor-pointer hover:text-indigo-300 select-none" 
                  onClick={toggle}
                >
                  {isArray ? `${key}:` : `"${key}":`}
                </span>
                <div className="flex-1 min-w-0">
                  <JsonViewer data={val} depth={depth + 1} maxDepth={maxDepth} />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
