"use client";

import { useState } from "react";
import { Light as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import python from "react-syntax-highlighter/dist/esm/languages/prism/python";
import javascript from "react-syntax-highlighter/dist/esm/languages/prism/javascript";
import ReactMarkdown from "react-markdown";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import type { DocumentBlock } from "@/lib/websocket-types";
import { Button } from "@/components/ui/button";
import { toast } from "@/components/toast";

// Register languages for syntax highlighter
SyntaxHighlighter.registerLanguage("python", python);
SyntaxHighlighter.registerLanguage("javascript", javascript);

interface AgentDocumentProps {
  documentBlocks: DocumentBlock[];
}

export function AgentDocument({ documentBlocks }: AgentDocumentProps) {
  const exportToPython = () => {
    const codeBlocks = documentBlocks.filter((block) => block.type === "code");
    const combinedCode = codeBlocks
      .map((block) => (block as any).content)
      .join("\n\n");

    const blob = new Blob([combinedCode], { type: "text/x-python" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "agent_code.py";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    toast({
      type: "success",
      description: "Code exported successfully!",
    });
  };

  return (
    <div className="flex h-full flex-col border-l bg-muted/30">
      {/* Header */}
      <div className="flex items-center justify-between border-b bg-background px-4 py-3">
        <h2 className="text-lg font-semibold">Document</h2>
        <Button onClick={exportToPython} size="sm" variant="outline">
          Export to Python
        </Button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="space-y-4">
          {documentBlocks.map((block) => {
            switch (block.type) {
              case "code":
                return <CodeBlockComponent key={block.id} block={block} />;
              case "chart":
                return <ChartBlockComponent key={block.id} block={block} />;
              case "markdown":
                return <MarkdownBlockComponent key={block.id} block={block} />;
              default:
                return null;
            }
          })}
        </div>
      </div>
    </div>
  );
}

// Code Block Component
function CodeBlockComponent({ block }: { block: Extract<DocumentBlock, { type: "code" }> }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(block.content);
    setCopied(true);
    toast({
      type: "success",
      description: "Code copied to clipboard!",
    });
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="rounded-lg border bg-background shadow-sm">
      <div className="flex items-center justify-between border-b px-4 py-2">
        <span className="text-sm font-medium text-muted-foreground">Code</span>
        <Button onClick={handleCopy} size="sm" variant="ghost">
          {copied ? "Copied!" : "Copy"}
        </Button>
      </div>
      <div className="overflow-x-auto">
        <SyntaxHighlighter
          language="python"
          style={oneDark}
          customStyle={{
            margin: 0,
            borderRadius: 0,
            background: "transparent",
          }}
        >
          {block.content}
        </SyntaxHighlighter>
      </div>
    </div>
  );
}

// Chart Block Component
function ChartBlockComponent({
  block,
}: {
  block: Extract<DocumentBlock, { type: "chart" }>;
}) {
  const { title, data } = block.content;

  // Determine chart type based on data keys
  const keys = Object.keys(data[0] || {});
  const xKey = keys[0];
  const yKeys = keys.slice(1);

  return (
    <div className="rounded-lg border bg-background p-4 shadow-sm">
      <h3 className="mb-4 text-sm font-semibold">{title}</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey={xKey} />
          <YAxis />
          <Tooltip />
          <Legend />
          {yKeys.map((key, idx) => (
            <Line
              key={key}
              type="monotone"
              dataKey={key}
              stroke={`hsl(${(idx * 137) % 360}, 70%, 50%)`}
              strokeWidth={2}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

// Markdown Block Component
function MarkdownBlockComponent({
  block,
}: {
  block: Extract<DocumentBlock, { type: "markdown" }>;
}) {
  return (
    <div className="rounded-lg border bg-background p-4 shadow-sm">
      <div className="prose prose-sm dark:prose-invert max-w-none">
        <ReactMarkdown>{block.content}</ReactMarkdown>
      </div>
    </div>
  );
}

