// Configuration for the WebSocket chat

export const getWebSocketUrl = (sessionId: string): string => {
  // Check for environment variable first
  const baseUrl =
    process.env.NEXT_PUBLIC_WS_URL ||
    (typeof window !== "undefined" && window.location.hostname === "localhost"
      ? "ws://localhost:8000"
      : `wss://${typeof window !== "undefined" ? window.location.host : ""}`);

  return `${baseUrl}/ws/${sessionId}`;
};

