'use client';

import { type FormEvent, useEffect, useRef, useState } from 'react';
import type { ChatMessage } from '@/app/types/chat';

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
  const [draft, setDraft] = useState('');
  const messagesRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!canSend) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- reset user input when sending is disabled
      setDraft('');
    }
  }, [canSend]);

  useEffect(() => {
    if (!messagesRef.current) return;
    messagesRef.current.scrollTo({
      top: messagesRef.current.scrollHeight,
      behavior: 'smooth',
    });
  }, [messages]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = draft.trim();
    if (!trimmed || isSending || !canSend) return;

    const success = await onSend(trimmed);
    if (success) {
      setDraft('');
    }
  };

  return (
    <aside className="flex h-screen shrink-0 flex-col gap-6 overflow-hidden bg-slate-50 px-6 py-8">
      <header className="space-y-2">
        <h2 className="text-lg font-semibold text-slate-900">Chat</h2>
        <p className="text-sm text-slate-500">Ask questions and review agent responses.</p>
      </header>
      <div
        ref={messagesRef}
        className="flex flex-1 flex-col space-y-3 overflow-y-auto pr-2"
        aria-live="polite"
      >
        {!canSend ? (
          <p className="rounded-xl bg-slate-100 p-4 text-center text-sm text-slate-500">
            Upload at least one dataset to begin.
          </p>
        ) : messages.length === 0 ? (
          <p className="rounded-xl bg-slate-100 p-4 text-center text-sm text-slate-500">
            Start a conversation to see responses here.
          </p>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`max-w-[260px] rounded-2xl px-4 py-2 text-sm leading-6 shadow-sm ${
                message.role === 'user'
                  ? 'self-end bg-blue-500 text-white'
                  : 'self-start bg-slate-100 text-slate-900'
              }`}
            >
              {message.content}
            </div>
          ))
        )}
      </div>
      <form className="flex items-center gap-2 border-t border-slate-200 pt-4" onSubmit={handleSubmit}>
        <input
          className="flex-1 rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100 disabled:bg-slate-100"
          placeholder="Ask about your model..."
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          autoComplete="off"
          disabled={!canSend || isSending}
          aria-label="Send a message to the agent"
        />
        <button
          type="submit"
          className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
          disabled={!canSend || isSending}
        >
          {isSending ? 'Sending…' : 'Send'}
        </button>
      </form>
    </aside>
  );
}
