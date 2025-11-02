# Pure WebSocket Implementation Prompt

## Context

You have the `agent-ml-engineer` repository with:
- **Backend**: Python WebSocket server with LangGraph ML agent (`backend/websocket_server.py`)
- **Frontend**: Next.js app based on Vercel AI Chatbot template
- **Current Problem**: AI SDK is conflicting with WebSocket implementation
- **Goal**: Remove AI SDK complexity, use pure WebSocket for everything, keep the beautiful UI

## Objective

Convert the chat interface to be **100% WebSocket-driven** while maintaining the existing beautiful UI and artifact system. The backend ML agent will handle all messages and stream results through WebSocket.

---

## Architecture Changes

### Current (Complex):
```
User Message → AI SDK → Backend LLM Provider (doesn't exist) ❌
User Message → WebSocket → ML Agent (works but limited) ✓
```

### Target (Simple):
```
User Message → WebSocket → ML Agent → Artifact System ✓
Everything goes through one channel!
```

---

## Implementation Steps

### 1. Simplify Chat Component

**File**: `frontend/components/chat.tsx`

**Current State**: Uses `useChat` hook from AI SDK
**Target State**: Use only WebSocket with local state

**Changes Required**:

```typescript
// REMOVE:
import { useChat } from "@ai-sdk/react";

// REPLACE WITH:
import { useState, useCallback } from "react";

// REMOVE the entire useChat() setup
const {
  messages,
  setMessages,
  sendMessage,
  status,
  stop,
  regenerate,
  resumeStream,
} = useChat({ ... });

// REPLACE WITH:
const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
const [isProcessing, setIsProcessing] = useState(false);

// Send message via WebSocket
const sendMessage = useCallback((message: { role: string; parts: any[] }) => {
  // Add user message to UI immediately
  const userMsg = {
    id: generateUUID(),
    role: "user" as const,
    parts: message.parts,
  };
  setMessages((prev) => [...prev, userMsg]);
  
  // Send to WebSocket backend
  const content = message.parts[0]?.text || "";
  wsRef.current?.send(JSON.stringify({
    type: "user_message",
    payload: {
      message: content,
    },
  }));
  
  setIsProcessing(true);
}, []);
```

### 2. Remove AI SDK Dependencies

**Files to Modify**:

**`frontend/components/chat.tsx`**:
```typescript
// Remove these imports:
import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport } from "ai";
import { useDataStream } from "./data-stream-provider";

// Keep these:
import { useState, useCallback, useEffect } from "react";
import { useWebSocketML } from "@/hooks/use-websocket-ml";
import { useArtifact } from "@/hooks/use-artifact";
```

**`frontend/app/(chat)/page.tsx`**:
```typescript
// Make WebSocket the default and only option
// Remove the toggle - WebSocket is always on
const useWebSocket = true; // Always enabled
```

### 3. Update WebSocket Message Handlers

**File**: `frontend/components/chat.tsx`

Expand WebSocket handlers to manage ALL chat interactions:

```typescript
const handleCreateDocument = useCallback(() => {
  // Initialize ML analysis artifact
  setArtifact({
    documentId: generateUUID(),
    content: "",
    kind: "ml-analysis",
    title: "ML Analysis",
    status: "streaming",
    isVisible: true,
    boundingBox: { top: 0, left: 0, width: 0, height: 0 },
  });
  
  setMetadata({ blocks: [] });
}, [setArtifact, setMetadata]);

const handleDocumentBlock = useCallback((block: DocumentBlock) => {
  // Add block to artifact
  setMetadata((prev: any) => ({
    ...prev,
    blocks: [...(prev?.blocks || []), block],
  }));
}, [setMetadata]);

const handleFinalAnswer = useCallback((content: string) => {
  // Mark artifact complete
  setArtifact((prev) => ({ ...prev, status: "idle" }));
  
  // Add assistant message to chat
  setMessages((prev) => [
    ...prev,
    {
      id: generateUUID(),
      role: "assistant",
      parts: [{ type: "text", text: content }],
    },
  ]);
  
  setIsProcessing(false);
}, [setArtifact, setMessages]);

const handleError = useCallback((error: Error) => {
  toast({
    type: "error",
    description: error.message,
  });
  setIsProcessing(false);
}, []);

// WebSocket connection (always enabled)
const { isConnected, sendMessage: wsSendMessage } = useWebSocketML({
  enabled: true, // Always on
  backendUrl: process.env.NEXT_PUBLIC_BACKEND_URL?.replace("http", "ws") || "ws://localhost:8000",
  onCreateDocument: handleCreateDocument,
  onDocumentBlock: handleDocumentBlock,
  onFinalAnswer: handleFinalAnswer,
  onError: handleError,
});
```

