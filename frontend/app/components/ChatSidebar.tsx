"use client";

import { type FormEvent, useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ChatMessage } from "@/app/types/chat";

type ChatSidebarProps = {
  messages: ChatMessage[];
  onSend: (message: string) => Promise<boolean>;
  isSending: boolean;
  canSend: boolean;
};

export default function ChatSidebar({
  messages,
  onSend,
  isSending,
  canSend,
}: ChatSidebarProps) {
  const [draft, setDraft] = useState("");
  const messagesRef = useRef<HTMLDivElement | null>(null);
  const markdownComponents = useMemo<Components>(
    () => ({
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
          className="overflow-x-auto rounded-2xl border border-slate-800 bg-slate-950/80 p-3 text-xs font-mono leading-6 text-slate-100 shadow-inner"
        >
          {children}
        </pre>
      ),
      code: ({ children, ...props }) => (
        <code
          {...props}
          className="rounded-md bg-slate-900/70 px-1.5 py-0.5 text-[0.8rem] text-slate-100"
        >
          {children}
        </code>
      ),
      p: ({ children, ...props }) => (
        <p {...props} className="mb-3 last:mb-0">
          {children}
        </p>
      ),
      ul: ({ children, ...props }) => (
        <ul {...props} className="mb-3 list-disc pl-5 text-left last:mb-0">
          {children}
        </ul>
      ),
      ol: ({ children, ...props }) => (
        <ol {...props} className="mb-3 list-decimal pl-5 text-left last:mb-0">
          {children}
        </ol>
      ),
      blockquote: ({ children, ...props }) => (
        <blockquote
          {...props}
          className="mb-3 rounded-xl border-l-2 border-slate-700 bg-slate-900/80 px-4 py-2 text-slate-200 last:mb-0"
        >
          {children}
        </blockquote>
      ),
    }),
    []
  );

  useEffect(() => {
    if (!canSend) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- reset user input when sending is disabled
      setDraft("");
    }
  }, [canSend]);

  useEffect(() => {
    if (!messagesRef.current) return;
    messagesRef.current.scrollTo({
      top: messagesRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = draft.trim();
    if (!trimmed || isSending || !canSend) return;

    const success = await onSend(trimmed);
    if (success) {
      setDraft("");
    }
  };

  return (
    <aside className="flex h-screen w-full shrink-0 flex-col gap-6 overflow-hidden border-r border-slate-900/80 bg-slate-950/90 px-7 py-8 text-slate-100 backdrop-blur-lg">
      <header className="space-y-1">
        <h2 className="text-lg font-semibold tracking-tight text-slate-50">
          Chat
        </h2>
        <p className="text-sm text-slate-400">
          Ask questions and review agent responses.
        </p>
      </header>
      <div
        ref={messagesRef}
        className="flex min-h-0 flex-1 flex-col space-y-3 overflow-y-auto pr-2"
        aria-live="polite"
      >
        {!canSend ? (
          <p className="rounded-xl border border-slate-800 bg-slate-900 p-4 text-center text-sm text-slate-300">
            Upload at least one dataset to begin.
          </p>
        ) : messages.length === 0 ? (
          <p className="rounded-xl border border-slate-800 bg-slate-900 p-4 text-center text-sm text-slate-300">
            Start a conversation to see responses here.
          </p>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`w-fit max-w-full wrap-break-word rounded-3xl px-4 py-3 text-sm leading-6 shadow-lg ring-1 ring-inset ${
                message.role === "user"
                  ? "self-end bg-slate-100 text-slate-900 ring-slate-200/40"
                  : "self-start border border-slate-800/80 bg-slate-900/90 text-slate-100 ring-slate-800/40"
              } [&>*:first-child]:mt-0`}
            >
              {message.role === "assistant" ? (
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={markdownComponents}
                  className="markdown-body text-sm leading-6 text-slate-100 [&>*:first-child]:mt-0"
                >
                  {message.content}
                </ReactMarkdown>
              ) : (
                <span className="whitespace-pre-wrap">{message.content}</span>
              )}
            </div>
          ))
        )}
      </div>
      <form
        className="flex items-center gap-3 rounded-3xl border border-slate-900/80 bg-slate-950/70 px-4 py-3 shadow-lg transition focus-within:border-slate-600 focus-within:shadow-[0_12px_40px_-24px_rgba(15,23,42,0.8)]"
        onSubmit={handleSubmit}
      >
        <input
          className="flex-1 bg-transparent text-sm text-slate-100 placeholder:text-slate-500 outline-none"
          placeholder="Ask about your model..."
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          autoComplete="off"
          disabled={!canSend || isSending}
          aria-label="Send a message to the agent"
        />
        <button
          type="submit"
          className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-slate-100 text-slate-900 shadow-md transition hover:bg-white/90 disabled:cursor-not-allowed disabled:opacity-60"
          disabled={!canSend || isSending}
        >
          {isSending ? (
            <svg
              className="h-4 w-4 animate-spin"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
              />
            </svg>
          ) : (
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              className="h-5 w-5"
            >
              <path d="M12 5l-6 6h4v8h4v-8h4l-6-6z" fill="currentColor" />
            </svg>
          )}
        </button>
      </form>
    </aside>
  );
}
