import { embeddingDim } from "@/db/pool";
import {
  getSettings,
  isEmbeddingConfigured,
  isModelConfigured,
  maskKey,
} from "@/lib/settings";
import { SettingsForm } from "./settings-form";

export const dynamic = "force-dynamic";

export default async function SettingsPage() {
  const s = await getSettings();

  return (
    <SettingsForm
      providerLabel={s.provider_label}
      baseUrl={s.base_url}
      apiKeyMasked={maskKey(s.api_key)}
      modelName={s.model_name}
      temperature={String(Number(s.temperature))}
      maxTokens={String(s.max_tokens)}
      systemPreamble={s.system_preamble}
      embBaseUrl={s.emb_base_url}
      embApiKeyMasked={maskKey(s.emb_api_key)}
      embModelName={s.emb_model_name}
      modelConfigured={isModelConfigured(s)}
      embConfigured={isEmbeddingConfigured(s)}
      embDim={embeddingDim()}
    />
  );
}
