import { createContext, useContext } from "react";
import type { NODE_NAME_MAP } from "@/components/assistant-ui/runtime/assistant-runtime-provider";
import type { BackendState, UOMGraphContext } from "@/lib/types";

/**
 * Context value structure for the global Application state.
 */
export interface AppContext {
	defaultUomGraphContext: Partial<UOMGraphContext>;
}

/**
 * React Context object that shares the LangGraph state and execution status across the application.
 */
export const AppContext = createContext<AppContext>({
  defaultUomGraphContext: {},
});

/**
 * Custom React hook that accesses the AppContext.
 * Must be used within an `AssistantRuntimeProviderWrapper` component.
 *
 * @throws {Error} If called outside of a provider context.
 * @returns {AppContext} The current AppContext value.
 */
export const useAppContext = () => {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error(
      "useAppContext must be used within a AppContextProvider",
    );
  }
  return context;
};
