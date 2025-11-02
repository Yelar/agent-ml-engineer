'use client';
/* eslint-disable @next/next/no-img-element */

import ReactMarkdown, { type Components } from 'react-markdown';
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

const markdownComponents: Components = {
  a: ({ children, href, ...props }) => (
    <a
      {...props}
      href={href}
      target="_blank"
      rel="noreferrer"
      className="underline decoration-dotted underline-offset-2 transition hover:text-white"
    >
      {children}
    </a>
  ),
  pre: ({ children, ...props }) => (
    <pre
      {...props}
      className="overflow-x-auto rounded-2xl border border-slate-800 bg-slate-950/80 p-4 text-xs font-mono leading-6 text-slate-100 shadow-inner"
    >
      {children}
    </pre>
  ),
  code: ({ children, ...props }) => (
    <code {...props} className="rounded-md bg-slate-900/60 px-1.5 py-0.5 text-[0.85rem]">
      {children}
    </code>
  ),
  p: ({ children, ...props }) => (
    <p {...props} className="mb-3 last:mb-0">
      {children}
    </p>
  ),
  ul: ({ children, ...props }) => (
    <ul {...props} className="mb-3 list-disc pl-5 last:mb-0">
      {children}
    </ul>
  ),
  ol: ({ children, ...props }) => (
    <ol {...props} className="mb-3 list-decimal pl-5 last:mb-0">
      {children}
    </ol>
  ),
  blockquote: ({ children, ...props }) => (
    <blockquote
      {...props}
      className="mb-3 rounded-2xl border-l-2 border-slate-700 bg-slate-900/70 px-4 py-2 last:mb-0"
    >
      {children}
    </blockquote>
  ),
};

