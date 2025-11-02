'use client';
/* eslint-disable @next/next/no-img-element */

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { EventMsg } from '@/app/hooks/useSessionEvents';

const isRecord = (value: unknown): value is Record<string, unknown> =>
  Boolean(value) && typeof value === 'object' && !Array.isArray(value);

const isArrayOfRecords = (value: unknown): value is Array<Record<string, unknown>> =>
  Array.isArray(value) && value.every(isRecord);

const formatTimestamp = (timestamp?: string) => {
  if (!timestamp) return '';
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return '';
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
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
    className="markdown-body text-sm leading-6 text-slate-800"
  >
    {content}
  </ReactMarkdown>
);

type CellProps = {
  event: EventMsg;
};

export default function Cell({ event }: CellProps) {
  const stepLabel = event.step ?? '·';
  const timestamp = formatTimestamp(event.timestamp);

  if (event.type === 'code' && isRecord(event.payload)) {
    const code = typeof event.payload.code === 'string' ? event.payload.code : '';
    const output = typeof event.payload.output === 'string' ? event.payload.output : '';
    const error = typeof event.payload.error === 'string' ? event.payload.error : '';

    return (
      <article className="animate-cell-enter space-y-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <header className="flex items-center justify-between text-xs uppercase tracking-wide text-slate-500">
          <span className="font-semibold text-blue-600">In&nbsp;[{stepLabel}]</span>
          {timestamp ? <span className="text-slate-400">{timestamp}</span> : null}
        </header>
        {code ? (
          <pre className="rounded-lg bg-slate-900/90 p-4 text-xs font-mono leading-6 text-slate-100 shadow-inner">
            {code}
          </pre>
        ) : null}
        {output ? (
          <section className="space-y-2">
            <div className="text-xs uppercase tracking-wide text-emerald-600">Out&nbsp;[{stepLabel}]</div>
            <pre className="rounded-lg bg-slate-50 p-4 text-sm leading-6 text-slate-800">{output}</pre>
          </section>
        ) : null}
        {error ? (
          <section className="space-y-2">
            <div className="text-xs uppercase tracking-wide text-red-600">Error</div>
            <pre className="rounded-lg bg-red-50 p-4 text-sm leading-6 text-red-700">{error}</pre>
          </section>
        ) : null}
      </article>
    );
  }

  if (event.type === 'plot' && isRecord(event.payload) && typeof event.payload.image === 'string') {
    return (
      <article className="animate-cell-enter space-y-3 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <header className="flex items-center justify-between text-xs uppercase tracking-wide text-slate-500">
          <span className="font-semibold text-slate-700">Figure&nbsp;{stepLabel}</span>
          {timestamp ? <span className="text-slate-400">{timestamp}</span> : null}
        </header>
        <img
          src={`data:image/png;base64,${event.payload.image}`}
          alt={`Notebook figure ${stepLabel}`}
          className="max-h-[420px] w-full rounded-lg border border-slate-200 bg-slate-50 object-contain p-2"
        />
      </article>
    );
  }

  if (event.type === 'plan' && isRecord(event.payload) && typeof event.payload.content === 'string') {
    return (
      <article className="animate-cell-enter space-y-3 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <header className="flex items-center justify-between text-xs uppercase tracking-wide text-slate-500">
          <span className="font-semibold text-slate-700">Plan</span>
          {timestamp ? <span className="text-slate-400">{timestamp}</span> : null}
        </header>
        <MarkdownBlock content={event.payload.content} />
      </article>
    );
  }

  if (
    event.type === 'assistant_message' &&
    isRecord(event.payload) &&
    typeof event.payload.content === 'string'
  ) {
    return (
      <article className="animate-cell-enter space-y-3 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <header className="flex items-center justify-between text-xs uppercase tracking-wide text-slate-500">
          <span className="font-semibold text-slate-700">Summary</span>
          {timestamp ? <span className="text-slate-400">{timestamp}</span> : null}
        </header>
        <MarkdownBlock content={event.payload.content} />
      </article>
    );
  }

  if (event.type === 'metadata' && isRecord(event.payload)) {
    return (
      <article className="animate-cell-enter space-y-3 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <header className="flex items-center justify-between text-xs uppercase tracking-wide text-slate-500">
          <span className="font-semibold text-slate-700">Run Metadata</span>
          {timestamp ? <span className="text-slate-400">{timestamp}</span> : null}
        </header>
        <dl className="grid grid-cols-1 gap-2 text-sm text-slate-700 md:grid-cols-2">
          {Object.entries(event.payload).map(([key, value]) => (
            <div key={key} className="rounded-lg bg-slate-50 px-3 py-2">
              <dt className="text-xs uppercase tracking-wide text-slate-500">{key}</dt>
              <dd className="break-all text-slate-800">{String(value ?? '')}</dd>
            </div>
          ))}
        </dl>
      </article>
    );
  }

  if (event.type === 'artifacts' && isRecord(event.payload)) {
    const items = isArrayOfRecords(event.payload.items) ? event.payload.items : [];
    return (
      <article className="animate-cell-enter space-y-3 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <header className="flex items-center justify-between text-xs uppercase tracking-wide text-slate-500">
          <span className="font-semibold text-slate-700">Artifacts</span>
          {timestamp ? <span className="text-slate-400">{timestamp}</span> : null}
        </header>
        {items.length === 0 ? (
          <p className="text-sm text-slate-600">No downloadable artifacts were produced.</p>
        ) : (
          <ul className="space-y-2 text-sm text-blue-600">
            {items.map((item, itemIndex) => {
              const name = typeof item.name === 'string' ? item.name : 'artifact';
              const url = typeof item.url === 'string' ? item.url : undefined;
              const kind = typeof item.kind === 'string' ? item.kind : 'artifact';
              return (
                <li
                  key={url ?? `${name}-${itemIndex}`}
                  className="flex items-center gap-3"
                >
                  <span className="rounded-full bg-blue-50 px-2 py-0.5 text-[11px] font-medium uppercase text-blue-500">
                    {kind}
                  </span>
                  {url ? (
                    <a
                      className="underline decoration-blue-400 decoration-dotted underline-offset-2 hover:text-blue-700"
                      href={url}
                      download
                      target="_blank"
                      rel="noreferrer"
                    >
                      {name}
                    </a>
                  ) : (
                    <span className="text-slate-600">{name}</span>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </article>
    );
  }

  if (event.type === 'status' && isRecord(event.payload)) {
    const stage = typeof event.payload.stage === 'string' ? event.payload.stage : 'pending';
    const message =
      typeof event.payload.message === 'string'
        ? event.payload.message
        : typeof event.payload.prompt === 'string'
        ? `Prompt: ${event.payload.prompt}`
        : 'Agent status updated.';

    return (
      <article className="animate-cell-enter space-y-2 rounded-xl border border-dashed border-slate-300 bg-slate-50 p-4 text-sm text-slate-600">
        <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{stage}</div>
        <p>{message}</p>
      </article>
    );
  }

  const fallback =
    typeof event.payload === 'string'
      ? event.payload
      : JSON.stringify(event.payload, null, 2);

  return (
    <article className="animate-cell-enter space-y-3 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <header className="flex items-center justify-between text-xs uppercase tracking-wide text-slate-500">
        <span className="font-semibold text-slate-700">{event.type}</span>
        {timestamp ? <span className="text-slate-400">{timestamp}</span> : null}
      </header>
      <MarkdownBlock content={fallback} />
    </article>
  );
}
