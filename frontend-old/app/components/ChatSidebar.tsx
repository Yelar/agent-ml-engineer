'use client';

import { type FormEvent, useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { ChatMessage } from '@/app/types/chat';
import { Button } from '@/app/components/ui/button';
import { Input } from '@/app/components/ui/input';

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
    <aside className="flex h-screen shrink-0 flex-col gap-6 overflow-hidden bg-muted/30 px-6 py-8">
      <header className="space-y-2">
        <h2 className="text-lg font-semibold text-foreground">Chat</h2>
        <p className="text-sm text-muted-foreground">Ask questions and review agent responses.</p>
      </header>
      <div
        ref={messagesRef}
        className="flex flex-1 flex-col space-y-3 overflow-y-auto pr-2"
        aria-live="polite"
      >
        {!canSend ? (
          <p className="rounded-xl bg-muted p-4 text-center text-sm text-muted-foreground">
            Upload at least one dataset to begin.
          </p>
        ) : messages.length === 0 ? (
          <p className="rounded-xl bg-muted p-4 text-center text-sm text-muted-foreground">
            Start a conversation to see responses here.
          </p>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`max-w-[260px] rounded-2xl px-4 py-2 text-sm leading-6 shadow-sm ${
                message.role === 'user'
                  ? 'self-end bg-primary text-primary-foreground'
                  : 'self-start bg-card text-foreground'
              }`}
            >
              {message.role === 'assistant' ? (
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  className="prose prose-sm dark:prose-invert text-sm leading-6 [&>*:first-child]:mt-0"
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
      <form className="flex items-center gap-2 border-t border-border pt-4" onSubmit={handleSubmit}>
        <Input
          className="flex-1"
          placeholder="Ask about your model..."
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          autoComplete="off"
          disabled={!canSend || isSending}
          aria-label="Send a message to the agent"
        />
        <Button type="submit" disabled={!canSend || isSending}>
          {isSending ? 'Sending…' : 'Send'}
        </Button>
      </form>
    </aside>
  );
}
