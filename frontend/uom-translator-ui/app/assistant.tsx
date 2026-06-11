"use client";

import dynamic from "next/dynamic";
import ComponentErrorBoundary from "@/app/component-error-boundary";
import { AssistantRuntimeProviderWrapper } from "@/components/assistant-ui/runtime/assistant-runtime-provider";
import { Thread } from "@/components/assistant-ui/thread";
import { ThreadListSidebar } from "@/components/assistant-ui/threadlist-sidebar";
import {
	SidebarInset,
	SidebarProvider,
	SidebarTrigger,
} from "@/components/ui/sidebar";
import {
	Tooltip,
	TooltipContent,
	TooltipTrigger,
} from "@/components/ui/tooltip";
import { UOMGraphContext } from "@/lib/types";
import { AppContext } from "@/hooks/use-app-context";
import { Suspense, useMemo } from "react";
import { SpinnerEmpty } from "@/components/custom-empty";

const DevToolsModal = dynamic(
	() => import("@assistant-ui/react-devtools").then((mod) => mod.DevToolsModal),
	{ ssr: false },
);

export interface UOMAssistantProps {
	inputData: {
		defaultUomGraphContext: UOMGraphContext;
		inputSuggestions: Array<{
			title: string;
			label: string;
			prompt: string;
		}>;
	};
}

function LoadingThread() {
	return (
		<div className="flex h-dvh w-full items-center justify-center">
			<SpinnerEmpty
				title="Loading..."
				description="Please wait while we load the current thread."
			/>
		</div>
	);
}

export function Assistant({
	inputData,
}: UOMAssistantProps) {
	const inputDataMemoized = useMemo(() => inputData, [inputData]); 
	return (
		<AppContext value={{ defaultUomGraphContext: inputDataMemoized.defaultUomGraphContext }}>
			<AssistantRuntimeProviderWrapper
				inputSuggestions={inputDataMemoized.inputSuggestions}
			>
				{process.env.NODE_ENV === "development" && <DevToolsModal />}
				<SidebarProvider defaultOpen>
					<div className="flex h-dvh w-full">
						<ComponentErrorBoundary title="An error occurred while loading the thread list.">
							<ThreadListSidebar />
						</ComponentErrorBoundary>
						<SidebarInset>
							<ComponentErrorBoundary title="An error occurred while loading the thread.">
								<Tooltip>
									<TooltipTrigger asChild>
										<SidebarTrigger className="absolute top-5 left-5 z-20 text-primary" />
									</TooltipTrigger>
									<TooltipContent side="right">
										<p>Toggle Sidebar</p>
									</TooltipContent>
								</Tooltip>
								<Thread />
							</ComponentErrorBoundary>
						</SidebarInset>
					</div>
				</SidebarProvider>
			</AssistantRuntimeProviderWrapper>
		</AppContext>
	);
}
