"use client";

import React, { useState } from "react";
import { Terminal, ExternalLink, Code2, Copy, Check, ChevronDown, MonitorPlay } from "lucide-react";
import { Button } from "@/components/ui/button";

export function IdeLink() {
  const [copied, setCopied] = useState(false);
  const [activeIde, setActiveIde] = useState<"vscode" | "cursor" | "jetbrains">("vscode");
  const [showDropdown, setShowDropdown] = useState(false);

  // Deep Link templates for Daytona sandbox integration
  const VSCODE_DEEP_LINK = "vscode://vscode-remote/ssh-remote+daytona-uom@localhost:2222/home/daytona/uom-workspace";
  const CURSOR_DEEP_LINK = "cursor://vscode-remote/ssh-remote+daytona-uom@localhost:2222/home/daytona/uom-workspace";
  const JETBRAINS_DEEP_LINK = "jetbrains-gateway://connect/ssh?host=localhost&port=2222&user=daytona&projectPath=/home/daytona/uom-workspace";
  
  const sshCommand = "ssh daytona-uom@localhost -p 2222";

  const handleCopySsh = () => {
    navigator.clipboard.writeText(sshCommand);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const getDeepLink = () => {
    if (activeIde === "vscode") return VSCODE_DEEP_LINK;
    if (activeIde === "cursor") return CURSOR_DEEP_LINK;
    return JETBRAINS_DEEP_LINK;
  };

  const getIdeLabel = () => {
    if (activeIde === "vscode") return "VS Code";
    if (activeIde === "cursor") return "Cursor";
    return "JetBrains Gateway";
  };

  return (
    <div className="relative flex items-center gap-2">
      {/* Dropdown Toggle */}
      <div className="flex items-center bg-slate-900 border border-slate-800 rounded-lg overflow-hidden h-8">
        <a
          href={getDeepLink()}
          target="_blank"
          rel="noreferrer"
          className="flex items-center gap-1.5 px-3 h-full hover:bg-slate-850 text-indigo-400 hover:text-indigo-300 text-xs font-semibold border-r border-slate-800/60 transition-colors"
          title={`Launch Daytona sandbox in ${getIdeLabel()}`}
        >
          <Code2 className="size-3.5" />
          <span>Remote IDE: {getIdeLabel()}</span>
          <ExternalLink className="size-3 shrink-0" />
        </a>

        <button
          type="button"
          onClick={() => setShowDropdown(prev => !prev)}
          className="px-2 h-full hover:bg-slate-850 text-slate-500 hover:text-slate-300 transition-colors"
        >
          <ChevronDown className="size-3.5" />
        </button>
      </div>

      {/* Dropdown Options */}
      {showDropdown && (
        <div className="absolute right-0 top-10 w-52 bg-slate-950 border border-slate-800 rounded-lg shadow-xl py-1 z-50 animate-in fade-in slide-in-from-top-1 duration-150">
          <span className="px-3 py-1.5 text-[9px] text-slate-500 uppercase font-bold tracking-wider block">Select Gateway</span>
          
          <button
            type="button"
            onClick={() => {
              setActiveIde("vscode");
              setShowDropdown(false);
            }}
            className={`w-full text-left px-3 py-1.5 text-xs transition-colors flex items-center justify-between ${
              activeIde === "vscode" ? "bg-indigo-600/10 text-indigo-400 font-semibold" : "text-slate-400 hover:bg-slate-900 hover:text-slate-200"
            }`}
          >
            <span>VS Code Remote</span>
            <span className="text-[9px] text-slate-500 font-mono">vscode://</span>
          </button>

          <button
            type="button"
            onClick={() => {
              setActiveIde("cursor");
              setShowDropdown(false);
            }}
            className={`w-full text-left px-3 py-1.5 text-xs transition-colors flex items-center justify-between ${
              activeIde === "cursor" ? "bg-indigo-600/10 text-indigo-400 font-semibold" : "text-slate-400 hover:bg-slate-900 hover:text-slate-200"
            }`}
          >
            <span>Cursor Remote</span>
            <span className="text-[9px] text-slate-500 font-mono">cursor://</span>
          </button>

          <button
            type="button"
            onClick={() => {
              setActiveIde("jetbrains");
              setShowDropdown(false);
            }}
            className={`w-full text-left px-3 py-1.5 text-xs transition-colors flex items-center justify-between ${
              activeIde === "jetbrains" ? "bg-indigo-600/10 text-indigo-400 font-semibold" : "text-slate-400 hover:bg-slate-900 hover:text-slate-200"
            }`}
          >
            <span>JetBrains Gateway</span>
            <span className="text-[9px] text-slate-500 font-mono">jetbrains://</span>
          </button>

          <hr className="border-slate-900 my-1" />

          {/* SSH Copy Button inside dropdown */}
          <div className="p-2">
            <button
              type="button"
              onClick={handleCopySsh}
              className="w-full bg-slate-900 hover:bg-slate-850 border border-slate-800 text-[10px] text-slate-300 font-mono rounded p-1.5 flex items-center justify-between transition-all"
            >
              <span className="truncate mr-2">{sshCommand}</span>
              {copied ? <Check className="size-3 text-emerald-400 shrink-0" /> : <Copy className="size-3 shrink-0" />}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
