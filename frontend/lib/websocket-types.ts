// WebSocket message types from the backend

export type WebSocketMessage =
  | CreateDocumentMessage
  | AppendToDocumentMessage
  | FinalAnswerMessage;

export interface CreateDocumentMessage {
  type: "create_document";
}

export interface AppendToDocumentMessage {
  type: "append_to_document";
  payload: DocumentBlock;
}

export interface FinalAnswerMessage {
  type: "final_answer";
  payload: string;
}

// Document block types

export type DocumentBlock = CodeBlock | ChartBlock | MarkdownBlock;

export interface CodeBlock {
  id: string;
  type: "code";
  content: string;
}

export interface ChartBlock {
  id: string;
  type: "chart";
  content: {
    title: string;
    data: Record<string, any>[];
  };
}

export interface MarkdownBlock {
  id: string;
  type: "markdown";
  content: string;
}

// Chat message type for the main chat window
export interface ChatMessageSimple {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: number;
}

