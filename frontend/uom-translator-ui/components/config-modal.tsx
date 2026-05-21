"use client";

import React, { useState, useEffect } from "react";
import { 
  Dialog, 
  DialogContent, 
  DialogHeader, 
  DialogTitle,
  DialogDescription,
  DialogFooter
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { 
  Settings, 
  Database, 
  Cpu, 
  Terminal, 
  HelpCircle, 
  CheckCircle,
  ExternalLink,
  BookOpen,
  Info
} from "lucide-react";

export interface UomConfig {
  ollamaHost: string;
  model: string;
  openaiApiUrl: string;
  openaiApiKey: string;
  mssqlConnectionString: string;
  mongodbUri: string;
  neo4jUri: string;
  neo4jPassword: string;
  daytonaTimeout: number;
}

const DEFAULT_CONFIG: UomConfig = {
  ollamaHost: "http://localhost:11434",
  model: "ollama/qwen3-coder:30b",
  openaiApiUrl: "https://einfra.net/v1",
  openaiApiKey: "",
  mssqlConnectionString: "Server=localhost;Database=uom_relational;User Id=sa;Password=YourStrongPass123!;",
  mongodbUri: "mongodb://localhost:27017/uom_document",
  neo4jUri: "bolt://localhost:7687",
  neo4jPassword: "neo4jpassword",
  daytonaTimeout: 300,
};

interface ConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (config: UomConfig) => void;
}

