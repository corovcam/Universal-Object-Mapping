import { createContext, useContext } from "react";
import type { BackendState } from "@/lib/types";

export const GraphStateContext = createContext<{
	graphState: Partial<BackendState>;
	error: { message: string; error?: any } | null;
	setError: (error: { message: string; error?: any } | null) => void;
	runError: { message: string; error?: any } | null;
	setRunError: (error: { message: string; error?: any } | null) => void;
}>({
	graphState: {},
	error: null,
	runError: null,
	setError: () => {},
	setRunError: () => {},
});

export const useGraphStateContext = () => {
	const context = useContext(GraphStateContext);
	if (context === undefined) {
		throw new Error(
			"useGraphStateContext must be used within a GraphStateProvider",
		);
	}
	return context;
};
