import { describe, expect, it } from "vitest";

import { SSEParser } from "./api";
import { citedRefs, parseAnswer, parseInline } from "./answer";

describe("SSEParser", () => {
  it("parses events split across chunks", () => {
    const parser = new SSEParser();
    expect(parser.push('event: token\ndata: {"text": "Che')).toEqual([]);
    const events = parser.push('ck"}\n\nevent: done\r\ndata: {"tool_calls": 2}\r\n\r\n');
    expect(events).toEqual([
      { type: "token", data: { text: "Check" } },
      { type: "done", data: { tool_calls: 2 } },
    ]);
  });

  it("skips malformed and empty events", () => {
    const parser = new SSEParser();
    expect(parser.push("event: token\ndata: {oops\n\n: comment\n\n")).toEqual([]);
  });
});

describe("answer parsing", () => {
  it("extracts citations and bold text", () => {
    expect(parseInline("Stop the pump [S1] **now** [L2].")).toEqual([
      { kind: "text", text: "Stop the pump " },
      { kind: "cite", ref: "S1" },
      { kind: "text", text: " " },
      { kind: "bold", text: "now" },
      { kind: "text", text: " " },
      { kind: "cite", ref: "L2" },
      { kind: "text", text: "." },
    ]);
  });

  it("groups numbered and bullet lists", () => {
    const blocks = parseAnswer("Intro\n1. First [S1]\n2. Second\n- a\n- b\nEnd");
    expect(blocks.map((b) => b.kind)).toEqual(["paragraph", "list", "list", "paragraph"]);
    const [, ordered, bullets] = blocks;
    expect(ordered.kind === "list" && ordered.ordered && ordered.items.length).toBe(2);
    expect(bullets.kind === "list" && !bullets.ordered && bullets.items.length).toBe(2);
  });

  it("lists unique cited refs in order", () => {
    expect(citedRefs("a [S2] b [L1] c [S2] [X1]")).toEqual(["S2", "L1"]);
  });
});
