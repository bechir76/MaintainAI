import { Fragment } from "react";

import type { Citation, ToolActivity } from "../api";
import { citedRefs, parseAnswer, type Inline } from "../answer";

export interface AssistantTurn {
  id: string;
  role: "assistant";
  text: string;
  tools: ToolActivity[];
  citations: Citation[];
  state: "streaming" | "done" | "error";
  error?: string;
  meta?: { tool_calls: number; elapsed_ms: number; grounded: boolean };
}

const TOOL_LABEL: Record<string, string> = {
  search_manuals: "Searched manuals",
  get_sensor_readings: "Read sensors",
  list_machines: "Checked machine status",
  create_maintenance_ticket: "Create ticket",
};

export function citationLabel(c: Citation): string {
  if (c.kind === "sensor") return c.machine_id === "all" ? "Live status" : `${c.machine_id} live`;
  return `${c.doc_id} p.${c.page}`;
}

function ToolLine({ tool }: { tool: ToolActivity }) {
  const running = tool.status === undefined;
  const icon = running ? "…" : tool.status === "ok" ? "✓" : tool.status === "denied" ? "⛔" : "!";
  const args = Object.entries(tool.arguments)
    .filter(([k]) => k === "machine_id" || k === "query")
    .map(([, v]) => String(v))
    .join(" · ");
  return (
    <li className={`tool tool-${tool.status ?? "running"}`}>
      <span className="tool-icon" aria-hidden>
        {icon}
      </span>
      <span className="tool-name">{TOOL_LABEL[tool.name] ?? tool.name}</span>
      {args && <span className="tool-args">{args}</span>}
      {tool.summary && <span className="tool-summary">{tool.summary}</span>}
    </li>
  );
}

interface Props {
  turn: AssistantTurn;
  onCite: (citation: Citation) => void;
  activeId: string | null;
}

export function AssistantMessage({ turn, onCite, activeId }: Props) {
  const byId = new Map(turn.citations.map((c) => [c.id, c]));

  const renderInline = (parts: Inline[]) =>
    parts.map((p, i) => {
      if (p.kind === "text") return <Fragment key={i}>{p.text}</Fragment>;
      if (p.kind === "bold") return <strong key={i}>{p.text}</strong>;
      const citation = byId.get(p.ref);
      if (!citation) {
        // Citations arrive at the end of the stream; until then show a quiet placeholder.
        return (
          <span key={i} className="cite cite-pending">
            {p.ref}
          </span>
        );
      }
      return (
        <button
          key={i}
          type="button"
          className={`cite cite-${citation.kind} ${activeId === citation.id ? "cite-active" : ""}`}
          onClick={() => onCite(citation)}
          title={citation.title}
        >
          {citationLabel(citation)}
        </button>
      );
    });

  const blocks = parseAnswer(turn.text);
  const sources = citedRefs(turn.text)
    .map((ref) => byId.get(ref))
    .filter((c): c is Citation => Boolean(c));

  return (
    <article className="msg msg-assistant" aria-live={turn.state === "streaming" ? "polite" : "off"}>
      {turn.tools.length > 0 && (
        <ul className="tools" aria-label="Tool calls">
          {turn.tools.map((t) => (
            <ToolLine key={t.id} tool={t} />
          ))}
        </ul>
      )}
      <div className="answer">
        {blocks.map((block, i) =>
          block.kind === "paragraph" ? (
            <p key={i}>{renderInline(block.inline)}</p>
          ) : block.ordered ? (
            <ol key={i}>
              {block.items.map((item, j) => (
                <li key={j}>{renderInline(item)}</li>
              ))}
            </ol>
          ) : (
            <ul key={i}>
              {block.items.map((item, j) => (
                <li key={j}>{renderInline(item)}</li>
              ))}
            </ul>
          ),
        )}
        {turn.state === "streaming" && <span className="cursor" aria-hidden />}
        {turn.state === "error" && <p className="error">{turn.error}</p>}
      </div>
      {sources.length > 0 && (
        <div className="sources">
          <span className="sources-label">Sources</span>
          {sources.map((c) => (
            <button
              key={c.id}
              type="button"
              className={`source source-${c.kind} ${activeId === c.id ? "cite-active" : ""}`}
              onClick={() => onCite(c)}
            >
              <span className="source-ref">{citationLabel(c)}</span>
              <span className="source-title">{c.title}</span>
            </button>
          ))}
        </div>
      )}
      {turn.meta && (
        <p className="meta">
          {turn.meta.tool_calls} tool call{turn.meta.tool_calls === 1 ? "" : "s"} ·{" "}
          {(turn.meta.elapsed_ms / 1000).toFixed(1)} s
          {!turn.meta.grounded && " · no supporting documents found"}
        </p>
      )}
    </article>
  );
}
