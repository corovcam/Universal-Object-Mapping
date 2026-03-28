"use client";

import { useState, useCallback, useRef } from "react";
import { useStream } from "@langchain/langgraph-sdk/react";
import { GRAPH_NAME } from "@/lib/langgraph-client";
import { generateId } from "@/lib/utils";
import type {
  ChatMessage,
  FrameworkType,
  PipelineState,
  PipelineStep,
  ToolCall,
} from "@/lib/types";

interface UseChatStreamOptions {
  apiUrl?: string;
  onMessage?: (message: ChatMessage) => void;
  onStepChange?: (step: PipelineStep) => void;
  onError?: (error: Error) => void;
}

interface StreamInput {
  messages: Array<{ role: string; content: string }>;
  source_code: string;
  source_target: string;
  destination_target: string;
}

export function useChatStream(options: UseChatStreamOptions = {}) {
  const { apiUrl = process.env.NEXT_PUBLIC_LANGGRAPH_API_URL || "http://localhost:8123" } = options;

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [pipeline, setPipeline] = useState<PipelineState>({
    currentStep: "idle",
    completedSteps: [],
    stepDetails: {},
  });
  const [activeTools, setActiveTools] = useState<ToolCall[]>([]);
  const [error, setError] = useState<Error | null>(null);

  const currentMessageRef = useRef<ChatMessage | null>(null);
  const threadIdRef = useRef<string | null>(null);

  const thread = useStream<StreamInput>({
    apiUrl,
    assistantId: GRAPH_NAME,
    streamMode: ["values", "messages", "updates"],
    onError: (err) => {
      console.error("[v0] Stream error:", err);
      setError(err instanceof Error ? err : new Error(String(err)));
      setIsStreaming(false);
      options.onError?.(err instanceof Error ? err : new Error(String(err)));
    },
  });

  const sendMessage = useCallback(
    async (
      content: string,
      sourceFramework: FrameworkType,
      targetFramework: FrameworkType
    ) => {
      setError(null);
      setIsStreaming(true);
      setPipeline({
        currentStep: "extract_input",
        completedSteps: [],
        stepDetails: {},
      });

      // Add user message
      const userMessage: ChatMessage = {
        id: generateId(),
        role: "user",
        content,
        timestamp: new Date(),
        sourceFramework,
        targetFramework,
        sourceCode: content,
      };
      setMessages((prev) => [...prev, userMessage]);
      options.onMessage?.(userMessage);

      // Create assistant placeholder
      const assistantMessage: ChatMessage = {
        id: generateId(),
        role: "assistant",
        content: "",
        timestamp: new Date(),
        sourceFramework,
        targetFramework,
        isStreaming: true,
      };
      currentMessageRef.current = assistantMessage;
      setMessages((prev) => [...prev, assistantMessage]);

      try {
        // Map framework types to the format expected by the orchestrator
        const sourceTarget = mapFrameworkToTarget(sourceFramework);
        const destinationTarget = mapFrameworkToTarget(targetFramework);

        // Submit to LangGraph
        thread.submit(
          {
            messages: [{ role: "user", content }],
            source_code: content,
            source_target: sourceTarget,
            destination_target: destinationTarget,
          },
          {
            streamMode: ["values", "messages", "updates"],
            onUpdate: (update) => {
              handleStreamUpdate(update);
            },
          }
        );
      } catch (err) {
        console.error("[v0] Failed to send message:", err);
        setError(err instanceof Error ? err : new Error("Failed to send message"));
        setIsStreaming(false);
      }
    },
    [thread, options]
  );

  const handleStreamUpdate = useCallback((update: unknown) => {
    if (!update || typeof update !== "object") return;

    const data = update as Record<string, unknown>;

    // Handle values updates (full state)
    if ("values" in data && data.values) {
      const values = data.values as Record<string, unknown>;

      // Update pipeline state based on which fields are populated
      if (values.schema_translated_code) {
        setPipeline((prev) => ({
          ...prev,
          currentStep: "complete",
          completedSteps: [
            "extract_input",
            "schema_inspection",
            "council_of_models",
            "translation_agent",
          ],
          stepDetails: {
            ...prev.stepDetails,
            translation: "Translation complete",
          },
        }));
      }
    }

    // Handle message updates (streaming tokens)
    if ("messages" in data && Array.isArray(data.messages)) {
      const lastMessage = data.messages[data.messages.length - 1];
      if (
        lastMessage &&
        typeof lastMessage === "object" &&
        "content" in lastMessage
      ) {
        const content =
          typeof lastMessage.content === "string"
            ? lastMessage.content
            : JSON.stringify(lastMessage.content);

        if (currentMessageRef.current) {
          currentMessageRef.current.content = content;
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === currentMessageRef.current?.id
                ? { ...msg, content, isStreaming: true }
                : msg
            )
          );
        }
      }
    }

    // Handle updates (node executions)
    if ("updates" in data && data.updates) {
      const updates = data.updates as Record<string, unknown>;
      const nodeNames = Object.keys(updates);

      if (nodeNames.length > 0) {
        const latestNode = nodeNames[0];
        const stepMap: Record<string, PipelineStep> = {
          extract_input: "extract_input",
          schema_inspection: "schema_inspection",
          council_of_models: "council_of_models",
          translation_agent: "translation_agent",
        };

        const step = stepMap[latestNode];
        if (step) {
          setPipeline((prev) => ({
            currentStep: step,
            completedSteps: getCompletedSteps(step),
            stepDetails: {
              ...prev.stepDetails,
              [step]: `Processing ${latestNode}`,
            },
          }));
          options.onStepChange?.(step);
        }
      }
    }
  }, [options]);

  // Watch for stream completion
  const streamStatus = thread.isLoading;

  // Effect to handle stream completion
  if (!streamStatus && isStreaming && currentMessageRef.current) {
    // Stream finished
    setMessages((prev) =>
      prev.map((msg) =>
        msg.id === currentMessageRef.current?.id
          ? { ...msg, isStreaming: false }
          : msg
      )
    );
    currentMessageRef.current = null;
    setIsStreaming(false);
    setPipeline((prev) => ({
      ...prev,
      currentStep: "complete",
    }));
  }

  const clearMessages = useCallback(() => {
    setMessages([]);
    setPipeline({
      currentStep: "idle",
      completedSteps: [],
      stepDetails: {},
    });
    setActiveTools([]);
    setError(null);
    threadIdRef.current = null;
  }, []);

  const stopStream = useCallback(() => {
    thread.stop();
    setIsStreaming(false);
    if (currentMessageRef.current) {
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === currentMessageRef.current?.id
            ? { ...msg, isStreaming: false }
            : msg
        )
      );
      currentMessageRef.current = null;
    }
  }, [thread]);

  return {
    messages,
    isStreaming,
    pipeline,
    activeTools,
    error,
    sendMessage,
    clearMessages,
    stopStream,
    threadId: threadIdRef.current,
  };
}

function mapFrameworkToTarget(framework: FrameworkType): string {
  const mapping: Record<FrameworkType, string> = {
    ms_sql_native: "MS SQL Native",
    csharp_efcore_linq: "C# EFCore LINQ",
    csharp_dapper: "C# Dapper",
    csharp_nhibernate_hql: "C# NHibernate HQL",
    java_spring_data_jpa: "Java Spring Data JPA",
    java_spring_data_mongodb: "Java Spring Data MongoDB",
    java_spring_data_neo4j: "Java Spring Data Neo4j",
  };
  return mapping[framework];
}

function getCompletedSteps(currentStep: PipelineStep): PipelineStep[] {
  const order: PipelineStep[] = [
    "extract_input",
    "schema_inspection",
    "council_of_models",
    "translation_agent",
  ];
  const idx = order.indexOf(currentStep);
  if (idx <= 0) return [];
  return order.slice(0, idx);
}
