import { FormEvent, useMemo, useState } from "react";
import { FileUp, Files, LockKeyhole, PlusCircle, Send, ShieldCheck } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import "./styles.css";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

type Classification = "General" | "Restricted" | "Sensitive";

type Source = {
  source_file: string;
  classification: Classification;
  score?: number;
};

type Message = {
  id: number;
  role: "user" | "assistant";
  content: string;
};

function App() {
  const [files, setFiles] = useState<File[]>([]);
  const [classification, setClassification] = useState<Classification>("General");
  const [clearance, setClearance] = useState<Classification>("Sensitive");
  const [chatInput, setChatInput] = useState("");
  const [sources, setSources] = useState<Source[]>([]);
  const [conversation, setConversation] = useState<Message[]>([]);
  const [availableFiles, setAvailableFiles] = useState<string[]>([]);
  const [status, setStatus] = useState("Ready for local ingestion.");
  const [busy, setBusy] = useState(false);

  const headers = useMemo(
    () => ({
      "X-User-Clearance": clearance,
      "X-User-Role": "admin",
      "X-User-Id": "workplace_admin",
    }),
    [clearance],
  );

  async function uploadDocument(event: FormEvent) {
    event.preventDefault();
    const form = event.currentTarget as HTMLFormElement;
    if (files.length === 0) return;

    setBusy(true);
    setStatus("Parsing documents, generating embeddings, and storing classified chunks.");
    const formData = new FormData();
    files.forEach((file) => formData.append("files", file));
    formData.append("classification", classification);

    try {
      const response = await fetch(`${API_BASE_URL}/documents/upload`, {
        method: "POST",
        headers,
        body: formData,
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail ?? "Upload failed");
      const uploadedNames = files.map((file) => file.name);
      setAvailableFiles((prev) => Array.from(new Set([...prev, ...uploadedNames])));
      setStatus(`Indexed ${payload.chunks_extracted} chunks from ${payload.file_count} file(s).`);
      setFiles([]);
      form.reset();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  function startNewChat() {
    setConversation([]);
    setSources([]);
    setStatus("Started a new chat. Your uploaded documents remain available.");
  }

  async function sendMessage(event: FormEvent) {
    event.preventDefault();
    const trimmedInput = chatInput.trim();
    if (!trimmedInput) return;

    setBusy(true);
    setStatus("Running metadata-filtered vector search, then asking local Ollama.");

    const userMessage: Message = { id: Date.now(), role: "user", content: trimmedInput };
    const nextConversation = [...conversation, userMessage];
    setConversation(nextConversation);
    setChatInput("");

    try {
      const response = await fetch(`${API_BASE_URL}/search/query`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...headers,
        },
        body: JSON.stringify({ query: trimmedInput, top_k: 5, history: nextConversation }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail ?? "Search failed");
      const assistantText = typeof payload.response === "string" ? payload.response : JSON.stringify(payload.response ?? "", null, 2);
      const consultedFiles = (payload.sources_consulted ?? []).map((source: Source) => source.source_file);
      setSources(payload.sources_consulted ?? []);
      setAvailableFiles((prev) => Array.from(new Set([...prev, ...consultedFiles])));
      setStatus(`Search completed with ${payload.access_clearance_applied} clearance.`);
      setConversation((prev) => [...prev, { id: Date.now() + 1, role: "assistant", content: assistantText }]);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Search failed";
      setStatus(errorMessage);
      setConversation((prev) => [...prev, { id: Date.now() + 2, role: "assistant", content: `Sorry, I couldn't answer that request. ${errorMessage}` }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="shell">
      <section className="topbar">
        <div>
          <p className="eyebrow">Local secure RAG workspace</p>
          <h1>University Document AI Assistant</h1>
        </div>
        <div className="status">
          <ShieldCheck size={18} />
          <span>{status}</span>
        </div>
      </section>

      <section className="grid">
        <form className="panel" onSubmit={uploadDocument}>
          <div className="panelHeader">
            <FileUp size={20} />
            <h2>Ingest</h2>
          </div>
          <input
            type="file"
            accept="application/pdf,.pdf,text/markdown,.md,.markdown"
            multiple
            onChange={(event) => setFiles(Array.from(event.target.files ?? []))}
          />
          {files.length > 0 && (
            <div className="fileList">
              {files.map((selectedFile) => (
                <span key={`${selectedFile.name}-${selectedFile.size}`}>{selectedFile.name}</span>
              ))}
            </div>
          )}
          <label>
            Document classification
            <select value={classification} onChange={(event) => setClassification(event.target.value as Classification)}>
              <option>General</option>
              <option>Restricted</option>
              <option>Sensitive</option>
            </select>
          </label>
          <button disabled={busy || files.length === 0}>
            <FileUp size={16} />
            Index Files
          </button>
        </form>

        <section className="panel answerPanel">
          <div className="panelHeader panelHeaderBetween">
            <div className="panelHeader">
              <LockKeyhole size={20} />
              <h2>Authorized Answer</h2>
            </div>
            <button type="button" className="secondaryButton" onClick={startNewChat}>
              <PlusCircle size={16} />
              New chat
            </button>
          </div>

          <div className="controlRow">
            <label>
              Access level
              <select value={clearance} onChange={(event) => setClearance(event.target.value as Classification)}>
                <option>General</option>
                <option>Restricted</option>
                <option>Sensitive</option>
              </select>
            </label>
          </div>

          <div className="referencePanel">
            <div className="panelHeader compact">
              <Files size={16} />
              <h3>Reference files</h3>
            </div>
            {availableFiles.length > 0 ? (
              <ul className="referenceList">
                {availableFiles.map((availableFile) => (
                  <li key={availableFile}>{availableFile}</li>
                ))}
              </ul>
            ) : (
              <p className="helperText">Upload documents to make them available as reference sources.</p>
            )}
          </div>

          <div className="chatWindow">
            {conversation.length > 0 ? (
              conversation.map((message) => (
                <article key={message.id} className={`message ${message.role}`}>
                  <div className="messageMeta">{message.role === "user" ? "You" : "Ollama"}</div>
                  <div className="messageBody">
                    {message.role === "assistant" ? (
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
                    ) : (
                      <p>{message.content}</p>
                    )}
                  </div>
                </article>
              ))
            ) : (
              <div className="emptyState">
                <p className="answer">Upload a PDF and ask a question. Results are filtered by classification before the prompt reaches Ollama.</p>
              </div>
            )}
          </div>

          {sources.length > 0 && (
            <div className="sourcesPanel">
              <h3>Sources consulted</h3>
              <div className="sources">
                {sources.map((source) => (
                  <span key={`${source.source_file}-${source.score}`}>
                    {source.source_file} - {source.classification}
                  </span>
                ))}
              </div>
            </div>
          )}

          <form className="composer" onSubmit={sendMessage}>
            <textarea
              value={chatInput}
              onChange={(event) => setChatInput(event.target.value)}
              placeholder="Continue the conversation with Ollama..."
              rows={2}
            />
            <button type="submit" disabled={busy || !chatInput.trim()}>
              <Send size={16} />
              Send
            </button>
          </form>
        </section>
      </section>
    </main>
  );
}

export default App;
