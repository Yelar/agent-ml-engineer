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

    for (const dataPart of dataStream) {
      // @ts-expect-error - Custom ML data types
      if (dataPart.type === "ml-status") {
        setMlState((prev) => ({
          ...prev,
          // @ts-expect-error - Custom ML data types
          status: dataPart.data,
        }));
        // @ts-expect-error - Custom ML data types
      } else if (dataPart.type === "ml-plan") {
        setMlState((prev) => ({
          ...prev,
          // @ts-expect-error - Custom ML data types
          plan: dataPart.data,
        }));
        // @ts-expect-error - Custom ML data types
      } else if (dataPart.type === "ml-thinking") {
        setMlState((prev) => ({
          ...prev,
          // @ts-expect-error - Custom ML data types
          thinking: dataPart.data,
        }));
        // @ts-expect-error - Custom ML data types
      } else if (dataPart.type === "ml-code") {
        setMlState((prev) => ({
          ...prev,
          codeBlocks: [
            ...prev.codeBlocks,
            {
              // @ts-expect-error - Custom ML data types
              code: dataPart.data.code,
              // @ts-expect-error - Custom ML data types
              output: dataPart.data.output,
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

