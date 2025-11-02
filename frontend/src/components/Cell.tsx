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
    <article className="animate-cell-enter flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <header className="flex items-center gap-3 text-xs uppercase tracking-wide text-slate-500">
        <span className="font-semibold text-slate-700">{event.type}</span>
        {event.step ? (
          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-600">
            Step {event.step}
          </span>
        ) : null}
      </header>
      <pre className="overflow-x-auto whitespace-pre-wrap wrap-break-word font-mono text-sm leading-6 text-slate-800">
        {payload}
      </pre>
    </article>
  );
}