### 4. Update Chat UI Components

**File**: `frontend/components/chat.tsx`

Update the JSX to remove AI SDK-specific elements:

```typescript
return (
  <>
    <div className="flex h-dvh min-w-0 flex-col bg-background">
      {/* Header with connection status */}
      <div className="flex items-center justify-between border-b">
        <ChatHeader
          chatId={id}
          isReadonly={isReadonly}
          selectedVisibilityType={initialVisibilityType}
        />
        <div className="flex items-center gap-2 px-4">
          <Badge variant={isConnected ? "default" : "secondary"}>
            {isConnected ? "Connected" : "Disconnected"}
          </Badge>
        </div>
      </div>

      {/* Messages */}
      <Messages
        chatId={id}
        isArtifactVisible={artifact.isVisible}
        isReadonly={isReadonly}
        messages={messages}
        selectedModelId={initialChatModel}
        setMessages={setMessages}
        status={isProcessing ? "in_progress" : "awaiting_message"}
        votes={votes}
      />

      {/* Input */}
      <div className="sticky bottom-0 z-1 mx-auto flex w-full max-w-4xl gap-2 border-t-0 bg-background px-2 pb-3 md:px-4 md:pb-4">
        {!isReadonly && (
          <MultimodalInput
            chatId={id}
            input={input}
            messages={messages}
            onModelChange={setCurrentModelId}
            selectedModelId={currentModelId}
            selectedVisibilityType={visibilityType}
            sendMessage={(msg) => {
              // Use WebSocket sendMessage
              const content = msg.parts[0]?.text || "";
              wsSendMessage("user_message", {
                session_id: sessionId,
                message: content,
              });
              
              // Add to UI
              setMessages((prev) => [...prev, msg]);
            }}
            setInput={setInput}
            setMessages={setMessages}
            status={isProcessing ? "in_progress" : "awaiting_message"}
            stop={() => {
              // Send stop signal to backend if needed
              wsSendMessage("stop", {});
              setIsProcessing(false);
            }}
          />
        )}
      </div>
    </div>

    {/* Artifact panel */}
    <Artifact
      chatId={id}
      input={input}
      isReadonly={isReadonly}
      messages={messages}
      selectedModelId={currentModelId}
      selectedVisibilityType={visibilityType}
      sendMessage={sendMessage}
      setInput={setInput}
      setMessages={setMessages}
      status={isProcessing ? "in_progress" : "awaiting_message"}
      votes={votes}
    />
  </>
);
```

### 5. Simplify Backend WebSocket Protocol

**File**: `backend/websocket_server.py`

The backend is already perfect! It sends:
1. `create_document` - Opens artifact panel
2. `append_to_document` - Adds code/markdown/chart blocks
3. `final_answer` - Completes analysis and adds chat message

**No changes needed to backend!** ✅

### 6. Remove Unused Files (Optional Cleanup)

These files become unnecessary:

```bash
# Can be removed or ignored:
frontend/lib/ai/providers.ts         # AI SDK provider config
frontend/lib/ai/prompts.ts           # AI SDK system prompts  
frontend/lib/ai/tools/*.ts           # AI SDK tool definitions (except types)
frontend/components/data-stream-provider.tsx  # AI SDK streaming
```

**Keep these** (still needed):
- `frontend/lib/websocket-types.ts` - Type definitions
- `frontend/hooks/use-websocket-ml.ts` - WebSocket hook
- `frontend/artifacts/ml-analysis/*` - Artifact rendering
- All UI components - they're framework-agnostic

---

## Key Benefits

### Before (Complex):
```typescript
// Two systems fighting each other
useChat() → AI SDK → Backend Provider ❌
useWebSocketML() → WebSocket → ML Agent ✓

// Configuration conflicts
const USE_BACKEND = true || false? 🤔
```

### After (Simple):
```typescript
// One system, one source of truth
useWebSocketML() → ML Agent → Everything ✓

// No configuration needed
const ALWAYS_USE_WEBSOCKET = true; 😊
```

---

## Testing Checklist

After implementation, verify:

### 1. Basic Chat Flow
```
✓ User types message
✓ Message appears in chat immediately
✓ WebSocket sends to backend
✓ Backend processes with ML agent
✓ Final answer appears in chat
```

