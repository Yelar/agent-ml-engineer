'use client';

import { type ChangeEvent, type FormEvent, useEffect, useRef, useState } from 'react';
import type { ChatMessage } from '@/app/types/chat';

type UploadProgress = {
  processed: number;
  total: number;
};

type PreSessionViewProps = {
  messages: ChatMessage[];
  onSend: (message: string) => Promise<boolean>;
  onFilesSelected: (files: FileList) => void;
  isSending: boolean;
  isUploading: boolean;
  progress: UploadProgress | null;
  canSend: boolean;
};

export default function PreSessionView({
  messages,
  onSend,
  onFilesSelected,
  isSending,
  isUploading,
  progress,
  canSend,
}: PreSessionViewProps) {
  const [draft, setDraft] = useState('');
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const transcriptRef = useRef<HTMLDivElement | null>(null);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = draft.trim();
    if (!trimmed || isSending || !canSend) return;

    const success = await onSend(trimmed);
    if (success) {
      setDraft('');
    }
  };

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files || files.length === 0) return;
    onFilesSelected(files);
    event.target.value = '';
  };

  const handleAttach = () => {
    fileInputRef.current?.click();
  };

  useEffect(() => {
    if (!transcriptRef.current) return;
    transcriptRef.current.scrollTo({
      top: transcriptRef.current.scrollHeight,
      behavior: 'smooth',
    });
  }, [messages]);

  return (
    <div className="flex h-screen flex-col bg-white">
      <main ref={transcriptRef} className="flex-1 overflow-y-auto px-8 py-12">
        {messages.length === 0 ? (
          <div className="mx-auto flex h-full max-w-2xl flex-col items-center justify-center text-center">
            <h1 className="text-2xl font-semibold text-slate-900">
              Ready to explore your datasets
            </h1>
            <p className="mt-3 max-w-md text-sm text-slate-500">
              Attach one or more CSV files, ask a question, and the notebook workspace will come alive
              with insights.
            </p>
          </div>
        ) : (
          <div className="mx-auto flex max-w-2xl flex-col space-y-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`w-fit max-w-full rounded-2xl px-4 py-2 text-sm leading-6 shadow-sm ${
                  message.role === 'user'
                    ? 'ml-auto bg-blue-500 text-white'
                    : 'mr-auto bg-slate-100 text-slate-900'
                }`}
              >
                {message.content}
              </div>
            ))}
          </div>
        )}
      </main>
      <form className="border-t border-slate-200 bg-white px-8 py-6" onSubmit={handleSubmit}>
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv"
          multiple
          className="hidden"
          onChange={handleFileChange}
        />
        <div className="flex items-end gap-3">
          <button
            type="button"
            className="rounded-xl border border-slate-300 bg-white p-3 text-slate-500 transition hover:border-slate-400 hover:text-slate-700"
            onClick={handleAttach}
            disabled={isUploading}
            aria-label="Attach datasets"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="currentColor"
              className="h-5 w-5"
            >
              <path d="M15.5 6.5a3.5 3.5 0 0 0-6-2.45L5.3 8.1a2.5 2.5 0 0 0 3.5 3.55l4.6-4.62a.75.75 0 1 1 1.06 1.06L9.86 12.7a4 4 0 0 1-5.66-5.66l4.2-4.05a5 5 0 1 1 7.07 7.07l-5.15 5.16a2.5 2.5 0 0 1-3.54-3.54l3.53-3.55a.75.75 0 1 1 1.06 1.06L8.84 12.9a1 1 0 0 0 1.42 1.4l5.24-5.24a3.47 3.47 0 0 0 1-2.56Z" />
            </svg>
          </button>
          <textarea
            className="h-24 flex-1 resize-none rounded-2xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 shadow-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100 disabled:bg-slate-100"
            placeholder={
              canSend
                ? 'Upload your data and ask anything…'
                : 'Upload at least one dataset to enable prompts…'
            }
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            disabled={isSending}
          />
          <button
            type="submit"
            className="rounded-xl bg-blue-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={isSending || !canSend}
          >
            {isSending ? 'Thinking…' : 'Send'}
          </button>
        </div>
        <div className="mt-3 flex items-center justify-between text-xs text-slate-500">
          <span>
            {isUploading && progress
              ? `Uploading ${progress.processed}/${progress.total} dataset${
                  progress.total > 1 ? 's' : ''
                }…`
              : canSend
              ? 'Dataset uploaded. Ask a question to start the agent.'
              : 'Attach one or many CSV datasets before sending your prompt.'}
          </span>
          {isSending ? <span className="text-blue-600">Generating insights…</span> : null}
        </div>
      </form>
    </div>
  );
}
