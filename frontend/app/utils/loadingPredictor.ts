/**
 * Utilities to predict what type of content might be generated next
 * based on user prompts and current context
 */

import type { EventMsg } from '@/app/hooks/useSessionEvents';

export type PredictedCellType = 'code' | 'plot' | 'plan' | 'summary' | 'status';

export interface LoadingPrediction {
  type: PredictedCellType;
  confidence: number; // 0-1
  step?: string;
  estimatedDuration?: number; // milliseconds
}

/**
 * Analyze user prompt to predict what type of analysis will be performed
 */
export function predictFromPrompt(prompt: string): LoadingPrediction {
  const lowerPrompt = prompt.toLowerCase();
  
  // Keywords that suggest different types of analysis
  const plotKeywords = [
    'plot', 'chart', 'graph', 'visualize', 'visualization', 'histogram', 
    'scatter', 'bar chart', 'line chart', 'heatmap', 'distribution',
    'show me', 'display', 'draw'
  ];
  
  const codeKeywords = [
    'calculate', 'compute', 'analyze', 'process', 'transform', 'clean',
    'filter', 'group', 'aggregate', 'merge', 'join', 'statistics'
  ];
  
  const planKeywords = [
    'plan', 'strategy', 'approach', 'steps', 'methodology', 'workflow',
    'outline', 'roadmap'
  ];
  
  const summaryKeywords = [
    'summary', 'summarize', 'overview', 'report', 'conclusion', 'findings',
    'results', 'insights'
  ];
  
  // Count keyword matches
  const plotScore = plotKeywords.filter(kw => lowerPrompt.includes(kw)).length;
  const codeScore = codeKeywords.filter(kw => lowerPrompt.includes(kw)).length;
  const planScore = planKeywords.filter(kw => lowerPrompt.includes(kw)).length;
  const summaryScore = summaryKeywords.filter(kw => lowerPrompt.includes(kw)).length;
  
  // Determine most likely type
  const scores = [
    { type: 'plot' as const, score: plotScore },
    { type: 'code' as const, score: codeScore },
    { type: 'plan' as const, score: planScore },
    { type: 'summary' as const, score: summaryScore }
  ];
  
  const maxScore = Math.max(...scores.map(s => s.score));
  const prediction = scores.find(s => s.score === maxScore);
  
  // If no clear prediction, default to plan for new sessions
  if (maxScore === 0) {
    return {
      type: 'plan',
      confidence: 0.3,
      estimatedDuration: 3000
    };
  }
  
  // Calculate confidence based on score and prompt length
  const confidence = Math.min(0.9, (maxScore / Math.max(1, prompt.split(' ').length)) * 2);
  
  return {
    type: prediction!.type,
    confidence,
    estimatedDuration: getEstimatedDuration(prediction!.type)
  };
}

/**
 * Predict next cell type based on recent events and patterns
 */
