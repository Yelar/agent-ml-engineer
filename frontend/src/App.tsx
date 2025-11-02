import ChatSidebar from "./components/ChatSidebar";
import NotebookView from "./components/NotebookView";

function App(): JSX.Element {
  return (
    <div className="app">
      <ChatSidebar />
      <NotebookView />
    </div>
  );
}

export default App;
