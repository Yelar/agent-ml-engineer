# ML Session App - Usage Guide

## Quick Start

### 1. Start the Backend
```bash
cd backend
python websocket_server.py  # or your backend start command
```

### 2. Start the Frontend
```bash
cd frontend
pnpm dev
```

### 3. Access the ML Session
Navigate to: `http://localhost:3000/ml-session`

## User Flow

### Phase 1: Pre-Session (File Upload)
1. User sees welcome screen with instructions
2. Click the attachment button or drag CSV files
3. Multiple files can be uploaded at once
4. Progress indicator shows upload status
5. Once uploaded, session ID is established

### Phase 2: Initial Prompt
1. After upload, user can type a prompt
2. Example: "Analyze this dataset and create visualizations"
3. Click "Send" to submit
4. UI transitions to two-pane layout

### Phase 3: Active Session
**Left Pane - Chat**
- Shows conversation history
- User messages in blue bubbles
- Assistant messages in gray bubbles
- Input field at bottom for follow-up questions

**Right Pane - Notebook**
- Top: Upload bar (add more datasets)
- Main: Live streaming notebook cells
- Shows code execution, plots, plans, status updates
- Auto-scrolls as new events arrive

### Phase 4: Real-Time Updates
Watch as the agent:
1. **Status**: "Starting..." → "Running..." → "Completed"
2. **Plan**: Shows analysis strategy
3. **Code**: Python code with syntax highlighting
4. **Output**: Execution results
5. **Plots**: Generated visualizations
6. **Summary**: Final analysis message

## Event Types Explained

### Code Cells
```
In [1]
┌─────────────────────────┐
│ import pandas as pd     │
│ df = pd.read_csv(...)   │
└─────────────────────────┘

Out [1]
┌─────────────────────────┐
│ Shape: (1000, 5)        │
└─────────────────────────┘
```

### Plot Cells
```
Figure 1
┌─────────────────────────┐
│                         │
│    [Base64 Image]       │
│                         │
└─────────────────────────┘
```

### Plan Cells
```
Plan
┌─────────────────────────┐
│ 1. Load and inspect     │
│ 2. Clean missing data   │
│ 3. Generate plots       │
└─────────────────────────┘
```

### Status Updates
```
┌─────────────────────────┐
│ RUNNING                 │
│ Agent is executing...   │
└─────────────────────────┘
```

## Component Architecture

### MLSessionApp (Main Controller)
- Manages session state
- Handles file uploads
- Processes WebSocket events
- Routes between pre-session and active views

### PreSessionView
- File upload interface
- Initial message display
- Prompt input

### Two-Pane Layout
```
┌──────────┬────────────────────┐
│          │  Upload Bar        │
│  Chat    ├────────────────────┤
│ Sidebar  │                    │
│ (320px)  │  Notebook View     │
│          │  (Auto-scroll)     │
└──────────┴────────────────────┘
```

### WebSocket Hook (useSessionEvents)
```typescript
const { events, isConnected, resetEvents, pushEvent } = useSessionEvents(
  sessionId,
  { connect: true }
);
```

## API Integration

### Upload Files
```typescript
// POST /upload
FormData: files[] = [File, File, ...]
Response: { session_id: string, datasets: string[] }
```

### Send Chat Message
```typescript
// POST /chat
Body: { message: string, session_id: string }
Response: { reply: string }
```

### WebSocket Events
```typescript
// ws://localhost:8000/sessions/{session_id}/events
Message: {
  event_id: string,
  type: "code" | "plot" | "plan" | "status" | ...,
  payload: { ... },
  timestamp: string
}
```

## Customization Examples

### Change Backend URL
```bash
# .env.local
NEXT_PUBLIC_API_BASE=http://your-backend:8000
```

### Add Custom Event Type
```typescript
// 1. Add to websocket-types.ts
export interface MyCustomPayload {
  customField: string;
}

// 2. Handle in notebook-cell.tsx
if (event.type === "my_custom") {
  const payload = event.payload as MyCustomPayload;
  return <CustomComponent data={payload.customField} />;
}
```

### Customize Styling
All components use Tailwind classes and shadcn/ui components. Modify in respective component files.

### Add Export Functionality
```typescript
// In upload-bar.tsx
<Button onClick={handleExport}>Export Notebook</Button>

const handleExport = () => {
  // Convert events to Jupyter format
  // Download as .ipynb
};
```

## Troubleshooting

### WebSocket Not Connecting
- Check backend is running on correct port
- Verify `NEXT_PUBLIC_API_BASE` env variable
- Check browser console for connection errors
- Ensure WebSocket endpoint is `/sessions/{id}/events`

### Files Not Uploading
- Check file size (max 50MB by default)
- Verify file type is CSV
- Check network tab for error responses
- Ensure backend `/upload` endpoint is accessible

### Events Not Appearing
- Check WebSocket connection status
- Verify events have unique `event_id`
- Check browser console for parsing errors
- Ensure event types match expected format

### Chat Messages Not Sending
- Verify session ID is set (after upload)
- Check `canSend` prop is true
- Ensure backend `/chat` endpoint responds

## Development Tips

### Debug WebSocket Events
```typescript
// In ml-session-app.tsx
useEffect(() => {
  console.log('New events:', events);
}, [events]);
```

### Test Without Backend
```typescript
// Use pushEvent for manual testing
const { pushEvent } = useSessionEvents();

pushEvent({
  event_id: crypto.randomUUID(),
  type: "code",
  payload: { code: "print('hello')", output: "hello" },
  timestamp: new Date().toISOString(),
});
```

### Monitor Performance
```typescript
// Add to useEffect in notebook-view.tsx
console.time('render');
// ... render logic
console.timeEnd('render');
```

## Best Practices

1. **Session Management**: Always reset events when session changes
2. **Event Deduplication**: Use unique event IDs to prevent duplicates
3. **Error Handling**: Show user-friendly messages for all errors
4. **Loading States**: Disable inputs during async operations
5. **Auto-scroll**: Only scroll on new content, not on user scroll
6. **Memory Management**: Clean up WebSocket connections on unmount
7. **Type Safety**: Use TypeScript types for all event payloads

## Advanced Usage

### Integrate with Existing Chat
```typescript
import { MLSessionApp } from "@/components/ml-session-app";
import { useArtifact } from "@/hooks/use-artifact";

// Embed in existing chat interface
<div className="flex">
  <ChatInterface />
  <MLSessionApp />
</div>
```

### Add Authentication
```typescript
// In ml-session-app.tsx
const session = await auth();
if (!session) return <LoginPrompt />;
```

### Persist Session History
```typescript
// Save to localStorage or database
useEffect(() => {
  if (sessionId) {
    localStorage.setItem('lastSession', sessionId);
  }
}, [sessionId]);
```

## Support

For issues or questions:
1. Check this guide
2. Review FRONTEND_MERGE_SUMMARY.md
3. Check backend logs
4. Review browser console errors
5. Verify environment configuration

