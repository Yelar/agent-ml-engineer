import { tool } from "ai";
import { z } from "zod";

export function runMLAnalysis({ dataStream }: { dataStream: any }) {
  return tool({
    description: `Run machine learning analysis on a dataset. This tool executes Python code using pandas, numpy, matplotlib, seaborn, and scikit-learn. 
    Use this when the user asks to:
    - Analyze data
    - Build ML models
    - Create visualizations
    - Generate predictions
    - Explore datasets`,
    inputSchema: z.object({
      prompt: z
        .string()
        .describe(
          "The analysis task to perform. Be specific about what to analyze or build."
        ),
      dataset: z
        .string()
        .optional()
        .describe(
          "Dataset name or path. If not provided, will use the currently loaded dataset."
        ),
    }),
    execute: async (args: { prompt: string; dataset?: string }) => {
      const { prompt, dataset } = args;
      try {
        // Send initial status to document
        dataStream.writeData({
          type: "ml-status",
          content: {
            status: "starting",
            message: "Initializing ML Engineer Agent...",
          },
        });

        // Call backend ML agent
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000"}/api/ml/analyze`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              prompt,
              dataset: dataset || "sample_sales",
            }),
          }
        );

        if (!response.ok) {
          throw new Error(`Backend error: ${response.statusText}`);
        }

        const reader = response.body?.getReader();
        if (!reader) {
          throw new Error("No response body");
        }

        const decoder = new TextDecoder();
        let buffer = "";
        let result = {
          plan: "",
          codeBlocks: [] as Array<{ code: string; output: string }>,
          solution: "",
        };

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (!line.trim() || !line.startsWith("data: ")) continue;

            try {
              const data = JSON.parse(line.slice(6));

              if (data.type === "plan") {
                result.plan = data.content;
                dataStream.writeData({
                  type: "ml-plan",
                  content: data.content,
                });
              } else if (data.type === "thinking") {
                dataStream.writeData({
                  type: "ml-thinking",
                  content: data.content,
                });
              } else if (data.type === "code") {
                result.codeBlocks.push({
                  code: data.content,
                  output: data.output || "",
                });
                dataStream.writeData({
                  type: "ml-code",
                  content: {
                    code: data.content,
                    output: data.output,
                  },
                });
              } else if (data.type === "solution") {
                result.solution = data.content;
              }
            } catch (e) {
              console.error("Error parsing SSE data:", e);
            }
          }
        }

        dataStream.writeData({
          type: "ml-status",
          content: {
            status: "complete",
            message: "Analysis complete!",
          },
        });

        return {
          success: true,
          summary: result.solution || "Analysis completed successfully",
          codeBlocksExecuted: result.codeBlocks.length,
        };
      } catch (error) {
        const errorMessage =
          error instanceof Error ? error.message : "Unknown error";

        dataStream.writeData({
          type: "ml-status",
          content: {
            status: "error",
            message: errorMessage,
          },
        });

        return {
          success: false,
          error: errorMessage,
        };
      }
    },
  });
}

