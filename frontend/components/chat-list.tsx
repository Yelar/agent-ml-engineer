"use client";

import type { ChatMessageSimple } from "@/lib/websocket-types";

interface ChatListProps {
  messages: ChatMessageSimple[];
}

export function ChatList({ messages }: ChatListProps) {
  if (messages.length === 0) {
    return (
      <div className="flex h-full items-center justify-center p-8">
        <div className="text-center text-muted-foreground">
          <p className="text-lg">Start a conversation</p>
          <p className="mt-2 text-sm">
            Ask a question or describe what you'd like to analyze
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto w-full max-w-3xl space-y-4 p-4">
      {messages.map((message) => (
        <div
          key={message.id}
          className={`flex ${
            message.role === "user" ? "justify-end" : "justify-start"
          }`}
        >
          <div
            className={`max-w-[80%] rounded-lg px-4 py-2 ${
              message.role === "user"
                ? "bg-primary text-primary-foreground"
                : "bg-muted"
            }`}
          >
            <div className="whitespace-pre-wrap break-words">
              {message.content}
            </div>
            <div className="mt-1 text-xs opacity-70">
              {new Date(message.timestamp).toLocaleTimeString()}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

