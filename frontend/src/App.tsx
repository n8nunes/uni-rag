import React, { FormEvent, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { FileUp, LockKeyhole, Search, ShieldCheck } from "lucide-react";
import "./styles.css";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

type Classification = "Public" | "Student-Only" | "Restricted-Internal";

type Source = {
  source_file: string;
  classification: Classification;
  score?: number;
};

function App() {
  const [file, setFile] = useState<File | null>(null);
  const [classification, setClassification] = useState<Classification>("Student-Only");
  const [clearance, setClearance] = useState<Classification>("Student-Only");
  const [query, setQuery] = useState("");
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState<Source[]>([]);
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
    if (!file) return;

    setBusy(true);
    setStatus("Parsing PDF, generating embeddings, and storing classified chunks.");
    const formData = new FormData();
    formData.append("file", file);
    formData.append("classification", classification);

    try {
      const response = await fetch(`${API_BASE_URL}/documents/upload`, {
        method: "POST",
        headers,
        body: formData,
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail ?? "Upload failed");
      setStatus(`Indexed ${payload.chunks_extracted} chunks from ${payload.file_name}.`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  async function searchDocuments(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setStatus("Running metadata-filtered vector search, then asking local Ollama.");

    try {
      const response = await fetch(`${API_BASE_URL}/search/query`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...headers,
        },
        body: JSON.stringify({ query, top_k: 5 }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail ?? "Search failed");
      setAnswer(payload.response);
      setSources(payload.sources_consulted ?? []);
      setStatus(`Search completed with ${payload.access_clearance_applied} clearance.`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Search failed");
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
          <input type="file" accept="application/pdf" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
          <label>
            Classification
            <select value={classification} onChange={(event) => setClassification(event.target.value as Classification)}>
              <option>Public</option>
              <option>Student-Only</option>
              <option>Restricted-Internal</option>
            </select>
          </label>
          <button disabled={busy || !file}>
            <FileUp size={16} />
            Index PDF
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
        </form>

        <section className="panel answerPanel">
          <div className="panelHeader">
            <LockKeyhole size={20} />
            <h2>Authorized Answer</h2>
          </div>
          <p className="answer">{answer || "Upload a PDF and ask a question. Results are filtered by classification before the prompt reaches Ollama."}</p>
          <div className="sources">
            {sources.map((source) => (
              <span key={`${source.source_file}-${source.score}`}>
                {source.source_file} · {source.classification}
              </span>
            ))}
          </div>
        </section>
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
