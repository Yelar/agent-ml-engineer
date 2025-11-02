import type { EventMsg } from "../hooks/useSessionEvents";

type CellProps = {
  event: EventMsg;
};

export default function Cell({ event }: CellProps) {
  const payload =
    typeof event.payload === "string"
      ? event.payload
      : JSON.stringify(event.payload, null, 2);

  return (
    <article className="notebook-cell">
      <header className="notebook-cell__meta">
        <span className="notebook-cell__type">{event.type}</span>
        {event.step ? (
          <span className="notebook-cell__step">Step {event.step}</span>
        ) : null}
      </header>
      <pre className="notebook-cell__payload">{payload}</pre>
    </article>
  );
}
