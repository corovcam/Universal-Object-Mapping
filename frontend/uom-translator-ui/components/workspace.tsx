"use client";

import React, { useState, useEffect, useMemo, useRef } from "react";
import { 
  AssistantRuntimeProvider,
  useAuiState
} from "@assistant-ui/react";
import {
  useLangGraphRuntime,
  type LangChainMessage
} from "@assistant-ui/react-langgraph";

import { createClient } from "@/lib/chatApi";
import { Thread } from "@/components/assistant-ui/thread";
import { ThreadManager, type ThreadItem } from "@/components/thread-manager";
import { ConfigModal, type UomConfig } from "@/components/config-modal";
import { LoadingEngagement } from "@/components/loading-engagement";
import { CodeComparison } from "@/components/code-comparison";
import { ExecutionTrace } from "@/components/execution-trace";
import { ManualIntervention } from "@/components/manual-intervention";
import { IdeLink } from "@/components/ide-link";

import { 
  Settings, 
  Terminal, 
  GitFork, 
  HelpCircle,
  FolderOpen,
  ArrowLeftRight,
  Sparkles,
  Info,
  Sun,
  Moon
} from "lucide-react";
import { Button } from "@/components/ui/button";

const ASSISTANT_ID = process.env.NEXT_PUBLIC_LANGGRAPH_ASSISTANT_ID || "universal-object-mapping-translator";

const NODE_NAME_MAP: Record<string, string> = {
  "extract_input": "Extracting Input",
  "schema_inspection": "Inspecting Database Schema",
  "generate_translation_node": "Translating Code",
  "prep_schema_validation": "Validating Schema (.NET & Java)",
  "validate_schema_node": "Validating Schema (.NET & Java)",
  "prep_query_validation": "Validating Query Logic",
  "validate_query_node": "Validating Query Logic",
  "prep_query_equivalence": "Evaluating Translation (Query Equivalence Check)",
  "check_query_equivalence_node": "Evaluating Translation (Query Equivalence Check)",
  "evaluation_node": "Evaluating Translation (Query Equivalence Check)",
  "human_intervention_node": "Manual Intervention"
};

