import { FormEvent, useMemo, useState } from "react";
import { FileUp, Files, LockKeyhole, Search, ShieldCheck } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import "./styles.css";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

type Classification = "Public" | "Student-Only" | "Restricted-Internal";

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
  const [classification, setClassification] = useState<Classification>("Student-Only");
  const [clearance, setClearance] = useState<Classification>("Student-Only");
  const [query, setQuery] = useState("");
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState<Source[]>([]);
  const [conversation, setConversation] = useState<Message[]>([]);
  const [availableFiles, setAvailableFiles] = useState<string[]>([]);
  const [status, setStatus] = useState("Ready for local ingestion.");
  const [busy, setBusy] = useState(false);

  const headers = useMemo(
    () => ({
      "X-User-Clearance": clearance,
      "X-User-Role": clearance === "Restricted-Internal" ? "faculty" : "student",
      "X-User-Id": "local_portfolio_user",
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

  async function searchDocuments(event: FormEvent) {
    event.preventDefault();
    const trimmedQuery = query.trim();
    if (!trimmedQuery) return;

    setBusy(true);
    setStatus("Running metadata-filtered vector search, then asking local Ollama.");

    const userMessage: Message = { id: Date.now(), role: "user", content: trimmedQuery };
    setConversation((prev) => [...prev, userMessage]);

    try {
      const response = await fetch(`${API_BASE_URL}/search/query`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...headers,
        },
        body: JSON.stringify({ query: trimmedQuery, top_k: 5 }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail ?? "Search failed");
      const assistantText = typeof payload.response === "string" ? payload.response : JSON.stringify(payload.response ?? "", null, 2);
      const consultedFiles = (payload.sources_consulted ?? []).map((source: Source) => source.source_file);
      setAnswer(assistantText);
      setSources(payload.sources_consulted ?? []);
      setAvailableFiles((prev) => Array.from(new Set([...prev, ...consultedFiles])));
      setStatus(`Search completed with ${payload.access_clearance_applied} clearance.`);
      setConversation((prev) => [...prev, { id: Date.now() + 1, role: "assistant", content: assistantText }]);
      setQuery("");
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
            Classification
            <select value={classification} onChange={(event) => setClassification(event.target.value as Classification)}>
              <option>Public</option>
              <option>Student-Only</option>
              <option>Restricted-Internal</option>
            </select>
          </label>
          <button disabled={busy || files.length === 0}>
            <FileUp size={16} />
            Index Files
          </button>
        </form>

        <form className="panel searchPanel" onSubmit={searchDocuments}>
          <div className="panelHeader">
            <Search size={20} />
            <h2>Query</h2>
          </div>
          <label>
            Active clearance
            <select value={clearance} onChange={(event) => setClearance(event.target.value as Classification)}>
              <option>Public</option>
              <option>Student-Only</option>
              <option>Restricted-Internal</option>
            </select>
          </label>
          <textarea value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Ask about your lecture notes, syllabus, or readings..." />
          <button disabled={busy || !query.trim()}>
            <Search size={16} />
            Ask Ollama
          </button>
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
        </form>

        <section className="panel answerPanel">
          <div className="panelHeader">
            <LockKeyhole size={20} />
            <h2>Authorized Answer</h2>
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
        </section>
      </section>
    </main>
  );
}

export default App;
