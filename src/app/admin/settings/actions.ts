"use server";

import { revalidatePath } from "next/cache";
import { q1 } from "@/db/pool";
import { requireRole } from "@/lib/session";
import { getSettings, isModelConfigured } from "@/lib/settings";
import { testConnection } from "@/lib/grading/call";

export type SettingsState =
  | {
      errors?: Record<string, string>;
      info?: string;
      test?: { ok: boolean; message: string };
    }
  | undefined;

function str(value: FormDataEntryValue | null): string {
  return typeof value === "string" ? value.trim() : "";
}

export async function saveSettings(
  _prev: SettingsState,
  formData: FormData,
): Promise<SettingsState> {
  const admin = await requireRole("admin");
  const current = await getSettings();
  const errors: Record<string, string> = {};

  const provider_label = str(formData.get("provider_label"));
  const base_url = str(formData.get("base_url"));
  const model_name = str(formData.get("model_name"));
  const temperatureRaw = str(formData.get("temperature"));
  const maxTokensRaw = str(formData.get("max_tokens"));
  const system_preamble = str(formData.get("system_preamble"));
  const emb_base_url = str(formData.get("emb_base_url"));
  const emb_model_name = str(formData.get("emb_model_name"));

  const api_key = formData.has("api_key")
    ? str(formData.get("api_key"))
    : current.api_key;
  const emb_api_key = formData.has("emb_api_key")
    ? str(formData.get("emb_api_key"))
    : current.emb_api_key;

  if (base_url && !/^https?:\/\//i.test(base_url)) {
    errors.base_url = "Alamat dasar harus diawali http:// atau https://.";
  }
  if (api_key && !base_url) {
    errors.base_url = "Alamat dasar wajib diisi saat kunci API terisi.";
  }
  if (api_key && !model_name) {
    errors.model_name = "Nama model wajib diisi saat kunci API terisi.";
  }

  const temperature = Number(temperatureRaw);
  if (temperatureRaw === "" || Number.isNaN(temperature) || temperature < 0 || temperature > 2) {
    errors.temperature = "Temperature harus antara 0 dan 2.";
  }

  const maxTokens = Number(maxTokensRaw);
  if (
    maxTokensRaw === "" ||
    !Number.isInteger(maxTokens) ||
    maxTokens < 1 ||
    maxTokens > 16000
  ) {
    errors.max_tokens = "Max tokens harus bilangan bulat 1–16000.";
  }

  if (!system_preamble) {
    errors.system_preamble = "System preamble wajib diisi.";
  }

  if (emb_api_key && !/^https?:\/\//i.test(emb_base_url)) {
    errors.emb_base_url = "Alamat dasar harus diawali http:// atau https://.";
  }
  if (emb_api_key && !emb_model_name) {
    errors.emb_model_name = "Nama model embedding wajib diisi.";
  }

  if (Object.keys(errors).length > 0) return { errors };

  await q1(
    `UPDATE model_settings
     SET provider_label = $1, base_url = $2, api_key = $3, model_name = $4,
         temperature = $5, max_tokens = $6, system_preamble = $7,
         emb_base_url = $8, emb_api_key = $9, emb_model_name = $10,
         updated_at = now(), updated_by = $11
     WHERE id = 1`,
    [
      provider_label,
      base_url,
      api_key,
      model_name,
      temperature,
      maxTokens,
      system_preamble,
      emb_base_url,
      emb_api_key,
      emb_model_name,
      admin.id,
    ],
  );

  revalidatePath("/admin/settings");
  return { info: "Pengaturan disimpan." };
}

export async function runTestConnection(
  _prev: SettingsState,
  _formData: FormData,
): Promise<SettingsState> {
  await requireRole("admin");
  const settings = await getSettings();
  if (!isModelConfigured(settings)) {
    return { test: { ok: false, message: "Model belum disetel." } };
  }
  const result = await testConnection(settings);
  return result.ok
    ? { test: { ok: true, message: "Koneksi berhasil." } }
    : {
        test: {
          ok: false,
          message: `Koneksi gagal. ${result.message}`.slice(0, 400),
        },
      };
}

export async function revealApiKey(): Promise<string> {
  await requireRole("admin");
  const settings = await getSettings();
  return settings.api_key;
}

export async function revealEmbeddingKey(): Promise<string> {
  await requireRole("admin");
  const settings = await getSettings();
  return settings.emb_api_key;
}
