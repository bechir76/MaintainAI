import { useEffect } from "react";

import type { Citation } from "../api";

interface Props {
  citation: Citation;
  onClose: () => void;
}

export function SourcePanel({ citation, onClose }: Props) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <aside className="source-panel" aria-label="Source">
      <header>
        <div>
          <p className="eyebrow">
            {citation.kind === "document" ? `${citation.doc_id} · page ${citation.page}` : "Live sensor data"}
          </p>
          <h3>{citation.title}</h3>
        </div>
        <button type="button" className="icon-btn" onClick={onClose} aria-label="Close source">
          ✕
        </button>
      </header>
      <blockquote>{citation.text}</blockquote>
      {citation.kind === "document" && (
        <dl className="source-details">
          <div>
            <dt>File</dt>
            <dd>{citation.document}</dd>
          </div>
          <div>
            <dt>Relevance</dt>
            <dd>{citation.score?.toFixed(2)}</dd>
          </div>
          {citation.source_url && (
            <div>
              <dt>Original</dt>
              <dd>
                <a href={citation.source_url} target="_blank" rel="noopener noreferrer">
                  Manufacturer PDF
                </a>
              </dd>
            </div>
          )}
        </dl>
      )}
    </aside>
  );
}
