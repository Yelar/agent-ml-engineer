"use client";

import { Light as SyntaxHighlighter } from "react-syntax-highlighter";
import { atomOneDark } from "react-syntax-highlighter/dist/esm/styles/hljs";
import python from "react-syntax-highlighter/dist/esm/languages/hljs/python";
import ReactMarkdown from "react-markdown";
import { toast } from "sonner";
import { Artifact } from "@/components/create-artifact";
import { CopyIcon, DownloadIcon } from "@/components/icons";
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
  onStreamPart: ({ streamPart, setArtifact, metadata, setMetadata }) => {
    // Handle WebSocket block additions
    if (streamPart.type === "data-ml-block") {
      const block = streamPart.data as DocumentBlock;
      
      setMetadata({
        ...metadata,
        blocks: [...(metadata?.blocks || []), block],
      });

      // Update visibility
      setArtifact((draft) => ({
        ...draft,
        isVisible: true,
        status: "streaming",
      }));
    }

    // Mark as complete
    if (streamPart.type === "data-ml-complete") {
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
          switch (block.type) {
            case "code":
              return <CodeBlock key={block.id} block={block} />;
            case "markdown":
              return <MarkdownBlock key={block.id} block={block} />;
            case "chart":
              return <ChartBlock key={block.id} block={block} />;
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
      label: "Export",
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
  return (
    <div className="rounded-lg border overflow-hidden">
      <div className="flex items-center justify-between bg-muted px-4 py-2 border-b">
        <span className="text-sm font-medium text-muted-foreground">Python</span>
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
      <div className="text-sm">
        <SyntaxHighlighter
          language="python"
          style={atomOneDark}
          customStyle={{
            margin: 0,
            padding: "1rem",
            background: "transparent",
          }}
        >
          {block.content}
        </SyntaxHighlighter>
      </div>
    </div>
  );
}

function MarkdownBlock({ block }: { block: DocumentBlock & { type: "markdown" } }) {
  return (
    <div className="prose prose-sm dark:prose-invert max-w-none">
      <ReactMarkdown>{block.content}</ReactMarkdown>
    </div>
  );
}

function ChartBlock({ block }: { block: DocumentBlock & { type: "chart" } }) {
  // For now, just display the chart data as JSON
  // In production, you'd render with recharts or similar
  return (
    <div className="rounded-lg border p-4">
      <h3 className="text-sm font-semibold mb-3">{block.content.title}</h3>
      <div className="text-xs text-muted-foreground">
        <pre className="bg-muted p-3 rounded overflow-x-auto">
          {JSON.stringify(block.content.data, null, 2)}
        </pre>
      </div>
    </div>
  );
}

