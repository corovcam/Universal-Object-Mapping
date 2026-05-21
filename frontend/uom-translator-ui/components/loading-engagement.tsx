"use client";

import React, { useState, useEffect } from "react";
import { Timer, Brain, Loader2, Sparkles, Database, Code, Terminal, CheckCircle2 } from "lucide-react";

interface LoadingEngagementProps {
  currentNode: string | null;
  isActive: boolean;
}

const STATUS_TIPS: Record<string, string[]> = {
  "Inspecting Database Schema": [
    "Querying Database MCP to extract MSSQL table schemas...",
    "Scanning primary keys, indexes, and relational integrity...",
    "Correlating foreign-key joins to establish entity graph relationships...",
    "Mapping relational column types to NoSQL BSON and Neo4j formats...",
    "Inspecting existing metadata to evaluate embed-vs-reference paradigms...",
    "Analyzing indexes to optimize target document queries..."
  ],
  "Translating Code": [
    "Synthesizing source C# relational DB architecture...",
    "Parsing EF Core LINQ / Dapper mapping structures...",
    "Generating Spring Data MongoDB entity models and Java representations...",
    "Drafting Spring Data Neo4j (OGM) nodes, relationships, and Cypher paths...",
    "Generating translation verification units and compiler tests...",
    "Applying paradigm-shift heuristics (Sql Joins to Graph Traversals)...",
    "Optimizing reactive database drivers and query templates..."
  ],
  "Validating .NET": [
    "Provisioning Daytona workspace container sandbox...",
    "Injecting source validation harness C# code...",
    "Running dotnet build to ensure relational syntax compiles perfectly...",
    "Executing verification tests against the SQL Server instance...",
    "Logging query metrics and initial sample result outputs..."
  ],
  "Validating Java": [
    "Mounting Target Spring Boot compiler profile inside Daytona...",
    "Injecting generated MongoDB / Neo4j Java repositories and entities...",
    "Running Maven/Gradle compilation passes on spring boot harness...",
    "Verifying Cypher-DSL and Mongo Criteria query construction...",
    "Running target integration test suites in isolated sandbox environment..."
  ],
  "Evaluating Translation (Query Equivalence Check)": [
    "Extracting JSON result maps from SQL Server and MongoDB/Neo4j runs...",
    "Running DeepDiff algorithms across relational rows and NoSQL documents...",
    "Evaluating row-to-node count mappings and deep equivalence heuristics...",
    "Checking edge cases, sorting orders, and null representation differences...",
    "Generating complete equivalence assessment reports..."
  ],
  "default": [
    "Orchestrating agent workflow phases...",
    "Resolving library definitions via Context7 MCP documentation...",
    "Structuring LLM generation outputs via deterministic Pydantic schemas...",
    "Analyzing telemetry and writing active transaction states...",
    "Running compilation checks and caching translation iterations..."
  ]
};

export function LoadingEngagement({ currentNode, isActive }: LoadingEngagementProps) {
  const [elapsedTime, setElapsedTime] = useState(0);
  const [currentTipIndex, setCurrentTipIndex] = useState(0);

  // Active Timer counting in tenths of a second
  useEffect(() => {
    if (!isActive) {
      setElapsedTime(0);
      return;
    }

    const startTime = Date.now();
    const interval = setInterval(() => {
      setElapsedTime((Date.now() - startTime) / 1000);
    }, 100);

    return () => clearInterval(interval);
  }, [isActive, currentNode]);

  // Rotate tips every 5 seconds
  useEffect(() => {
    if (!isActive) return;

    setCurrentTipIndex(0);
    const interval = setInterval(() => {
      setCurrentTipIndex((prev) => prev + 1);
    }, 5000);

    return () => clearInterval(interval);
  }, [isActive, currentNode]);

  if (!isActive) return null;

  const nodeName = currentNode || "Processing Request";
  const tips = STATUS_TIPS[nodeName] || STATUS_TIPS["default"];
  const currentTip = tips[currentTipIndex % tips.length];

  const getIcon = () => {
    switch (nodeName) {
      case "Inspecting Database Schema":
        return <Database className="size-4 text-sky-400 animate-bounce" />;
      case "Translating Code":
        return <Code className="size-4 text-indigo-400 animate-pulse" />;
      case "Validating .NET":
      case "Validating Java":
        return <Terminal className="size-4 text-emerald-400 animate-pulse" />;
      case "Evaluating Translation (Query Equivalence Check)":
        return <Sparkles className="size-4 text-purple-400 animate-spin" />;
      default:
        return <Loader2 className="size-4 text-slate-400 animate-spin" />;
    }
  };

  return (
    <div className="w-full bg-slate-950/60 rounded-xl border border-slate-800/80 p-4 space-y-3.5 shadow-lg shadow-black/10 overflow-hidden glow-indigo">
      <div className="flex items-center justify-between gap-3 border-b border-slate-800/40 pb-2.5">
        <div className="flex items-center gap-2">
          <div className="p-1.5 bg-slate-900 rounded-lg border border-slate-850 shrink-0">
            {getIcon()}
          </div>
          <div>
            <span className="text-slate-200 text-xs font-semibold block">{nodeName}</span>
            <span className="text-[10px] text-slate-500 block">LangGraph Pipeline Phase</span>
          </div>
        </div>

        {/* Live Timer */}
        <div className="flex items-center gap-1.5 px-2 py-1 bg-slate-900 rounded-lg border border-slate-850 text-slate-300 font-mono text-xs">
          <Timer className="size-3.5 text-indigo-400 animate-spin-slow" />
          <span>{elapsedTime.toFixed(1)}s</span>
        </div>
      </div>

      <div className="space-y-2">
        <div className="flex items-start gap-2.5">
          <Brain className="size-3.5 text-indigo-400 shrink-0 mt-0.5" />
          <span className="text-slate-300 text-xs leading-relaxed transition-all duration-300">
            {currentTip}
          </span>
        </div>

        {/* Custom Progress Bar simulating work */}
        <div className="w-full bg-slate-900 rounded-full h-1 overflow-hidden">
          <div 
            className="bg-indigo-600 h-full rounded-full transition-all duration-300"
            style={{ 
              width: `${Math.min(98, 5 + (elapsedTime * 2.2))}%` 
            }}
          />
        </div>
      </div>
    </div>
  );
}
