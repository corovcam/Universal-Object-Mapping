"use client";

import React, { useState } from "react";
import { 
  GitCommit, 
  Terminal, 
  Settings, 
  Play, 
  CheckCircle2, 
  XCircle, 
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  Database,
  Cpu,
  Layers,
  Activity,
  Diff,
  FileJson
} from "lucide-react";

interface ExecutionTraceProps {
  currentNode: string | null;
  history: string[];
  loopCount: number;
  deepDiffs: any | null;
  schemaContext: string | null;
  rawState: any;
}

export function ExecutionTrace({
  currentNode,
  history = [],
  loopCount = 0,
  deepDiffs,
  schemaContext,
  rawState,
}: ExecutionTraceProps) {
  const [activeTab, setActiveTab] = useState<"pipeline" | "diffs" | "inspector">("pipeline");
  const [expandedSection, setExpandedSection] = useState<string | null>(null);

  // Hardcoded node list that aligns with python graph.py enums
  const ALL_NODES = [
    { key: "extract_input", label: "Extracting Input", desc: "Extract C# schema and intent" },
    { key: "schema_inspection", label: "Inspecting Database Schema", desc: "Scan MSSQL & Target db context" },
    { key: "generate_translation_node", label: "Translating Code", desc: "Generate Spring Data models & queries" },
    { key: "validate_schema_node", label: "Validating Schema (.NET & Java)", desc: "Build check targets in Daytona sandbox" },
    { key: "validate_query_node", label: "Validating Query Logic", desc: "Execute target queries against running DBs" },
    { key: "check_query_equivalence_node", label: "Evaluating Translation (Query Equivalence Check)", desc: "Evaluate deep difference of return samples" },
    { key: "human_intervention_node", label: "Manual Intervention", desc: "Pause and request developer review" }
  ];

  const toggleExpand = (sec: string) => {
    setExpandedSection(prev => (prev === sec ? null : sec));
  };

  const activeIdx = ALL_NODES.findIndex(n => n.label === currentNode);
  const getStepStatus = (nodeLabel: string, idx: number) => {
    if (currentNode === nodeLabel) return "active";
    if (activeIdx !== -1 && idx < activeIdx) return "completed";
    
    // State presence fallback (so timeline looks correct even when run completes/stops)
    if (nodeLabel === "Extracting Input" && rawState?.source_target) return "completed";
    if (nodeLabel === "Inspecting Database Schema" && rawState?.schema_context) return "completed";
    if (nodeLabel === "Translating Code" && (rawState?.translated_schema_code || rawState?.translated_query_code)) return "completed";
    if (nodeLabel === "Validating Schema (.NET & Java)" && (rawState?.target_query_validation_results || rawState?.query_equivalence_deep_diffs || rawState?.explanation_message)) return "completed";
    if (nodeLabel === "Validating Query Logic" && (rawState?.target_query_validation_results || rawState?.query_equivalence_deep_diffs || rawState?.explanation_message)) return "completed";
    if (nodeLabel === "Evaluating Translation (Query Equivalence Check)" && (rawState?.query_equivalence_deep_diffs || rawState?.explanation_message)) return "completed";
    if (nodeLabel === "Manual Intervention" && rawState?.explanation_message && !currentNode) return "completed";
    return "pending";
  };

  return (
    <div className="flex flex-col h-full bg-slate-900/20 border border-slate-800/80 rounded-xl overflow-hidden min-h-0">
      {/* Sub tabs header */}
      <div className="bg-slate-950/80 p-2.5 border-b border-slate-850 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => setActiveTab("pipeline")}
            className={`flex items-center gap-1 px-3 py-1 rounded text-xs font-semibold transition-all ${
              activeTab === "pipeline"
                ? "bg-slate-800 text-slate-100 border border-slate-700/60"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Layers className="size-3.5 text-indigo-400" />
            <span>Execution Timeline</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("diffs")}
            className={`flex items-center gap-1 px-3 py-1 rounded text-xs font-semibold transition-all relative ${
              activeTab === "diffs"
                ? "bg-slate-800 text-slate-100 border border-slate-700/60"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Diff className="size-3.5 text-pink-400" />
            <span>Deep Diff Inspector</span>
            {deepDiffs && (
              <span className="absolute -top-1 -right-1 flex size-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-pink-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-pink-500"></span>
              </span>
            )}
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("inspector")}
            className={`flex items-center gap-1 px-3 py-1 rounded text-xs font-semibold transition-all ${
              activeTab === "inspector"
                ? "bg-slate-800 text-slate-100 border border-slate-700/60"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <FileJson className="size-3.5 text-teal-400" />
            <span>Global State</span>
          </button>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-[10px] text-slate-500 font-medium">Loop retries:</span>
          <span className="font-mono text-xs text-indigo-450 bg-indigo-650/10 px-2 py-0.5 border border-indigo-500/20 rounded font-bold">
            {loopCount}/3
          </span>
        </div>
      </div>

      {/* Main Inner Panel */}
      <div className="flex-1 p-4 overflow-y-auto custom-scrollbar min-h-0 bg-slate-950/15">
        {activeTab === "pipeline" && (
          <div className="space-y-4 max-w-xl mx-auto py-2">
            {ALL_NODES.map((n, idx) => {
              const status = getStepStatus(n.label, idx);
              return (
                <div key={n.key} className="flex gap-4 relative">
                  {/* Vertical Timeline connectors */}
                  {idx < ALL_NODES.length - 1 && (
                    <div className={`absolute left-[13px] top-7 bottom-0 w-0.5 ${
                      status === "completed" ? "bg-indigo-650" : "bg-slate-800"
                    }`} style={{ height: "calc(100% + 16px)" }} />
                  )}

                  {/* Indicator Dot */}
                  <div className="relative shrink-0 z-10">
                    {status === "completed" ? (
                      <div className="size-7 rounded-full bg-indigo-600/10 border-2 border-indigo-500 flex items-center justify-center text-indigo-400">
                        <CheckCircle2 className="size-4" />
                      </div>
                    ) : status === "active" ? (
                      <div className="size-7 rounded-full bg-indigo-600 border-2 border-indigo-400 flex items-center justify-center text-white pulse-dot">
                        <Activity className="size-4 animate-pulse" />
                      </div>
                    ) : (
                      <div className="size-7 rounded-full bg-slate-900 border-2 border-slate-800 flex items-center justify-center text-slate-650">
                        <span className="text-[10px] font-bold">{idx + 1}</span>
                      </div>
                    )}
                  </div>

                  {/* Detail text */}
                  <div className={`flex-1 p-3.5 rounded-xl border transition-all ${
                    status === "active"
                      ? "bg-slate-900 border-indigo-500/35 glow-indigo"
                      : status === "completed"
                      ? "bg-slate-900/60 border-indigo-950/30 opacity-80"
                      : "bg-slate-900/20 border-slate-900 opacity-40"
                  }`}>
                    <div className="flex items-center justify-between gap-2">
                      <span className={`text-xs font-semibold ${status === "active" ? "text-indigo-400" : "text-slate-350"}`}>
                        {n.label}
                      </span>
                      {status === "active" && (
                        <span className="text-[9px] bg-indigo-600/10 border border-indigo-550/20 text-indigo-400 font-bold px-1.5 py-0.5 rounded animate-pulse">
                          Running
                        </span>
                      )}
                    </div>
                    <span className="text-[10px] text-slate-500 block mt-1 leading-relaxed">{n.desc}</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {activeTab === "diffs" && (
          <div className="space-y-4">
            {!deepDiffs ? (
              <div className="text-center py-12">
                <Diff className="size-8 text-slate-700 mx-auto mb-2 opacity-50" />
                <span className="text-xs text-slate-500 block">No deep diff evaluations executed yet.</span>
                <span className="text-[10px] text-slate-650 block mt-1">DeepDiff comparison triggers during the query equivalence verification node.</span>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="p-3 bg-pink-500/5 border border-pink-500/15 rounded-lg flex items-center gap-2">
                  <AlertTriangle className="size-4 text-pink-400" />
                  <div className="text-xs">
                    <span className="font-bold text-slate-200">Equivalence Discrepancy Found</span>
                    <span className="text-slate-400 block text-[10px] mt-0.5">The C# relational outputs and Spring Boot MongoDB/Neo4j query results differed.</span>
                  </div>
                </div>

                {/* Displaying Diff mapping properties */}
                {Object.entries(deepDiffs).map(([key, diffObj]: [string, any]) => {
                  const hasCountDiff = diffObj.count_diff;
                  const firstDiff = diffObj.first_sample_diff;
                  const lastDiff = diffObj.last_sample_diff;
                  const deepDiffMapping = diffObj.deepdiff_mapping;
                  const errMessage = diffObj.error;

                  return (
                    <div key={key} className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden p-4 space-y-4">
                      <div className="flex items-center gap-2 border-b border-slate-850 pb-2">
                        <GitCommit className="size-4 text-indigo-400" />
                        <span className="text-xs font-bold text-slate-200">Query Verification Suite: {key}</span>
                      </div>

                      {errMessage && (
                        <div className="p-3 bg-rose-500/5 border border-rose-500/15 rounded font-mono text-[10px] text-rose-400">
                          {errMessage}
                        </div>
                      )}

                      {/* Count Check representation */}
                      {hasCountDiff && (
                        <div className="grid grid-cols-2 gap-4">
                          <div className="p-3 bg-slate-950 rounded border border-slate-850 space-y-1">
                            <span className="text-[9px] text-slate-500 uppercase font-bold tracking-wider">C# Relational Rows</span>
                            <span className="font-mono text-sm text-slate-300 font-semibold">{hasCountDiff.source || 0} items</span>
                          </div>
                          <div className="p-3 bg-slate-950 rounded border border-slate-850 space-y-1">
                            <span className="text-[9px] text-slate-500 uppercase font-bold tracking-wider">Spring target Nodes/Docs</span>
                            <span className="font-mono text-sm text-pink-400 font-semibold">{hasCountDiff.target || 0} items</span>
                          </div>
                        </div>
                      )}

                      {/* Custom deep diff card mapping details */}
                      {deepDiffMapping && (
                        <div className="space-y-2">
                          <span className="text-[10px] text-slate-400 uppercase font-bold block tracking-wider">Structural differences</span>
                          <div className="bg-slate-950 border border-slate-850 rounded p-3 text-[11px] space-y-2 font-mono text-slate-350">
                            {typeof deepDiffMapping === "object" ? (
                              Object.entries(deepDiffMapping).map(([diffPath, diffVal]: [string, any]) => (
                                <div key={diffPath} className="border-b border-slate-900/60 pb-2 last:border-0">
                                  <span className="text-indigo-400 text-[10px] block font-bold truncate">{diffPath}</span>
                                  <div className="flex gap-4 mt-1 text-[10px]">
                                    <span className="text-slate-500 shrink-0">Source: <span className="text-slate-300 select-all font-semibold">{JSON.stringify(diffVal.old || diffVal.dictionary_item_removed || "")}</span></span>
                                    <span className="text-pink-400 shrink-0">Target: <span className="text-pink-300 select-all font-semibold">{JSON.stringify(diffVal.new || diffVal.dictionary_item_added || "")}</span></span>
                                  </div>
                                </div>
                              ))
                            ) : (
                              <pre className="whitespace-pre-wrap">{JSON.stringify(deepDiffMapping, null, 2)}</pre>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {activeTab === "inspector" && (
          <div className="space-y-4">
            <div className="flex items-center gap-1.5 p-2 bg-slate-950 rounded border border-slate-850">
              <Database className="size-4 text-indigo-400" />
              <span className="text-[11px] font-bold text-slate-350 uppercase">Active Relational Schema Context</span>
            </div>
            
            <div className="bg-slate-950 border border-slate-850 rounded-xl p-3 font-mono text-[11px] text-slate-400 whitespace-pre-wrap max-h-60 overflow-y-auto custom-scrollbar leading-relaxed select-text">
              {schemaContext || "No active DB schema metadata collected yet."}
            </div>

            <hr className="border-slate-800" />

            <div className="bg-slate-900/30 border border-slate-850 rounded-xl overflow-hidden">
              <button
                type="button"
                onClick={() => toggleExpand("raw_state")}
                className="w-full flex items-center justify-between p-3 text-xs font-semibold text-slate-350 hover:bg-slate-900 transition-colors"
              >
                <span className="flex items-center gap-1.5">
                  <Terminal className="size-4 text-emerald-400" />
                  Raw State JSON
                </span>
                {expandedSection === "raw_state" ? <ChevronDown className="size-4" /> : <ChevronRight className="size-4" />}
              </button>

              {expandedSection === "raw_state" && (
                <div className="p-3 bg-slate-950 font-mono text-[10px] text-slate-450 border-t border-slate-850 overflow-x-auto select-all max-h-64 custom-scrollbar">
                  <pre>{JSON.stringify(rawState || {}, null, 2)}</pre>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
