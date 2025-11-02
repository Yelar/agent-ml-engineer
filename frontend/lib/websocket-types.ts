// WebSocket message types from the backend

export type WebSocketMessage =
  | CreateDocumentMessage
  | AppendToDocumentMessage
  | FinalAnswerMessage
  | EventMessage;

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

// Event message from WebSocket (like useSessionEvents in frontend-old)
export interface EventMessage {
  type: "event";
  payload: EventMsg;
}

// Event types matching backend ML agent events
export interface EventMsg {
  event_id: string;
  type: "code" | "plot" | "plan" | "assistant_message" | "metadata" | "artifacts" | "status" | "error" | "log" | string;
  step?: string;
  payload: unknown;
  timestamp?: string;
}

// Type guards for event payloads
export interface CodeEventPayload {
  code?: string;
  snippet?: string;
  output?: string;
  error?: string;
}

export interface PlotEventPayload {
  image: string; // base64 encoded
  figure?: {
    data: unknown[];
    layout?: Record<string, unknown>;
  };
}

export interface StatusEventPayload {
  stage: "starting" | "running" | "completed" | "failed" | string;
  message?: string;
  prompt?: string;
}

export interface ErrorEventPayload {
  message: string;
  error?: string;
}

export interface AssistantMessagePayload {
  content: string;
  message?: string;
}

export interface PlanPayload {
  content: string;
}

export interface LogPayload {
  message: string;
}

// Document block types

export type DocumentBlock = 
  | CodeBlock 
  | ChartBlock 
  | MarkdownBlock 
  | PlotBlock
  | PlanBlock
  | AssistantMessageBlock
  | MetadataBlock
  | ArtifactsBlock
  | StatusBlock;

export interface CodeBlock {
  id: string;
  type: "code";
  content: string;
  output?: string;
  error?: string;
}

export interface ChartBlock {
  id: string;
  type: "chart";
  content: {
    title: string;
    data: Record<string, unknown>[];
  };
}

export interface MarkdownBlock {
  id: string;
  type: "markdown";
  content: string;
}

export interface PlotBlock {
  id: string;
  type: "plot";
  image: string; // base64 encoded image
  step?: string;
}

export interface PlanBlock {
  id: string;
  type: "plan";
  content: string;
}

export interface AssistantMessageBlock {
  id: string;
  type: "assistant_message";
  content: string;
}

export interface MetadataBlock {
  id: string;
  type: "metadata";
  data: Record<string, unknown>;
}

export interface ArtifactsBlock {
  id: string;
  type: "artifacts";
  items: Array<{
    name: string;
    url?: string;
    kind: string;
  }>;
}

export interface StatusBlock {
  id: string;
  type: "status";
  stage: string;
  message?: string;
  prompt?: string;
}

// Chat message type for the main chat window
export interface ChatMessageSimple {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: number;
}

