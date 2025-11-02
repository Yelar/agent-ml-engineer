"use client";

import { useEffect, useState } from "react";
import { useDataStream } from "./data-stream-provider";
import { MLAnalysis } from "./elements/ml-analysis";

export function MLDataHandler() {
  const { dataStream } = useDataStream();
  const [mlState, setMlState] = useState<{
    status?: { status: string; message: string };
    plan?: string;
    thinking?: string;
    codeBlocks: Array<{ code: string; output: string; index: number }>;
  }>({
    codeBlocks: [],
  });

  useEffect(() => {
    if (!dataStream) return;

    for (const data of dataStream) {
      if (data.type === "ml-status") {
        setMlState((prev) => ({
          ...prev,
          status: data.content,
        }));
      } else if (data.type === "ml-plan") {
        setMlState((prev) => ({
          ...prev,
          plan: data.content,
        }));
      } else if (data.type === "ml-thinking") {
        setMlState((prev) => ({
          ...prev,
          thinking: data.content,
        }));
      } else if (data.type === "ml-code") {
        setMlState((prev) => ({
          ...prev,
          codeBlocks: [
            ...prev.codeBlocks,
            {
              code: data.content.code,
              output: data.content.output,
              index: prev.codeBlocks.length + 1,
            },
          ],
        }));
      }
    }
  }, [dataStream]);

  if (
    !mlState.status &&
    !mlState.plan &&
    !mlState.thinking &&
    mlState.codeBlocks.length === 0
  ) {
    return null;
  }

  return <MLAnalysis {...mlState} />;
}

