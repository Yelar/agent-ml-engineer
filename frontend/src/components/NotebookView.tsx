import { JSX } from "react";
import { useSessionEvents } from "../hooks/useSessionEvents";
import Cell from "./Cell";

export default function NotebookView(): JSX.Element {
  const sessionId = "test-session"; // temporary until upload implemented
  const events = useSessionEvents(sessionId);

  return (
    <section className="notebook-view">
      <header className="notebook-view__header">
        <h2>Notebook</h2>
        <p>Live updates from the current analysis session.</p>
      </header>
      <div className="notebook-view__events">
        {events.length === 0 ? (
          <p className="notebook-view__empty">
            Notebook entries will appear here as the session runs.
          </p>
        ) : (
          events.map((event) => <Cell key={event.event_id} event={event} />)
        )}
      </div>
    </section>
  );
}