export function ConfigModal({ isOpen, onClose, onSave }: ConfigModalProps) {
  const [config, setConfig] = useState<UomConfig>(DEFAULT_CONFIG);
  const [activeTab, setActiveTab] = useState<"onboarding" | "llm" | "db" | "daytona">("onboarding");
  const [saveSuccess, setSaveSuccess] = useState(false);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("uom_translator_config");
      if (saved) {
        try {
          setConfig({ ...DEFAULT_CONFIG, ...JSON.parse(saved) });
        } catch (e) {
          console.error("Error reading saved config", e);
        }
      }
    }
  }, [isOpen]);

  const handleChange = (key: keyof UomConfig, value: any) => {
    setConfig(prev => ({
      ...prev,
      [key]: value
    }));
  };

  const handleSave = () => {
    localStorage.setItem("uom_translator_config", JSON.stringify(config));
    localStorage.setItem("uom_config_onboarded", "true");
    setSaveSuccess(true);
    setTimeout(() => {
      setSaveSuccess(false);
      onSave(config);
      onClose();
    }, 800);
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => { if (!open) onClose(); }}>
      <DialogContent className="max-w-3xl bg-slate-900 border border-slate-800 text-slate-100 shadow-2xl p-0 overflow-hidden rounded-xl">
        <div className="flex h-[550px]">
          {/* Sidebar Nav */}
          <div className="w-1/4 bg-slate-950 border-r border-slate-800/60 p-4 flex flex-col justify-between">
            <div className="space-y-1">
              <div className="flex items-center gap-2 px-2 py-3 mb-2">
                <div className="size-6 rounded-lg bg-indigo-600 flex items-center justify-center text-xs font-bold text-white shadow-lg shadow-indigo-600/30">
                  UOM
                </div>
                <span className="font-semibold text-sm tracking-wide text-indigo-400">Settings Hub</span>
              </div>
              
              <button
                type="button"
                onClick={() => setActiveTab("onboarding")}
                className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-left text-xs font-medium transition-all ${
                  activeTab === "onboarding"
                    ? "bg-indigo-600/15 text-indigo-400 border border-indigo-500/20"
                    : "text-slate-400 hover:bg-slate-900 hover:text-slate-200 border border-transparent"
                }`}
              >
                <BookOpen className="size-4" />
                <span>Onboarding Guide</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab("llm")}
                className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-left text-xs font-medium transition-all ${
                  activeTab === "llm"
                    ? "bg-indigo-600/15 text-indigo-400 border border-indigo-500/20"
                    : "text-slate-400 hover:bg-slate-900 hover:text-slate-200 border border-transparent"
                }`}
              >
                <Cpu className="size-4" />
                <span>LLM Settings</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab("db")}
                className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-left text-xs font-medium transition-all ${
                  activeTab === "db"
                    ? "bg-indigo-600/15 text-indigo-400 border border-indigo-500/20"
                    : "text-slate-400 hover:bg-slate-900 hover:text-slate-200 border border-transparent"
                }`}
              >
                <Database className="size-4" />
                <span>Database URIs</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab("daytona")}
                className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-left text-xs font-medium transition-all ${
                  activeTab === "daytona"
                    ? "bg-indigo-600/15 text-indigo-400 border border-indigo-500/20"
                    : "text-slate-400 hover:bg-slate-900 hover:text-slate-200 border border-transparent"
                }`}
              >
                <Terminal className="size-4" />
                <span>Daytona Sandbox</span>
              </button>
            </div>

            <div className="px-2 py-3 bg-slate-900/60 rounded-lg border border-slate-800/40">
              <span className="text-[10px] text-slate-500 block uppercase font-semibold mb-1">Status</span>
              <div className="flex items-center gap-1.5 text-xs text-emerald-400 font-medium">
                <span className="size-1.5 rounded-full bg-emerald-500 pulse-dot"></span>
                System Configured
              </div>
            </div>
          </div>

          {/* Main Pane */}
          <div className="flex-1 flex flex-col min-h-0 bg-slate-900/40">
            <div className="flex-1 p-6 overflow-y-auto custom-scrollbar">
              {activeTab === "onboarding" && (
                <div className="space-y-5">
                  <div>
                    <h2 className="text-lg font-semibold text-slate-100 flex items-center gap-2">
                      <span>🚀 Getting Started with UOM</span>
                    </h2>
                    <p className="text-slate-400 text-xs mt-1">
                      Migrate Relational schema/queries to Spring Data MongoDB &amp; Neo4j.
                    </p>
                  </div>

                  <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-lg space-y-2">
                    <div className="flex items-center gap-2 text-amber-400 text-xs font-semibold">
                      <Info className="size-4 shrink-0" />
                      <span>CRITICAL PREREQUISITE</span>
                    </div>
                    <p className="text-[11px] text-slate-300 leading-relaxed">
                      Your database environments <strong>MUST be set up and running</strong> before the orchestrator can execute translations. The orchestrator connects directly to them to inspect schemas, build mapping rules, and run live query verification tests.
                    </p>
                  </div>

                  <div className="space-y-3">
                    <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Useful References &amp; Commands</h3>
                    
                    <div className="space-y-2 text-xs">
                      <div className="flex items-start justify-between gap-3 p-3 bg-slate-950/60 rounded-lg border border-slate-800/50">
                        <div>
                          <span className="font-medium text-slate-200 block">Universal-Object-Mapping Repository</span>
                          <span className="text-[10px] text-slate-400 block mt-0.5">Contains all docker-compose stacks and environment scripts.</span>
                        </div>
                        <a 
                          href="https://github.com/corovcam/Universal-Object-Mapping" 
                          target="_blank" 
                          rel="noreferrer" 
                          className="text-indigo-400 hover:text-indigo-300 flex items-center gap-1 font-semibold shrink-0"
                        >
                          Repo <ExternalLink className="size-3" />
                        </a>
                      </div>

                      <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800/50 space-y-2">
                        <span className="font-medium text-slate-200 block">Neo4j ETL UI tool setup</span>
                        <span className="text-[10px] text-slate-400 block leading-relaxed">
                          We utilize the official <strong>Neo4j ETL Tool UI</strong>. Follow the documentation below to extract relational schemas and import target Spring graph mappings smoothly:
                        </span>
                        <a 
                          href="https://neo4j.com/developer/neo4j-etl/" 
                          target="_blank" 
                          rel="noreferrer" 
                          className="inline-flex items-center gap-1 text-[11px] text-indigo-400 hover:text-indigo-300 font-semibold"
                        >
                          Neo4j ETL Docs <ExternalLink className="size-3" />
                        </a>
                      </div>

                      <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800/50 space-y-1.5">
                        <span className="font-medium text-slate-200 block">Quick Start DB Cluster</span>
                        <p className="text-[10px] text-slate-400">Run this inside the workspace root to boot up SQL Server, Redis, MongoDB, and Neo4j:</p>
                        <div className="bg-slate-900 p-2 rounded font-mono text-[10px] text-indigo-300 border border-slate-800 select-all">
                          docker compose up -d
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {activeTab === "llm" && (
                <div className="space-y-4">
                  <div>
                    <h2 className="text-sm font-bold text-slate-200">LLM Orchestration Settings</h2>
                    <p className="text-slate-400 text-[11px]">Specify backend model selectors and API endpoints.</p>
                  </div>

                  <div className="space-y-3">
                    <div className="space-y-1">
                      <label className="text-[11px] font-semibold text-slate-300 block">Ollama Endpoint URL</label>
                      <input 
                        type="text" 
                        value={config.ollamaHost}
                        onChange={(e) => handleChange("ollamaHost", e.target.value)}
                        className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs focus:outline-none focus:border-indigo-500 font-mono text-slate-300"
                        placeholder="e.g. http://localhost:11434"
                      />
                    </div>

                    <div className="space-y-1">
                      <label className="text-[11px] font-semibold text-slate-300 block">Target Translation LLM Model</label>
                      <input 
                        type="text" 
                        value={config.model}
                        onChange={(e) => handleChange("model", e.target.value)}
                        className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs focus:outline-none focus:border-indigo-500 font-mono text-slate-300"
                        placeholder="ollama/qwen3-coder:30b"
                      />
                      <span className="text-[10px] text-slate-500 block">Must match the provider/name paradigm (e.g. einfra/kimi-k2.6 or ollama/qwen3-coder:30b).</span>
                    </div>

                    <hr className="border-slate-800" />

                    <div className="space-y-1">
                      <label className="text-[11px] font-semibold text-slate-300 block">E-Infra API Base URL (Optional)</label>
                      <input 
                        type="text" 
                        value={config.openaiApiUrl}
                        onChange={(e) => handleChange("openaiApiUrl", e.target.value)}
                        className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs focus:outline-none focus:border-indigo-500 font-mono text-slate-300"
                        placeholder="https://einfra.net/v1"
                      />
                    </div>

                    <div className="space-y-1">
                      <label className="text-[11px] font-semibold text-slate-300 block">E-Infra API Secret Token</label>
                      <input 
                        type="password" 
                        value={config.openaiApiKey}
                        onChange={(e) => handleChange("openaiApiKey", e.target.value)}
                        className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs focus:outline-none focus:border-indigo-500 font-mono text-slate-300"
                        placeholder="Enter API key"
                      />
                    </div>
                  </div>
                </div>
              )}

              {activeTab === "db" && (
                <div className="space-y-4">
                  <div>
                    <h2 className="text-sm font-bold text-slate-200">Database Connection Mappings</h2>
                    <p className="text-slate-400 text-[11px]">Define URIs where target databases and caches reside.</p>
                  </div>

                  <div className="space-y-3">
                    <div className="space-y-1">
                      <label className="text-[11px] font-semibold text-slate-300 block">MS SQL Server Connection String</label>
                      <textarea 
                        value={config.mssqlConnectionString}
                        onChange={(e) => handleChange("mssqlConnectionString", e.target.value)}
                        rows={2}
                        className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs focus:outline-none focus:border-indigo-500 font-mono text-slate-300 resize-none"
                      />
                    </div>

                    <div className="space-y-1">
                      <label className="text-[11px] font-semibold text-slate-300 block">MongoDB target URI</label>
                      <input 
                        type="text" 
                        value={config.mongodbUri}
                        onChange={(e) => handleChange("mongodbUri", e.target.value)}
                        className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs focus:outline-none focus:border-indigo-500 font-mono text-slate-300"
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-1">
                        <label className="text-[11px] font-semibold text-slate-300 block">Neo4j target URI</label>
                        <input 
                          type="text" 
                          value={config.neo4jUri}
                          onChange={(e) => handleChange("neo4jUri", e.target.value)}
                          className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs focus:outline-none focus:border-indigo-500 font-mono text-slate-300"
                        />
                      </div>
                      <div className="space-y-1">
                        <label className="text-[11px] font-semibold text-slate-300 block">Neo4j Database Password</label>
                        <input 
                          type="password" 
                          value={config.neo4jPassword}
                          onChange={(e) => handleChange("neo4jPassword", e.target.value)}
                          className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs focus:outline-none focus:border-indigo-500 font-mono text-slate-300"
                        />
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {activeTab === "daytona" && (
                <div className="space-y-4">
                  <div>
                    <h2 className="text-sm font-bold text-slate-200">Daytona Dev Sandbox</h2>
                    <p className="text-slate-400 text-[11px]">Define compiler timeouts and Daytona workspace rules.</p>
                  </div>

                  <div className="space-y-3">
                    <div className="space-y-1">
                      <label className="text-[11px] font-semibold text-slate-300 block">Sandbox Build Timeout (seconds)</label>
                      <input 
                        type="number" 
                        value={config.daytonaTimeout}
                        onChange={(e) => handleChange("daytonaTimeout", Number(e.target.value))}
                        className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs focus:outline-none focus:border-indigo-500 font-mono text-slate-300"
                      />
                      <span className="text-[10px] text-slate-500 block">Time allowed for .NET and Spring compilation &amp; verification runs inside the container.</span>
                    </div>

                    <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800/40 text-xs leading-relaxed space-y-2">
                      <div className="flex items-center gap-1.5 text-indigo-400 font-semibold text-[11px]">
                        <Terminal className="size-3.5" />
                        <span>Daytona Local Sandbox Sandbox Mode</span>
                      </div>
                      <p className="text-slate-400 text-[10px]">
                        Daytona is automatically loaded and configured in the devcontainer environment. Target compilation builds run securely in parallel sandbox environments to ensure generated C# queries and target Java spring mappings build successfully before comparing data equivalence.
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Footer Buttons */}
            <div className="p-4 bg-slate-950/80 border-t border-slate-800/80 flex items-center justify-between">
              <span className="text-[10px] text-slate-500">Universal Object Mapping Translator v0.1</span>
              <div className="flex items-center gap-2">
                <Button 
                  variant="outline" 
                  onClick={onClose}
                  className="bg-slate-900 border-slate-800 text-slate-300 hover:bg-slate-800 hover:text-slate-100 text-xs px-3 h-8"
                >
                  Cancel
                </Button>
                <Button 
                  onClick={handleSave}
                  disabled={saveSuccess}
                  className="bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs px-4 h-8 flex items-center gap-1.5 shadow-lg shadow-indigo-600/20"
                >
                  {saveSuccess ? (
                    <>
                      <CheckCircle className="size-3.5 animate-bounce" />
                      <span>Saved!</span>
                    </>
                  ) : (
                    <>
                      <Settings className="size-3.5" />
                      <span>Save Mappings</span>
                    </>
                  )}
                </Button>
              </div>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