const MarkdownBlock = ({ content }: { content: string }) => (
  <ReactMarkdown
    remarkPlugins={[remarkGfm]}
    components={markdownComponents}
    className="markdown-body text-sm leading-6 text-slate-100"
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
      <article className="animate-cell-enter space-y-4 rounded-3xl border border-slate-800/80 bg-slate-900/80 p-6 shadow-[0_32px_90px_-50px_rgba(15,23,42,0.9)]">
        <header className="flex items-center justify-between text-xs uppercase tracking-wide text-slate-400">
          <span className="font-semibold text-slate-100">In&nbsp;[{stepLabel}]</span>
          {timestamp ? <span className="text-slate-500">{timestamp}</span> : null}
        </header>
        {code ? (
          <pre className="overflow-x-auto rounded-2xl border border-slate-800 bg-slate-950/80 p-4 text-xs font-mono leading-6 text-slate-100 shadow-inner break-words whitespace-pre-wrap">
            {code}
          </pre>
        ) : null}
        {output ? (
          <section className="space-y-2">
            <div className="text-xs uppercase tracking-wide text-slate-300">Out&nbsp;[{stepLabel}]</div>
            <pre className="overflow-x-auto rounded-2xl border border-slate-800 bg-slate-900/80 p-4 text-sm leading-6 text-slate-100 break-words whitespace-pre-wrap max-h-96 overflow-y-auto">
              {output}
            </pre>
          </section>
        ) : null}
        {error ? (
          <section className="space-y-2">
            <div className="text-xs uppercase tracking-wide text-red-300">Error</div>
            <pre className="overflow-x-auto rounded-2xl border border-red-500/30 bg-red-900/40 p-4 text-sm leading-6 text-red-200">
              {error}
            </pre>
          </section>
        ) : null}
      </article>
    );
  }

  if (event.type === 'plot' && isRecord(event.payload) && typeof event.payload.image === 'string') {
    return (
      <article className="animate-cell-enter space-y-3 rounded-3xl border border-slate-800/80 bg-slate-900/80 p-6 shadow-[0_32px_90px_-50px_rgba(15,23,42,0.9)]">
        <header className="flex items-center justify-between text-xs uppercase tracking-wide text-slate-400">
          <span className="font-semibold text-slate-100">Figure&nbsp;{stepLabel}</span>
          {timestamp ? <span className="text-slate-500">{timestamp}</span> : null}
        </header>
        <div className="flex justify-center overflow-hidden rounded-2xl border border-slate-800 bg-slate-950/80">
          <img
            src={`data:image/png;base64,${event.payload.image}`}
            alt={`Notebook figure ${stepLabel}`}
            className="max-h-[500px] max-w-full object-contain p-4"
            style={{ imageRendering: 'auto' }}
          />
        </div>
      </article>
    );
  }

  if (event.type === 'plan' && isRecord(event.payload) && typeof event.payload.content === 'string') {
    return (
      <article className="animate-cell-enter space-y-3 rounded-3xl border border-slate-800/80 bg-slate-900/80 p-6 shadow-[0_32px_90px_-50px_rgba(15,23,42,0.9)]">
        <header className="flex items-center justify-between text-xs uppercase tracking-wide text-slate-400">
          <span className="font-semibold text-slate-100">Plan</span>
          {timestamp ? <span className="text-slate-500">{timestamp}</span> : null}
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
      <article className="animate-cell-enter space-y-3 rounded-3xl border border-slate-800/80 bg-slate-900/80 p-6 shadow-[0_32px_90px_-50px_rgba(15,23,42,0.9)]">
        <header className="flex items-center justify-between text-xs uppercase tracking-wide text-slate-400">
          <span className="font-semibold text-slate-100">Summary</span>
          {timestamp ? <span className="text-slate-500">{timestamp}</span> : null}
        </header>
        <MarkdownBlock content={event.payload.content} />
      </article>
    );
  }

  if (event.type === 'metadata' && isRecord(event.payload)) {
    return (
      <article className="animate-cell-enter space-y-3 rounded-3xl border border-slate-800/80 bg-slate-900/80 p-6 shadow-[0_32px_90px_-50px_rgba(15,23,42,0.9)]">
        <header className="flex items-center justify-between text-xs uppercase tracking-wide text-slate-400">
          <span className="font-semibold text-slate-100">Run Metadata</span>
          {timestamp ? <span className="text-slate-500">{timestamp}</span> : null}
        </header>
        <dl className="grid grid-cols-1 gap-2 text-sm text-slate-200 md:grid-cols-2">
          {Object.entries(event.payload).map(([key, value]) => (
            <div
              key={key}
              className="rounded-2xl border border-slate-800/70 bg-slate-950/70 px-3 py-2"
            >
              <dt className="text-xs uppercase tracking-wide text-slate-400">{key}</dt>
              <dd className="break-words text-slate-100">{String(value ?? '')}</dd>
            </div>
          ))}
        </dl>
      </article>
    );
  }

  if (event.type === 'artifacts' && isRecord(event.payload)) {
    const items = isArrayOfRecords(event.payload.items) ? event.payload.items : [];
    return (
      <article className="animate-cell-enter space-y-3 rounded-3xl border border-slate-800/80 bg-slate-900/80 p-6 shadow-[0_32px_90px_-50px_rgba(15,23,42,0.9)]">
        <header className="flex items-center justify-between text-xs uppercase tracking-wide text-slate-400">
          <span className="font-semibold text-slate-100">Artifacts</span>
          {timestamp ? <span className="text-slate-500">{timestamp}</span> : null}
        </header>
        {items.length === 0 ? (
          <p className="text-sm text-slate-300">No downloadable artifacts were produced.</p>
        ) : (
          <ul className="space-y-2 text-sm text-slate-100">
            {items.map((item, itemIndex) => {
              const name = typeof item.name === 'string' ? item.name : 'artifact';
              const url = typeof item.url === 'string' ? item.url : undefined;
              const kind = typeof item.kind === 'string' ? item.kind : 'artifact';
              return (
                <li
                  key={url ?? `${name}-${itemIndex}`}
                  className="flex items-center gap-3"
                >
                  <span className="rounded-full bg-slate-800/80 px-2 py-0.5 text-[11px] font-medium uppercase text-slate-200">
                    {kind}
                  </span>
                  {url ? (
                    <a
                      className="underline decoration-slate-300 decoration-dotted underline-offset-2 hover:text-white"
                      href={url}
                      download
                      target="_blank"
                      rel="noreferrer"
                    >
                      {name}
                    </a>
                  ) : (
                    <span className="text-slate-300">{name}</span>
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
      <article className="animate-cell-enter space-y-2 rounded-3xl border border-dashed border-slate-800/80 bg-slate-900/70 p-5 text-sm text-slate-200 shadow-[0_24px_60px_-40px_rgba(15,23,42,0.8)]">
        <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">{stage}</div>
        <p className="whitespace-pre-wrap break-words">{message}</p>
      </article>
    );
  }

  const fallback =
    typeof event.payload === 'string'
      ? event.payload
      : JSON.stringify(event.payload, null, 2);

  return (
    <article className="animate-cell-enter space-y-3 rounded-3xl border border-slate-800/80 bg-slate-900/80 p-6 shadow-[0_32px_90px_-50px_rgba(15,23,42,0.9)]">
      <header className="flex items-center justify-between text-xs uppercase tracking-wide text-slate-400">
        <span className="font-semibold text-slate-100">{event.type}</span>
        {timestamp ? <span className="text-slate-500">{timestamp}</span> : null}
      </header>
      <MarkdownBlock content={fallback} />
    </article>
  );
}
