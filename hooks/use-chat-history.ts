"use client";

import { useState, useEffect, useCallback } from "react";
import {
  getConversations,
  saveConversations,
  createConversation,
  addMessageToConversation,
  deleteConversation,
  clearAllConversations,
} from "@/lib/storage";
import type { Conversation, ChatMessage } from "@/lib/types";

export function useChatHistory() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [isLoaded, setIsLoaded] = useState(false);

  // Load conversations from localStorage on mount
  useEffect(() => {
    const stored = getConversations();
    setConversations(stored);
    if (stored.length > 0) {
      setActiveConversationId(stored[0].id);
    }
    setIsLoaded(true);
  }, []);

  // Save conversations to localStorage when they change
  useEffect(() => {
    if (isLoaded) {
      saveConversations(conversations);
    }
  }, [conversations, isLoaded]);

  const activeConversation = conversations.find(
    (c) => c.id === activeConversationId
  );

  const startNewConversation = useCallback((firstMessage?: ChatMessage) => {
    const newConv = createConversation(firstMessage);
    setConversations((prev) => [newConv, ...prev]);
    setActiveConversationId(newConv.id);
    return newConv.id;
  }, []);

  const addMessage = useCallback(
    (message: ChatMessage) => {
      if (!activeConversationId) {
        const newId = startNewConversation(message);
        return newId;
      }
      setConversations((prev) =>
        addMessageToConversation(prev, activeConversationId, message)
      );
      return activeConversationId;
    },
    [activeConversationId, startNewConversation]
  );

  const removeConversation = useCallback(
    (id: string) => {
      setConversations((prev) => deleteConversation(prev, id));
      if (activeConversationId === id) {
        const remaining = conversations.filter((c) => c.id !== id);
        setActiveConversationId(remaining.length > 0 ? remaining[0].id : null);
      }
    },
    [activeConversationId, conversations]
  );

  const clearAll = useCallback(() => {
    clearAllConversations();
    setConversations([]);
    setActiveConversationId(null);
  }, []);

  const selectConversation = useCallback((id: string) => {
    setActiveConversationId(id);
  }, []);

  return {
    conversations,
    activeConversation,
    activeConversationId,
    isLoaded,
    startNewConversation,
    addMessage,
    removeConversation,
    clearAll,
    selectConversation,
  };
}
