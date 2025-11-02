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

const createId = () =>
  typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`;

const SIMULATED_SEQUENCE: Array<Omit<EventMsg, 'event_id'> & { delay: number }> = [
  {
    delay: 600,
    type: 'log',
    payload: { message: 'Loading datasets and preparing workspace…' },
  },
  {
    delay: 1500,
    type: 'log',
    payload: { message: 'Running exploratory data analysis…' },
  },
  {
    delay: 2300,
    type: 'plot',
    payload: {
      figure: {
        data: [
          {
            x: ['train', 'validation', 'test'],
            y: [0.82, 0.76, 0.79],
            type: 'bar',
            marker: { color: ['#2563eb', '#7c3aed', '#0f172a'] },
          },
        ],
        layout: { title: 'Dataset Split Distribution' },
      },
    },
  },
  {
    delay: 3200,
    type: 'table',
    step: 'feature-summary',
    payload: {
      columns: ['feature', 'mean', 'std'],
      rows: [
        ['sepal_length', '5.84', '0.83'],
        ['petal_length', '3.76', '1.76'],
        ['sepal_width', '3.05', '0.43'],
      ],
    },
  },
  {
    delay: 4200,
    type: 'code',
    payload: {
      snippet:
        'model = RandomForestClassifier(n_estimators=200, random_state=42)\nmodel.fit(X_train, y_train)\npreds = model.predict(X_test)',
    },
  },
  {
    delay: 5200,
    type: 'metric',
    payload: { name: 'accuracy', value: 0.87 },
  },
  {
    delay: 6200,
    type: 'log',
    payload: { message: 'Run complete. Review the notebook for details.' },
  },
];

export default function App() {
  const [sessionId, setSessionId] = useState<string>();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isActive, setIsActive] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [uploadState, setUploadState] = useState<{
    isUploading: boolean;
    progress: UploadProgress | null;
  }>({ isUploading: false, progress: null });
  const [isDemoSession, setIsDemoSession] = useState(false);

  const timersRef = useRef<number[]>([]);

  const { events, pushEvent, resetEvents } = useSessionEvents(sessionId, {
    connect: isActive && !isDemoSession,
  });

  const clearTimers = useCallback(() => {
    timersRef.current.forEach((timer) => window.clearTimeout(timer));
    timersRef.current = [];
  }, []);

  useEffect(() => clearTimers, [clearTimers]);

  useEffect(() => {
    setMessages([]);
    resetEvents();
    clearTimers();
    setIsActive(false);
  }, [clearTimers, resetEvents, sessionId]);

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

  const activateDemoSession = useCallback(() => {
    const demoId = `demo-${createId()}`;
    setIsDemoSession(true);
    setSessionId(demoId);
    return demoId;
  }, []);

  const runSimulation = useCallback(() => {
    resetEvents();
    clearTimers();

    SIMULATED_SEQUENCE.forEach(({ delay, ...event }) => {
      const timer = window.setTimeout(() => {
        pushEvent({
          ...event,
          event_id: createId(),
        });
      }, delay);
      timersRef.current.push(timer);
    });
  }, [clearTimers, pushEvent, resetEvents]);

  const handleFilesSelected = useCallback(
    async (files: FileList) => {
      const selected = Array.from(files);
      if (selected.length === 0) return;

      setUploadState({
        isUploading: true,
        progress: { processed: 0, total: selected.length },
      });

      let successfulSession = false;

      for (const [index, file] of selected.entries()) {
        const formData = new FormData();
        formData.append('csv', file);

        try {
          const { data } = await axios.post<{ session_id: string }>('http://localhost:8000/upload', formData);
          setSessionId(data.session_id);
          setIsDemoSession(false);
          successfulSession = true;
        } catch (error) {
          console.error(`Upload failed for ${file.name}`, error);
        } finally {
          setUploadState((prev) => {
            const total = prev.progress?.total ?? selected.length;
            const processed = Math.min(index + 1, total);
            return {
              isUploading: true,
              progress: { processed, total },
            };
          });
        }
      }

      setUploadState({ isUploading: false, progress: null });

      if (!successfulSession) {
        activateDemoSession();
      }
    },
    [activateDemoSession],
  );

  const handleSend = useCallback(
    async (prompt: string) => {
      const trimmed = prompt.trim();
      if (!trimmed || isSending) return false;

      appendMessage('user', trimmed);
      if (!isActive) {
        setIsActive(true);
      }

      const thinkingMessageId = appendMessage('assistant', 'Thinking…');
      setIsSending(true);

      try {
        if (isDemoSession) {
          await new Promise((resolve) => window.setTimeout(resolve, 600));
          updateMessage(thinkingMessageId, "Here's a sample insight based on the demo dataset.");
          runSimulation();
          return true;
        }

        if (!sessionId) {
          throw new Error('Missing session id');
        }

        const { data } = await axios.post<{ reply?: string }>('http://localhost:8000/chat', {
          message: trimmed,
          session_id: sessionId,
        });

        updateMessage(thinkingMessageId, data.reply?.trim() ?? "I don't have a reply yet.");

        runSimulation();
        return true;
      } catch (error) {
        console.error('Failed to send chat message', error);
        const fallback = sessionId
          ? 'Sorry, something went wrong.'
          : 'Please upload a dataset or switch to demo mode before sending a prompt.';
        updateMessage(thinkingMessageId, fallback);
        return false;
      } finally {
        setIsSending(false);
      }
    },
    [appendMessage, isActive, isDemoSession, isSending, runSimulation, sessionId, updateMessage],
  );

  const layout = useMemo(() => {
    if (!isActive) {
      return (
        <PreSessionView
          messages={messages}
          onSend={handleSend}
          onFilesSelected={handleFilesSelected}
          onUseSample={activateDemoSession}
          isSending={isSending}
          isUploading={uploadState.isUploading}
          progress={uploadState.progress}
          canSend={Boolean(sessionId) || isDemoSession}
          isSampleSession={isDemoSession}
        />
      );
    }

    return (
      <div className="grid h-screen grid-cols-[320px_1fr] overflow-hidden bg-slate-100 text-slate-900">
        <ChatSidebar
          messages={messages}
          onSend={handleSend}
          isSending={isSending}
          canSend={Boolean(sessionId)}
          demoMode={isDemoSession}
        />
        <div className="flex h-screen flex-col overflow-hidden bg-white">
          <UploadBar
            onFilesSelected={handleFilesSelected}
            isUploading={uploadState.isUploading}
            progress={uploadState.progress}
            demoMode={isDemoSession}
          />
          <NotebookView sessionId={sessionId} events={events} isActive={isActive} />
        </div>
      </div>
    );
  }, [
    activateDemoSession,
    events,
    handleFilesSelected,
    handleSend,
    isActive,
    isDemoSession,
    isSending,
    messages,
    sessionId,
    uploadState,
  ]);

  return layout;
}
