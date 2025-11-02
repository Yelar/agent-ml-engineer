"use client";

import { useEffect, useState } from "react";
import { ChatWebSocket } from "@/components/chat-websocket";
import { generateUUID } from "@/lib/utils";

export default function WebSocketChatPage() {
  const [sessionId, setSessionId] = useState<string>("");

  useEffect(() => {
    // Generate or retrieve session ID
    const storedSessionId = sessionStorage.getItem("chat_session_id");
    if (storedSessionId) {
      setSessionId(storedSessionId);
    } else {
      const newSessionId = generateUUID();
      sessionStorage.setItem("chat_session_id", newSessionId);
      setSessionId(newSessionId);
    }
  }, []);

  if (!sessionId) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-muted-foreground">Initializing session...</div>
      </div>
    );
  }

  // WebSocket URL - update this to match your backend
  const websocketUrl = `ws://localhost:8000/ws/${sessionId}`;

  return <ChatWebSocket websocketUrl={websocketUrl} sessionId={sessionId} />;
}

