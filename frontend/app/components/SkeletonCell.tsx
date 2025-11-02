'use client';

import { useEffect, useState } from 'react';

type SkeletonCellType = 'code' | 'plot' | 'plan' | 'summary' | 'status' | 'generic';

type SkeletonCellProps = {
  type?: SkeletonCellType;
  step?: string;
  className?: string;
};

// Shimmer animation component
const Shimmer = ({ className = '' }: { className?: string }) => (
  <div className={`bg-slate-700 animate-pulse ${className}`} />
);

// Skeleton line component with random widths for more realistic loading
const SkeletonLine = ({ width = 'full', className = '' }: { width?: string; className?: string }) => {
  const widthMap = {
    'full': 'w-full',
    'long': 'w-5/6',
    'medium': 'w-2/3',
    'short': 'w-1/3',
    'random': 'w-3/4'
  };

  const widthClass = widthMap[width as keyof typeof widthMap] || 'w-full';

  return (
    <div 
      className={`h-4 rounded bg-slate-700 animate-pulse ${widthClass} ${className}`}
    />
  );
};

// Skeleton code block
const SkeletonCodeBlock = () => (
  <div className="space-y-3">
    <div className="rounded-2xl border border-slate-800 bg-slate-950/80 p-4 shadow-inner">
      <div className="space-y-2 font-mono text-xs">
        <SkeletonLine width="medium" />
        <SkeletonLine width="long" />
        <SkeletonLine width="short" />
        <SkeletonLine width="long" />
        <SkeletonLine width="medium" />
      </div>
    </div>
  </div>
);

// Skeleton output block
const SkeletonOutputBlock = ({ step }: { step?: string }) => (
  <section className="space-y-2">
    <div className="text-xs uppercase tracking-wide text-slate-300">
      <Shimmer className="h-3 w-16 rounded" />
    </div>
    <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
      <div className="space-y-2">
        <SkeletonLine width="long" />
        <SkeletonLine width="medium" />
        <SkeletonLine width="short" />
      </div>
    </div>
  </section>
);

// Skeleton plot/figure
const SkeletonPlot = () => (
  <div className="flex justify-center overflow-hidden rounded-2xl border border-slate-800 bg-slate-950/80">
    <div className="flex h-64 w-full items-center justify-center p-4">
      <div className="flex flex-col items-center space-y-3">
        <Shimmer className="h-32 w-48 rounded-lg" />
        <div className="flex space-x-2">
          <Shimmer className="h-2 w-12 rounded" />
          <Shimmer className="h-2 w-16 rounded" />
          <Shimmer className="h-2 w-10 rounded" />
        </div>
      </div>
    </div>
  </div>
);

// Skeleton markdown content
const SkeletonMarkdown = ({ lines = 4 }: { lines?: number }) => (
  <div className="space-y-3">
    {Array.from({ length: lines }, (_, i) => (
      <SkeletonLine 
        key={i} 
        width={i === lines - 1 ? 'short' : 'random'} 
      />
    ))}
  </div>
);

// Skeleton metadata grid
const SkeletonMetadata = () => (
  <dl className="grid grid-cols-1 gap-2 text-sm text-slate-200 md:grid-cols-2">
    {Array.from({ length: 4 }, (_, i) => (
      <div key={i} className="rounded-2xl border border-slate-800/70 bg-slate-950/70 px-3 py-2">
        <dt className="text-xs uppercase tracking-wide text-slate-400">
          <Shimmer className="h-3 w-16 rounded" />
        </dt>
        <dd className="mt-1">
          <Shimmer className="h-4 w-24 rounded" />
        </dd>
      </div>
    ))}
  </dl>
);

// Pulsing dots for status loading
const PulsingDots = () => (
  <div className="flex space-x-1">
    {[0, 1, 2].map((i) => (
      <div
        key={i}
        className="h-1.5 w-1.5 rounded-full bg-slate-400 animate-pulse"
        style={{
          animationDelay: `${i * 0.2}s`,
          animationDuration: '1s'
        }}
      />
    ))}
  </div>
);

