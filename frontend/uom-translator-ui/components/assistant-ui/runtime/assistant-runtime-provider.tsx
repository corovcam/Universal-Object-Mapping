"use client";

import {
	AssistantCloud,
	AssistantRuntimeProvider,
	type RemoteThreadListAdapter,
	Suggestions,
	useAui,
} from "@assistant-ui/react";
import {
	type LangChainMessage,
	useLangGraphRuntime,
} from "@assistant-ui/react-langgraph";
import { useCallback, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { GraphStateContext } from "@/hooks/use-graph-state-context";
import { createClient } from "@/lib/chatApi";
import { createAssistantStream } from "assistant-stream";
import type { BackendState, UOMGraphContext } from "@/lib/types";

/**
 * LangGraph Assistant ID for routing queries to the correct graph execution.
 * Configurable via `NEXT_PUBLIC_LANGGRAPH_ASSISTANT_ID` env variable.
 */
const ASSISTANT_ID =
	process.env.NEXT_PUBLIC_LANGGRAPH_ASSISTANT_ID ||
	"universal-object-mapping-translator";

/**
 * Mapping of LangGraph node execution IDs to human-friendly description titles.
 * Used in the UI sidebar/header to show the user the active step of the migration process.
 */
export const NODE_NAME_MAP = {
	/** Node responsible for using Pydantic schemas to extract framework specifications from C# inputs */
	extract_input: "Extracting Input",
	/** Node checking database schemas using MCP server tools */
	schema_inspection: "Inspecting Database Schema",
	/** Node executing LLM translation of source mappings to target entities/queries */
	generate_translation_node: "Translating Code",
	/** Node setting up workspace schemas for .csproj or pom.xml builds */
	prep_schema_validation: "Validating Schema (.NET & Java)",
	/** Node executing isolated container compilation via Daytona */
	validate_schema_node: "Validating Schema (.NET & Java)",
	/** Node preparing target query validation payloads */
	prep_query_validation: "Validating Query Logic",
	/** Node executing target query compilations inside sandboxes */
	validate_query_node: "Validating Query Logic",
	/** Node preparing SQL Server vs MongoDB/Neo4j query results comparison */
	prep_query_equivalence: "Evaluating Translation (Query Equivalence Check)",
	/** Node calculating DeepDiff semantic difference for outputs */
	check_query_equivalence_node:
		"Evaluating Translation (Query Equivalence Check)",
	/** Node executing LLM Judge evaluation for compile stdout/stderr and query equivalence */
	evaluation_node: "Evaluating Translation (Query Equivalence Check)",
	/** Suspended state graph node waiting for manual user intervention */
	human_intervention_node: "Manual Intervention",
};

/**
 * Normalizes message content so that no raw strings exist within a content array.
 * Converts any string elements in the array to text part objects.
 */
function normalizeMessageContent(message: any): any {
	if (!message) return message;
	if (message.content !== undefined && message.content !== null) {
		if (Array.isArray(message.content)) {
			message.content = message.content.map((part: any) => {
				if (typeof part === "string") {
					return { type: "text", text: part };
				}
				return part;
			});
		}
	}
	return message;
}

/**
 * Normalizes any events in the LangGraph stream so that nested message contents are correctly structured.
 */
function normalizeEvent(event: any): any {
	if (!event || typeof event !== "object") return event;
	if (event.data && typeof event.data === "object") {
		const data = event.data;
		if (event.event === "messages" && Array.isArray(data) && data.length > 0) {
			data[0] = normalizeMessageContent(data[0]);
		}
		if (
			(event.event === "messages/partial" || event.event === "messages/complete") &&
			Array.isArray(data)
		) {
			event.data = data.map(normalizeMessageContent);
		}
		if (event.event === "values" && Array.isArray(data.messages)) {
			data.messages = data.messages.map(normalizeMessageContent);
		}
		if (event.event === "updates") {
			if (Array.isArray(data.messages)) {
				data.messages = data.messages.map(normalizeMessageContent);
			}
			for (const key of Object.keys(data)) {
				const val = data[key];
				if (val && typeof val === "object" && Array.isArray(val.messages)) {
					val.messages = val.messages.map(normalizeMessageContent);
				}
			}
		}
	}
	return event;
}

/**
 * Errors that should be filtered out from showing up as global red error alerts.
 * Often happens when user cancels a running stream or browser environment discards requests.
 */
const EXCLUDED_ERRORS = ["signal is aborted without reason"];


/**
 * Wrapper component that sets up the LangGraph client, manages local React state for execution tracking,
 * and configures the `@assistant-ui/react-langgraph` runtime with hooks, streams, and thread lists.
 *
 * @param {object} props - Component properties.
 * @param {any} props.inputSuggestions - Array of onboarding query templates read from txt files.
 * @param {React.ReactNode} props.children - Child components to render within the state provider.
 * @returns {React.JSX.Element} The runtime provider and state provider context wrapper.
 */
export function AssistantRuntimeProviderWrapper({
	inputSuggestions,
	children,
}: {
	inputSuggestions: any;
	children: React.ReactNode;
}) {
	const client = useMemo(() => createClient(), []);
	const [graphState, setGraphState] = useState<Partial<BackendState>>({});
	const [error, setError] = useState<{ message: string; error?: any } | null>(
		null,
	);
	const [runError, setRunError] = useState<{
		message: string;
		error?: any;
	} | null>(null);
	const [activeNode, setActiveNode] = useState<
		keyof typeof NODE_NAME_MAP | null
	>(null);
	const activeNodeRef = useRef<keyof typeof NODE_NAME_MAP | null>(activeNode);

	/**
	 * Custom LangGraph stream connection handler.
	 * Invoked by assistant-ui when a user triggers a message.
	 * Fetches local database, Daytona sandbox, and LLM configuration keys from localStorage
	 * and yields streamable event updates from the backend client.
	 *
	 * @param {any[]} messages - Current list of conversational messages.
	 * @param {any} config - Client runtime stream config hooks.
	 * @returns {Promise<any>} An event stream promise containing LangGraph execution logs.
	 */
	const stream = useMemo(() => {
		return async (messages: any[], config: any) => {
			const { externalId } = await config.initialize();
			if (!externalId) {
				throw new Error("Thread has not been initialized");
			}

			const savedConfig =
				typeof window !== "undefined"
					? localStorage.getItem("uom_translator_config")
					: null;
			const configurable: UOMGraphContext = savedConfig
				? JSON.parse(savedConfig)
				: {};

			const payload = {
				input: messages.length ? { messages } : null,
				// "updates" is required for human-in-the-loop: @assistant-ui/react-langgraph
				// only captures the LangGraph `interrupt()` payload from `updates` events
				// (it reads `chunk.data.__interrupt__`). Without it the suspension is never
				// surfaced to `useLangGraphInterruptState()` during a live run.
				streamMode: ["messages-tuple", "updates", "values", "custom"],
				streamSubgraphs: true,
				...(config.abortSignal != null && { signal: config.abortSignal }),
				onDisconnect: "cancel",
				multitaskStrategy: "reject",
				...(config.command != null && { command: config.command }),
				...(config.checkpointId != null && {
					checkpoint: { checkpoint_id: config.checkpointId },
				}),
				context: {
					ollama_host: configurable.ollamaHost || undefined,
					openai_api_url: configurable.openaiApiUrl || undefined,
					openai_api_key: configurable.openaiApiKey || undefined,
					model: configurable.model || undefined,
					db_toolbox_uri: configurable.dbToolboxUri || undefined,
					mongodb_mcp_uri: configurable.mongodbMcpUri || undefined,
					ms_sql_connection_string:
						configurable.mssqlConnectionString || undefined,
					mongodb_uri: configurable.mongodbUri || undefined,
					neo4j_uri: configurable.neo4jUri || undefined,
					neo4j_password: configurable.neo4jPassword || undefined,
					daytona_api_url: configurable.daytonaApiUrl || undefined,
					daytona_api_key: configurable.daytonaApiKey || undefined,
					daytona_target: configurable.daytonaTarget || undefined,
					sandbox_execution_timeout: configurable.daytonaTimeout || undefined,
				},
			};

			// TODO: clieant.runs.stream is deprecated, use client.threads.stream https://github.com/langchain-ai/langgraphjs/blob/2f0010e3a59e79cae1ff22b05985c7c82f8a2261/libs/sdk/docs/runs.md
			// const threadStream = await client.threads.stream(externalId, {
			// 	assistantId: ASSISTANT_ID,
			// });
			// await threadStream.run.start({ input: payload });
			// return threadStream;
			const eventStream = await client.runs.stream(
				externalId,
				ASSISTANT_ID,
				payload as any,
			);
			return eventStream;

			// const wrappedStream = async function* () {
			// 	for await (const chunk of eventStream) {
			// 		console.debug("[UOM] Stream chunk:", chunk);
			// 		yield chunk;
			// 	}
			// };

			// return wrappedStream();
		};
	}, [client]);

	/**
	 * Standardized error handling handler. Logs error stack traces to console and sets UI alerts.
	 * Filters out typical canceled request warnings.
	 */
	const handleError = useCallback((message: string, error: any) => {
		if (EXCLUDED_ERRORS.includes(error?.message)) {
			console.warn("Excluded error occurred:", error);
			return;
		}
		console.error("[UOM] Runtime error:", error);
		setError({
			message,
			error,
		});
	}, []);

	/**
	 * Adapter conforming to RemoteThreadListAdapter from assistant-ui.
	 * Binds thread-level UI actions (new thread, deletion, renaming, fetching details)
	 * directly to corresponding LangGraph client SDK methods.
	 */
	const threadListAdapter = useMemo<RemoteThreadListAdapter>(() => {
		return {
			/**
			 * Queries active conversation history from LangGraph database.
			 *
			 * @returns {Promise<{ threads: any[] }>} List of simplified remote thread metadata objects.
			 */
			async list() {
				try {
					const list = await client.threads.search({
						limit: 50,
						select: ["thread_id", "metadata", "created_at"],
						sortBy: "created_at",
						sortOrder: "desc",
					});
					return {
						threads: list.map((t) => ({
							remoteId: t.thread_id,
							externalId: t.thread_id,
							status: "regular" as const,
							title:
								(t.metadata as { title?: string } | undefined)?.title ||
								`Migration ${t.thread_id.slice(0, 4)}`,
						})),
					};
				} catch (error) {
					handleError("Failed to list threads", error);
					throw error;
				}
			},
			/**
			 * Renames a thread by updating metadata key-value values on the backend.
			 *
			 * @param {string} remoteId - Unique ID of the target thread.
			 * @param {string} newTitle - The new human-readable title.
			 */
			async rename(remoteId, newTitle) {
				try {
					await client.threads.update(remoteId, {
						metadata: { title: newTitle },
					});
				} catch (error) {
					handleError("Failed to rename thread", error);
					throw error;
				}
			},
			async archive() {},
			async unarchive() {},
			/**
			 * Deletes the specified conversation history completely from the server storage.
			 *
			 * @param {string} remoteId - ID of the thread to delete.
			 */
			async delete(remoteId) {
				try {
					await client.threads.delete(remoteId);
				} catch (error) {
					handleError("Failed to delete thread", error);
					throw error;
				}
			},
			/**
			 * Pre-allocates a new thread ID with a localized timestamp placeholder title.
			 *
			 * @returns {Promise<{ remoteId: string, externalId: string }>} Initialized thread references.
			 */
			async initialize() {
				try {
					const defaultTitle = `Migration ${new Date().toLocaleTimeString([], {
						hour: "2-digit",
						minute: "2-digit",
					})}`;
					const { thread_id } = await client.threads.create({
						metadata: { title: defaultTitle },
					});
					return { remoteId: thread_id, externalId: thread_id };
				} catch (error) {
					handleError("Failed to create thread", error);
					throw error;
				}
			},
			/**
			 * Fetches metadata details for a single thread.
			 *
			 * @param {string} threadId - ID of the thread to fetch.
			 * @returns {Promise<any>} Thread configuration details.
			 */
			async fetch(threadId) {
				try {
					const t = await client.threads.get(threadId, {
						include: ["thread_id", "metadata"],
					});
					return {
						remoteId: threadId,
						externalId: threadId,
						status: "regular" as const,
						title:
							(t.metadata as { title?: string } | undefined)?.title ||
							`Migration ${threadId.slice(0, 4)}`,
					};
				} catch (error) {
					handleError("Failed to fetch thread", error);
					throw error;
				}
			},
			/**
			 * Generates an automated title for the thread.
			 * Currently stubbed out to bypass additional LLM lookups.
			 */
			async generateTitle(remoteId) {
				return createAssistantStream(async (controller) => {
					let title = `Migration ${remoteId.slice(0, 4)}`;
					try {
						const thread = await client.threads.get(remoteId, {
							include: ["metadata"],
						});
						title = (thread.metadata as { title?: string } | undefined)?.title || title;
					} catch (error) {
						console.error("[UOM] Error generating title:", error);
					}
					controller.appendText(title);
				});
			},
		};
	}, [client, handleError]);

	// const cloud = useMemo(
  //   () =>
  //     new AssistantCloud({
  //       baseUrl: process.env.NEXT_PUBLIC_ASSISTANT_BASE_URL!,
  //       anonymous: true, // Creates browser session-based user ID
	// 			telemetry: true, // Enables assistant-ui's built-in telemetry for usage analytics and debugging
  //     }),
  //   [],
  // );

	/**
	 * Configures and hooks into the LangGraph client state manager.
	 * Synchronizes local conversational lists with the LangGraph backend,
	 * mapping events like onMessageChunk and onUpdates to the React state.
	 */
	const runtime = useLangGraphRuntime({
		// cloud, // Pass the cloud instance to enable assistant-ui's cloud features like session management and analytics
		/** Enables user to cancel long-running agent loops manually. */
		unstable_allowCancellation: true,
		/** Core event stream callback. */
		stream,
		/** Thread list adapter for synchronization. */
		unstable_threadListAdapter: threadListAdapter,
		/**
		 * Handler to create a new thread with default title and persist it on the server.
		 * Called by assistant-ui when a new chat starts.
		 *
		 * @returns {Promise<{ externalId: string }>} Resolves to the newly created thread ID.
		 */
		create: async () => {
			try {
				const defaultTitle = `Migration ${new Date().toLocaleTimeString([], {
					hour: "2-digit",
					minute: "2-digit",
				})}`;
				const { thread_id } = await client.threads.create({
					metadata: { title: defaultTitle },
				});
				return { externalId: thread_id };
			} catch (error) {
				handleError("Failed to create thread for runtime", error);
				throw error;
			}
		},
		/**
		 * Loads full conversational messages and active interrupts for the specified thread.
		 * Called by assistant-ui when switching between threads.
		 *
		 * @param {string} externalId - Unique thread ID.
		 * @param {any} [config] - Config options including abort signals.
		 * @returns {Promise<{ messages: LangChainMessage[], interrupts: any[] }>} Messages and interrupts.
		 */
		load: async (externalId, config) => {
			try {
				const state = await client.threads.getState<{
					messages: LangChainMessage[];
				}>(
					externalId,
					undefined,
					config?.signal
						? { signal: config.signal, subgraphs: true }
						: { subgraphs: true },
				);

				// const rawMessages = state.values?.messages || [];
				// const normalizedMessages = rawMessages.map(normalizeMessageContent);

				// Restore any pending `interrupt()` so the human-intervention card
				// reappears when the conversation is reloaded via the thread list adapter.
				// The runtime feeds `interrupts[0]` into `useLangGraphInterruptState`.
				// Collect across all tasks (not just tasks[0]) for robustness.
				return {
					messages: state.values?.messages || [],
					interrupts: (state.tasks ?? []).flatMap(
						(task) => task.interrupts ?? [],
					),
				};
			} catch (error) {
				handleError("Failed to load thread state", error);
				return { messages: [], interrupts: [] };
			}
		},
		delete: async (externalId) => {
			try {
				await client.threads.delete(externalId);
			} catch (error) {
				handleError("Failed to delete thread", error);
				throw error;
			}
		},
		/**
		 * Retrieves the matching checkpoint ID for a thread state matching parent messages.
		 * Enables history-aware updates and backtracking.
		 *
		 * @param {string} threadId - Unique ID of the thread.
		 * @param {any[]} parentMessages - List of parent messages to match.
		 * @returns {Promise<string | null>} The resolved checkpoint ID, or null.
		 */
		getCheckpointId: async (threadId, parentMessages) => {
			try {
				const history = await client.threads.getHistory<BackendState>(threadId);
				for (const state of history) {
					const stateMessages = state.values.messages;
					if (
						!stateMessages ||
						stateMessages.length !== parentMessages.length
					) {
						continue;
					}
					const hasStableIds =
						parentMessages.every((m) => typeof m.id === "string") &&
						stateMessages.every((m) => typeof m.id === "string");
					if (!hasStableIds) continue;
					const isMatch = parentMessages.every(
						(m, i) => m.id === stateMessages[i]?.id,
					);
					if (isMatch) {
						return state.checkpoint.checkpoint_id ?? null;
					}
				}
				return null;
			} catch (error) {
				handleError("Failed to get checkpoint ID", error);
				return null;
			}
		},
		/**
		 * Event handlers triggered as LangGraph processes nodes and streams chunks.
		 */
		eventHandlers: {
			/**
			 * Triggered when a new token or structured data chunk is streamed from a node.
			 * Used to set the currently active node dynamically in the UI.
			 */
			onMessageChunk: (_chunk, metadata) => {
				const nodeName =(metadata?.langgraph_checkpoint_ns as string)?.split(":")[0];
				console.debug(`[UOM] Message Metadata: ${metadata}`);
				// TODO: use useRef for activeNode to avoid unnecessary re-renders on every chunk, and only update when nodeName changes
				if (nodeName !== activeNodeRef.current && NODE_NAME_MAP?.[nodeName as keyof typeof NODE_NAME_MAP]) {
					console.debug(`[UOM] Active node set to: ${nodeName}`);
					setActiveNode(nodeName as keyof typeof NODE_NAME_MAP);
					activeNodeRef.current = nodeName as keyof typeof NODE_NAME_MAP;
				}
			},
			/**
			 * Triggered when the full values of the state graph are updated.
			 */
			onValues: (values: any) => {
				if (values) {
					console.debug("[UOM] Values:", values);
					setGraphState(values);
				}
			},
			/**
			 * Triggered when incremental state updates are broadcasted.
			 */
			onUpdates: (updates: any) => {
				if (!updates || typeof updates !== "object") return;
				console.debug("[UOM] Updates:", updates);
				// `updates` events are keyed by node name (`{ nodeName: { ...stateDelta } }`)
				// and may also carry the special `__interrupt__` channel. Flatten the
				// per-node deltas into the flat graph state and drop `__interrupt__` so the
				// inspected state mirrors the `values` shape (the interrupt itself is handled
				// by the runtime and surfaced via `useLangGraphInterruptState`).
				const { __interrupt__, ...nodeUpdates } = updates;
				const merged = Object.values(nodeUpdates).reduce<Record<string, any>>(
					(acc, delta) =>
						delta && typeof delta === "object" && !Array.isArray(delta)
							? { ...acc, ...delta }
							: acc,
					{},
				);
				if (Object.keys(merged).length > 0) {
					setGraphState((prev) => ({ ...prev, ...merged }));
				}
			},
			/**
			 * Triggered when sub-graphs values update.
			 */
			onSubgraphValues: (namespace: string, values: any) => {
				console.debug(`[UOM] Subgraph values [${namespace}]:`, values);
				// if (values) {
				// 	setGraphState((prev) => ({ ...prev, ...values }));
				// }
			},
			/**
			 * Triggered when incremental sub-graph updates are broadcasted.
			 */
			onSubgraphUpdates: (namespace: string, updates: any) => {
				console.debug(`[UOM] Subgraph updates [${namespace}]:`, updates);
			},
			/**
			 * Catch-all error reporter for execution loops.
			 * Dispatches visual alerts via Sonner toast components.
			 */
			onError: (error: any) => {
				console.error("[UOM] Runtime error:", error);
				setRunError({
					message: "Error occurred while running the assistant",
					error,
				});
				toast.error("An error occurred while running the assistant", {
					description: error?.message || String(error),
				});
			},
			/**
			 * Catch-all error reporter for sub-graphs.
			 */
			onSubgraphError: (namespace: string, error: any) => {
				console.error(`[UOM] Subgraph [${namespace}] error:`, error);
			},
			/**
			 * Custom event receiver. Receives custom container build stdout/stderr streams
			 * and snapshot logs dispatched from the Python orchestrator in real-time.
			 */
			onCustomEvent: (type: string, data: any) => {
				console.log(`[UOM] Custom event [${type}]:`, data);
			},
		},
	});

	/**
	 * Configures assistant-ui wrapper context, initializing query suggestion templates.
	 */
	const aui = useAui({
		suggestions: Suggestions(inputSuggestions),
	});

	return (
		<GraphStateContext
			value={{ graphState, error, setError, runError, setRunError, activeNode }}
		>
			<AssistantRuntimeProvider aui={aui} runtime={runtime}>
				{children}
			</AssistantRuntimeProvider>
		</GraphStateContext>
	);
}
