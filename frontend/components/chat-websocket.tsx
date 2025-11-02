"use client";

import { useEffect, useState, useCallback } from "react";
import { useWebSocket } from "use-websocket";
import type {
  WebSocketMessage,
  DocumentBlock,
  ChatMessageSimple,
} from "@/lib/websocket-types";
import { AgentDocument } from "@/components/agent-document";
import { ChatList } from "@/components/chat-list";
import { ChatInput } from "@/components/chat-input";
import { generateUUID } from "@/lib/utils";

// ReadyState type (0-3)
type ReadyState = 0 | 1 | 2 | 3;

const ReadyStateEnum = {
  CONNECTING: 0 as ReadyState,
  OPEN: 1 as ReadyState,
  CLOSING: 2 as ReadyState,
  CLOSED: 3 as ReadyState,
};

interface ChatWebSocketProps {
  websocketUrl: string;
  sessionId: string;
}

export function ChatWebSocket({ websocketUrl, sessionId }: ChatWebSocketProps) {
  const [messages, setMessages] = useState<ChatMessageSimple[]>([]);
  const [documentBlocks, setDocumentBlocks] = useState<DocumentBlock[]>([]);
  const [isPanelOpen, setIsPanelOpen] = useState(false);
  const [inputValue, setInputValue] = useState("");

  const { webSocket, readyState } = useWebSocket(websocketUrl, {
    onMessage: (event: MessageEvent) => {
      try {
        const message = JSON.parse(event.data) as WebSocketMessage;
        handleWebSocketMessage(message);
      } catch (error) {
        console.error("Failed to parse WebSocket message:", error);
      }
    },
    onOpen: () => {
      console.log("WebSocket connected");
    },
    onClose: () => {
      console.log("WebSocket disconnected");
    },
    onError: (error) => {
      console.error("WebSocket error:", error);
    },
  });

  // Handle incoming WebSocket messages
  const handleWebSocketMessage = useCallback((message: WebSocketMessage) => {
    switch (message.type) {
      case "create_document":
        setIsPanelOpen(true);
        break;

      case "append_to_document":
        setDocumentBlocks((prev) => [...prev, message.payload]);
        break;

      case "final_answer":
        setMessages((prev) => [
          ...prev,
          {
            id: generateUUID(),
            role: "assistant",
            content: message.payload,
            timestamp: Date.now(),
          },
        ]);
        break;
    }
  }, []);

  const handleSendMessage = useCallback(
    (content: string) => {
      if (!content.trim() || !webSocket || readyState !== ReadyStateEnum.OPEN) return;

      // Add user message to chat
      const userMessage: ChatMessageSimple = {
        id: generateUUID(),
        role: "user",
        content,
        timestamp: Date.now(),
      };

      setMessages((prev) => [...prev, userMessage]);

      // Send to backend via WebSocket
      const message = {
        type: "user_message",
        payload: {
          session_id: sessionId,
          message: content,
        },
      };
      webSocket.send(JSON.stringify(message));

      setInputValue("");
    },
    [webSocket, readyState, sessionId]
  );

  const connectionStatus = {
    [ReadyStateEnum.CONNECTING]: "Connecting",
    [ReadyStateEnum.OPEN]: "Connected",
    [ReadyStateEnum.CLOSING]: "Closing",
    [ReadyStateEnum.CLOSED]: "Disconnected",
  }[readyState] || "Unknown";

  return (
    <div className="flex h-dvh">
      {/* Main Chat Column */}
      <div
        className={`flex flex-col transition-all duration-300 ${
          isPanelOpen ? "w-[40%]" : "w-full"
        }`}
      >
        {/* Connection Status */}
        <div className="border-b bg-muted/50 px-4 py-2 text-xs text-muted-foreground">
          Status: {connectionStatus}
        </div>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto">
          <ChatList messages={messages} />
        </div>

        {/* Input Area */}
        <div className="border-t bg-background p-4">
          <ChatInput
            value={inputValue}
            onChange={setInputValue}
            onSend={handleSendMessage}
            disabled={readyState !== ReadyStateEnum.OPEN}
          />
        </div>
      </div>

      {/* Document Panel (conditionally rendered) */}
      {isPanelOpen && (
        <div className="w-[60%] transition-all duration-300">
          <AgentDocument documentBlocks={documentBlocks} />
        </div>
      )}
    </div>
  );
}

