"use client";

import { AssistantRuntimeProviderWrapper } from "@/components/assistant-ui/runtime/assistant-runtime-provider";
import { Thread } from "@/components/assistant-ui/thread";
import { ThreadListSidebar } from "@/components/assistant-ui/threadlist-sidebar";
import { SidebarProvider } from "@/components/ui/sidebar";

export function Assistant({ inputData }: { inputData: { inputSuggestions: any } }) {
  return (
    <AssistantRuntimeProviderWrapper inputSuggestions={inputData.inputSuggestions}>
      <SidebarProvider defaultOpen>
        <div className="flex h-dvh w-full">
          <ThreadListSidebar />
          <div className="flex-1 flex flex-col min-w-0">
            <Thread />
          </div>
        </div>
      </SidebarProvider>
    </AssistantRuntimeProviderWrapper>
  );
}
