import { useState } from "react";
import ChatSidebar from "./components/ChatSidebar";
import NotebookView from "./components/NotebookView";
import UploadBar from "./components/UploadBar";

function App() {
  const [sessionId, setSessionId] = useState<string>();

  return (
    <div className="grid h-screen grid-cols-[320px_1fr] overflow-hidden bg-slate-100 text-slate-900">
      <ChatSidebar sessionId={sessionId} />
      <div className="flex h-screen flex-col overflow-hidden bg-white">
        <UploadBar onUpload={setSessionId} />
        <NotebookView sessionId={sessionId} />
      </div>
    </div>
  );
}

export default App;
