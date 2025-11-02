"use client";

import {
  type ChangeEvent,
  type DragEvent,
  type FormEvent,
  useEffect,
  useRef,
  useState,
} from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ChatMessage } from "@/app/types/chat";

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
  const [draft, setDraft] = useState("");
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const transcriptRef = useRef<HTMLDivElement | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = draft.trim();
    if (!trimmed || isSending || !canSend) return;

    const success = await onSend(trimmed);
    if (success) {
      setDraft("");
    }
  };

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files || files.length === 0) return;
    onFilesSelected(files);
    event.target.value = "";
  };

  const handleAttach = () => {
    fileInputRef.current?.click();
  };

  const handleDragOver = (
    event: DragEvent<HTMLDivElement | HTMLTextAreaElement>
  ) => {
    event.preventDefault();
    event.stopPropagation();
    if (!isDragging) {
      setIsDragging(true);
    }
  };

  const handleDragLeave = (
    event: DragEvent<HTMLDivElement | HTMLTextAreaElement>
  ) => {
    event.preventDefault();
    event.stopPropagation();
    if (isDragging) {
      setIsDragging(false);
    }
  };

  const handleDrop = (
    event: DragEvent<HTMLDivElement | HTMLTextAreaElement>
  ) => {
    event.preventDefault();
    event.stopPropagation();
    setIsDragging(false);
    const files = event.dataTransfer.files;
    if (files && files.length > 0) {
      onFilesSelected(files);
    }
  };

  useEffect(() => {
    if (!transcriptRef.current) return;
    transcriptRef.current.scrollTo({
      top: transcriptRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages]);

  return (
    <div className="flex items-center justify-center min-h-screen flex-col bg-slate-950 text-slate-100">
      <main
        ref={transcriptRef}
        className="flex-1 overflow-y-auto px-8 py-12 mt-[150px]"
      >
        {messages.length === 0 ? (
          <div className="mx-auto flex h-full max-w-3xl flex-col items-center justify-center text-center">
            <div className="rounded-full border border-slate-800 bg-slate-900 px-4 py-1 text-xs uppercase tracking-[0.3em] text-slate-300/90">
              Autonomous ML Engineering
            </div>

            <h1 className="mt-5 text-4xl font-semibold text-slate-50">
              Build ML Models by Talking to Your Data
            </h1>
            <p className="mt-4 max-w-xl text-base text-slate-500">
              Just upload a dataset and tell the agent your specific goals -
              it'll explore, engineer features, train models, and explain its
              reasoning in real time.
            </p>
          </div>
        ) : (
          <div className="mx-auto flex max-w-2xl flex-col space-y-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`w-fit max-w-full rounded-2xl px-4 py-2 text-sm leading-6 shadow-sm ${
                  message.role === "user"
                    ? "ml-auto bg-slate-100 text-slate-900"
                    : "mr-auto border border-slate-800 bg-slate-900 text-slate-100"
                }`}
              >
                {message.role === "assistant" ? (
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    className="markdown-body text-sm leading-6 text-slate-100 [&>*:first-child]:mt-0"
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
            ))}
          </div>
        )}
      </main>
      <form className="px-6 py-12 pb-[200px] min-w-2/3" onSubmit={handleSubmit}>
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv"
          multiple
          className="hidden"
          onChange={handleFileChange}
        />
        <div className="flex justify-center">
          <div
            className={`relative w-full max-w-4xl rounded-4xl border ${
              isDragging ? "border-slate-400" : "border-slate-700/70"
            } bg-slate-900/80 p-6 shadow-[0_40px_120px_-60px_rgba(15,23,42,0.85)] backdrop-blur-xl transition-colors`}
            onDragOver={handleDragOver}
            onDragEnter={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <div className="mb-4 flex items-center justify-between px-1 text-xs uppercase tracking-[0.3em] text-slate-400">
              <span>Compose</span>
              <span>{isSending ? "Sending…" : "Ready"}</span>
            </div>
            <div className="relative">
              <textarea
                className={`min-h-28 w-full resize-none rounded-3xl border ${
                  isDragging ? "border-slate-400" : "border-slate-700"
                } bg-slate-950/80 px-16 py-5 text-sm text-slate-100 shadow-inner outline-none transition focus:border-slate-400 focus:ring-2 focus:ring-slate-400/30 disabled:opacity-50`}
                placeholder={
                  canSend
                    ? "Upload your data and ask anything…"
                    : "Upload at least one dataset to enable prompts…"
                }
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                disabled={isSending}
                onDragOver={handleDragOver}
                onDragEnter={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
              />
              <button
                type="button"
                className="absolute left-5 bottom-5 inline-flex h-10 w-10 items-center justify-center rounded-full border border-slate-700 bg-slate-900 text-slate-300 transition hover:border-slate-500 hover:text-slate-100 disabled:opacity-50"
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
                  <title>Attach files</title>
                  <path d="M15.5 6.5a3.5 3.5 0 0 0-6-2.45L5.3 8.1a2.5 2.5 0 0 0 3.5 3.55l4.6-4.62a.75.75 0 1 1 1.06 1.06L9.86 12.7a4 4 0 0 1-5.66-5.66l4.2-4.05a5 5 0 1 1 7.07 7.07l-5.15 5.16a2.5 2.5 0 0 1-3.54-3.54l3.53-3.55a.75.75 0 1 1 1.06 1.06L8.84 12.9a1 1 0 0 0 1.42 1.4l5.24-5.24a3.47 3.47 0 0 0 1-2.56Z" />
                </svg>
              </button>
              <button
                type="submit"
                className="absolute right-5 bottom-5 inline-flex h-11 w-11 items-center justify-center rounded-full bg-slate-100 text-slate-900 shadow-lg transition hover:bg-white/90 disabled:opacity-50"
                disabled={isSending || !canSend}
                aria-label="Send prompt"
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
                    className="h-6 w-6"
                  >
                    <path d="M12 5l-6 6h4v8h4v-8h4l-6-6z" fill="currentColor" />
                  </svg>
                )}
              </button>
            </div>
            <div className="mt-4 flex flex-wrap items-center justify-between text-xs text-slate-400">
              <span>
                {isUploading && progress
                  ? `Uploading ${progress.processed}/${progress.total} dataset${
                      progress.total > 1 ? "s" : ""
                    }…`
                  : canSend
                  ? "Dataset uploaded. Ask a question to start the agent."
                  : "Attach one or many CSV datasets before sending your prompt."}
              </span>
              {isSending ? (
                <span className="text-slate-300">Generating insights…</span>
              ) : null}
            </div>
          </div>
        </div>
      </form>
    </div>
  );
}