### 2. ML Analysis with Artifact
```
✓ User: "Analyze sample_sales dataset"
✓ Artifact panel slides in (create_document)
✓ Code blocks appear with syntax highlighting
✓ Markdown blocks render (thinking, plan)
✓ Final summary in chat
✓ Export button works
```

### 3. Connection Handling
```
✓ Badge shows "Connected" when WS active
✓ Badge shows "Disconnected" if backend down
✓ Auto-reconnect on connection loss
✓ Error messages display properly
```

### 4. UI Polish
```
✓ Messages scroll smoothly
✓ Input accepts Enter to send
✓ Loading state shows during processing
✓ Artifact animations are smooth
✓ Dark mode works
✓ Mobile responsive
```

---

## Environment Variables

**File**: `frontend/.env.local` (create if doesn't exist)

```env
# Backend WebSocket URL (always used)
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000

# Remove or ignore these (not needed anymore):
# AI_GATEWAY_URL=...
# NEXT_PUBLIC_USE_BACKEND=...
```

---

## File-by-File Changes Summary

### Must Change:
1. **`frontend/components/chat.tsx`** - Replace useChat with WebSocket state
2. **`frontend/app/(chat)/page.tsx`** - Remove WebSocket toggle
3. **`frontend/components/multimodal-input.tsx`** - Update sendMessage to use WS

### Keep As-Is:
1. **`backend/websocket_server.py`** - Already perfect! ✅
2. **`frontend/artifacts/ml-analysis/*`** - Working great ✅
3. **`frontend/hooks/use-websocket-ml.ts`** - Already correct ✅
4. **All UI components** - Framework-agnostic ✅

### Can Delete (Optional):
1. `frontend/lib/ai/providers.ts`
2. `frontend/lib/ai/tools/*.ts` (except type imports)
3. `frontend/components/data-stream-provider.tsx`

---

## Expected Outcome

### Architecture Diagram:
```
┌─────────────────────────────────────────────────────┐
│                    FRONTEND                          │
│                                                      │
│  ┌─────────────────────────────────────────────┐   │
│  │  Chat UI (same beautiful UI)                │   │
│  │  - Messages                                 │   │
│  │  - Input                                    │   │
│  │  - [Connected] badge                        │   │
│  └────────────────┬────────────────────────────┘   │
│                   │                                  │
│                   │ WebSocket (one channel)          │
│                   ▼                                  │
│  ┌─────────────────────────────────────────────┐   │
│  │  ML Analysis Artifact                       │   │
│  │  - Code blocks                              │   │
│  │  - Markdown                                 │   │
│  │  - Charts                                   │   │
│  │  - Export                                   │   │
│  └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
                        ↕
          WebSocket (ws://localhost:8000)
                        ↕
┌─────────────────────────────────────────────────────┐
│                    BACKEND                           │
│  Python WebSocket Server                            │
│  - MLEngineerAgent (LangGraph)                      │
│  - AgentStreamer                                    │
│  - Dataset management                               │
└─────────────────────────────────────────────────────┘
```

### User Experience:
1. User opens app → WebSocket connects automatically
2. User types: "Analyze sales data"
3. Message appears instantly in chat
4. Artifact panel slides in with analysis
5. Code blocks stream in with syntax highlighting  
6. Final answer appears in chat
7. User can export code or continue chatting

**Same beautiful UI, 50% less complexity!** 🎉

---

## Implementation Priority

### Phase 1 (Core - Must Do):
1. Replace `useChat` with WebSocket state in `chat.tsx`
2. Wire up `sendMessage` to WebSocket
3. Test basic message flow

### Phase 2 (Polish):
1. Remove AI SDK toggle UI
2. Clean up unused imports
3. Update environment variables

### Phase 3 (Optional Cleanup):
1. Delete unused AI SDK files
2. Update documentation
3. Add WebSocket error recovery

---

## Start Here

Begin by modifying `frontend/components/chat.tsx`:

1. Remove the `useChat` hook import and usage
2. Add `useState` for messages
3. Wire `sendMessage` to `useWebSocketML`
4. Test that messages flow through WebSocket
5. Verify artifact still works

Once that works, the rest is just cleanup!

---

**Result**: A clean, simple architecture where WebSocket drives everything, the beautiful UI stays intact, and there are no AI SDK conflicts. Your ML agent backend is the star of the show! 🌟

