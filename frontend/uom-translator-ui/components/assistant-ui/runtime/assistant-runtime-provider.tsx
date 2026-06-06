"use client";

import {
	AssistantRuntimeProvider,
	type RemoteThreadListAdapter,
	Suggestions,
	useAui,
} from "@assistant-ui/react";
import {
	convertLangChainMessages,
	type LangChainMessage,
	useLangGraphRuntime,
} from "@assistant-ui/react-langgraph";
import { useCallback, useMemo, useState } from "react";
import { toast } from "sonner";
import { GraphStateContext } from "@/hooks/use-graph-state-context";
import { createClient } from "@/lib/chatApi";
import type { BackendState, UomConfig } from "@/lib/types";

const ASSISTANT_ID =
	process.env.NEXT_PUBLIC_LANGGRAPH_ASSISTANT_ID ||
	"universal-object-mapping-translator";

const NODE_NAME_MAP: Record<string, string> = {
	extract_input: "Extracting Input",
	schema_inspection: "Inspecting Database Schema",
	generate_translation_node: "Translating Code",
	prep_schema_validation: "Validating Schema (.NET & Java)",
	validate_schema_node: "Validating Schema (.NET & Java)",
	prep_query_validation: "Validating Query Logic",
	validate_query_node: "Validating Query Logic",
	prep_query_equivalence: "Evaluating Translation (Query Equivalence Check)",
	check_query_equivalence_node:
		"Evaluating Translation (Query Equivalence Check)",
	evaluation_node: "Evaluating Translation (Query Equivalence Check)",
	human_intervention_node: "Manual Intervention",
};

const EXCLUDED_ERRORS = [
	"signal is aborted without reason", // This is a common message when aborting a run, and doesn't indicate an actual error (mostly happens in development environment)
];

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
	// const [serverActive, setServerActive] = useState(true);

	// Custom stream callback that works end-to-end with our LangGraph server
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
			const configurable: UomConfig = savedConfig
				? JSON.parse(savedConfig)
				: {};

			const payload = {
				input: messages.length ? { messages } : null,
				streamMode: ["messages", "updates", "custom"],
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

			// const cleanChunk = (val: any): any => {
			// 	if (val === null || typeof val !== "object") {
			// 		return val;
			// 	}
			// 	if (Array.isArray(val)) {
			// 		return val.map(cleanChunk);
			// 	}
			// 	const copy = { ...val };
			// 	for (const key in copy) {
			// 		if (key === "argsText" && copy[key] === "{}") {
			// 			copy[key] = "";
			// 		} else {
			// 			copy[key] = cleanChunk(copy[key]);
			// 		}
			// 	}
			// 	return copy;
			// };

			// async function* cleanStream() {
			// 	for await (const chunk of eventStream) {
			// 		yield cleanChunk(chunk);
			// 	}
			// }
			// return cleanStream();
		};
	}, [client]);

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

	const threadListAdapter = useMemo<RemoteThreadListAdapter>(() => {
		return {
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
			async delete(remoteId) {
				await client.threads.delete(remoteId);
			},
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
			async generateTitle() {
				// return createAssistantStream(async (controller) => {
				// 	const { title } = await fetch(`/api/threads/${remoteId}/title`, {
				// 		method: "POST",
				// 		body: JSON.stringify({ messages }),
				// 	}).then((r) => r.json());
				// 	controller.appendText(title);
				// });
				return new ReadableStream({
					start(controller) {
						controller.close();
					},
				}) as any;
			},
		};
	}, [client, handleError]);

	const runtime = useLangGraphRuntime({
		unstable_allowCancellation: true,
		stream,
		unstable_threadListAdapter: threadListAdapter,
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

				return {
					messages: state.values?.messages || [],
					interrupts: state.tasks?.[0]?.interrupts || [],
				};
			} catch (error) {
				handleError("Failed to load thread state", error);
				return { messages: [], interrupts: [] };
			}
		},
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
		eventHandlers: {
			onMessageChunk: (chunk: any, metadata: any) => {
				const nodeName = metadata?.langgraph_node;
				if (nodeName && NODE_NAME_MAP[nodeName]) {
					console.debug(`[UOM] Node: ${NODE_NAME_MAP[nodeName]}`);
					// setActiveNode(NODE_NAME_MAP[nodeName]);
				}
			},
			onValues: (values: any) => {
				if (values) {
					console.debug("[UOM] Values:", values);
					setGraphState(values);
				}
			},
			onUpdates: (updates: any) => {
				if (updates) {
					console.debug("[UOM] Updates:", updates);
					setGraphState((prev: any) => {
						const next = { ...prev };
						for (const [nodeName, nodeState] of Object.entries(updates)) {
							if (nodeState && typeof nodeState === "object") {
								Object.assign(next, nodeState);
							}
							if (NODE_NAME_MAP[nodeName]) {
								console.debug(`[UOM] Node: ${NODE_NAME_MAP[nodeName]}`);
								// setActiveNode(NODE_NAME_MAP[nodeName]);
							}
						}
						return next;
					});
				}
			},
			onSubgraphValues: (namespace: string, values: any) => {
				console.debug(`[UOM] Subgraph values [${namespace}]:`, values);
				if (values) {
					setGraphState((prev) => ({ ...prev, ...values }));
				}
			},
			onSubgraphUpdates: (namespace: string, updates: any) => {
				console.debug(`[UOM] Subgraph updates [${namespace}]:`, updates);
				// if (updates) {
				// 	setGraphState((prev: any) => {
				// 		const next = { ...prev };
				// 		for (const [nodeName, nodeState] of Object.entries(updates)) {
				// 			if (nodeState && typeof nodeState === "object") {
				// 				Object.assign(next, nodeState);
				// 			}
				// 		}
				// 		return next;
				// 	});
				// }
			},
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
			onSubgraphError: (namespace: string, error: any) => {
				console.error(`[UOM] Subgraph [${namespace}] error:`, error);
			},
			onCustomEvent: (type: string, data: any) => {
				console.log(`[UOM] Custom event [${type}]:`, data);
			},
		},
	});

	const aui = useAui({
		// tools: Tools({ toolkit: uomToolkit }),
		suggestions: Suggestions(inputSuggestions),
	});

	return (
		<GraphStateContext
			value={{ graphState, error, setError, runError, setRunError }}
		>
			<AssistantRuntimeProvider aui={aui} runtime={runtime}>
				{children}
			</AssistantRuntimeProvider>
		</GraphStateContext>
	);
}