export function Workspace() {
  const client = useMemo(() => createClient(), []);
  
  // Local Settings & State
  const [currentThreadId, setCurrentThreadId] = useState<string | null>(null);
  const [isConfigOpen, setIsConfigOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [isRightPaneExpanded, setIsRightPaneExpanded] = useState(false);

  // Theme & Drag resizing state
  const [theme, setTheme] = useState<"light" | "dark">("dark");
  const [leftWidth, setLeftWidth] = useState(40); // percentage for left pane
  const [isDragging, setIsDragging] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Active state data fetched directly from Python state.py model
  const [graphState, setGraphState] = useState<Partial<BackendState>>({});
  const [activeInterrupt, setActiveInterrupt] = useState<any>(null);
  const [isPolling, setIsPolling] = useState(false);
  const [isSubmittingInterrupt, setIsSubmittingInterrupt] = useState(false);
  const [activeNode, setActiveNode] = useState<string | null>(null);

  // Real-time server state sync
  const [threads, setThreads] = useState<ThreadItem[]>([]);
  const [serverActive, setServerActive] = useState(true);
  const [runError, setRunError] = useState<string | null>(null);

  // Fetch threads directly from LangGraph API server
  const fetchThreads = async () => {
    try {
      const list = await client.threads.search({ 
        limit: 50, 
        select: ["thread_id", "metadata", "created_at"],
        sortBy: "created_at",
        sortOrder: "desc",
        // metadata: { "title": "Migration" } 
      });
      const mapped = list.map((t) => ({
        id: t.thread_id,
        title: (t.metadata as { title?: string } | undefined)?.title || `Migration ${t.thread_id.slice(0, 4)}`,
        createdAt: t.created_at || new Date().toISOString()
      }));
      setThreads(mapped);
      setServerActive(true);
      return mapped;
    } catch (e) {
      console.error("Failed to query threads list from server", e);
      setServerActive(false);
      return [];
    }
  };

  // Check connection active status on mount and load initial threads
  useEffect(() => {
    if (typeof window !== "undefined") {
      const onboarded = localStorage.getItem("uom_config_onboarded");
      if (!onboarded) {
        setIsConfigOpen(true);
      }
    }

    const loadInitialThreads = async () => {
      const currentList = await fetchThreads();
      if (currentList.length > 0) {
        setCurrentThreadId(currentList[0].id);
      } else {
        await handleNewThread();
      }
    };
    loadInitialThreads();
  }, []);

  // Theme loading & toggler (defaulting to dark variables, adding light class if requested)
  useEffect(() => {
    if (typeof window !== "undefined") {
      const savedTheme = localStorage.getItem("uom_ui_theme") as "light" | "dark" | null;
      const initialTheme = savedTheme || "dark";
      setTheme(initialTheme);
      if (initialTheme === "light") {
        document.documentElement.classList.add("light");
      } else {
        document.documentElement.classList.remove("light");
      }
    }
  }, []);

  const toggleTheme = () => {
    const nextTheme = theme === "dark" ? "light" : "dark";
    setTheme(nextTheme);
    if (typeof window !== "undefined") {
      localStorage.setItem("uom_ui_theme", nextTheme);
      if (nextTheme === "light") {
        document.documentElement.classList.add("light");
      } else {
        document.documentElement.classList.remove("light");
      }
    }
  };

  // Dragging mouse handlers for resizable slider
  useEffect(() => {
    if (!isDragging) return;

    const handleMouseMove = (e: MouseEvent) => {
      if (!containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const newWidth = ((e.clientX - rect.left) / rect.width) * 100;
      setLeftWidth(Math.max(20, Math.min(80, newWidth)));
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    
    document.body.style.userSelect = "none";

    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
      document.body.style.userSelect = "";
    };
  }, [isDragging]);

  // Onboarding auto-open trigger
  useEffect(() => {
    if (typeof window !== "undefined") {
      const onboarded = localStorage.getItem("uom_config_onboarded");
      if (!onboarded) {
        setIsConfigOpen(true);
      }
      
      // Auto-load or create initial thread
      const savedThreads = localStorage.getItem("uom_saved_threads");
      if (savedThreads) {
        try {
          const list: ThreadItem[] = JSON.parse(savedThreads);
          if (list.length > 0) {
            setCurrentThreadId(list[0].id);
            return;
          }
        } catch (e) {
          console.error(e);
        }
      }
      // Trigger new thread if none exists
      handleNewThread();
    }
  }, []);

  // Initialize stream for assistant-ui runtime
  const stream = useMemo(() => {
    return async (messages: any[], streamConfig: any) => {
      const savedConfig = typeof window !== "undefined" ? localStorage.getItem("uom_translator_config") : null;
      const configurable = savedConfig ? JSON.parse(savedConfig) : {};

      const { externalId } = await streamConfig.initialize();
      if (!externalId) {
        throw new Error("Thread has not been initialized.");
      }

      const payload = {
        input: messages.length ? { messages } : null,
        streamMode: ["messages", "updates", "custom"],
        signal: streamConfig.abortSignal,
        onDisconnect: "cancel",
        ...(streamConfig.command != null && { command: streamConfig.command }),
        ...(streamConfig.checkpointId != null && {
          checkpoint: { checkpoint_id: streamConfig.checkpointId },
        }),
        config: {
          configurable: {
            ollama_host: configurable.ollamaHost,
            model: configurable.model,
            openai_api_url: configurable.openaiApiUrl,
            openai_api_key: configurable.openaiApiKey,
            mssql_connection_string: configurable.mssqlConnectionString,
            mongodb_uri: configurable.mongodbUri,
            neo4j_uri: configurable.neo4jUri,
            neo4j_password: configurable.neo4jPassword,
            daytona_timeout: configurable.daytonaTimeout
          }
        }
      };
      
      const eventStream = await client.runs.stream(externalId, ASSISTANT_ID, payload as any);
      async function* makeGenerator() {
        for await (const chunk of eventStream) {
          // Process chunk
          if (chunk.event === "updates" && chunk.data) {
            setGraphState((prev: any) => {
              const next = { ...prev };
              for (const [nodeName, nodeState] of Object.entries(chunk.data)) {
                if (nodeState && typeof nodeState === "object") {
                  Object.assign(next, nodeState);
                }
                if (NODE_NAME_MAP[nodeName]) {
                  setActiveNode(NODE_NAME_MAP[nodeName]);
                }
              }
              return next;
            });
          }
          if (chunk.event === "values" && chunk.data) {
            setGraphState((prev: any) => ({ ...prev, ...chunk.data }));
          }
          if (chunk.event === "messages/metadata" && chunk.data) {
            const entry = Object.values(chunk.data)[0] as any;
            const nodeName = entry?.metadata?.langgraph_node;
            if (nodeName && NODE_NAME_MAP[nodeName]) {
              setActiveNode(NODE_NAME_MAP[nodeName]);
            }
          }
          yield chunk;
        }
      }
      return makeGenerator();
    };
  }, [client, currentThreadId]);

  // Bind assistant-ui runtime
  const runtime = useLangGraphRuntime({
    unstable_allowCancellation: true,
    stream,
    create: async () => {
      const { thread_id } = await client.threads.create();
      return { externalId: thread_id };
    },
    load: async (externalId) => {
      const state = await client.threads.getState<{
        messages: LangChainMessage[];
      }>(externalId);
      return {
        messages: state.values.messages,
        interrupts: state.tasks[0]?.interrupts,
      };
    },
  });

  // Keep track of current thread ID inside assistant-ui runtime
  useEffect(() => {
    if (currentThreadId) {
      runtime.threads.switchToThread(currentThreadId);
      fetchFullBackendState();
    }
  }, [currentThreadId, runtime]);

  // Fetch full state directly from Python orchestrator endpoint
  const fetchFullBackendState = async () => {
    if (!currentThreadId) return;
    try {
      const state = await client.threads.getState(currentThreadId);
      if (state && state.values) {
        setGraphState(state.values);
        
        // Grab current interrupt
        const activeTask = state.tasks?.[0];
        if (activeTask && activeTask.interrupts && activeTask.interrupts.length > 0) {
          setActiveInterrupt(activeTask.interrupts[0]);
        } else {
          setActiveInterrupt(null);
        }
      }
    } catch (e) {
      console.error("Failed to query backend thread state", e);
    }
  };

  // Poll state during active run stream
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isPolling && currentThreadId) {
      interval = setInterval(() => {
        fetchFullBackendState();
      }, 1500);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isPolling, currentThreadId]);

  // Start new translation session
  const handleNewThread = async () => {
    try {
      const { thread_id } = await client.threads.create();
      
      const newThread: ThreadItem = {
        id: thread_id,
        title: `Migration ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`,
        createdAt: new Date().toISOString()
      };

      const saved = localStorage.getItem("uom_saved_threads");
      const currentList: ThreadItem[] = saved ? JSON.parse(saved) : [];
      const updatedList = [newThread, ...currentList];
      
      localStorage.setItem("uom_saved_threads", JSON.stringify(updatedList));
      setCurrentThreadId(thread_id);
    } catch (e) {
      console.error("Error provisioning new thread", e);
    }
  };

  // Handle human-in-the-loop manual intervention submissions
  const handleSubmitInterrupt = async (decision: "accept" | "reject", feedback: string) => {
    if (!currentThreadId) return;
    setIsSubmittingInterrupt(true);
    try {
      // Resume run by posting resume payload to active thread state runs
      await client.runs.create(currentThreadId, ASSISTANT_ID, {
        command: {
          resume: {
            decision,
            feedback
          }
        }
      });

      // Start polling for updates
      setIsPolling(true);
      setActiveInterrupt(null);
      
      // Wait for backend compilation and refresh state
      setTimeout(async () => {
        await fetchFullBackendState();
        setIsSubmittingInterrupt(false);
      }, 1500);
    } catch (e) {
      console.error("Failed submitting manual intervention to LangGraph runtime", e);
      setIsSubmittingInterrupt(false);
    }
  };

  // Check running status of the assistant-ui components reactively
  const [isRunning, setIsRunning] = useState(false);

  useEffect(() => {
    setIsRunning(runtime.thread.getState().isRunning);
    return runtime.thread.subscribe(() => {
      setIsRunning(runtime.thread.getState().isRunning);
    });
  }, [runtime]);
  
  // Sync polling state with stream execution
  useEffect(() => {
    if (isRunning) {
      setIsPolling(true);
      setActiveNode("Extracting Input"); // Set initial active node when run starts
    } else {
      // Small timeout to catch the final completed state block
      setTimeout(() => {
        setIsPolling(false);
        fetchFullBackendState();
        setActiveNode(null); // Clear active node when run stops
      }, 1000);
    }
  }, [isRunning]);

  // Find active node is managed via state variables dynamically updated during runs

  return (
    <div className="flex h-screen w-screen bg-slate-950 font-sans overflow-hidden">
      {/* Sidebar Thread Navigation */}
      <ThreadManager
        currentThreadId={currentThreadId}
        onSelectThread={setCurrentThreadId}
        onNewThread={handleNewThread}
        isCollapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
      />

      {/* Main Dual Pane Workspace */}
      <div className="flex-1 flex flex-col min-w-0">
        
        {/* Workspace Top Toolbar */}
        <header className="h-14 bg-slate-900 border-b border-slate-850 px-6 flex items-center justify-between shrink-0 z-15">
          <div className="flex items-center gap-2.5">
            <div className="size-8 rounded-lg bg-indigo-600/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 font-bold">
              <GitFork className="size-4 shrink-0" />
            </div>
            <div>
              <h1 className="text-sm font-semibold text-slate-100 flex items-center gap-1.5 leading-none">
                <span>Universal Object Mapping Translator</span>
              </h1>
              <span className="text-[10px] text-slate-500 block mt-1 font-medium">
                Active Paradigm Migrator: Relational .NET to Graph/Doc Java
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <IdeLink />

            {/* Premium Theme Switcher */}
            <Button
              size="icon"
              variant="outline"
              onClick={toggleTheme}
              className="size-8 bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200"
              title={theme === "dark" ? "Switch to Light Mode" : "Switch to Dark Mode"}
            >
              {theme === "dark" ? (
                <Sun className="size-4 text-amber-400" />
              ) : (
                <Moon className="size-4 text-indigo-400" />
              )}
            </Button>
            
            <Button
              size="icon"
              variant="outline"
              onClick={() => setIsConfigOpen(true)}
              className="size-8 bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200"
              title="Global settings & db setup scripts"
            >
              <Settings className="size-4" />
            </Button>
          </div>
        </header>

        {/* Dynamic Split Layout with Draggable Resizer Handle */}
        <div ref={containerRef} className="flex-1 flex min-h-0 overflow-hidden relative">
          
          {/* Left Pane: Enhanced Assistant-UI Chat */}
          <div 
            style={{ 
              width: isRightPaneExpanded ? "0px" : `${leftWidth}%`, 
              display: isRightPaneExpanded ? "none" : "flex" 
            }}
            className="border-r border-slate-850 flex flex-col min-h-0 bg-slate-950/20"
          >
            <AssistantRuntimeProvider runtime={runtime}>
              <Thread />
            </AssistantRuntimeProvider>
          </div>

          {/* Draggable Divider Slider Handle */}
          {!isRightPaneExpanded && (
            <div
              onMouseDown={() => setIsDragging(true)}
              onDoubleClick={() => setLeftWidth(40)}
              className={`w-1.5 hover:w-2 bg-transparent hover:bg-indigo-500/30 active:bg-indigo-500/50 cursor-col-resize transition-all z-18 relative flex items-center justify-center group h-full border-l border-r ${
                isDragging ? "bg-indigo-500/40 w-2" : "border-slate-850"
              }`}
              title="Drag to resize, double click to reset to 40%"
            >
              {/* Vertical drag guide line */}
              <div className="w-[1px] h-12 bg-slate-800 group-hover:bg-indigo-400 group-active:bg-indigo-400 rounded transition-colors" />
              
              <div className="absolute top-4 scale-0 group-hover:scale-100 transition-transform bg-slate-900 border border-slate-800 text-[10px] text-slate-400 px-1.5 py-0.5 rounded shadow-md pointer-events-none whitespace-nowrap">
                Drag to resize
              </div>
            </div>
          )}

          {/* Collapsible divider toggle */}
          <button
            type="button"
            onClick={() => setIsRightPaneExpanded(prev => !prev)}
            style={{ 
              left: isRightPaneExpanded ? "12px" : `${leftWidth}%` 
            }}
            className={`absolute top-1/2 -translate-y-1/2 -translate-x-1/2 z-20 size-6 rounded-full bg-slate-900 border border-slate-800 text-slate-400 hover:text-indigo-400 hover:border-indigo-500/50 flex items-center justify-center shadow-lg transition-all hover:scale-105 cursor-pointer max-md:hidden ${
              isRightPaneExpanded ? "left-3 translate-x-0 rotate-180" : ""
            }`}
            title={isRightPaneExpanded ? "Restore split layout" : "Expand Code view"}
          >
            <ArrowLeftRight className="size-3.5" />
          </button>

          {/* Right Pane: Comparisons, Timelines, Interventions */}
          <div 
            style={{ 
              width: isRightPaneExpanded ? "100%" : `${100 - leftWidth}%` 
            }}
            className="flex flex-col min-h-0 p-4 space-y-4 bg-slate-950/45"
          >
            
            {/* Boredom Mitigation Active Loader */}
            <LoadingEngagement
              currentNode={activeNode}
              isActive={isRunning}
            />

            {/* Human-in-the-loop Interrupt Screen */}
            {activeInterrupt && (
              <div className="animate-in slide-in-from-top-2 duration-300 shrink-0">
                <ManualIntervention
                  interruptPayload={activeInterrupt.value}
                  onSubmitResponse={handleSubmitInterrupt}
                  isSubmitting={isSubmittingInterrupt}
                />
              </div>
            )}

            {/* Split Comparison & Timelines */}
            <div className="flex-1 grid grid-rows-5 gap-4 min-h-0">
              
              {/* Code comparison panel (rows 1-3) */}
              <div className="row-span-3 min-h-0">
                <CodeComparison
                  sourceSchema={graphState.source_schema_code}
                  translatedSchema={graphState.translated_schema_code}
                  sourceQuery={graphState.source_query_code}
                  translatedQuery={graphState.translated_query_code}
                  sourceHarness={graphState.source_validation_harness_code}
                  translatedHarness={graphState.target_validation_harness_code}
                  sourceTarget={graphState.source_target}
                  destinationTarget={graphState.destination_target}
                  sourceValidationResults={graphState.source_query_validation_results}
                  targetValidationResults={graphState.target_query_validation_results}
                />
              </div>

              {/* Execution progress track & diffs (rows 4-5) */}
              <div className="row-span-2 min-h-0">
                <ExecutionTrace
                  currentNode={activeNode}
                  history={[]}
                  loopCount={graphState.translation_loop_count || 0}
                  deepDiffs={graphState.query_equivalence_deep_diffs}
                  schemaContext={graphState.schema_context}
                  rawState={graphState}
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Global Configuration & Database Setup Onboarding Modal */}
      <ConfigModal
        isOpen={isConfigOpen}
        onClose={() => setIsConfigOpen(false)}
        onSave={() => {
          // Trigger a silent reload of stream settings mapping
          setCurrentThreadId(prev => prev);
        }}
      />
    </div>
  );
}
