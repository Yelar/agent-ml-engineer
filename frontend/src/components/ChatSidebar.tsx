import { type FormEvent, useEffect, useState } from "react";
import axios from "axios";

type Message = {
  role: "user" | "assistant";
  content: string;
};

type ChatSidebarProps = {
  sessionId?: string;
};

export default function ChatSidebar({ sessionId }: ChatSidebarProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);

  const isReady = Boolean(sessionId);

  useEffect(() => {
    setMessages([]);
    setInput("");
  }, [sessionId]);

  const sendMessage = async (): Promise<void> => {
    const trimmed = input.trim();
    if (!trimmed || isSending || !sessionId) return;

    const userMessage: Message = { role: "user", content: trimmed };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsSending(true);

    try {
      const { data } = await axios.post<{ reply?: string }>(
        "http://localhost:8000/chat",
        { message: trimmed, session_id: sessionId }
      );
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.reply?.trim() ?? "I don't have a reply yet.",
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Sorry, something went wrong." },
      ]);
    } finally {
      setIsSending(false);
    }
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!sessionId) return;
    void sendMessage();
  };

  return (
    <aside className="flex h-screen shrink-0 flex-col gap-6 overflow-hidden bg-slate-50 px-6 py-8">
      <header className="space-y-2">
        <h2 className="text-lg font-semibold text-slate-900">Chat</h2>
        <p className="text-sm text-slate-500">
          Ask questions and review agent responses.
        </p>
      </header>
      <div
        className="flex flex-1 flex-col space-y-3 overflow-y-auto pr-2"
        aria-live="polite"
      >
        {!isReady ? (
          <p className="rounded-xl bg-slate-100 p-4 text-center text-sm text-slate-500">
            Upload a dataset to start chatting with the agent.
          </p>
        ) : messages.length === 0 ? (
          <p className="rounded-xl bg-slate-100 p-4 text-center text-sm text-slate-500">
            Start a conversation to see responses here.
          </p>
        ) : (
          messages.map((message, index) => (
            <div
              key={`message-${index}`}
              className={`max-w-[260px] rounded-2xl px-4 py-2 text-sm leading-6 shadow-sm ${
                message.role === "user"
                  ? "self-end bg-blue-500 text-white"
                  : "self-start bg-slate-100 text-slate-900"
              }`}
            >
              {message.content}
            </div>
          ))
        )}
      </div>
      <form
        className="flex items-center gap-2 border-t border-slate-200 pt-4"
        onSubmit={handleSubmit}
      >
        <input
          className="flex-1 rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100 disabled:bg-slate-100"
          placeholder="Ask about your model..."
          value={input}
          onChange={(event) => setInput(event.target.value)}
          autoComplete="off"
          disabled={isSending || !isReady}
          aria-label="Send a message to the agent"
        />
        <button
          type="submit"
          className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
          disabled={isSending || !isReady}
        >
          {isSending ? "Sending…" : "Send"}
        </button>
      </form>
    </aside>
  );
}
