/** Splits an answer into blocks and inline segments, keeping citation markers like [S1]. */

export type Inline =
  | { kind: "text"; text: string }
  | { kind: "bold"; text: string }
  | { kind: "cite"; ref: string };

export type Block =
  | { kind: "paragraph"; inline: Inline[] }
  | { kind: "list"; ordered: boolean; items: Inline[][] };

const CITE_OR_BOLD = /\[((?:S|L)\d+)\]|\*\*(.+?)\*\*/g;

export function parseInline(text: string): Inline[] {
  const out: Inline[] = [];
  let last = 0;
  for (const match of text.matchAll(CITE_OR_BOLD)) {
    const index = match.index ?? 0;
    if (index > last) out.push({ kind: "text", text: text.slice(last, index) });
    if (match[1]) out.push({ kind: "cite", ref: match[1] });
    else out.push({ kind: "bold", text: match[2] });
    last = index + match[0].length;
  }
  if (last < text.length) out.push({ kind: "text", text: text.slice(last) });
  return out;
}

const ORDERED = /^\s*\d+[.)]\s+/;
const BULLET = /^\s*[-*•]\s+/;

export function parseAnswer(text: string): Block[] {
  const blocks: Block[] = [];
  for (const raw of text.split("\n")) {
    const line = raw.trimEnd();
    if (!line.trim()) continue;
    const ordered = ORDERED.test(line);
    const bullet = !ordered && BULLET.test(line);
    if (ordered || bullet) {
      const content = parseInline(line.replace(ordered ? ORDERED : BULLET, ""));
      const prev = blocks[blocks.length - 1];
      if (prev && prev.kind === "list" && prev.ordered === ordered) prev.items.push(content);
      else blocks.push({ kind: "list", ordered, items: [content] });
    } else {
      blocks.push({ kind: "paragraph", inline: parseInline(line) });
    }
  }
  return blocks;
}

export function citedRefs(text: string): string[] {
  return [...new Set([...text.matchAll(/\[((?:S|L)\d+)\]/g)].map((m) => m[1]))];
}
