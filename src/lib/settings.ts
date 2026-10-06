import { q1 } from "@/db/pool";

export type SettingsRow = {
  id: number;
  provider_label: string;
  base_url: string;
  api_key: string;
  model_name: string;
  temperature: number | string;
  max_tokens: number;
  system_preamble: string;
  emb_base_url: string;
  emb_api_key: string;
  emb_model_name: string;
  updated_at: string | null;
  updated_by: string | null;
};

export async function getSettings(): Promise<SettingsRow> {
  const row = await q1<SettingsRow>("SELECT * FROM model_settings WHERE id = 1");
  if (row) return row;
  const inserted = await q1<SettingsRow>(
    `INSERT INTO model_settings (id, system_preamble)
     VALUES (1, 'Anda adalah asisten penilaian mata kuliah. Balas dalam bahasa Indonesia yang singkat dan jelas.')
     ON CONFLICT (id) DO NOTHING
     RETURNING *`,
  );
  if (inserted) return inserted;
  const again = await q1<SettingsRow>("SELECT * FROM model_settings WHERE id = 1");
  if (!again) throw new Error("model_settings tidak tersedia");
  return again;
}

export function isModelConfigured(s: SettingsRow): boolean {
  return Boolean(s.api_key.trim() && s.base_url.trim() && s.model_name.trim());
}

export function isEmbeddingConfigured(s: SettingsRow): boolean {
  return Boolean(
    s.emb_api_key.trim() && s.emb_base_url.trim() && s.emb_model_name.trim(),
  );
}

export function maskKey(key: string): string {
  const k = key.trim();
  if (!k) return "";
  if (k.length <= 8) return "••••••••";
  return `${k.slice(0, 3)}••••••${k.slice(-4)}`;
}
