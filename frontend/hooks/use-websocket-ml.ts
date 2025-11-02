"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { WebSocketMessage, DocumentBlock } from "@/lib/websocket-types";

interface UseWebSocketMLOptions {
  enabled?: boolean;
  backendUrl?: string;
  onCreateDocument?: () => void;
  onDocumentBlock?: (block: DocumentBlock) => void;
  onFinalAnswer?: (content: string) => void;
  onError?: (error: Error) => void;
}

export function useWebSocketML({
  enabled = false,
  backendUrl = "ws://localhost:8000",
  onCreateDocument,
  onDocumentBlock,
  onFinalAnswer,
  onError,
}: UseWebSocketMLOptions = {}) {
  const [isConnected, setIsConnected] = useState(false);
  const [sessionId, setSessionId] = useState<string>("");
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();
  const reconnectAttempts = useRef(0);
  
  // Store callbacks in refs to avoid reconnection loops
  const onCreateDocumentRef = useRef(onCreateDocument);
  const onDocumentBlockRef = useRef(onDocumentBlock);
  const onFinalAnswerRef = useRef(onFinalAnswer);
  const onErrorRef = useRef(onError);

  // Update refs when callbacks change
  useEffect(() => {
    onCreateDocumentRef.current = onCreateDocument;
    onDocumentBlockRef.current = onDocumentBlock;
    onFinalAnswerRef.current = onFinalAnswer;
    onErrorRef.current = onError;
  }, [onCreateDocument, onDocumentBlock, onFinalAnswer, onError]);

  // Generate or retrieve session ID
  useEffect(() => {
    if (enabled) {
      const stored = sessionStorage.getItem("ml_websocket_session_id");
      if (stored) {
        setSessionId(stored);
      } else {
        const newId = crypto.randomUUID();
        sessionStorage.setItem("ml_websocket_session_id", newId);
        setSessionId(newId);
      }
    }
  }, [enabled]);

  const connect = useCallback(() => {
    if (!enabled || !sessionId) {
      return;
    }

    // Prevent connecting if already connected or connecting
    if (wsRef.current?.readyState === WebSocket.OPEN || wsRef.current?.readyState === WebSocket.CONNECTING) {
      console.log("[WebSocket ML] Already connected or connecting, skipping");
      return;
    }

    // Close any existing connection first
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    try {
      console.log(`[WebSocket ML] Connecting to ${backendUrl}/ws/${sessionId}`);
      const ws = new WebSocket(`${backendUrl}/ws/${sessionId}`);

      ws.onopen = () => {
        console.log("[WebSocket ML] Connected");
        setIsConnected(true);
        reconnectAttempts.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as WebSocketMessage;

          switch (message.type) {
            case "create_document":
              onCreateDocumentRef.current?.();
              break;

            case "append_to_document":
              onDocumentBlockRef.current?.(message.payload);
              break;

            case "final_answer":
              onFinalAnswerRef.current?.(message.payload);
              break;
          }
        } catch (error) {
          console.error("[WebSocket ML] Failed to parse message:", error);
          onErrorRef.current?.(error as Error);
        }
      };

      ws.onerror = (error) => {
        console.error("[WebSocket ML] Error:", error);
        onErrorRef.current?.(new Error("WebSocket connection error"));
      };

      ws.onclose = () => {
        console.log("[WebSocket ML] Disconnected");
        setIsConnected(false);

        // Attempt to reconnect with exponential backoff
        if (enabled && reconnectAttempts.current < 5) {
          const delay = Math.min(1000 * 2 ** reconnectAttempts.current, 10000);
          reconnectAttempts.current += 1;

          console.log(
            `[WebSocket ML] Reconnecting in ${delay}ms (attempt ${reconnectAttempts.current})`
          );

          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, delay);
        }
      };

      wsRef.current = ws;
    } catch (error) {
      console.error("[WebSocket ML] Connection failed:", error);
      onErrorRef.current?.(error as Error);
    }
  }, [enabled, sessionId, backendUrl]);

  // Connect when enabled and session ID is ready
  useEffect(() => {
    if (enabled && sessionId) {
      console.log("[WebSocket ML] Effect triggered, attempting to connect");
      connect();
    }

    return () => {
      console.log("[WebSocket ML] Cleanup: closing connection");
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = undefined;
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      reconnectAttempts.current = 0;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, sessionId, backendUrl]);

  const sendMessage = useCallback(
    (type: string, payload?: any) => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type, payload }));
      } else {
        console.warn("[WebSocket ML] Not connected, cannot send message");
      }
    },
    []
  );

  const runMLAnalysis = useCallback(
    (prompt: string, dataset?: string) => {
      sendMessage("user_message", {
        session_id: sessionId,
        message: prompt,
        dataset: dataset || "sample_sales",
      });
    },
    [sessionId, sendMessage]
  );

  return {
    isConnected,
    sendMessage,
    runMLAnalysis,
    sessionId,
  };
}

