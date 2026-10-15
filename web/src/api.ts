export type Role = "viewer" | "technician";
export type Status = "ok" | "warning" | "alarm" | "no_data";

export interface Flag {
  metric: string;
  level: "warning" | "alarm";
  value: number;
  limit: number;
  message: string;
  source: string;
}

export interface Reading {
  ts: string;
  temperature_c: number | null;
  vibration_mm_s: number | null;
  pressure_bar: number | null;
  current_a: number | null;
}

export interface Machine {
  id: string;
  name: string;
  type: string;
  model: string;
  location: string;
  rated_current_a: number;
  status: Status;
  flags: Flag[];
  latest: Reading | null;
}

export interface Citation {
  id: string;
  kind: "document" | "sensor";
  title: string;
  text: string;
  doc_id: string | null;
  document: string | null;
  page: number | null;
  score: number | null;
  machine_id: string | null;
}

export interface ToolActivity {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
  status?: "ok" | "error" | "denied" | "blocked";
  summary?: string;
}

export type ChatEvent =
  | { type: "tool_start"; data: { id: string; name: string; arguments: Record<string, unknown> } }
  | { type: "tool_end"; data: { id: string; name: string; status: ToolActivity["status"]; summary: string } }
  | { type: "token"; data: { text: string } }
  | { type: "citations"; data: { citations: Citation[] } }
  | { type: "done"; data: { tool_calls: number; grounded: boolean; elapsed_ms: number } }
  | { type: "error"; data: { message: string } };

export interface HistoryItem {
  role: "user" | "assistant";
  content: string;
}

const BASE = "/api";

export async function fetchMachines(signal?: AbortSignal): Promise<Machine[]> {
  const response = await fetch(`${BASE}/machines`, { signal });
  if (!response.ok) throw new Error(`machines: HTTP ${response.status}`);
  const body = (await response.json()) as { machines: Machine[] };
  return body.machines;
}

/** Incremental parser for a text/event-stream body. */
export class SSEParser {
  private buffer = "";

  push(chunk: string): ChatEvent[] {
    this.buffer += chunk.replace(/\r\n/g, "\n");
    const events: ChatEvent[] = [];
    let end: number;
    while ((end = this.buffer.indexOf("\n\n")) !== -1) {
      const block = this.buffer.slice(0, end);
      this.buffer = this.buffer.slice(end + 2);
      let type = "message";
      const data: string[] = [];
      for (const line of block.split("\n")) {
        if (line.startsWith("event:")) type = line.slice(6).trim();
        else if (line.startsWith("data:")) data.push(line.slice(5).trimStart());
      }
      if (data.length === 0) continue;
      try {
        events.push({ type, data: JSON.parse(data.join("\n")) } as ChatEvent);
      } catch {
        // ignore malformed events rather than breaking the stream
      }
    }
    return events;
  }
}

export async function streamChat(
  message: string,
  role: Role,
  history: HistoryItem[],
  onEvent: (event: ChatEvent) => void,
  signal: AbortSignal,
): Promise<void> {
  const response = await fetch(`${BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, role, history }),
    signal,
  });
  if (!response.ok || !response.body) {
    throw new Error(`chat: HTTP ${response.status}`);
  }
  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
  const parser = new SSEParser();
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    for (const event of parser.push(value)) onEvent(event);
  }
}