export default function SkeletonCell({ type = 'generic', step, className = '' }: SkeletonCellProps) {
  const stepLabel = step ?? '·';



  // Base article classes matching the real cells
  const baseClasses = "animate-cell-enter space-y-4 rounded-3xl border border-slate-800/80 bg-slate-900/80 p-6 shadow-[0_32px_90px_-50px_rgba(15,23,42,0.9)]";
  
  // Status cells have different styling
  const statusClasses = "animate-cell-enter space-y-2 rounded-3xl border border-dashed border-slate-800/80 bg-slate-900/70 p-5 text-sm text-slate-200 shadow-[0_24px_60px_-40px_rgba(15,23,42,0.8)]";

  if (type === 'status') {
    return (
      <article className={`${statusClasses} ${className}`}>
        <div className="flex items-center space-x-2">
          <Shimmer className="h-3 w-20 rounded" />
          <PulsingDots />
        </div>
        <div className="space-y-2">
          <SkeletonLine width="long" />
          <SkeletonLine width="medium" />
        </div>
      </article>
    );
  }

  return (
    <article className={`${baseClasses} ${className}`}>
      {/* Header */}
      <header className="flex items-center justify-between text-xs uppercase tracking-wide text-slate-400">
        <span className="font-semibold text-slate-100 flex items-center space-x-2">
          {type === 'code' && (
            <>
              <span>In&nbsp;[{stepLabel}]</span>
              <PulsingDots />
            </>
          )}
          {type === 'plot' && (
            <>
              <span>Figure&nbsp;{stepLabel}</span>
              <PulsingDots />
            </>
          )}
          {type === 'plan' && (
            <>
              <span>Plan</span>
              <PulsingDots />
            </>
          )}
          {type === 'summary' && (
            <>
              <span>Summary</span>
              <PulsingDots />
            </>
          )}
          {type === 'generic' && (
            <>
              <span>Loading...</span>
              <PulsingDots />
            </>
          )}
        </span>
        <div className="h-3 w-12 rounded bg-slate-700 animate-pulse" />
      </header>

      {/* Content based on type - Always show content */}
      <div className="space-y-3">
        {type === 'code' && (
          <>
            <SkeletonCodeBlock />
            <SkeletonOutputBlock step={stepLabel} />
          </>
        )}

        {type === 'plot' && <SkeletonPlot />}

        {type === 'plan' && <SkeletonMarkdown lines={6} />}

        {type === 'summary' && <SkeletonMarkdown lines={4} />}

        {(type === 'generic' || !type) && <SkeletonMarkdown lines={3} />}
      </div>
    </article>
  );
}

// Specialized skeleton components for different scenarios
export const SkeletonCodeCell = ({ step }: { step?: string }) => (
  <SkeletonCell type="code" step={step} />
);

export const SkeletonPlotCell = ({ step }: { step?: string }) => (
  <SkeletonCell type="plot" step={step} />
);

export const SkeletonPlanCell = () => (
  <SkeletonCell type="plan" />
);

export const SkeletonSummaryCell = () => (
  <SkeletonCell type="summary" />
);

export const SkeletonStatusCell = () => (
  <SkeletonCell type="status" />
);

// Loading indicator for when agent is thinking
export const ThinkingIndicator = ({ message = "Agent is thinking" }: { message?: string }) => (
  <article className="animate-cell-enter space-y-2 rounded-3xl border border-dashed border-blue-500/30 bg-blue-900/20 p-5 text-sm text-blue-200 shadow-[0_24px_60px_-40px_rgba(59,130,246,0.3)]">
    <div className="flex items-center space-x-3">
      <div className="flex space-x-1">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className="h-2 w-2 rounded-full bg-blue-400 animate-bounce"
            style={{
              animationDelay: `${i * 0.1}s`,
              animationDuration: '0.6s'
            }}
          />
        ))}
      </div>
      <span className="text-xs font-semibold uppercase tracking-wide text-blue-300">
        {message}
      </span>
    </div>
  </article>
);