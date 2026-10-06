import { q, q1, tx, embeddingTopK } from "@/db/pool";
import { embedCall } from "./call";
import type { SettingsRow } from "@/lib/settings";

export function chunkText(text: string): string[] {
  const paragraphs = text
    .split(/\n+/)
    .map((p) => p.trim())
    .filter(Boolean);

  const units: string[] = [];
  for (const paragraph of paragraphs) {
    if (paragraph.length <= 1200) {
      units.push(paragraph);
      continue;
    }
    const sentences = paragraph.split(/(?<=[.!?])\s+/);
    let buffer = "";
    for (const sentence of sentences) {
      if (buffer && buffer.length + sentence.length + 1 > 1200) {
        units.push(buffer);
        buffer = sentence;
      } else {
        buffer = buffer ? `${buffer} ${sentence}` : sentence;
      }
    }
    if (buffer) units.push(buffer);
  }

  const chunks: string[] = [];
  let current = "";
  for (const unit of units) {
    if (current && current.length + unit.length + 1 > 1400) {
      chunks.push(current);
      current = `${current.slice(-200)} ${unit}`;
    } else {
      current = current ? `${current}\n${unit}` : unit;
    }
  }
  if (current) chunks.push(current);
  return chunks.length > 0 ? chunks : [text.slice(0, 1400)];
}

function toVector(values: number[]): string {
  return `[${values.join(",")}]`;
}

export async function ensureChunks(
  submissionId: string,
  text: string,
  settings: SettingsRow,
): Promise<void> {
  const existing = await q1<{ n: string }>(
    "SELECT count(*)::text AS n FROM document_chunks WHERE submission_id = $1",
    [submissionId],
  );
  if (Number(existing?.n ?? 0) > 0) return;

  const chunks = chunkText(text);
  const vectors = await embedCall(settings, chunks);

  await tx(async (client) => {
    for (let i = 0; i < chunks.length; i++) {
      await client.query(
        `INSERT INTO document_chunks (submission_id, position, content, embedding)
         VALUES ($1, $2, $3, $4::vector)`,
        [submissionId, i, chunks[i], toVector(vectors[i])],
      );
    }
  });
}

export async function retrieveExcerpts(
  submissionId: string,
  query: string,
  settings: SettingsRow,
): Promise<string[]> {
  const [queryVector] = await embedCall(settings, [query]);
  const rows = await q<{ content: string }>(
    `SELECT content FROM document_chunks
     WHERE submission_id = $1
     ORDER BY embedding <=> $2::vector
     LIMIT $3`,
    [submissionId, toVector(queryVector), embeddingTopK()],
  );
  return rows.map((r) => r.content);
}
