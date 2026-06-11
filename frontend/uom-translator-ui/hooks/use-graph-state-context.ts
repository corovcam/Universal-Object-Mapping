import { createContext, useContext } from "react";
import type { NODE_NAME_MAP } from "@/components/assistant-ui/runtime/assistant-runtime-provider";
import type { BackendState } from "@/lib/types";

/**
 * Context value structure for the LangGraph State Graph.
 * Holds active node execution state, errors, and the current state snapshot of the translation pipeline.
 */
export interface GraphStateContextType {
	/** Represents the structured state values of the orchestrator state graph. */
	graphState: Partial<BackendState>;
	/** Tracks general runtime errors displayed in a global banner. */
	error: { message: string; error?: any } | null;
	/** Sets or clears a general runtime error. */
	setError: (error: { message: string; error?: any } | null) => void;
	/** Tracks execution errors that happen specifically during run processes (e.g. streaming issues). */
	runError: { message: string; error?: any } | null;
	/** Sets or clears a run-specific error. */
	setRunError: (error: { message: string; error?: any } | null) => void;
	/** The currently active LangGraph node matching keys of NODE_NAME_MAP. */
	activeNode: keyof typeof NODE_NAME_MAP | null;
}

/**
 * React Context object that shares the LangGraph state and execution status across the application.
 */
export const GraphStateContext = createContext<GraphStateContextType>({
	graphState: {},
	error: null,
	runError: null,
	setError: () => {},
	setRunError: () => {},
	activeNode: null,
});

/**
 * Custom React hook that accesses the GraphStateContext.
 * Must be used within an `AssistantRuntimeProviderWrapper` component.
 *
 * @throws {Error} If called outside of a provider context.
 * @returns {GraphStateContextType} The current LangGraph state context value.
 */
export const useGraphStateContext = () => {
	const context = useContext(GraphStateContext);
	if (context === undefined) {
		throw new Error(
			"useGraphStateContext must be used within a GraphStateContextProvider",
		);
	}
	return context;
};
