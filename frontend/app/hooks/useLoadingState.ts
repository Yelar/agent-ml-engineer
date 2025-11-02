'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import type { EventMsg } from '@/app/hooks/useSessionEvents';
import { getCombinedPrediction, getLoadingMessage, type LoadingPrediction } from '@/app/utils/loadingPredictor';

export type LoadingState = {
  isLoading: boolean;
  expectedType?: 'code' | 'plot' | 'plan' | 'summary' | 'status';
  step?: string;
  message?: string;
  confidence?: number;
  prediction?: LoadingPrediction;
};

export type LoadingStateManager = {
  loadingState: LoadingState;
  startLoading: (type?: LoadingState['expectedType'], step?: string, message?: string) => void;
  stopLoading: () => void;
  updateLoadingMessage: (message: string) => void;
};

/**
 * Hook to manage loading states for notebook cells
 * Automatically shows skeleton loaders while waiting for backend events
 */
export function useLoadingState(
  isSending: boolean,
  events: EventMsg[],
  lastPrompt?: string
): LoadingStateManager {
  const [loadingState, setLoadingState] = useState<LoadingState>({
    isLoading: false,
  });
  
  const loadingTimeoutRef = useRef<NodeJS.Timeout | undefined>(undefined);
  const lastEventCountRef = useRef(0);

  // Start loading with optional type prediction
  const startLoading = useCallback((
    type?: LoadingState['expectedType'], 
    step?: string, 
    message?: string
  ) => {
    setLoadingState({
      isLoading: true,
      expectedType: type,
      step,
      message: message || 'Processing...'
    });

    // Clear any existing timeout
    if (loadingTimeoutRef.current) {
      clearTimeout(loadingTimeoutRef.current);
      loadingTimeoutRef.current = undefined;
    }

    // Auto-stop loading after 30 seconds as fallback
    loadingTimeoutRef.current = setTimeout(() => {
      setLoadingState(prev => ({ ...prev, isLoading: false }));
    }, 30000) as NodeJS.Timeout;
  }, []);

  // Stop loading
  const stopLoading = useCallback(() => {
    setLoadingState(prev => ({ ...prev, isLoading: false }));
    if (loadingTimeoutRef.current) {
      clearTimeout(loadingTimeoutRef.current);
      loadingTimeoutRef.current = undefined;
    }
  }, []);

  // Update loading message
  const updateLoadingMessage = useCallback((message: string) => {
    setLoadingState(prev => ({ ...prev, message }));
  }, []);

  // Auto-manage loading state based on events and sending state
  useEffect(() => {
    const currentEventCount = events.length;
    
    // If we're sending and no new events, start loading with prediction
    if (isSending && currentEventCount === lastEventCountRef.current) {
      if (!loadingState.isLoading) {
        const prediction = getCombinedPrediction(lastPrompt || '', events);
        const message = getLoadingMessage(prediction);
        
        setLoadingState({
          isLoading: true,
          expectedType: prediction.type,
          step: prediction.step,
          message,
          confidence: prediction.confidence,
          prediction
        });

        // Set timeout based on prediction
        if (loadingTimeoutRef.current) {
          clearTimeout(loadingTimeoutRef.current);
          loadingTimeoutRef.current = undefined;
        }
        
        const timeout = Math.min(30000, (prediction.estimatedDuration || 5000) * 2);
        loadingTimeoutRef.current = setTimeout(() => {
          setLoadingState(prev => ({ ...prev, isLoading: false }));
        }, timeout) as NodeJS.Timeout;
      }
    }
    
    // If we got new events, stop loading
    if (currentEventCount > lastEventCountRef.current) {
      stopLoading();
      lastEventCountRef.current = currentEventCount;
    }
    
    // If sending stopped, stop loading
    if (!isSending && loadingState.isLoading) {
      stopLoading();
    }
  }, [isSending, events.length, loadingState.isLoading, lastPrompt, stopLoading]);

  // Predict next cell type based on recent events
  useEffect(() => {
    if (!loadingState.isLoading || events.length === 0) return;

    const recentEvents = events.slice(-3); // Look at last 3 events
    const lastEvent = recentEvents[recentEvents.length - 1];
    
    // Predict what might come next based on patterns
    let predictedType: LoadingState['expectedType'] = 'status';
    let predictedStep: string | undefined;
    
    if (lastEvent?.type === 'status') {
      const stage = typeof lastEvent.payload === 'object' && lastEvent.payload && 'stage' in lastEvent.payload 
        ? lastEvent.payload.stage 
        : '';
      
      if (stage === 'running') {
        predictedType = 'code';
        predictedStep = String((events.filter(e => e.type === 'code').length || 0) + 1);
      } else if (stage === 'starting') {
        predictedType = 'plan';
      }
    } else if (lastEvent?.type === 'plan') {
      predictedType = 'code';
      predictedStep = '1';
    } else if (lastEvent?.type === 'code') {
      // After code, we might get output, plot, or more code
      const codeEvents = events.filter(e => e.type === 'code');
      const plotEvents = events.filter(e => e.type === 'plot');
      
      // If this code block might generate a plot
      const lastCodePayload = lastEvent.payload;
      if (typeof lastCodePayload === 'object' && lastCodePayload && 'code' in lastCodePayload) {
        const code = String(lastCodePayload.code || '');
        if (code.includes('plt.') || code.includes('plot') || code.includes('seaborn') || code.includes('sns.')) {
          predictedType = 'plot';
          predictedStep = String(plotEvents.length + 1);
        } else {
          predictedType = 'code';
          predictedStep = String(codeEvents.length + 1);
        }
      }
    }
    
    // Update prediction if it changed
    if (predictedType !== loadingState.expectedType || predictedStep !== loadingState.step) {
      setLoadingState(prev => ({
        ...prev,
        expectedType: predictedType,
        step: predictedStep
      }));
    }
  }, [events, loadingState.isLoading, loadingState.expectedType, loadingState.step]);

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (loadingTimeoutRef.current) {
        clearTimeout(loadingTimeoutRef.current);
      }
    };
  });

  return {
    loadingState,
    startLoading,
    stopLoading,
    updateLoadingMessage,
  };
}

/**
 * Hook to detect when we should show a skeleton loader
 * Based on timing patterns and event gaps
 */
export function useSkeletonTiming(
  events: EventMsg[],
  isSending: boolean,
  minDelay: number = 1000 // Minimum delay before showing skeleton
) {
  const [shouldShowSkeleton, setShouldShowSkeleton] = useState(false);
  const timeoutRef = useRef<NodeJS.Timeout | undefined>(undefined);
  const lastEventTimeRef = useRef<number>(Date.now());

  useEffect(() => {
    // Clear existing timeout
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = undefined;
    }

    if (isSending) {
      // Start timer to show skeleton after delay
      timeoutRef.current = setTimeout(() => {
        setShouldShowSkeleton(true);
      }, minDelay) as NodeJS.Timeout;
    } else {
      // Hide skeleton immediately when not sending
      setShouldShowSkeleton(false);
    }

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = undefined;
      }
    };
  }, [isSending, minDelay]);

  // Hide skeleton when new events arrive
  useEffect(() => {
    if (events.length > 0) {
      setShouldShowSkeleton(false);
      lastEventTimeRef.current = Date.now();
    }
  }, [events.length]);

  return shouldShowSkeleton;
}