import type { SettingsRow } from "@/lib/settings";
import type { AnswerContext } from "./prompt";

export type ChatMessage = { role: "system" | "user"; content: string };

function joinUrl(base: string, path: string): string {
  return `${base.trim().replace(/\/+$/, "")}${path}`;
}

export type CallResult =
  | { ok: true; content: string }
  | { ok: false; message: string };

export async function callChat(
  settings: SettingsRow,
  messages: ChatMessage[],
  opts: { temperature: number; maxTokens: number },
): Promise<CallResult> {
  let res: Response;
  try {
    res = await fetch(joinUrl(settings.base_url, "/chat/completions"), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${settings.api_key.trim()}`,
      },
      body: JSON.stringify({
        model: settings.model_name.trim(),
        temperature: opts.temperature,
        max_tokens: opts.maxTokens,
        messages,
      }),
      signal: AbortSignal.timeout(60_000),
    });
  } catch (err) {
    return { ok: false, message: shortError(err) };
  }

  if (!res.ok) {
    const body = await res.text().catch(() => "");
    return {
      ok: false,
      message: `HTTP ${res.status}${body ? ` — ${body.slice(0, 240)}` : ""}`,
    };
  }

  let data: unknown;
  try {
    data = await res.json();
  } catch {
    return { ok: false, message: "Respons server bukan JSON." };
  }

  const content = (
    data as { choices?: { message?: { content?: unknown } }[] }
  )?.choices?.[0]?.message?.content;

  if (typeof content !== "string" || content.trim().length === 0) {
    return { ok: false, message: "Respons tidak berisi teks." };
  }

  return { ok: true, content };
}

export async function embedCall(
  settings: SettingsRow,
  inputs: string[],
): Promise<number[][]> {
  let res: Response;
  try {
    res = await fetch(joinUrl(settings.emb_base_url, "/embeddings"), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${settings.emb_api_key.trim()}`,
      },
      body: JSON.stringify({
        model: settings.emb_model_name.trim(),
        input: inputs,
      }),
      signal: AbortSignal.timeout(60_000),
    });
  } catch (err) {
    throw new Error(shortError(err));
  }

  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`HTTP ${res.status}${body ? ` — ${body.slice(0, 240)}` : ""}`);
  }

  const data = (await res.json()) as {
    data?: { index?: number; embedding?: unknown }[];
  };
  const list = (data.data ?? [])
    .slice()
    .sort((a, b) => (a.index ?? 0) - (b.index ?? 0))
    .map((d) => d.embedding);

  if (list.length !== inputs.length) {
    throw new Error("Jumlah embedding tidak sesuai.");
  }
  for (const vec of list) {
    if (!Array.isArray(vec) || vec.length === 0) {
      throw new Error("Respons embedding tidak valid.");
    }
  }
  return list as number[][];
}

export async function testConnection(
  settings: SettingsRow,
): Promise<CallResult> {
  return callChat(
    settings,
    [{ role: "user", content: "Balas satu kata: siap" }],
    { temperature: 0, maxTokens: 8 },
  );
}

function shortError(err: unknown): string {
  if (err instanceof Error) {
    if (err.name === "TimeoutError" || err.name === "AbortError") {
      return "Waktu tunggu habis.";
    }
    return err.message.slice(0, 240);
  }
  return "Gagal terhubung.";
}

export type { AnswerContext };
