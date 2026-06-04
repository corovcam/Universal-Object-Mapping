import { createContext, useContext } from "react";
import type { BackendState } from "@/lib/types";

export const GraphStateContext = createContext<Partial<BackendState>>({});

export const useGraphStateContext = () => {
	const context = useContext(GraphStateContext);
	if (context === undefined) {
		throw new Error(
			"useGraphStateContext must be used within a GraphStateProvider",
		);
	}
	return context;
};
