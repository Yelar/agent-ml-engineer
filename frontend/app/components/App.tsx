'use client';

import axios from 'axios';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import ChatSidebar from '@/app/components/ChatSidebar';
import NotebookView from '@/app/components/NotebookView';
import PreSessionView from '@/app/components/PreSessionView';
import UploadBar from '@/app/components/UploadBar';
import { useSessionEvents, type EventMsg } from '@/app/hooks/useSessionEvents';
import type { ChatMessage } from '@/app/types/chat';

type UploadProgress = {
  processed: number;
  total: number;
};

type UploadResponse = {
  session_id: string;
  datasets: string[];
};

type ChatResponse = {
  reply: string;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:8000';

const createId = () =>
  typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`;

export default function App() {
  const [sessionId, setSessionId] = useState<string>();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isActive, setIsActive] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [pendingAssistantMessageId, setPendingAssistantMessageId] = useState<string | null>(null);
  const [uploadState, setUploadState] = useState<{
    isUploading: boolean;
    progress: UploadProgress | null;
  }>({ isUploading: false, progress: null });
  const [sidebarWidth, setSidebarWidth] = useState(320);
  const [isResizingSidebar, setIsResizingSidebar] = useState(false);

  const processedEventsRef = useRef<Set<string>>(new Set());
  const layoutRef = useRef<HTMLDivElement | null>(null);

  const { events, resetEvents } = useSessionEvents(sessionId, {
    connect: Boolean(sessionId),
  });

  useEffect(() => {
    setMessages([]);
    resetEvents();
    setIsActive(false);
    setPendingAssistantMessageId(null);
    setIsSending(false);
    processedEventsRef.current.clear();
  }, [resetEvents, sessionId]);

  const appendMessage = useCallback((role: 'user' | 'assistant', content: string) => {
    const message: ChatMessage = {
      id: createId(),
      role,
      content,
    };
    setMessages((prev) => [...prev, message]);
    return message.id;
  }, []);

  const updateMessage = useCallback((id: string, content: string) => {
    setMessages((prev) => prev.map((message) => (message.id === id ? { ...message, content } : message)));
  }, []);

  const handleFilesSelected = useCallback(
    async (files: FileList) => {
      const selected = Array.from(files);
      if (selected.length === 0) return;

      setUploadState({
        isUploading: true,
        progress: { processed: 0, total: selected.length },
      });

      const formData = new FormData();
      selected.forEach((file) => formData.append('files', file));

      try {
        const { data } = await axios.post<UploadResponse>(`${API_BASE}/upload`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
        setSessionId(data.session_id);
      } catch (error) {
        console.error('Failed to upload dataset(s)', error);
        appendMessage('assistant', 'Failed to upload dataset(s). Please try again.');
      } finally {
        setUploadState({
          isUploading: false,
          progress: { processed: selected.length, total: selected.length },
        });
        window.setTimeout(() => {
          setUploadState({ isUploading: false, progress: null });
        }, 400);
      }
    },
    [appendMessage],
  );

  const handleSend = useCallback(
    async (prompt: string) => {
      const trimmed = prompt.trim();
      if (!trimmed || isSending) return false;

      if (!sessionId) {
        appendMessage('assistant', 'Upload at least one dataset before sending a prompt.');
        return false;
      }

      appendMessage('user', trimmed);
      if (!isActive) {
        setIsActive(true);
      }

      const thinkingMessageId = appendMessage('assistant', 'Processing prompt…');
      setPendingAssistantMessageId(thinkingMessageId);
      setIsSending(true);

      try {
        const { data } = await axios.post<ChatResponse>(`${API_BASE}/chat`, {
          message: trimmed,
          session_id: sessionId,
        });

        updateMessage(
          thinkingMessageId,
          data.reply?.trim() ?? 'The agent accepted your request. Live updates will stream in shortly.',
        );
        return true;
      } catch (error) {
        console.error('Failed to send chat message', error);
        updateMessage(
          thinkingMessageId,
          'Failed to start the agent. Check your backend logs and try again.',
        );
        setPendingAssistantMessageId(null);
        setIsSending(false);
        return false;
      }
    },
    [appendMessage, isActive, isSending, sessionId, updateMessage],
  );

  const readPayloadField = useCallback((payload: unknown, field: string) => {
    if (typeof payload === 'string' && field === 'content') {
      return payload;
    }

    if (payload && typeof payload === 'object' && field in payload) {
      const value = (payload as Record<string, unknown>)[field];
      return typeof value === 'string' ? value : undefined;
    }
    return undefined;
  }, []);

  const handleEvent = useCallback(
    (event: EventMsg) => {
      if (event.type === 'assistant_message') {
        const content =
          readPayloadField(event.payload, 'content') ??
          readPayloadField(event.payload, 'message') ??
          'Agent run completed.';

        if (pendingAssistantMessageId) {
          updateMessage(pendingAssistantMessageId, content);
          setPendingAssistantMessageId(null);
        } else {
          appendMessage('assistant', content);
        }
        setIsSending(false);
        return;
      }

      if (event.type === 'error') {
        const message =
          readPayloadField(event.payload, 'message') ?? 'The agent encountered an unexpected error.';
        if (pendingAssistantMessageId) {
          updateMessage(pendingAssistantMessageId, message);
          setPendingAssistantMessageId(null);
        } else {
          appendMessage('assistant', message);
        }
        setIsSending(false);
        return;
      }

      if (event.type === 'status') {
        const stage = readPayloadField(event.payload, 'stage');
        if (stage === 'starting' && pendingAssistantMessageId) {
          updateMessage(
            pendingAssistantMessageId,
            'Preparing the workspace and loading datasets…',
          );
        }

        if (stage === 'running' && pendingAssistantMessageId) {
          updateMessage(
            pendingAssistantMessageId,
            'Agent is running. Watch the notebook for live updates.',
          );
        }

        if (stage === 'failed') {
          if (pendingAssistantMessageId) {
            updateMessage(
              pendingAssistantMessageId,
              'The agent run failed. Review the notebook updates for more details.',
            );
            setPendingAssistantMessageId(null);
          } else {
            appendMessage(
              'assistant',
              'The agent run failed. Review the notebook updates for more details.',
            );
          }
          setIsSending(false);
        }

        if (stage === 'completed') {
          setIsSending(false);
        }

        return;
      }
    },
    [appendMessage, pendingAssistantMessageId, readPayloadField, updateMessage],
  );

  useEffect(() => {
    events.forEach((event) => {
      if (processedEventsRef.current.has(event.event_id)) return;
      processedEventsRef.current.add(event.event_id);
      handleEvent(event);
    });
  }, [events, handleEvent]);

  useEffect(() => {
    if (!isResizingSidebar) return undefined;

    const handleMouseMove = (event: MouseEvent) => {
      if (!layoutRef.current) return;
      const { left } = layoutRef.current.getBoundingClientRect();
      const newWidth = event.clientX - left;
      const clamped = Math.min(Math.max(newWidth, 240), 520);
      setSidebarWidth(clamped);
    };

    const handleMouseUp = () => {
      setIsResizingSidebar(false);
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizingSidebar]);

  const startResizing = useCallback((event: React.MouseEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsResizingSidebar(true);
  }, []);

  const layout = useMemo(() => {
    if (!isActive) {
      return (
        <PreSessionView
          messages={messages}
          onSend={handleSend}
          onFilesSelected={handleFilesSelected}
          isSending={isSending}
          isUploading={uploadState.isUploading}
          progress={uploadState.progress}
          canSend={Boolean(sessionId) && !uploadState.isUploading}
        />
      );
    }

    return (
      <div ref={layoutRef} className="flex h-screen min-h-0 bg-slate-950 text-slate-100">
        <div style={{ width: sidebarWidth }} className="flex h-full min-h-0">
          <ChatSidebar
            messages={messages}
            onSend={handleSend}
            isSending={isSending}
            canSend={Boolean(sessionId)}
          />
        </div>
        <div
          onMouseDown={startResizing}
          className={`w-1 cursor-col-resize bg-slate-900/70 transition-colors hover:bg-slate-700/80 ${
            isResizingSidebar ? 'bg-slate-600' : ''
          }`}
        />
        <div className="flex h-full min-h-0 flex-1 flex-col bg-slate-950 overflow-hidden">
          <UploadBar
            onFilesSelected={handleFilesSelected}
            isUploading={uploadState.isUploading}
            progress={uploadState.progress}
          />
          <NotebookView sessionId={sessionId} events={events} isActive={isActive} />
        </div>
      </div>
    );
  }, [
    events,
    handleFilesSelected,
    handleSend,
    isActive,
    isSending,
    messages,
    sessionId,
    uploadState,
    sidebarWidth,
  ]);

  return <div className="bg-slate-950 text-slate-100">{layout}</div>;
}
