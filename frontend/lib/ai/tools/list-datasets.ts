import { tool } from "ai";
import { z } from "zod";

export const listDatasets = tool({
  description:
    "List all available datasets that can be analyzed. Use this when the user asks what datasets are available.",
  parameters: z.object({}),
  execute: async () => {
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000"}/datasets`
      );

      if (!response.ok) {
        throw new Error(`Backend error: ${response.statusText}`);
      }

      const data = await response.json();
      return {
        datasets: data.datasets || [],
        count: data.datasets?.length || 0,
      };
    } catch (error) {
      return {
        error:
          error instanceof Error ? error.message : "Failed to fetch datasets",
        datasets: [],
        count: 0,
      };
    }
  },
});

