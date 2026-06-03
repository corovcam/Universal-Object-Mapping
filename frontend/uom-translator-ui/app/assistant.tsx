"use client";

import dynamic from "next/dynamic";
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

const DevToolsModal = dynamic(
	() => import("@assistant-ui/react-devtools").then((mod) => mod.DevToolsModal),
	{ ssr: false },
);

export function Assistant({
	inputData,
}: {
	inputData: { inputSuggestions: any };
}) {
	return (
		<AssistantRuntimeProviderWrapper
			inputSuggestions={inputData.inputSuggestions}
		>
			{process.env.NODE_ENV === "development" && <DevToolsModal />}
			<SidebarProvider defaultOpen>
				<div className="flex h-dvh w-full">
					<ThreadListSidebar />
					<SidebarInset>
						<Tooltip>
							<TooltipTrigger asChild>
								<SidebarTrigger className="absolute top-5 left-5 z-20" />
							</TooltipTrigger>
							<TooltipContent side="right">
								<p>Toggle Sidebar</p>
							</TooltipContent>
						</Tooltip>
						<Thread />
					</SidebarInset>
				</div>
			</SidebarProvider>
		</AssistantRuntimeProviderWrapper>
	);
}
