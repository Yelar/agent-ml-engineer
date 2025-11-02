"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type {
  EventMsg,
  CodeEventPayload,
  PlotEventPayload,
  StatusEventPayload,
  AssistantMessagePayload,
  PlanPayload,
} from "@/lib/websocket-types";

const isRecord = (value: unknown): value is Record<string, unknown> =>
  Boolean(value) && typeof value === "object" && !Array.isArray(value);

const isArrayOfRecords = (
  value: unknown,
): value is Array<Record<string, unknown>> =>
  Array.isArray(value) && value.every(isRecord);

const formatTimestamp = (timestamp?: string) => {
  if (!timestamp) return "";
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
};

const MarkdownBlock = ({ content }: { content: string }) => (
  <ReactMarkdown
    remarkPlugins={[remarkGfm]}
    components={{
      a: ({ children, href, ...props }) => (
        <a
          {...props}
          href={href}
          target="_blank"
          rel="noreferrer"
          className="underline decoration-dotted"
        >
          {children}
        </a>
      ),
    }}
    className="prose prose-sm dark:prose-invert max-w-none text-sm leading-6"
  >
    {content}
  </ReactMarkdown>
);

interface NotebookCellProps {
  event: EventMsg;
}

export function NotebookCell({ event }: NotebookCellProps) {
  const stepLabel = event.step ?? "·";
  const timestamp = formatTimestamp(event.timestamp);

  if (event.type === "code" && isRecord(event.payload)) {
    const payload = event.payload as CodeEventPayload;
    const code =
      typeof payload.code === "string"
        ? payload.code
        : typeof payload.snippet === "string"
        ? payload.snippet
        : "";
    const output = typeof payload.output === "string" ? payload.output : "";
    const error = typeof payload.error === "string" ? payload.error : "";

    return (
      <article className="animate-in fade-in-50 duration-300 space-y-4 rounded-xl border border-border bg-card p-5 shadow-sm">
        <header className="flex items-center justify-between text-xs uppercase tracking-wide text-muted-foreground">
          <span className="font-semibold text-primary">
            In&nbsp;[{stepLabel}]
          </span>
          {timestamp ? <span className="text-muted-foreground">{timestamp}</span> : null}
        </header>
        {code ? (
          <pre className="rounded-lg bg-slate-900/90 dark:bg-slate-950 p-4 text-xs font-mono leading-6 text-slate-100 shadow-inner overflow-x-auto">
            {code}
          </pre>
        ) : null}
        {output ? (
          <section className="space-y-2">
            <div className="text-xs uppercase tracking-wide text-emerald-600 dark:text-emerald-400">
              Out&nbsp;[{stepLabel}]
            </div>
            <pre className="rounded-lg bg-muted p-4 text-sm leading-6 overflow-x-auto">
              {output}
            </pre>
          </section>
        ) : null}
        {error ? (
          <section className="space-y-2">
            <div className="text-xs uppercase tracking-wide text-destructive">
              Error
            </div>
            <pre className="rounded-lg bg-destructive/10 p-4 text-sm leading-6 text-destructive overflow-x-auto">
              {error}
            </pre>
          </section>
        ) : null}
      </article>
    );
  }

  if (
    event.type === "plot" &&
    isRecord(event.payload) &&
    typeof (event.payload as PlotEventPayload).image === "string"
  ) {
    const payload = event.payload as PlotEventPayload;
    return (
      <article className="animate-in fade-in-50 duration-300 space-y-3 rounded-xl border border-border bg-card p-5 shadow-sm">
        <header className="flex items-center justify-between text-xs uppercase tracking-wide text-muted-foreground">
          <span className="font-semibold">Figure&nbsp;{stepLabel}</span>
          {timestamp ? <span className="text-muted-foreground">{timestamp}</span> : null}
        </header>
        <img
          src={`data:image/png;base64,${payload.image}`}
          alt={`Notebook figure ${stepLabel}`}
          className="max-h-[420px] w-full rounded-lg border border-border bg-muted/30 object-contain p-2"
        />
      </article>
    );
  }

  if (
    event.type === "plan" &&
    isRecord(event.payload) &&
    typeof (event.payload as PlanPayload).content === "string"
  ) {
    const payload = event.payload as PlanPayload;
    return (
      <article className="animate-in fade-in-50 duration-300 space-y-3 rounded-xl border border-border bg-card p-5 shadow-sm">
        <header className="flex items-center justify-between text-xs uppercase tracking-wide text-muted-foreground">
          <span className="font-semibold">Plan</span>
          {timestamp ? <span className="text-muted-foreground">{timestamp}</span> : null}
        </header>
        <MarkdownBlock content={payload.content} />
      </article>
    );
  }

  if (
    event.type === "assistant_message" &&
    isRecord(event.payload) &&
    typeof (event.payload as AssistantMessagePayload).content === "string"
  ) {
    const payload = event.payload as AssistantMessagePayload;
    return (
      <article className="animate-in fade-in-50 duration-300 space-y-3 rounded-xl border border-border bg-card p-5 shadow-sm">
        <header className="flex items-center justify-between text-xs uppercase tracking-wide text-muted-foreground">
          <span className="font-semibold">Summary</span>
          {timestamp ? <span className="text-muted-foreground">{timestamp}</span> : null}
        </header>
        <MarkdownBlock content={payload.content} />
      </article>
    );
  }

  if (event.type === "metadata" && isRecord(event.payload)) {
    return (
      <article className="animate-in fade-in-50 duration-300 space-y-3 rounded-xl border border-border bg-card p-5 shadow-sm">
        <header className="flex items-center justify-between text-xs uppercase tracking-wide text-muted-foreground">
          <span className="font-semibold">Run Metadata</span>
          {timestamp ? <span className="text-muted-foreground">{timestamp}</span> : null}
        </header>
        <dl className="grid grid-cols-1 gap-2 text-sm text-foreground md:grid-cols-2">
          {Object.entries(event.payload).map(([key, value]) => (
            <div key={key} className="rounded-lg bg-muted px-3 py-2">
              <dt className="text-xs uppercase tracking-wide text-muted-foreground">
                {key}
              </dt>
              <dd className="break-all">{String(value ?? "")}</dd>
            </div>
          ))}
        </dl>
      </article>
    );
  }

  if (event.type === "artifacts" && isRecord(event.payload)) {
    const items = isArrayOfRecords(event.payload.items)
      ? event.payload.items
      : [];
    return (
      <article className="animate-in fade-in-50 duration-300 space-y-3 rounded-xl border border-border bg-card p-5 shadow-sm">
        <header className="flex items-center justify-between text-xs uppercase tracking-wide text-muted-foreground">
          <span className="font-semibold">Artifacts</span>
          {timestamp ? <span className="text-muted-foreground">{timestamp}</span> : null}
        </header>
        {items.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No downloadable artifacts were produced.
          </p>
        ) : (
          <ul className="space-y-2 text-sm text-primary">
            {items.map((item, itemIndex) => {
              const name = typeof item.name === "string" ? item.name : "artifact";
              const url = typeof item.url === "string" ? item.url : undefined;
              const kind = typeof item.kind === "string" ? item.kind : "artifact";
              return (
                <li
                  key={url ?? `${name}-${itemIndex}`}
                  className="flex items-center gap-3"
                >
                  <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[11px] font-medium uppercase">
                    {kind}
                  </span>
                  {url ? (
                    <a
                      className="underline decoration-primary/40 decoration-dotted underline-offset-2 hover:decoration-solid"
                      href={url}
                      download
                      target="_blank"
                      rel="noreferrer"
                    >
                      {name}
                    </a>
                  ) : (
                    <span className="text-muted-foreground">{name}</span>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </article>
    );
  }

  if (event.type === "status" && isRecord(event.payload)) {
    const payload = event.payload as StatusEventPayload;
    const stage = typeof payload.stage === "string" ? payload.stage : "pending";
    const message =
      typeof payload.message === "string"
        ? payload.message
        : typeof payload.prompt === "string"
        ? `Prompt: ${payload.prompt}`
        : "Agent status updated.";

    return (
      <article className="animate-in fade-in-50 duration-300 space-y-2 rounded-xl border border-dashed border-border bg-muted/50 p-4 text-sm">
        <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          {stage}
        </div>
        <p className="text-foreground">{message}</p>
      </article>
    );
  }

  const fallback =
    typeof event.payload === "string"
      ? event.payload
      : JSON.stringify(event.payload, null, 2);

  return (
    <article className="animate-in fade-in-50 duration-300 space-y-3 rounded-xl border border-border bg-card p-5 shadow-sm">
      <header className="flex items-center justify-between text-xs uppercase tracking-wide text-muted-foreground">
        <span className="font-semibold">{event.type}</span>
        {timestamp ? <span className="text-muted-foreground">{timestamp}</span> : null}
      </header>
      <MarkdownBlock content={fallback} />
    </article>
  );
}

