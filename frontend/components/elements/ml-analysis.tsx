"use client";

import { memo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Loader2, CheckCircle2, XCircle, Brain, Code2 } from "lucide-react";
import { CodeBlock } from "./code-block";

interface MLAnalysisProps {
  status?: {
    status: string;
    message: string;
  };
  plan?: string;
  thinking?: string;
  codeBlocks?: Array<{
    code: string;
    output: string;
    index: number;
  }>;
}

function PureMLAnalysis({ status, plan, thinking, codeBlocks }: MLAnalysisProps) {
  return (
    <div className="space-y-4">
      {/* Status */}
      {status && (
        <Card className="border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-950">
          <CardContent className="flex items-center gap-3 p-4">
            {status.status === "starting" && (
              <Loader2 className="size-5 animate-spin text-blue-600 dark:text-blue-400" />
            )}
            {status.status === "complete" && (
              <CheckCircle2 className="size-5 text-green-600 dark:text-green-400" />
            )}
            {status.status === "error" && (
              <XCircle className="size-5 text-red-600 dark:text-red-400" />
            )}
            <span className="text-sm font-medium">{status.message}</span>
          </CardContent>
        </Card>
      )}

      {/* Plan */}
      {plan && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Brain className="size-4" />
              Execution Plan
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="prose prose-sm max-w-none dark:prose-invert">
              {plan}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Thinking */}
      {thinking && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Brain className="size-4" />
              Agent Thinking
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="prose prose-sm max-w-none dark:prose-invert">
              {thinking}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Code Blocks */}
      {codeBlocks && codeBlocks.length > 0 && (
        <div className="space-y-3">
          {codeBlocks.map((block, idx) => (
            <Card key={block.index || idx}>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <Code2 className="size-4" />
                  Code Block {block.index || idx + 1}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {/* <CodeBlock language="python">{block.code}</CodeBlock> */}

                {block.output && (
                  <div>
                    <Badge variant="outline" className="mb-2">
                      Output
                    </Badge>
                    <pre className="rounded-md bg-muted p-3 text-xs overflow-x-auto">
                      <code>{block.output}</code>
                    </pre>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

export const MLAnalysis = memo(PureMLAnalysis, (prevProps, nextProps) => {
  return (
    prevProps.status === nextProps.status &&
    prevProps.plan === nextProps.plan &&
    prevProps.thinking === nextProps.thinking &&
    prevProps.codeBlocks === nextProps.codeBlocks
  );
});

MLAnalysis.displayName = "MLAnalysis";

