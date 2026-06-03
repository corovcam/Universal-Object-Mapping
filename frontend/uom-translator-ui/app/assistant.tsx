"use client";

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

export function Assistant({
	inputData,
}: {
	inputData: { inputSuggestions: any };
}) {
	return (
		<AssistantRuntimeProviderWrapper
			inputSuggestions={inputData.inputSuggestions}
		>
			<SidebarProvider defaultOpen>
				<div className="flex h-dvh w-full">
					<ThreadListSidebar variant="inset" />
					<SidebarInset>
						<Tooltip>
							<TooltipTrigger asChild>
								<SidebarTrigger className="ml-5 mt-5" />
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
