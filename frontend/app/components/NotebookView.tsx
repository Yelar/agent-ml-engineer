"use client";

import { useEffect, useRef } from "react";
import type { EventMsg } from "@/app/hooks/useSessionEvents";
import Cell from "@/app/components/Cell";

type NotebookViewProps = {
  sessionId?: string;
  events: EventMsg[];
  isActive: boolean;
};

export default function NotebookView({
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
      <section className="flex flex-1 min-h-0 flex-col items-center justify-center bg-slate-950 text-slate-300">
        <p className="rounded-xl border border-dashed border-slate-800 bg-slate-900 px-6 py-10 text-center text-sm">
          Start a conversation to open the notebook workspace.
        </p>
      </section>
    );
  }

  return (
    <section className="flex flex-1 min-h-0 flex-col gap-6 bg-slate-950 px-8 pb-12 pt-8 text-slate-100">
      <header className="shrink-0 space-y-1">
        <h2 className="text-lg font-semibold text-slate-50">Notebook</h2>
        <p className="text-sm text-slate-400">
          Live updates from the current analysis session.
        </p>
      </header>

      {/* 🔑 Ensure this flex parent can shrink */}
      <div className="flex flex-1 min-h-0 flex-col rounded-4xl border border-slate-900/70 bg-slate-950/70 p-6 shadow-[0_48px_120px_-64px_rgba(15,23,42,0.95)] backdrop-blur-xl">
        {/* 🔑 The scroll container with proper scrollbar styling */}
        <div
          ref={eventsRef}
          className="flex flex-1 min-h-0 flex-col space-y-4 overflow-y-auto pr-2"
          style={{
            scrollbarWidth: 'thin',
            scrollbarColor: 'rgb(51 65 85 / 0.5) rgb(15 23 42 / 0.5)'
          }}
        >
          {!hasSession ? (
            <p className="rounded-2xl border border-dashed border-slate-800 bg-slate-900/70 px-6 py-10 text-center text-sm text-slate-300">
              Upload a dataset to start populating the notebook.
            </p>
          ) : events.length === 0 ? (
            <p className="rounded-2xl border border-dashed border-slate-800 bg-slate-900/70 px-6 py-10 text-center text-sm text-slate-300">
              Notebook entries will appear here as the session runs.
            </p>
          ) : (
            events.map((event) => <Cell key={event.event_id} event={event} />)
          )}
        </div>
      </div>
    </section>
  );
}
