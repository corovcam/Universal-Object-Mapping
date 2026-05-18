"use client";

import { AssistantRuntimeProvider } from "@assistant-ui/react";
import {
  type LangChainMessage,
  unstable_createLangGraphStream,
  useLangGraphRuntime,
} from "@assistant-ui/react-langgraph";
import { useMemo, useState } from "react";
import {
  CheckEquivalenceToolUI,
  ValidateDotnetToolUI,
  ValidateJavaToolUI,
  ExtractInputToolUI,
  SchemaInspectionToolUI,
} from "@/components/assistant-ui/custom-tools";
import { Thread } from "@/components/assistant-ui/thread";
import { ThemeToggle } from "@/components/theme-toggle";
import { createClient } from "@/lib/chatApi";
import { ChatForm } from "./chat-form";
import { LangGraphInterrupt } from "./interrupt-ui";
import { OnboardingModal } from "./onboarding";
import { SettingsModal } from "./settings";

const ASSISTANT_ID = process.env.NEXT_PUBLIC_LANGGRAPH_ASSISTANT_ID ?? "agent";

export function Assistant() {
  const client = useMemo(() => createClient(), []);

  const stream = useMemo(
    () =>
      unstable_createLangGraphStream({
        client,
        assistantId: ASSISTANT_ID,
      }),
    [client],
  );

  const runtime = useLangGraphRuntime({
    unstable_allowCancellation: true,
    stream,
    create: async () => {
      const { thread_id } = await client.threads.create();
      return { externalId: thread_id };
    },
    load: async (externalId) => {
      const state = await client.threads.getState<any>(externalId);
      return {
        messages: state.values.messages || [],
        interrupts: state.tasks[0]?.interrupts,
      };
    },
  });

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <ExtractInputToolUI />
      <SchemaInspectionToolUI />
      <ValidateDotnetToolUI />
      <ValidateJavaToolUI />
      <CheckEquivalenceToolUI />

      <div className="flex h-full w-full overflow-hidden bg-background text-foreground">
        {/* Left Pane: Structured State Form */}
        <div className="w-1/3 min-w-[350px] max-w-md border-r flex flex-col h-full bg-muted/10">
          <div className="flex-none p-4 border-b flex items-center justify-between bg-muted/30">
            <div>
              <h2 className="text-lg font-semibold tracking-tight">UOM Orchestrator</h2>
              <p className="text-sm text-muted-foreground">Universal Object Mapping</p>
            </div>
            <div className="flex items-center gap-1">
              <OnboardingModal />
              <SettingsModal />
              <ThemeToggle />
            </div>
          </div>
          <div className="flex-1 overflow-y-auto p-4">
            <ChatForm />
          </div>
        </div>

        {/* Right Pane: Streaming Chat & Interrupts */}
        <div className="flex-1 flex flex-col h-full relative">
          <LangGraphInterrupt />
          <Thread />
        </div>
      </div>
    </AssistantRuntimeProvider>
  );
}
