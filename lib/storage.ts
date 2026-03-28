import type { Conversation, ChatMessage } from "./types";
import { generateId } from "./utils";

const STORAGE_KEY = "uom-chat-history";

export function getConversations(): Conversation[] {
  if (typeof window === "undefined") return [];
  try {
    const data = localStorage.getItem(STORAGE_KEY);
    if (!data) return [];
    const parsed = JSON.parse(data);
    return parsed.map((conv: Conversation) => ({
      ...conv,
      createdAt: new Date(conv.createdAt),
      updatedAt: new Date(conv.updatedAt),
      messages: conv.messages.map((msg: ChatMessage) => ({
        ...msg,
        timestamp: new Date(msg.timestamp),
      })),
    }));
  } catch {
    return [];
  }
}

export function saveConversations(conversations: Conversation[]): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations));
  } catch (error) {
    console.error("Failed to save conversations:", error);
  }
}

export function createConversation(firstMessage?: ChatMessage): Conversation {
  const now = new Date();
  return {
    id: generateId(),
    title: firstMessage?.content.slice(0, 50) || "New Conversation",
    messages: firstMessage ? [firstMessage] : [],
    createdAt: now,
    updatedAt: now,
  };
}

export function addMessageToConversation(
  conversations: Conversation[],
  conversationId: string,
  message: ChatMessage
): Conversation[] {
  return conversations.map((conv) => {
    if (conv.id === conversationId) {
      return {
        ...conv,
        messages: [...conv.messages, message],
        updatedAt: new Date(),
      };
    }
    return conv;
  });
}

export function updateMessageInConversation(
  conversations: Conversation[],
  conversationId: string,
  messageId: string,
  updates: Partial<ChatMessage>
): Conversation[] {
  return conversations.map((conv) => {
    if (conv.id === conversationId) {
      return {
        ...conv,
        messages: conv.messages.map((msg) =>
          msg.id === messageId ? { ...msg, ...updates } : msg
        ),
        updatedAt: new Date(),
      };
    }
    return conv;
  });
}

export function deleteConversation(
  conversations: Conversation[],
  conversationId: string
): Conversation[] {
  return conversations.filter((conv) => conv.id !== conversationId);
}

export function clearAllConversations(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(STORAGE_KEY);
}
