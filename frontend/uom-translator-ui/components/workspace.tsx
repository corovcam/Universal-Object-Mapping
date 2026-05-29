"use client";

import {
  type RemoteThreadListAdapter
} from "@assistant-ui/react";
import { DevToolsModal } from "@assistant-ui/react-devtools";
import {
  useLangGraphRuntime,
  type LangChainMessage
} from "@assistant-ui/react-langgraph";
import { useEffect, useMemo, useRef, useState } from "react";

import { Thread } from "@/components/assistant-ui/thread";
import { CodeComparison } from "@/components/code-comparison";
import { ConfigModal } from "@/components/config-modal";
import { ExecutionTrace } from "@/components/execution-trace";
import { IdeLink } from "@/components/ide-link";
import { LoadingEngagement } from "@/components/loading-engagement";
import { ManualIntervention } from "@/components/manual-intervention";
import { ThreadManager, type ThreadItem } from "@/components/thread-manager";
import { createClient } from "@/lib/chatApi";

import { Button } from "@/components/ui/button";
import type { BackendState, UomConfig } from "@/lib/types";
import {
  AlertCircle,
  ArrowLeftRight,
  GitFork,
  Settings,
  X
} from "lucide-react";
import { UomRuntime } from "./assistant-ui/runtime/uom-runtime";

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

  // Initialize stream for assistant-ui runtime
  const stream = useMemo(() => {
    return async (messages: any[], streamConfig: any) => {
      setRunError(null);
      const savedConfig = typeof window !== "undefined" ? localStorage.getItem("uom_translator_config") : null;
      const configurable: UomConfig = savedConfig ? JSON.parse(savedConfig) : {};

      const { externalId } = await streamConfig.initialize();
      if (!externalId) {
        throw new Error("Thread has not been initialized.");
      }

      const payload = {
        input: messages.length ? { messages } : null,
        streamMode: ["messages", "updates", "custom"],
        streamSubgraphs: true,
        signal: streamConfig.abortSignal,
        onDisconnect: "cancel",
        multitaskStrategy: "reject",
        ...(streamConfig.command != null && { command: streamConfig.command }),
        ...(streamConfig.checkpointId != null && {
          checkpoint: { checkpoint_id: streamConfig.checkpointId },
        }),
        context: {
          ollama_host: configurable.ollamaHost || undefined,
          openai_api_url: configurable.openaiApiUrl || undefined,
          openai_api_key: configurable.openaiApiKey || undefined,
          model: configurable.model || undefined,
          db_toolbox_uri: configurable.dbToolboxUri || undefined,
          mongodb_mcp_uri: configurable.mongodbMcpUri || undefined,
          ms_sql_connection_string: configurable.mssqlConnectionString || undefined,
          mongodb_uri: configurable.mongodbUri || undefined,
          neo4j_uri: configurable.neo4jUri || undefined,
          neo4j_password: configurable.neo4jPassword || undefined,
          sandbox_execution_timeout: configurable.daytonaTimeout || undefined
        }
      };
      
      // TODO: clieant.runs.stream is deprecated, use client.threads.stream https://github.com/langchain-ai/langgraphjs/blob/2f0010e3a59e79cae1ff22b05985c7c82f8a2261/libs/sdk/docs/runs.md
      // const threadStream = await client.threads.stream(externalId, { assistantId: ASSISTANT_ID });
      // threadStream.run.start({ input: payload })
      // threadStream.messages
      const eventStream = await client.runs.stream(externalId, ASSISTANT_ID, payload as any);
      return eventStream;
      // async function* makeGenerator() {
      //   try {
      //     for await (const chunk of eventStream) {
      //       // Process chunk
      //       if (chunk.event === "updates" && chunk.data) {
      //         setGraphState((prev: any) => {
      //           const next = { ...prev };
      //           for (const [nodeName, nodeState] of Object.entries(chunk.data)) {
      //             if (nodeState && typeof nodeState === "object") {
      //               Object.assign(next, nodeState);
      //             }
      //             if (NODE_NAME_MAP[nodeName]) {
      //               setActiveNode(NODE_NAME_MAP[nodeName]);
      //             }
      //           }
      //           return next;
      //         });
      //       }
      //       // not used
      //       if (chunk.event === "values" && chunk.data) {
      //         setGraphState((prev: any) => ({ ...prev, ...chunk.data }));
      //       }
      //       if (chunk.event === "messages/metadata" && chunk.data) {
      //         const entry = Object.values(chunk.data)[0] as any;
      //         const nodeName = entry?.metadata?.langgraph_node;
      //         if (nodeName && NODE_NAME_MAP[nodeName]) {
      //           setActiveNode(NODE_NAME_MAP[nodeName]);
      //         }
      //       }
      //       if (chunk.event === "error") {
      //         const errMsg = (chunk.data as any)?.message || JSON.stringify(chunk.data);
      //         setRunError(errMsg);
      //         setServerActive(false);
      //       }
      //       if (chunk.event === "custom") {
      //         console.log("Custom event from LangGraph:", chunk.data);
      //       }
      //       yield chunk;
      //     }
      //   } catch (err: any) {
      //     console.error("Error during LangGraph run stream:", err);
      //     setRunError(err.message || String(err));
      //     setServerActive(false);
      //     throw err;
      //   }
      // }
      // return makeGenerator();
    };
  }, [client, currentThreadId]);

  // Adapter to feed custom thread list to assistant-ui runtime (server-backed)
  const threadListAdapter = useMemo<RemoteThreadListAdapter>(() => {
    return {
      async list() {
        try {
          const list = await client.threads.search({ 
            limit: 50, 
            select: ["thread_id", "metadata", "created_at"],
            sortBy: "created_at",
            sortOrder: "desc",
            // metadata: { "title": "Migration" } 
          });
          setServerActive(true);
          return {
            threads: list.map((t) => ({
              remoteId: t.thread_id,
              externalId: t.thread_id,
              status: "regular",
              title: (t.metadata as { title?: string } | undefined)?.title || `Migration ${t.thread_id.slice(0, 4)}`,
            })),
          };
        } catch (e) {
          console.error("Failed to list threads in adapter:", e);
          setServerActive(false);
          return { threads: [] };
        }
      },
      async rename(remoteId, newTitle) {
        try {
          await client.threads.update(remoteId, { metadata: { title: newTitle } });
          await fetchThreads();
        } catch (e) {
          console.error("Failed to rename thread in adapter:", e);
          setServerActive(false);
          setRunError("Failed renaming migration session on LangGraph server.");
        }
      },
      async archive() {},
      async unarchive() {},
      async delete(remoteId) {
        try {
          await client.threads.delete(remoteId);
          const currentList = await fetchThreads();
          // If deleted current, select another
          if (currentThreadId === remoteId) {
            if (currentList.length > 0) {
              setCurrentThreadId(currentList[0].id);
            } else {
              await handleNewThread();
            }
          }
        } catch (e) {
          console.error("Failed to delete thread in adapter:", e);
          setServerActive(false);
          setRunError("Failed deleting migration session from LangGraph server.");
        }
      },
      async initialize(threadId) {
        return {
          remoteId: threadId,
          externalId: threadId,
        };
      },
      async fetch(threadId) {
        try {
          const t = await client.threads.get(threadId, {
            include: ["thread_id", "metadata"],
          });
          return {
            remoteId: threadId,
            externalId: threadId,
            status: "regular",
            title: (t.metadata as { title?: string } | undefined)?.title || `Migration ${threadId.slice(0, 4)}`,
          };
        } catch (e) {
          console.error("Failed to fetch thread in adapter:", e);
          return {
            remoteId: threadId,
            externalId: threadId,
            status: "regular",
            title: "New Migration",
          };
        }
      },
      async generateTitle() {
        return {
          async *[Symbol.asyncIterator]() {
            yield { type: "text", text: "" };
          }
        } as any;
      }
    };
  }, [client, currentThreadId]);

  // Bind assistant-ui runtime
  const runtime = useLangGraphRuntime({
    unstable_allowCancellation: true,
    stream,
    unstable_threadListAdapter: threadListAdapter,
    load: async (externalId) => {
      try {
        const state = await client.threads.getState<{
          messages: LangChainMessage[];
        }>(externalId);
        setServerActive(true);
        return {
          messages: state.values?.messages || [],
          interrupts: state.tasks?.[0]?.interrupts || [],
        };
      } catch (e) {
        console.error("Failed to load thread in runtime:", e);
        setServerActive(false);
        return { messages: [], interrupts: [] };
      }
    },
    eventHandlers: {
      onMessageChunk: (chunk: any, metadata: any) => {
        const nodeName = metadata?.langgraph_node;
        if (nodeName && NODE_NAME_MAP[nodeName]) {
          setActiveNode(NODE_NAME_MAP[nodeName]);
        }
      },
      onValues: (values: any) => {
        if (values) {
          setGraphState((prev) => ({ ...prev, ...values }));
        }
      },
      onUpdates: (updates: any) => {
        if (updates) {
          setGraphState((prev: any) => {
            const next = { ...prev };
            for (const [nodeName, nodeState] of Object.entries(updates)) {
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
      },
      onSubgraphValues: (namespace: string, values: any) => {
        console.log(`Subgraph values received for namespace: ${namespace}`, values);
        if (values) {
          setGraphState((prev) => ({ ...prev, ...values }));
        }
      },
      onSubgraphUpdates: (namespace: string, updates: any) => {
        console.log(`Subgraph updates received for namespace: ${namespace}`, updates);
        if (updates) {
          setGraphState((prev: any) => {
            const next = { ...prev };
            for (const [nodeName, nodeState] of Object.entries(updates)) {
              if (nodeState && typeof nodeState === "object") {
                Object.assign(next, nodeState);
              }
            }
            return next;
          });
        }
      },
      onError: (error: any) => {
        console.error("LangGraph runtime error event:", error);
        setRunError(error.message || String(error));
        setServerActive(false);
      },
      onSubgraphError: (namespace: string, error: any) => {
        console.error(`LangGraph subgraph [${namespace}] error event:`, error);
        setRunError(`Subgraph [${namespace}] failure: ${error.message || String(error)}`);
        setServerActive(false);
      },
      onCustomEvent: (type: string, data: any) => {
        console.log(`Custom event received: ${type}`, data);
      }
    }
  });

  // Keep track of current thread ID inside assistant-ui runtime
  useEffect(() => {
    if (currentThreadId) {
      try {
        runtime.threads.switchToThread(currentThreadId);
      } catch (e) {
        console.warn("Could not switch thread in runtime:", e);
      }
      fetchFullBackendState();
    }
  }, [currentThreadId, runtime]);

  // Fetch full state directly from Python orchestrator endpoint
  const fetchFullBackendState = async () => {
    if (!currentThreadId) return;
    try {
      const state = await client.threads.getState(currentThreadId);
      if (state && state.values) {
        setGraphState(state.values as any);
        setServerActive(true);
        
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
      setServerActive(false);
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

  // Start new translation session on LangGraph server
  const handleNewThread = async () => {
    try {
      const defaultTitle = `Migration ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
      const thread = await client.threads.create({
        metadata: { title: defaultTitle }
      });
      
      setCurrentThreadId(thread.thread_id);
      await fetchThreads();
    } catch (e) {
      console.error("Error provisioning new thread", e);
      setServerActive(false);
      setRunError("LangGraph Server Offline. Please ensure the Python orchestrator is running.");
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
      setRunError("Failed submitting manual intervention feedback to LangGraph.");
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

  return (
    <div className="flex h-screen w-screen bg-slate-950 font-sans overflow-hidden">
      {/* Sidebar Thread Navigation */}
      <ThreadManager
        currentThreadId={currentThreadId}
        onSelectThread={setCurrentThreadId}
        onNewThread={handleNewThread}
        isCollapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
        threads={threads}
        onDeleteThread={async (id) => {
          try {
            await client.threads.delete(id);
            const currentList = await fetchThreads();
            if (currentThreadId === id) {
              if (currentList.length > 0) {
                setCurrentThreadId(currentList[0].id);
              } else {
                await handleNewThread();
              }
            }
          } catch (err: any) {
            console.error("Failed to delete thread:", err);
            setRunError("Failed deleting migration session from LangGraph server.");
          }
        }}
        serverActive={serverActive}
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
            <UomRuntime runtime={runtime}>
              <DevToolsModal />
              <Thread />
            </UomRuntime>
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
