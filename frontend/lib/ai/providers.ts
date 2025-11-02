import { gateway } from "@ai-sdk/gateway";
import { createOpenAI } from "@ai-sdk/openai";
import {
  customProvider,
  extractReasoningMiddleware,
  wrapLanguageModel,
} from "ai";
import { isTestEnvironment } from "../constants";

// Use backend for LLM calls or Vercel Gateway
const USE_BACKEND = process.env.NEXT_PUBLIC_USE_BACKEND === "true" || true;
const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

// Create backend provider (OpenAI-compatible)
// Your backend implements /v1/chat/completions at the correct endpoint
const backendOpenAI = createOpenAI({
  baseURL: `${BACKEND_URL}/v1`,
  apiKey: "not-needed", // Backend handles OpenAI API key internally
  fetch: async (url, init) => {
    // Log requests for debugging
    console.log('[Backend Provider] Request:', { url: url.toString(), method: init?.method });
    const response = await fetch(url, init);
    
    // Log response for debugging
    if (!response.ok) {
      const text = await response.text();
      console.error('[Backend Provider] Error:', { status: response.status, body: text });
      throw new Error(`Backend request failed: ${response.status} ${text}`);
    }
    
    return response;
  },
});

// Fallback to Vercel Gateway if backend not configured
const gatewayModels = {
  "chat-model": gateway.languageModel("xai/grok-2-vision-1212"),
  "chat-model-reasoning": wrapLanguageModel({
    model: gateway.languageModel("xai/grok-3-mini"),
    middleware: extractReasoningMiddleware({ tagName: "think" }),
  }),
  "title-model": gateway.languageModel("xai/grok-2-1212"),
  "artifact-model": gateway.languageModel("xai/grok-2-1212"),
};

// Backend models (if using backend)
const backendModels = {
  "chat-model": backendOpenAI("gpt-4o-mini"),
  "chat-model-reasoning": backendOpenAI("gpt-4o"),
  "title-model": backendOpenAI("gpt-4o-mini"),
  "artifact-model": backendOpenAI("gpt-4o-mini"),
};

export const myProvider = isTestEnvironment
  ? (() => {
      const {
        artifactModel,
        chatModel,
        reasoningModel,
        titleModel,
      } = require("./models.mock");
      return customProvider({
        languageModels: {
          "chat-model": chatModel,
          "chat-model-reasoning": reasoningModel,
          "title-model": titleModel,
          "artifact-model": artifactModel,
        },
      });
    })()
  : customProvider({
      languageModels: USE_BACKEND ? backendModels : gatewayModels,
    });
