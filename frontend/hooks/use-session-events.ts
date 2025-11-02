"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { EventMsg } from "@/lib/websocket-types";

interface UseSessionEventsOptions {
  connect?: boolean;
  backendUrl?: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export function useSessionEvents(
  sessionId?: string,
  { connect = true, backendUrl = API_BASE }: UseSessionEventsOptions = {},
) {
  const [events, setEvents] = useState<EventMsg[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();
  const reconnectAttempts = useRef(0);
  const processedEventsRef = useRef<Set<string>>(new Set());

  // Reset events when session changes
  useEffect(() => {
    setEvents([]);
    processedEventsRef.current.clear();
    return () => {
      socketRef.current?.close();
      socketRef.current = null;
    };
  }, [sessionId]);

  const connectWebSocket = useCallback(() => {
    if (!sessionId || !connect) return;

    // Prevent duplicate connections
    if (
      socketRef.current?.readyState === WebSocket.OPEN ||
      socketRef.current?.readyState === WebSocket.CONNECTING
    ) {
      return;
    }

    // Close existing connection
    if (socketRef.current) {
      socketRef.current.close();
      socketRef.current = null;
    }

    try {
      const url = new URL(`/sessions/${sessionId}/events`, backendUrl);
      url.protocol = url.protocol.replace("http", "ws");
      const socket = new WebSocket(url.toString());
      socketRef.current = socket;

      socket.onopen = () => {
        setIsConnected(true);
        reconnectAttempts.current = 0;
      };

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as EventMsg;
          
          // Deduplicate events
          if (processedEventsRef.current.has(data.event_id)) {
            return;
          }
          processedEventsRef.current.add(data.event_id);
          
          setEvents((prev) => [...prev, data]);
        } catch (error) {
          console.error("Failed to parse event payload", error);
        }
      };

      socket.onerror = (error) => {
        console.error("Session event socket error", error);
      };

      socket.onclose = () => {
        setIsConnected(false);

        // Attempt to reconnect with exponential backoff
        if (connect && reconnectAttempts.current < 5) {
          const delay = Math.min(1000 * 2 ** reconnectAttempts.current, 10000);
          reconnectAttempts.current += 1;

          reconnectTimeoutRef.current = setTimeout(() => {
            connectWebSocket();
          }, delay);
        }
      };
    } catch (error) {
      console.error("Failed to create WebSocket connection", error);
    }
  }, [sessionId, connect, backendUrl]);

  // Connect when session ID and connect flag are ready
  useEffect(() => {
    if (sessionId && connect) {
      connectWebSocket();
    }

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = undefined;
      }
      if (socketRef.current) {
        socketRef.current.close();
        socketRef.current = null;
      }
      reconnectAttempts.current = 0;
    };
  }, [sessionId, connect, connectWebSocket]);

  const resetEvents = useCallback(() => {
    setEvents([]);
    processedEventsRef.current.clear();
  }, []);

  const pushEvent = useCallback((event: EventMsg) => {
    if (processedEventsRef.current.has(event.event_id)) {
      return;
    }
    processedEventsRef.current.add(event.event_id);
    setEvents((prev) => [...prev, event]);
  }, []);

  const sendMessage = useCallback(
    (type: string, payload?: unknown) => {
      if (socketRef.current?.readyState === WebSocket.OPEN) {
        socketRef.current.send(JSON.stringify({ type, payload }));
      } else {
        console.warn("[WebSocket] Not connected, cannot send message");
      }
    },
    [],
  );

  return {
    events,
    isConnected,
    resetEvents,
    pushEvent,
    sendMessage,
  };
}

