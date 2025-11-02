import { useEffect, useState } from "react";

export interface EventMsg {
  event_id: string;
  type: string;
  step?: string;
  payload: unknown;
}

export function useSessionEvents(sessionId?: string): EventMsg[] {
  const [events, setEvents] = useState<EventMsg[]>([]);

  useEffect(() => {
    if (!sessionId) return undefined;

    const ws = new WebSocket(
      `ws://localhost:8000/sessions/${sessionId}/events`
    );

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data) as EventMsg;
      setEvents((prev) => [...prev, data]);
    };

    return () => {
      ws.close();
    };
  }, [sessionId]);

  return events;
}
