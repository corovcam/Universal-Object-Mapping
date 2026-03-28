import { Client } from "@langchain/langgraph-sdk";

const LANGGRAPH_API_URL =
  process.env.NEXT_PUBLIC_LANGGRAPH_API_URL || "http://localhost:8123";

export function createLangGraphClient() {
  return new Client({
    apiUrl: LANGGRAPH_API_URL,
  });
}

export const langGraphClient = createLangGraphClient();

// Graph name from langgraph.json
export const GRAPH_NAME = "agent";

// Thread management
export async function createThread() {
  const client = createLangGraphClient();
  const thread = await client.threads.create();
  return thread;
}

export async function getThread(threadId: string) {
  const client = createLangGraphClient();
  return client.threads.get(threadId);
}
