"use client";

import React, { useState } from "react";
import { 
  Code, 
  Copy, 
  Check, 
  Download, 
  FileCode, 
  AlertTriangle, 
  CheckCircle,
  Database,
  Braces
} from "lucide-react";
import { Button } from "@/components/ui/button";

interface CodeComparisonProps {
  sourceSchema: string | null;
  translatedSchema: string | null;
  sourceQuery: string | null;
  translatedQuery: string | null;
  sourceHarness: string | null;
  translatedHarness: string | null;
  sourceTarget: string | null;
  destinationTarget: string | null;
  sourceValidationResults: any | null;
  targetValidationResults: any | null;
}

export function CodeComparison({
  sourceSchema,
  translatedSchema,
  sourceQuery,
  translatedQuery,
  sourceHarness,
  translatedHarness,
  sourceTarget,
  destinationTarget,
  sourceValidationResults,
  targetValidationResults,
}: CodeComparisonProps) {
  const [activeTab, setActiveTab] = useState<"schema" | "query" | "harness">("schema");
  const [copiedBlock, setCopiedBlock] = useState<string | null>(null);

  const handleCopy = (text: string | null, blockId: string) => {
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopiedBlock(blockId);
    setTimeout(() => setCopiedBlock(null), 1500);
  };

  const getSourceCode = () => {
    if (activeTab === "schema") return sourceSchema || "// No source C# schema loaded yet.";
    if (activeTab === "query") return sourceQuery || "// No source C# query loaded yet.";
    return sourceHarness || "// No source C# validation harness loaded yet.";
  };

  const getTargetCode = () => {
    if (activeTab === "schema") return translatedSchema || "// No translated Java schema loaded yet.";
    if (activeTab === "query") return translatedQuery || "// No translated Java query loaded yet.";
    return translatedHarness || "// No translated Java validation harness loaded yet.";
  };

  const hasSourceError = sourceValidationResults && sourceValidationResults.error;
  const hasTargetError = targetValidationResults && targetValidationResults.error;

  return (
    <div className="flex flex-col h-full bg-slate-900/20 border border-slate-800/80 rounded-xl overflow-hidden min-h-0">
      {/* Code Header Bar */}
      <div className="bg-slate-950/80 p-3 border-b border-slate-850 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-1.5 bg-slate-900 p-0.5 rounded-lg border border-slate-800">
          <button
            type="button"
            onClick={() => setActiveTab("schema")}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-semibold transition-all ${
              activeTab === "schema"
                ? "bg-indigo-600 text-white shadow-sm"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Database className="size-3.5" />
            <span>Schema Mappings</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("query")}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-semibold transition-all ${
              activeTab === "query"
                ? "bg-indigo-600 text-white shadow-sm"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Braces className="size-3.5" />
            <span>Queries &amp; Traversals</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("harness")}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-semibold transition-all ${
              activeTab === "harness"
                ? "bg-indigo-600 text-white shadow-sm"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <FileCode className="size-3.5" />
            <span>Full Harness</span>
          </button>
        </div>

        <div className="flex items-center gap-2">
          {/* Validation Badges */}
          <div className="flex gap-2">
            {sourceValidationResults && (
              <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold ${
                hasSourceError 
                  ? "bg-rose-500/10 text-rose-400 border border-rose-500/20" 
                  : "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
              }`}>
                {hasSourceError ? <AlertTriangle className="size-3" /> : <CheckCircle className="size-3" />}
                <span>.NET {hasSourceError ? "Error" : "Built"}</span>
              </span>
            )}

            {targetValidationResults && (
              <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold ${
                hasTargetError 
                  ? "bg-rose-500/10 text-rose-400 border border-rose-500/20" 
                  : "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
              }`}>
                {hasTargetError ? <AlertTriangle className="size-3" /> : <CheckCircle className="size-3" />}
                <span>Java {hasTargetError ? "Error" : "Built"}</span>
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Side-by-side Dual Code View */}
      <div className="flex-1 flex min-h-0 divide-x divide-slate-850">
        {/* Source Side (C#) */}
        <div className="w-1/2 flex flex-col min-h-0 bg-slate-950/20">
          <div className="p-2.5 bg-slate-950/40 border-b border-slate-900 flex items-center justify-between shrink-0">
            <span className="text-[10px] font-bold tracking-wider text-slate-400 uppercase">
              C# {sourceTarget || "Relational (.NET)"}
            </span>
            <Button
              size="icon"
              variant="ghost"
              onClick={() => handleCopy(getSourceCode(), "source")}
              className="size-7 text-slate-500 hover:text-slate-350 hover:bg-slate-900"
              title="Copy C# Code"
            >
              {copiedBlock === "source" ? <Check className="size-3.5 text-emerald-400" /> : <Copy className="size-3.5" />}
            </Button>
          </div>

          <div className="flex-1 p-4 overflow-auto custom-scrollbar bg-slate-950/10">
            <pre className="font-mono text-xs text-slate-300 leading-relaxed whitespace-pre-wrap select-text">
              <code>{getSourceCode()}</code>
            </pre>
          </div>

          {hasSourceError && (
            <div className="p-3 bg-rose-500/5 border-t border-rose-500/15 shrink-0 max-h-24 overflow-y-auto custom-scrollbar">
              <span className="text-[10px] font-bold text-rose-400 block uppercase">Compiler Error</span>
              <p className="font-mono text-[10px] text-slate-400 mt-0.5 leading-relaxed">
                {sourceValidationResults.error}
              </p>
            </div>
          )}
        </div>

        {/* Target Side (Java) */}
        <div className="w-1/2 flex flex-col min-h-0 bg-slate-950/40">
          <div className="p-2.5 bg-slate-950/45 border-b border-slate-900 flex items-center justify-between shrink-0">
            <span className="text-[10px] font-bold tracking-wider text-slate-400 uppercase">
              Java {destinationTarget || "NoSQL (Spring Boot)"}
            </span>
            <Button
              size="icon"
              variant="ghost"
              onClick={() => handleCopy(getTargetCode(), "target")}
              className="size-7 text-slate-500 hover:text-slate-350 hover:bg-slate-900"
              title="Copy Java Code"
            >
              {copiedBlock === "target" ? <Check className="size-3.5 text-emerald-400" /> : <Copy className="size-3.5" />}
            </Button>
          </div>

          <div className="flex-1 p-4 overflow-auto custom-scrollbar bg-slate-950/10 font-mono select-text">
            <pre className="font-mono text-xs text-slate-300 leading-relaxed whitespace-pre-wrap">
              <code>{getTargetCode()}</code>
            </pre>
          </div>

          {hasTargetError && (
            <div className="p-3 bg-rose-500/5 border-t border-rose-500/15 shrink-0 max-h-24 overflow-y-auto custom-scrollbar">
              <span className="text-[10px] font-bold text-rose-400 block uppercase">Compiler Error</span>
              <p className="font-mono text-[10px] text-slate-400 mt-0.5 leading-relaxed">
                {targetValidationResults.error}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
