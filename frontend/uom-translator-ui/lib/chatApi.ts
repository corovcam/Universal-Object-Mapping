import { Client } from "@langchain/langgraph-sdk";

/**
 * Factory function to create and configure a LangGraph SDK Client.
 * Automatically resolves the endpoint URL:
 * - Reads `NEXT_PUBLIC_LANGGRAPH_API_URL` env variable.
 * - In browser context, falls back to appending `/api` to the window location (proxied via Next.js passthrough).
 * - Otherwise defaults to `/api`.
 *
 * @returns {Client} An instance of the LangGraph SDK Client.
 */
export const createClient = () => {
	const apiUrl =
		process.env.NEXT_PUBLIC_LANGGRAPH_API_URL ||
		(typeof window !== "undefined"
			? new URL("/api", window.location.href).href
			: "/api");
	return new Client({ apiUrl });
};
