// Edit src/hooks/useSessionEvents.ts to include a mock mode for now.

import { useEffect, useState } from "react";

export interface EventMsg {
  event_id: string;
  type: string;
  step?: string;
  payload: any;
}

export function useSessionEvents(sessionId?: string, mock = true) {
  const [events, setEvents] = useState<EventMsg[]>([]);

  useEffect(() => {
    if (mock) {
      // Simulate notebook updates every 2s
      const sequence: EventMsg[] = [
        {
          event_id: crypto.randomUUID(),
          type: "log",
          payload: { message: "Starting EDA..." },
        },
        {
          event_id: crypto.randomUUID(),
          type: "plot",
          payload: {
            figure: {
              data: [{ x: [1, 2, 3], y: [2, 6, 3], type: "bar" }],
              layout: { title: "Sample Plot" },
            },
          },
        },
        {
          event_id: crypto.randomUUID(),
          type: "table",
          payload: {
            columns: ["col", "val"],
            rows: [
              ["a", 1],
              ["b", 2],
            ],
          },
        },
        {
          event_id: crypto.randomUUID(),
          type: "code",
          payload: { snippet: "df['ratio'] = df['x'] / (df['y']+1e-6)" },
        },
        {
          event_id: crypto.randomUUID(),
          type: "metric",
          payload: { name: "accuracy", value: 0.87 },
        },
      ];
      let i = 0;
      const interval = setInterval(() => {
        if (i < sequence.length) setEvents((prev) => [...prev, sequence[i++]]);
        else clearInterval(interval);
      }, 2000);
      return () => clearInterval(interval);
    }

    // Real WS mode (backend later)
    if (!sessionId) return;
    const ws = new WebSocket(
      `ws://localhost:8000/sessions/${sessionId}/events`
    );
    ws.onmessage = (e) => {
      const data = JSON.parse(e.data);
      setEvents((prev) => [...prev, data]);
    };
    return () => ws.close();
  }, [sessionId, mock]);

  return events;
}
