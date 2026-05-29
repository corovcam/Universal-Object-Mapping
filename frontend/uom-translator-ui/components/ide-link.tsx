"use client";

import { FrameworkType, LanguageType } from "@/lib/types";
import { getFrameworkTypeByName } from "@/lib/utils";
import { Check, ChevronDown, Code2, Copy, ExternalLink, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";

export enum SupportedIDEs {
  vscode = "vscode",
  cursor = "cursor",
  jetbrains = "jetbrains",
}

export interface SandboxInfo {
  framework: FrameworkType | null;
  sandboxId: string;
  sshCommand: string;
  token: string;
}

export function IdeLink({ graphState }: { graphState: any }) {
  const [copied, setCopied] = useState(false);
  const [activeIde, setActiveIde] = useState<SupportedIDEs>(SupportedIDEs.vscode);
  const [showDropdown, setShowDropdown] = useState(false);

  const [activePlatform, setActivePlatform] = useState<LanguageType>(LanguageType.JAVA);
  const [loading, setLoading] = useState(false);
  const [sandboxInfo, setSandboxInfo] = useState<SandboxInfo | null>(null);

  const sourceFramework = graphState?.source_target ? getFrameworkTypeByName(graphState.source_target) : FrameworkType.DOTNET_EFCORE;
  const destFramework = graphState?.destination_target ? getFrameworkTypeByName(graphState.destination_target) : FrameworkType.JAVA_SPRING_DATA_MONGODB;
  const activeFramework = activePlatform === LanguageType.DOTNET ? sourceFramework : destFramework;

  const fetchSandboxSsh = async () => {
    setLoading(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_LANGGRAPH_API_URL || "http://localhost:2024";
      
      // 1. Fetch sandbox for framework
      const sandboxRes = await fetch(`${apiUrl}/sandboxes/framework/${activeFramework}`);
      // const sandboxRes = await fetch(`${apiUrl}/sandboxes/framework/${activeFramework}`, { cache: "force-cache", "next": { revalidate: 900 } });
      if (!sandboxRes.ok) throw new Error(`Failed to fetch sandbox: ${sandboxRes.status} ${sandboxRes.statusText} ${await sandboxRes.text()}`);
      const sandboxData = await sandboxRes.json();
      console.log(sandboxData)
      
      // 2. Post to create SSH token
      const tokenRes = await fetch(`${apiUrl}/sandbox/${sandboxData.id}/ssh-token`, { method: "POST" });
      // const tokenRes = await fetch(`${apiUrl}/sandbox/${sandboxData.id}/ssh-token`, { cache: "force-cache", "next": { revalidate: 900 } });
      if (!tokenRes.ok) throw new Error(`Failed to create SSH token: ${tokenRes.status} ${tokenRes.statusText} ${await tokenRes.text()}`);
      const tokenData = await tokenRes.json();
      console.log(tokenData)
      
      setSandboxInfo({
        framework: activeFramework,
        sandboxId: sandboxData.id,
        sshCommand: tokenData.ssh_command,
        token: tokenData.token
      });
    } catch (err) {
      console.error("Failed fetching sandbox SSH credentials from API", err);
      setSandboxInfo(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSandboxSsh();
  }, [activeFramework]);

  // Parse SSH command to construct dynamic deep links
  const parseSshCommand = (cmd?: string, token?: string) => {
    let user = null;
    let host = "localhost";
    let port = "2222";

    if (!cmd && !token) return { user, host, port };

    // Matches ssh username@host -p port or similar formats
    const match = cmd?.match(/ssh\s+(?:\s+-p\s+(\d+))?\s+([^@\s]+)@([^\s]+)/);
    if (match) {
      if (match[1]) {
        port = match[1];
      }
      user = match[2];
      host = match[3];
    }
    if (!user) user = token ?? null;
    return { user, host, port };
  };

  const { user, host, port } = parseSshCommand(sandboxInfo?.sshCommand, sandboxInfo?.token);

  // Dynamic deep links
  const VSCODE_DEEP_LINK = `vscode://vscode-remote/ssh-remote+${user}@${host}:${port}/sandbox`;
  const CURSOR_DEEP_LINK = `cursor://vscode-remote/ssh-remote+${user}@${host}:${port}/sandbox`;
  const JETBRAINS_DEEP_LINK = `jetbrains-gateway://connect/ssh?host=${host}&port=${port}&user=${user}&projectPath=/sandbox`;
  
  const displaySshCommand = sandboxInfo?.sshCommand || `ssh ${user}@${host} -p ${port}`;

  const handleCopySsh = () => {
    navigator.clipboard.writeText(displaySshCommand);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const getDeepLink = () => {
    if (activeIde === SupportedIDEs.vscode) return VSCODE_DEEP_LINK;
    if (activeIde === SupportedIDEs.cursor) return CURSOR_DEEP_LINK;
    return JETBRAINS_DEEP_LINK;
  };

  const getIdeLabel = () => {
    if (activeIde === SupportedIDEs.vscode) return "VS Code";
    if (activeIde === SupportedIDEs.cursor) return "Cursor";
    return "JetBrains Gateway";
  };

  return (
    <div className="relative flex items-center gap-2">
      {/* Platform Sandbox Switcher */}
      <div className={`flex items-center bg-slate-900 border border-slate-800 rounded-lg overflow-hidden h-8 p-0.5 ${!sandboxInfo ? "opacity-55" : ""}`}>
        <button
          type="button"
          onClick={() => setActivePlatform(LanguageType.DOTNET)}
          className={`px-2.5 h-full rounded text-[10px] font-bold tracking-wide uppercase transition-all ${
            activePlatform === LanguageType.DOTNET
              ? "bg-indigo-600/15 border border-indigo-500/20 text-indigo-400 font-bold"
              : "text-slate-500 hover:text-slate-350"
          }`}
          title={`Source Sandbox: ${sourceFramework}`}
        >
          .NET
        </button>
        <button
          type="button"
          onClick={() => setActivePlatform(LanguageType.JAVA)}
          className={`px-2.5 h-full rounded text-[10px] font-bold tracking-wide uppercase transition-all ${
            activePlatform === LanguageType.JAVA
              ? "bg-indigo-600/15 border border-indigo-500/20 text-indigo-400 font-bold"
              : "text-slate-500 hover:text-slate-350"
          }`}
          title={`Target Sandbox: ${destFramework}`}
        >
          Java
        </button>

      {/* Dropdown Toggle */}
        <a
          href={sandboxInfo ? getDeepLink() : undefined}
          target={sandboxInfo ? "_blank" : undefined}
          rel="noreferrer"
          className={`flex items-center gap-1.5 px-3 h-full text-xs font-semibold border-r border-slate-800/60 transition-colors ${
            sandboxInfo 
              ? "text-indigo-400 hover:text-indigo-300 hover:bg-slate-850 cursor-pointer" 
              : "text-slate-500 cursor-not-allowed pointer-events-none"
          }`}
          title={sandboxInfo ? `Launch Daytona sandbox in ${getIdeLabel()} (${activeFramework})` : "Sandbox connection unavailable"}
        >
          {loading ? (
            <RefreshCw className="size-3.5 animate-spin text-slate-500" />
          ) : (
            <Code2 className="size-3.5" />
          )}
          <span>Remote IDE: {getIdeLabel()}</span>
          <ExternalLink className="size-3 shrink-0" />
        </a>
        <button
          type="button"
          onClick={() => { if (sandboxInfo) setShowDropdown(prev => !prev); }}
          disabled={!sandboxInfo}
          className={`px-2 h-full text-slate-500 transition-colors ${
            sandboxInfo 
              ? "hover:bg-slate-850 hover:text-slate-300 cursor-pointer" 
              : "cursor-not-allowed"
          }`}
        >
          <ChevronDown className="size-3.5" />
        </button>
      </div>

      {/* Dropdown Options */}
      {showDropdown && (
        <div className="absolute right-0 top-10 w-56 bg-slate-950 border border-slate-800 rounded-lg shadow-xl py-1.5 z-50 animate-in fade-in slide-in-from-top-1 duration-150">
          <div className="px-3 py-1 flex items-center justify-between border-b border-slate-900 pb-1.5 mb-1">
            <span className="text-[9px] text-slate-500 uppercase font-bold tracking-wider block">Select Gateway</span>
            <button 
              type="button"
              onClick={fetchSandboxSsh} 
              className="text-[9px] text-indigo-400 hover:text-indigo-300 font-semibold flex items-center gap-0.5"
              title="Force Refresh Token"
            >
              <RefreshCw className="size-2.5" />
              <span>Refresh</span>
            </button>
          </div>
          
          <button
            type="button"
            onClick={() => {
              setActiveIde(SupportedIDEs.vscode);
              setShowDropdown(false);
            }}
            className={`w-full text-left px-3 py-1.5 text-xs transition-colors flex items-center justify-between ${
              activeIde === SupportedIDEs.vscode ? "bg-indigo-600/10 text-indigo-400 font-semibold" : "text-slate-400 hover:bg-slate-900 hover:text-slate-200"
            }`}
          >
            <span>VS Code Remote</span>
            <span className="text-[9px] text-slate-500 font-mono">vscode://</span>
          </button>

          <button
            type="button"
            onClick={() => {
              setActiveIde(SupportedIDEs.cursor);
              setShowDropdown(false);
            }}
            className={`w-full text-left px-3 py-1.5 text-xs transition-colors flex items-center justify-between ${
              activeIde === SupportedIDEs.cursor ? "bg-indigo-600/10 text-indigo-400 font-semibold" : "text-slate-400 hover:bg-slate-900 hover:text-slate-200"
            }`}
          >
            <span>Cursor Remote</span>
            <span className="text-[9px] text-slate-500 font-mono">cursor://</span>
          </button>

          <button
            type="button"
            onClick={() => {
              setActiveIde(SupportedIDEs.jetbrains);
              setShowDropdown(false);
            }}
            className={`w-full text-left px-3 py-1.5 text-xs transition-colors flex items-center justify-between ${
              activeIde === SupportedIDEs.jetbrains ? "bg-indigo-600/10 text-indigo-400 font-semibold" : "text-slate-400 hover:bg-slate-900 hover:text-slate-200"
            }`}
          >
            <span>JetBrains Gateway</span>
            <span className="text-[9px] text-slate-500 font-mono">jetbrains://</span>
          </button>

          <hr className="border-slate-900 my-1.5" />

          {/* SSH Copy Button inside dropdown */}
          <div className="px-2 pb-1">
            <span className="text-[8px] text-slate-500 font-bold uppercase tracking-wider block px-1 mb-1">Raw SSH Access Command</span>
            <button
              type="button"
              onClick={handleCopySsh}
              className="w-full bg-slate-900 hover:bg-slate-850 border border-slate-800 text-[10px] text-slate-350 font-mono rounded p-1.5 flex items-center justify-between transition-all"
              title="Click to copy full command with dynamic token"
            >
              <span className="truncate mr-2 text-[9px]">{displaySshCommand}</span>
              {copied ? <Check className="size-3 text-emerald-400 shrink-0" /> : <Copy className="size-3 text-indigo-400 shrink-0" />}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
