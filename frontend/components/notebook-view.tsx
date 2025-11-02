"use client";

import { useEffect, useRef } from "react";
import type { EventMsg } from "@/lib/websocket-types";
import { NotebookCell } from "@/components/notebook-cell";

interface NotebookViewProps {
  sessionId?: string;
  events: EventMsg[];
  isActive: boolean;
}

export function NotebookView({
  sessionId,
  events,
  isActive,
}: NotebookViewProps) {
  const eventsRef = useRef<HTMLDivElement | null>(null);
  const hasSession = Boolean(sessionId);

  useEffect(() => {
    if (!eventsRef.current) return;
    eventsRef.current.scrollTo({
      top: eventsRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [events]);

  if (!isActive) {
    return (
      <section className="flex flex-1 flex-col items-center justify-center bg-background">
        <p className="rounded-xl border border-dashed border-border bg-muted px-6 py-10 text-center text-sm text-muted-foreground">
          Start a conversation to open the notebook workspace.
        </p>
      </section>
    );
  }

  return (
    <section className="flex flex-1 flex-col gap-6 overflow-hidden px-8 pb-12 pt-8">
      <header className="space-y-1">
        <h2 className="text-lg font-semibold text-foreground">Notebook</h2>
        <p className="text-sm text-muted-foreground">
          Live updates from the current analysis session.
        </p>
      </header>
      <div
        ref={eventsRef}
        className="flex flex-1 flex-col space-y-4 overflow-y-auto pr-4"
      >
        {!hasSession ? (
          <p className="rounded-xl border border-dashed border-border bg-muted px-6 py-10 text-center text-sm text-muted-foreground">
            Upload a dataset to start populating the notebook.
          </p>
        ) : events.length === 0 ? (
          <p className="rounded-xl border border-dashed border-border bg-muted px-6 py-10 text-center text-sm text-muted-foreground">
            Notebook entries will appear here as the session runs.
          </p>
        ) : (
          events.map((event) => (
            <NotebookCell key={event.event_id} event={event} />
          ))
        )}
      </div>
    </section>
  );
}