export function predictFromEvents(events: EventMsg[]): LoadingPrediction {
  if (events.length === 0) {
    return {
      type: 'plan',
      confidence: 0.8,
      step: '1',
      estimatedDuration: 2000
    };
  }
  
  const lastEvent = events[events.length - 1];
  const recentEvents = events.slice(-5); // Look at last 5 events
  
  // Count different event types
  const eventCounts = {
    code: events.filter(e => e.type === 'code').length,
    plot: events.filter(e => e.type === 'plot').length,
    plan: events.filter(e => e.type === 'plan').length,
    summary: events.filter(e => e.type === 'assistant_message').length,
    status: events.filter(e => e.type === 'status').length
  };
  
  // Predict based on last event type
  switch (lastEvent.type) {
    case 'status':
      const stage = getEventStage(lastEvent);
      if (stage === 'starting') {
        return {
          type: 'plan',
          confidence: 0.9,
          estimatedDuration: 2000
        };
      } else if (stage === 'running') {
        return {
          type: 'code',
          confidence: 0.8,
          step: String(eventCounts.code + 1),
          estimatedDuration: 4000
        };
      }
      break;
      
    case 'plan':
      return {
        type: 'code',
        confidence: 0.9,
        step: '1',
        estimatedDuration: 3000
      };
      
    case 'code':
      // Analyze the code to predict what comes next
      const codeContent = getEventCode(lastEvent);
      
      if (containsPlotCode(codeContent)) {
        return {
          type: 'plot',
          confidence: 0.85,
          step: String(eventCounts.plot + 1),
          estimatedDuration: 2000
        };
      } else {
        // Might be more code or summary
        const codeToSummaryRatio = eventCounts.code / Math.max(1, eventCounts.summary);
        
        if (codeToSummaryRatio > 3) {
          return {
            type: 'summary',
            confidence: 0.7,
            estimatedDuration: 3000
          };
        } else {
          return {
            type: 'code',
            confidence: 0.6,
            step: String(eventCounts.code + 1),
            estimatedDuration: 4000
          };
        }
      }
      
    case 'plot':
      // After a plot, usually more analysis or summary
      return {
        type: eventCounts.code > eventCounts.summary ? 'summary' : 'code',
        confidence: 0.6,
        step: eventCounts.code > eventCounts.summary ? undefined : String(eventCounts.code + 1),
        estimatedDuration: 3500
      };
      
    default:
      return {
        type: 'status',
        confidence: 0.5,
        estimatedDuration: 1000
      };
  }
  
  return {
    type: 'status',
    confidence: 0.4,
    estimatedDuration: 2000
  };
}

/**
 * Get estimated duration for different cell types
 */
function getEstimatedDuration(type: PredictedCellType): number {
  const durations = {
    status: 1000,
    plan: 2500,
    code: 4000,
    plot: 2000,
    summary: 3000
  };
  
  return durations[type] || 2000;
}

/**
 * Extract stage from status event
 */
function getEventStage(event: EventMsg): string {
  if (typeof event.payload === 'object' && event.payload && 'stage' in event.payload) {
    return String(event.payload.stage || '');
  }
  return '';
}

/**
 * Extract code content from code event
 */
function getEventCode(event: EventMsg): string {
  if (typeof event.payload === 'object' && event.payload && 'code' in event.payload) {
    return String(event.payload.code || '');
  }
  return '';
}

/**
 * Check if code contains plotting commands
 */
function containsPlotCode(code: string): boolean {
  const plotPatterns = [
    /plt\./,
    /\.plot\(/,
    /seaborn|sns\./,
    /plotly/,
    /matplotlib/,
    /\.hist\(/,
    /\.scatter\(/,
    /\.bar\(/,
    /\.line\(/
  ];
  
  return plotPatterns.some(pattern => pattern.test(code));
}

/**
 * Combine prompt and event predictions for better accuracy
 */
export function getCombinedPrediction(
  prompt: string, 
  events: EventMsg[]
): LoadingPrediction {
  const promptPrediction = predictFromPrompt(prompt);
  const eventPrediction = predictFromEvents(events);
  
  // If we have no events, trust the prompt more
  if (events.length === 0) {
    return {
      ...promptPrediction,
      confidence: Math.max(0.6, promptPrediction.confidence)
    };
  }
  
  // If event prediction has high confidence, use it
  if (eventPrediction.confidence > 0.7) {
    return eventPrediction;
  }
  
  // Otherwise, blend the predictions
  const blendedConfidence = (promptPrediction.confidence + eventPrediction.confidence) / 2;
  
  return {
    type: eventPrediction.confidence > promptPrediction.confidence 
      ? eventPrediction.type 
      : promptPrediction.type,
    confidence: blendedConfidence,
    step: eventPrediction.step,
    estimatedDuration: Math.max(
      promptPrediction.estimatedDuration || 2000,
      eventPrediction.estimatedDuration || 2000
    )
  };
}

/**
 * Get a user-friendly loading message based on prediction
 */
export function getLoadingMessage(prediction: LoadingPrediction): string {
  const messages = {
    status: 'Initializing analysis...',
    plan: 'Creating analysis plan...',
    code: `Executing analysis step ${prediction.step || ''}...`,
    plot: `Generating visualization ${prediction.step || ''}...`,
    summary: 'Summarizing results...'
  };
  
  return messages[prediction.type] || 'Processing...';
}