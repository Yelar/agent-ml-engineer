'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

export interface EventMsg {
  event_id: string;
  type: string;
  step?: string;
  payload: unknown;
  timestamp?: string;
}

type UseSessionEventsOptions = {
  connect?: boolean;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:8000';

export function useSessionEvents(
  sessionId?: string,
  { connect = true }: UseSessionEventsOptions = {},
) {
  const [events, setEvents] = useState<EventMsg[]>([]);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- clear cached events when the session changes
    setEvents([]);
    return () => {
      socketRef.current?.close();
      socketRef.current = null;
    };
  }, [sessionId]);

  useEffect(() => {
    if (!sessionId || !connect) return undefined;

    const url = new URL(`/sessions/${sessionId}/events`, API_BASE);
    url.protocol = url.protocol.replace('http', 'ws');
    const socket = new WebSocket(url.toString());
    socketRef.current = socket;

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as EventMsg;
        setEvents((prev) => [...prev, data]);
      } catch (error) {
        console.error('Failed to parse event payload', error);
      }
    };

    socket.onerror = (error) => {
      console.error('Session event socket error', error);
    };

    return () => {
      socket.close();
      socketRef.current = null;
    };
  }, [sessionId, connect]);

  const resetEvents = useCallback(() => setEvents([]), []);

  return { events, resetEvents };
}
