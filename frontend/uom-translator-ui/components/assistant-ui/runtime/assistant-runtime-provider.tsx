"use client";

import {
	AssistantRuntimeProvider,
	type RemoteThreadListAdapter,
	Suggestions,
	useAui,
} from "@assistant-ui/react";
import {
	type LangChainMessage,
	useLangGraphRuntime,
} from "@assistant-ui/react-langgraph";
import { useMemo, useState } from "react";

import { GraphStateContext } from "@/hooks/use-graph-state-context";
import { createClient } from "@/lib/chatApi";
import type { BackendState } from "@/lib/types";

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

export function AssistantRuntimeProviderWrapper({
	inputSuggestions,
	children,
}: {
	inputSuggestions: any;
	children: React.ReactNode;
}) {
	const client = useMemo(() => createClient(), []);
	const [graphState, setGraphState] = useState<Partial<BackendState>>({});

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
			const configurable = savedConfig ? JSON.parse(savedConfig) : {};

			const payload = {
				input: messages.length ? { messages } : null,
				streamMode: ["messages", "updates", "custom"],
				streamSubgraphs: true,
				signal: config.abortSignal,
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
					sandbox_execution_timeout: configurable.daytonaTimeout || undefined,
				},
			};

			// TODO: clieant.runs.stream is deprecated, use client.threads.stream https://github.com/langchain-ai/langgraphjs/blob/2f0010e3a59e79cae1ff22b05985c7c82f8a2261/libs/sdk/docs/runs.md
			// const threadStream = await client.threads.stream(externalId, { assistantId: ASSISTANT_ID });
			// threadStream.run.start({ input: payload })
			// threadStream.messages
			const eventStream = await client.runs.stream(
				externalId,
				ASSISTANT_ID,
				payload as any,
			);
			return eventStream;
			// async function* makeDebugGenerator() {
			// 	try {
			// 		for await (const chunk of eventStream) {
			// 			console.debug("Received chunk:", chunk);
			// 			yield chunk;
			// 		}
			// 	} catch (err: any) {
			// 		console.error("Error during LangGraph run stream:", err);
			// 		throw err;
			// 	}
			// }
			// return makeDebugGenerator();
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
	}, [client]);

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
				} catch (e) {
					console.error("Failed to list threads in adapter:", e);
					return { threads: [] };
				}
			},
			async rename(remoteId, newTitle) {
				await client.threads.update(remoteId, {
					metadata: { title: newTitle },
				});
			},
			async archive() {},
			async unarchive() {},
			async delete(remoteId) {
				await client.threads.delete(remoteId);
			},
			async initialize() {
				const defaultTitle = `Migration ${new Date().toLocaleTimeString([], {
					hour: "2-digit",
					minute: "2-digit",
				})}`;
				const { thread_id } = await client.threads.create({
					metadata: { title: defaultTitle },
				});
				return { remoteId: thread_id, externalId: thread_id };
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
				} catch (e) {
					console.error("Failed to fetch thread in adapter:", e);
					return {
						remoteId: threadId,
						externalId: threadId,
						status: "regular" as const,
						title: "New Migration",
					};
				}
			},
			async generateTitle() {
				return {
					async *[Symbol.asyncIterator]() {
						yield { type: "text", text: "" };
					},
				} as any;
			},
		};
	}, [client]);

	const runtime = useLangGraphRuntime({
		unstable_allowCancellation: true,
		stream,
		unstable_threadListAdapter: threadListAdapter,
		create: async () => {
			const defaultTitle = `Migration ${new Date().toLocaleTimeString([], {
				hour: "2-digit",
				minute: "2-digit",
			})}`;
			const { thread_id } = await client.threads.create({
				metadata: { title: defaultTitle },
			});
			return { externalId: thread_id };
		},
		load: async (externalId, config) => {
			try {
				const state = await client.threads.getState<{
					messages: LangChainMessage[];
				}>(
					externalId,
					undefined,
					config?.signal ? { signal: config.signal } : undefined,
				);
				return {
					messages: state.values?.messages || [],
					interrupts: state.tasks?.[0]?.interrupts || [],
				};
			} catch (e) {
				console.error("Failed to load thread state:", e);
				return { messages: [], interrupts: [] };
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
				console.error("[UOM] Runtime error:", error);
			},
			onSubgraphError: (namespace: string, error: any) => {
				console.error(`[UOM] Subgraph [${namespace}] error:`, error);
			},
			onCustomEvent: (type: string, data: any) => {
				console.debug(`[UOM] Custom event [${type}]:`, data);
			},
		},
	});

	const aui = useAui({
		// tools: Tools({ toolkit: uomToolkit }),
		suggestions: Suggestions(inputSuggestions),
	});

	return (
		<GraphStateContext value={graphState}>
			<AssistantRuntimeProvider aui={aui} runtime={runtime}>
				{children}
			</AssistantRuntimeProvider>
		</GraphStateContext>
	);
}
