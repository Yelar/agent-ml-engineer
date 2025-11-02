"use client";

import { Light as SyntaxHighlighter } from "react-syntax-highlighter";
import { atomOneDark } from "react-syntax-highlighter/dist/esm/styles/hljs";
import python from "react-syntax-highlighter/dist/esm/languages/hljs/python";
import ReactMarkdown from "react-markdown";
import { toast } from "sonner";
import { Artifact } from "@/components/create-artifact";
import { CopyIcon, DownloadIcon, FileIcon } from "@/components/icons";
import type { DocumentBlock } from "@/lib/websocket-types";

SyntaxHighlighter.registerLanguage("python", python);

type Metadata = {
  blocks: DocumentBlock[];
};

export const mlAnalysisArtifact = new Artifact<"ml-analysis", Metadata>({
  kind: "ml-analysis",
  description: "ML analysis results with code execution, visualizations, and insights",
  initialize: ({ setMetadata }) => {
    setMetadata({
      blocks: [],
    });
  },
  onStreamPart: ({ streamPart, setArtifact, setMetadata }) => {
    // Handle WebSocket block additions
    if (streamPart.type === "data-mlBlock") {
      const block = streamPart.data;
      
      setMetadata((metadata) => ({
        ...metadata,
        blocks: [...(metadata.blocks || []), block],
      }));

      // Update visibility
      setArtifact((draft) => ({
        ...draft,
        isVisible: true,
        status: "streaming",
      }));
    }

    // Mark as complete
    if (streamPart.type === "data-mlComplete") {
      setArtifact((draft) => ({
        ...draft,
        status: "idle",
      }));
    }
  },
  content: ({ metadata }) => {
    if (!metadata?.blocks || metadata.blocks.length === 0) {
      return (
        <div className="flex h-full items-center justify-center p-8 text-muted-foreground">
          <p>Agent is analyzing...</p>
        </div>
      );
    }

    return (
      <div className="space-y-6 p-6">
        {metadata.blocks.map((block) => {
          // Convert DocumentBlock to EventMsg format for NotebookCell
          const event = {
            event_id: block.id,
            type: block.type,
            step: block.id,
            payload: block.type === "code" 
              ? { code: block.content, output: block.output, error: block.error }
              : block.type === "plot"
              ? { image: block.image }
              : block.type === "markdown"
              ? { content: block.content }
              : block.type === "chart"
              ? block.content
              : block.type === "plan"
              ? { content: block.content }
              : block.type === "assistant_message"
              ? { content: block.content }
              : block.type === "metadata"
              ? block.data
              : block.type === "artifacts"
              ? { items: block.items }
              : block.type === "status"
              ? { stage: block.stage, message: block.message, prompt: block.prompt }
              : block,
            timestamp: new Date().toISOString(),
          };
          
          switch (block.type) {
            case "code":
              return <CodeBlock key={block.id} block={block} />;
            case "markdown":
              return <MarkdownBlock key={block.id} block={block} />;
            case "chart":
              return <ChartBlock key={block.id} block={block} />;
            case "plot":
              return <PlotBlock key={block.id} block={block} />;
            case "plan":
              return <PlanBlock key={block.id} block={block} />;
            case "assistant_message":
              return <AssistantMessageBlock key={block.id} block={block} />;
            case "metadata":
              return <MetadataBlock key={block.id} block={block} />;
            case "artifacts":
              return <ArtifactsBlock key={block.id} block={block} />;
            case "status":
              return <StatusBlock key={block.id} block={block} />;
            default:
              return null;
          }
        })}
      </div>
    );
  },
  actions: [
    {
      icon: <DownloadIcon size={18} />,
      label: "Export Notebook",
      description: "Download as Jupyter notebook",
      onClick: ({ metadata }) => {
        if (!metadata?.blocks) return;

        // Generate notebook JSON
        const cells = metadata.blocks
          .filter((b) => b.type === "code" || b.type === "markdown")
          .map((block) => {
            if (block.type === "code") {
              return {
                cell_type: "code",
                execution_count: null,
                metadata: {},
                outputs: block.output ? [
                  {
                    output_type: "stream",
                    name: "stdout",
                    text: block.output.split("\n"),
                  }
                ] : [],
                source: block.content.split("\n"),
              };
            }
            return {
              cell_type: "markdown",
              metadata: {},
              source: block.content.split("\n"),
            };
          });

        const notebook = {
          cells,
          metadata: {
            kernelspec: {
              display_name: "Python 3",
              language: "python",
              name: "python3",
            },
            language_info: {
              name: "python",
              version: "3.11.0",
            },
          },
          nbformat: 4,
          nbformat_minor: 5,
        };

        const blob = new Blob([JSON.stringify(notebook, null, 2)], {
          type: "application/json",
        });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "ml_analysis.ipynb";
        a.click();
        URL.revokeObjectURL(url);

        toast.success("Downloaded as ml_analysis.ipynb");
      },
    },
    {
      icon: <DownloadIcon size={18} />,
      label: "Export Python",
      description: "Download as Python script",
      onClick: ({ metadata }) => {
        if (!metadata?.blocks) return;

        const codeBlocks = metadata.blocks
          .filter((b) => b.type === "code")
          .map((b) => b.content)
          .join("\n\n");

        const blob = new Blob([codeBlocks], { type: "text/x-python" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "ml_analysis.py";
        a.click();
        URL.revokeObjectURL(url);

        toast.success("Downloaded as ml_analysis.py");
      },
    },
    {
      icon: <CopyIcon size={18} />,
      description: "Copy all code",
      onClick: ({ metadata }) => {
        if (!metadata?.blocks) return;

        const codeBlocks = metadata.blocks
          .filter((b) => b.type === "code")
          .map((b) => b.content)
          .join("\n\n");

        navigator.clipboard.writeText(codeBlocks);
        toast.success("Copied all code to clipboard!");
      },
    },
  ],
  toolbar: [],
});

// Sub-components

function CodeBlock({ block }: { block: DocumentBlock & { type: "code" } }) {
  const stepLabel = block.id || "·";
  
  return (
    <div className="animate-in fade-in-50 duration-300 space-y-4 rounded-xl border border-border bg-card p-5 shadow-sm">
      <div className="flex items-center justify-between text-xs uppercase tracking-wide text-muted-foreground">
        <span className="font-semibold text-primary">In&nbsp;[{stepLabel}]</span>
        <button
          type="button"
          onClick={() => {
            navigator.clipboard.writeText(block.content);
            toast.success("Copied!");
          }}
          className="text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          Copy
        </button>
      </div>
      {block.content ? (
        <div className="text-sm rounded-lg overflow-hidden">
          <SyntaxHighlighter
            language="python"
            style={atomOneDark}
            customStyle={{
              margin: 0,
              padding: "1rem",
              borderRadius: "0.5rem",
            }}
          >
            {block.content}
          </SyntaxHighlighter>
        </div>
      ) : null}
      {block.output ? (
        <div className="space-y-2">
          <div className="text-xs uppercase tracking-wide text-emerald-600 dark:text-emerald-400">
            Out&nbsp;[{stepLabel}]
          </div>
          <pre className="rounded-lg bg-muted p-4 text-sm leading-6 overflow-x-auto">
            {block.output}
          </pre>
        </div>
      ) : null}
      {block.error ? (
        <div className="space-y-2">
          <div className="text-xs uppercase tracking-wide text-destructive">Error</div>
          <pre className="rounded-lg bg-destructive/10 p-4 text-sm leading-6 text-destructive overflow-x-auto">
            {block.error}
          </pre>
        </div>
      ) : null}
    </div>
  );
}

function MarkdownBlock({ block }: { block: DocumentBlock & { type: "markdown" } }) {
  return (
    <div className="animate-in fade-in-50 duration-300 rounded-xl border border-border bg-card p-5 shadow-sm">
      <div className="prose prose-sm dark:prose-invert max-w-none">
        <ReactMarkdown>{block.content}</ReactMarkdown>
      </div>
    </div>
  );
}

function ChartBlock({ block }: { block: DocumentBlock & { type: "chart" } }) {
  return (
    <div className="animate-in fade-in-50 duration-300 rounded-lg border border-border bg-card p-4 shadow-sm">
      <h3 className="text-sm font-semibold mb-3">{block.content.title}</h3>
      <div className="text-xs text-muted-foreground">
        <pre className="bg-muted p-3 rounded overflow-x-auto">
          {JSON.stringify(block.content.data, null, 2)}
        </pre>
      </div>
    </div>
  );
}

function PlotBlock({ block }: { block: DocumentBlock & { type: "plot" } }) {
  const stepLabel = block.step || block.id || "·";
  
  return (
    <div className="animate-in fade-in-50 duration-300 space-y-3 rounded-xl border border-border bg-card p-5 shadow-sm">
      <div className="flex items-center justify-between text-xs uppercase tracking-wide text-muted-foreground">
        <span className="font-semibold">Figure&nbsp;{stepLabel}</span>
      </div>
      <div className="relative w-full rounded-lg border border-border bg-muted/30 p-2">
        <img
          src={`data:image/png;base64,${block.image}`}
          alt={`Notebook figure ${stepLabel}`}
          className="max-h-[420px] w-full rounded-lg object-contain"
        />
      </div>
    </div>
  );
}

function PlanBlock({ block }: { block: DocumentBlock & { type: "plan" } }) {
  return (
    <div className="animate-in fade-in-50 duration-300 space-y-3 rounded-xl border border-border bg-card p-5 shadow-sm">
      <div className="flex items-center justify-between text-xs uppercase tracking-wide text-muted-foreground">
        <span className="font-semibold">Plan</span>
      </div>
      <div className="prose prose-sm dark:prose-invert max-w-none">
        <ReactMarkdown>{block.content}</ReactMarkdown>
      </div>
    </div>
  );
}

function AssistantMessageBlock({ block }: { block: DocumentBlock & { type: "assistant_message" } }) {
  return (
    <div className="animate-in fade-in-50 duration-300 space-y-3 rounded-xl border border-border bg-card p-5 shadow-sm">
      <div className="flex items-center justify-between text-xs uppercase tracking-wide text-muted-foreground">
        <span className="font-semibold">Summary</span>
      </div>
      <div className="prose prose-sm dark:prose-invert max-w-none">
        <ReactMarkdown>{block.content}</ReactMarkdown>
      </div>
    </div>
  );
}

function MetadataBlock({ block }: { block: DocumentBlock & { type: "metadata" } }) {
  return (
    <div className="animate-in fade-in-50 duration-300 space-y-3 rounded-xl border border-border bg-card p-5 shadow-sm">
      <div className="flex items-center justify-between text-xs uppercase tracking-wide text-muted-foreground">
        <span className="font-semibold">Run Metadata</span>
      </div>
      <dl className="grid grid-cols-1 gap-2 text-sm md:grid-cols-2">
        {Object.entries(block.data).map(([key, value]) => (
          <div key={key} className="rounded-lg bg-muted px-3 py-2">
            <dt className="text-xs uppercase tracking-wide text-muted-foreground">{key}</dt>
            <dd className="break-all text-foreground">{String(value ?? "")}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

function ArtifactsBlock({ block }: { block: DocumentBlock & { type: "artifacts" } }) {
  return (
    <div className="animate-in fade-in-50 duration-300 space-y-3 rounded-xl border border-border bg-card p-5 shadow-sm">
      <div className="flex items-center justify-between text-xs uppercase tracking-wide text-muted-foreground">
        <span className="font-semibold">Artifacts</span>
      </div>
      {block.items.length === 0 ? (
        <p className="text-sm text-muted-foreground">No downloadable artifacts were produced.</p>
      ) : (
        <ul className="space-y-2 text-sm">
          {block.items.map((item, idx) => (
            <li key={item.url ?? `${item.name}-${idx}`} className="flex items-center gap-3">
              <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[11px] font-medium uppercase text-primary">
                {item.kind}
              </span>
              {item.url ? (
                <a
                  className="flex items-center gap-1 text-primary underline decoration-primary/40 decoration-dotted underline-offset-2 hover:decoration-solid"
                  href={item.url}
                  download
                  target="_blank"
                  rel="noreferrer"
                >
                  <FileIcon size={14} />
                  {item.name}
                </a>
              ) : (
                <span className="flex items-center gap-1 text-muted-foreground">
                  <FileIcon size={14} />
                  {item.name}
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function StatusBlock({ block }: { block: DocumentBlock & { type: "status" } }) {
  const message =
    block.message ||
    (block.prompt ? `Prompt: ${block.prompt}` : "Agent status updated.");

  return (
    <div className="animate-in fade-in-50 duration-300 space-y-2 rounded-xl border border-dashed border-border bg-muted/50 p-4 text-sm">
      <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        {block.stage}
      </div>
      <p className="text-foreground">{message}</p>
    </div>
  );
}

