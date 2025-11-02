import { type FormEvent, JSX, useState } from "react";
import axios from "axios";

type Message = {
  role: "user" | "assistant";
  content: string;
};

export default function ChatSidebar(): JSX.Element {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);

  const sendMessage = async (): Promise<void> => {
    const trimmed = input.trim();
    if (!trimmed || isSending) return;

    const userMessage: Message = { role: "user", content: trimmed };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsSending(true);

    try {
      const { data } = await axios.post<{ reply?: string }>(
        "http://localhost:8000/chat",
        { message: trimmed }
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
    void sendMessage();
  };

  return (
    <aside className="chat-sidebar">
      <header className="chat-sidebar__header">
        <h2>Chat</h2>
        <p>Ask questions and review agent responses.</p>
      </header>
      <div className="chat-sidebar__messages" aria-live="polite">
        {messages.length === 0 ? (
          <p className="chat-sidebar__empty">
            Start a conversation to see responses here.
          </p>
        ) : (
          messages.map((message, index) => (
            <div
              key={`message-${index}`}
              className={`chat-message chat-message--${message.role}`}
            >
              {message.content}
            </div>
          ))
        )}
      </div>
      <form className="chat-sidebar__composer" onSubmit={handleSubmit}>
        <input
          className="chat-sidebar__input"
          placeholder="Ask about your model..."
          value={input}
          onChange={(event) => setInput(event.target.value)}
          autoComplete="off"
          disabled={isSending}
          aria-label="Send a message to the agent"
        />
        <button
          type="submit"
          className="chat-sidebar__button"
          disabled={isSending}
        >
          {isSending ? "Sending…" : "Send"}
        </button>
      </form>
    </aside>
  );
}
