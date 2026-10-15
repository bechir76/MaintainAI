import { useCallback, useEffect, useRef, useState } from "react";

import { fetchMachines, streamChat, type ChatEvent, type Citation, type Machine, type Role } from "./api";
import { AssistantMessage, type AssistantTurn } from "./components/AssistantMessage";
import { MachineSidebar } from "./components/MachineSidebar";
import { SourcePanel } from "./components/SourcePanel";

interface UserTurn {
  id: string;
  role: "user";
  text: string;
}
type Turn = UserTurn | AssistantTurn;

const EXAMPLES = [
  "Pump P-3 is vibrating, what should I check?",
  "M-2 is overheating. What are the likely causes?",
  "How do I release the pressure before changing the compressor oil?",
  "What is the regreasing interval for the M-200L motor bearings?",
];

const POLL_MS = 5000;

function loadRole(): Role {
  try {
    return localStorage.getItem("role") === "technician" ? "technician" : "viewer";
  } catch {
    return "viewer";
  }
}

let counter = 0;
const nextId = () => `t${++counter}`;

export default function App() {
  const [role, setRole] = useState<Role>(loadRole);
  const [machines, setMachines] = useState<Machine[] | null>(null);
  const [machinesError, setMachinesError] = useState<string | null>(null);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [active, setActive] = useState<Citation | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const endRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);
  const busy = turns.some((t) => t.role === "assistant" && t.state === "streaming");

  useEffect(() => {
    try {
      localStorage.setItem("role", role);
    } catch {
      // storage unavailable (private mode); the role just won't persist
    }
  }, [role]);

  useEffect(() => {
    const controller = new AbortController();
    const load = () =>
      fetchMachines(controller.signal)
        .then((m) => {
          setMachines(m);
          setMachinesError(null);
        })
        .catch((e: Error) => {
          if (e.name !== "AbortError") setMachinesError(e.message);
        });
    load();
    const timer = window.setInterval(load, POLL_MS);
    return () => {
      controller.abort();
      window.clearInterval(timer);
    };
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turns]);

  const update = useCallback((id: string, fn: (t: AssistantTurn) => AssistantTurn) => {
    setTurns((all) => all.map((t) => (t.id === id && t.role === "assistant" ? fn(t) : t)));
  }, []);

  const send = useCallback(
    async (text: string) => {
      const message = text.trim();
      if (!message || busy) return;
      const history = turns
        .filter((t) => t.role === "user" || t.state === "done")
        .slice(-8)
        .map((t) => ({ role: t.role, content: t.text }));
      const answerId = nextId();
      setTurns((all) => [
        ...all,
        { id: nextId(), role: "user", text: message },
        { id: answerId, role: "assistant", text: "", tools: [], citations: [], state: "streaming" },
      ]);
      setInput("");
      setActive(null);

      const controller = new AbortController();
      abortRef.current = controller;
      const onEvent = (event: ChatEvent) => {
        switch (event.type) {
          case "tool_start":
            update(answerId, (t) => ({ ...t, tools: [...t.tools, { ...event.data }] }));
            break;
          case "tool_end":
            update(answerId, (t) => ({
              ...t,
              tools: t.tools.map((x) =>
                x.id === event.data.id ? { ...x, status: event.data.status, summary: event.data.summary } : x,
              ),
            }));
            break;
          case "token":
            update(answerId, (t) => ({ ...t, text: t.text + event.data.text }));
            break;
          case "citations":
            update(answerId, (t) => ({ ...t, citations: event.data.citations }));
            break;
          case "done":
            update(answerId, (t) => ({ ...t, state: "done", meta: event.data }));
            break;
          case "error":
            update(answerId, (t) => ({ ...t, state: "error", error: event.data.message }));
            break;
        }
      };
      try {
        await streamChat(message, role, history, onEvent, controller.signal);
        update(answerId, (t) => (t.state === "streaming" ? { ...t, state: "done" } : t));
      } catch (e) {
        const aborted = (e as Error).name === "AbortError";
        update(answerId, (t) => ({
          ...t,
          state: aborted ? "done" : "error",
          error: aborted ? undefined : "Could not reach the assistant. Is the API running?",
        }));
      } finally {
        abortRef.current = null;
        inputRef.current?.focus();
      }
    },
    [busy, role, turns, update],
  );

  return (
    <div className={`app ${active ? "with-panel" : ""}`}>
      <header className="topbar">
        <div className="brand">
          <img src="/favicon.svg" alt="" width={28} height={28} />
          <div>
            <h1>MaintainAI</h1>
            <p>Maintenance assistant · pumps, motors, compressors</p>
          </div>
        </div>
        <div className="role-switch" role="radiogroup" aria-label="Role">
          {(["viewer", "technician"] as const).map((r) => (
            <button
              key={r}
              type="button"
              role="radio"
              aria-checked={role === r}
              className={role === r ? "active" : ""}
              onClick={() => setRole(r)}
              disabled={busy}
            >
              {r === "viewer" ? "Viewer" : "Technician"}
            </button>
          ))}
        </div>
      </header>

      <MachineSidebar
        machines={machines}
        error={machinesError}
        onAsk={(m) => {
          setInput(`${m.id} (${m.name}) — what is its status and what should I check?`);
          inputRef.current?.focus();
        }}
      />

      <main className="chat">
        <div className="messages">
          {turns.length === 0 && (
            <section className="empty">
              <h2>Ask about a machine, a fault or a procedure</h2>
              <p>
                Answers come only from the equipment manuals, safety procedures and live sensor data, with a
                source for every statement.
              </p>
              <div className="examples">
                {EXAMPLES.map((q) => (
                  <button key={q} type="button" onClick={() => void send(q)}>
                    {q}
                  </button>
                ))}
              </div>
            </section>
          )}
          {turns.map((t) =>
            t.role === "user" ? (
              <article key={t.id} className="msg msg-user">
                {t.text}
              </article>
            ) : (
              <AssistantMessage key={t.id} turn={t} onCite={setActive} activeId={active?.id ?? null} />
            ),
          )}
          <div ref={endRef} />
        </div>

        <form
          className="composer"
          onSubmit={(e) => {
            e.preventDefault();
            void send(input);
          }}
        >
          <textarea
            ref={inputRef}
            value={input}
            placeholder="e.g. Pump P-3 is vibrating, what should I check?"
            rows={2}
            maxLength={2000}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void send(input);
              }
            }}
          />
          {busy ? (
            <button type="button" className="btn btn-secondary" onClick={() => abortRef.current?.abort()}>
              Stop
            </button>
          ) : (
            <button type="submit" className="btn" disabled={!input.trim()}>
              Send
            </button>
          )}
        </form>
        <p className="hint">
          Signed in as <strong>{role}</strong>
          {role === "viewer" ? " · read-only, cannot create tickets" : " · can create maintenance tickets"}
        </p>
      </main>

      {active && <SourcePanel citation={active} onClose={() => setActive(null)} />}
    </div>
  );
}
