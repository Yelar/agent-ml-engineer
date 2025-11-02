import type { UIMessageStreamWriter } from "ai";
import type { Session } from "next-auth";
import type { ChatMessage } from "@/lib/types";

type OnCreateDocumentProps = {
  id: string;
  title: string;
  dataStream: UIMessageStreamWriter<ChatMessage>;
  session: Session;
};

export const mlAnalysisHandler = {
  kind: "ml-analysis" as const,
  onCreateDocument: async ({
    id,
    title,
  }: OnCreateDocumentProps) => {
    // ML analysis is driven by WebSocket, not AI SDK streaming
    // Return empty content - the artifact will be populated via WebSocket messages
    return "";
  },
  onUpdateDocument: async () => {
    // ML analysis doesn't support updates (read-only from agent)
    return "";
  },
};

