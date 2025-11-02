"use client";

import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import useSWR, { useSWRConfig } from "swr";
import { unstable_serialize } from "swr/infinite";
import { ChatHeader } from "@/components/chat-header";
import { Badge } from "@/components/ui/badge";
import { useArtifact, useArtifactSelector } from "@/hooks/use-artifact";
import { useChatVisibility } from "@/hooks/use-chat-visibility";
import { useWebSocketML } from "@/hooks/use-websocket-ml";
import type { Vote } from "@/lib/db/schema";
import type { Attachment, ChatMessage } from "@/lib/types";
import { fetcher, generateUUID } from "@/lib/utils";
import type { DocumentBlock } from "@/lib/websocket-types";
import { Artifact } from "./artifact";
import { Messages } from "./messages";
import { MultimodalInput } from "./multimodal-input";
import { getChatHistoryPaginationKey } from "./sidebar-history";
import { toast } from "./toast";
import type { VisibilityType } from "./visibility-selector";

export function Chat({
  id,
  initialMessages,
  initialChatModel,
  initialVisibilityType,
  isReadonly,
}: {
  id: string;
  initialMessages: ChatMessage[];
  initialChatModel: string;
  initialVisibilityType: VisibilityType;
  isReadonly: boolean;
}) {
  const { visibilityType } = useChatVisibility({
    chatId: id,
    initialVisibilityType,
  });

  const { mutate } = useSWRConfig();
  const { setArtifact, setMetadata } = useArtifact();

  const [input, setInput] = useState<string>("");
  const [currentModelId, setCurrentModelId] = useState(initialChatModel);
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const [isProcessing, setIsProcessing] = useState(false);
  const sessionIdRef = useRef(generateUUID());

  // WebSocket ML Analysis Handler - bridges to artifact system
  const handleCreateDocument = useCallback(() => {
    // Initialize ML analysis artifact
    setArtifact({
      documentId: generateUUID(),
      content: "",
      kind: "ml-analysis",
      title: "ML Analysis",
      status: "streaming",
      isVisible: true,
      boundingBox: {
        top: 0,
        left: 0,
        width: 0,
        height: 0,
      },
    });

    // Initialize metadata with empty blocks
    setMetadata({
      blocks: [],
    });
  }, [setArtifact, setMetadata]);

  const handleDocumentBlock = useCallback((block: DocumentBlock) => {
    // Add block to artifact metadata
    setMetadata((prev: any) => ({
      ...prev,
      blocks: [...(prev?.blocks || []), block],
    }));
  }, [setMetadata]);

  const handleFinalAnswer = useCallback(
    (content: string) => {
      // Mark artifact as complete
      setArtifact((prev) => ({
        ...prev,
        status: "idle",
      }));

      // Add assistant message from WebSocket
      setMessages((prevMessages) => [
        ...prevMessages,
        {
          id: generateUUID(),
          role: "assistant",
          parts: [{ type: "text", text: content }],
        },
      ]);

      setIsProcessing(false);
      mutate(unstable_serialize(getChatHistoryPaginationKey));
    },
    [setArtifact, setMessages, mutate]
  );

  const handleError = useCallback((error: Error) => {
    toast({
      type: "error",
      description: error.message,
    });
    setIsProcessing(false);
  }, []);

  // Initialize WebSocket connection (always enabled)
  const { isConnected, sendMessage: wsSendMessage } = useWebSocketML({
    enabled: true,
    backendUrl:
      process.env.NEXT_PUBLIC_BACKEND_URL?.replace("http", "ws") ||
      "ws://localhost:8000",
    onCreateDocument: handleCreateDocument,
    onDocumentBlock: handleDocumentBlock,
    onFinalAnswer: handleFinalAnswer,
    onError: handleError,
  });

  // Send message handler
  const sendMessage = useCallback(
    (message?: { role?: string; parts?: unknown[] }) => {
      if (!message?.parts) return Promise.resolve();

      // Add user message to UI immediately
      const userMsg: ChatMessage = {
        id: generateUUID(),
        role: "user" as const,
        parts: message.parts as ChatMessage["parts"],
      };
      setMessages((prev) => [...prev, userMsg]);

      // Extract text content
      const textPart = message.parts.find(
        (p: unknown) =>
          typeof p === "object" &&
          p !== null &&
          "text" in p &&
          "type" in p &&
          p.type === "text"
      ) as { text: string } | undefined;
      const content = textPart?.text || "";

      // Send to WebSocket backend
      wsSendMessage("user_message", {
        session_id: sessionIdRef.current,
        message: content,
      });

      setIsProcessing(true);
      return Promise.resolve();
    },
    [wsSendMessage]
  );

  // Stop handler
  const stop = useCallback(() => {
    wsSendMessage("stop", {});
    setIsProcessing(false);
    return Promise.resolve();
  }, [wsSendMessage]);

  // Regenerate handler (stub for compatibility)
  const regenerate = useCallback(() => {
    toast({
      type: "error",
      description: "Regenerate not yet implemented for WebSocket mode",
    });
    return Promise.resolve();
  }, []);

  const searchParams = useSearchParams();
  const query = searchParams.get("query");

  const [hasAppendedQuery, setHasAppendedQuery] = useState(false);

  useEffect(() => {
    if (query && !hasAppendedQuery && isConnected) {
      sendMessage({
        role: "user" as const,
        parts: [{ type: "text", text: query }],
      });

      setHasAppendedQuery(true);
      window.history.replaceState({}, "", `/chat/${id}`);
    }
  }, [query, sendMessage, hasAppendedQuery, id, isConnected]);

  const { data: votes } = useSWR<Vote[]>(
    messages.length >= 2 ? `/api/vote?chatId=${id}` : null,
    fetcher
  );

  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const isArtifactVisible = useArtifactSelector((state) => state.isVisible);

  // Status for UI compatibility (matching AI SDK status values)
  const status = isProcessing ? ("submitted" as const) : ("ready" as const);

  return (
    <>
      <div className="overscroll-behavior-contain flex h-dvh min-w-0 touch-pan-y flex-col bg-background">
        <div className="flex items-center justify-between border-b">
          <ChatHeader
            chatId={id}
            isReadonly={isReadonly}
            selectedVisibilityType={initialVisibilityType}
          />
          {/* WebSocket Status Badge */}
          <div className="flex items-center gap-2 px-4">
            <Badge
              variant={isConnected ? "default" : "secondary"}
              className="text-xs"
            >
              {isConnected ? "Connected" : "Disconnected"}
            </Badge>
          </div>
        </div>

        <Messages
          chatId={id}
          isArtifactVisible={isArtifactVisible}
          isReadonly={isReadonly}
          messages={messages}
          regenerate={regenerate}
          selectedModelId={initialChatModel}
          setMessages={setMessages}
          status={status}
          votes={votes}
        />

        <div className="sticky bottom-0 z-1 mx-auto flex w-full max-w-4xl gap-2 border-t-0 bg-background px-2 pb-3 md:px-4 md:pb-4">
          {!isReadonly && (
            <MultimodalInput
              attachments={attachments}
              chatId={id}
              input={input}
              messages={messages}
              onModelChange={setCurrentModelId}
              selectedModelId={currentModelId}
              selectedVisibilityType={visibilityType}
              sendMessage={sendMessage}
              setAttachments={setAttachments}
              setInput={setInput}
              setMessages={setMessages}
              status={status}
              stop={stop}
            />
          )}
        </div>
      </div>

      <Artifact
        attachments={attachments}
        chatId={id}
        input={input}
        isReadonly={isReadonly}
        messages={messages}
        regenerate={regenerate}
        selectedModelId={currentModelId}
        selectedVisibilityType={visibilityType}
        sendMessage={sendMessage}
        setAttachments={setAttachments}
        setInput={setInput}
        setMessages={setMessages}
        status={status}
        stop={stop}
        votes={votes}
      />
    </>
  );
}
