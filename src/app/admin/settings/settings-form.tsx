"use client";

import { useActionState, useRef, useState } from "react";
import {
  revealApiKey,
  revealEmbeddingKey,
  runTestConnection,
  saveSettings,
  type SettingsState,
} from "./actions";
import { Button } from "@/components/ui/button";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Card, ErrorLine, Notice, PageHeader } from "@/components/ui/misc";
import { Field, Input, Textarea } from "@/components/ui/field";

type Props = {
  providerLabel: string;
  baseUrl: string;
  apiKeyMasked: string;
  modelName: string;
  temperature: string;
  maxTokens: string;
  systemPreamble: string;
  embBaseUrl: string;
  embApiKeyMasked: string;
  embModelName: string;
  modelConfigured: boolean;
  embConfigured: boolean;
  embDim: number;
};

export function SettingsForm(props: Props) {
  const [saveState, saveAction, savePending] = useActionState<
    SettingsState,
    FormData
  >(saveSettings, undefined);
  const [testState, testAction, testPending] = useActionState<
    SettingsState,
    FormData
  >(runTestConnection, undefined);

  const keyRef = useRef<HTMLInputElement>(null);
  const embKeyRef = useRef<HTMLInputElement>(null);
  const [keyDirty, setKeyDirty] = useState(false);
  const [embKeyDirty, setEmbKeyDirty] = useState(false);
  const [keyShown, setKeyShown] = useState(false);
  const [embKeyShown, setEmbKeyShown] = useState(false);

  const errors = saveState?.errors ?? {};

  async function revealKey() {
    if (!keyShown) {
      const real = await revealApiKey();
      if (keyRef.current) keyRef.current.value = real;
      setKeyShown(true);
    } else {
      setKeyShown(false);
    }
  }

  async function revealEmbKey() {
    if (!embKeyShown) {
      const real = await revealEmbeddingKey();
      if (embKeyRef.current) embKeyRef.current.value = real;
      setEmbKeyShown(true);
    } else {
      setEmbKeyShown(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <Breadcrumb items={[{ label: "Setelan model" }]} />
      <PageHeader
        title="Setelan model"
        description="Berlaku untuk semua panggilan penilaian."
        action={
          <Button
            type="submit"
            form="settings-form"
            variant="primary"
            disabled={savePending}
          >
            {savePending ? "Menyimpan..." : "Simpan"}
          </Button>
        }
      />

      {saveState?.info ? <Notice dot="#1d7a3e">{saveState.info}</Notice> : null}
      {testState?.test ? (
        <Notice dot={testState.test.ok ? "#1d7a3e" : "#ca3120"}>
          {testState.test.message}
        </Notice>
      ) : null}

      <form
        id="settings-form"
        action={saveAction}
        className="flex flex-col gap-6"
      >
        <Card className="flex flex-col gap-4 p-6">
          <div className="flex items-center justify-between gap-4">
            <h2>Penilaian model</h2>
            {!props.modelConfigured ? (
              <Notice>Grading nonaktif. API key belum diisi.</Notice>
            ) : (
              <Notice dot="#1d7a3e">Grading aktif.</Notice>
            )}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <Field
              label="Label penyedia"
              htmlFor="provider_label"
              error={errors.provider_label}
            >
              <Input
                id="provider_label"
                name="provider_label"
                defaultValue={props.providerLabel}
                placeholder="Penyedia utama"
              />
            </Field>
            <Field
              label="Nama model"
              htmlFor="model_name"
              error={errors.model_name}
            >
              <Input
                id="model_name"
                name="model_name"
                defaultValue={props.modelName}
                placeholder="nama-model"
              />
            </Field>

            <Field
              label="Alamat dasar"
              htmlFor="base_url"
              error={errors.base_url}
              hint="Endpoint chat completions yang kompatibel."
            >
              <Input
                id="base_url"
                name="base_url"
                defaultValue={props.baseUrl}
                placeholder="https://..."
              />
            </Field>
            <Field
              label="API key"
              htmlFor="api_key"
              error={errors.api_key}
              hint={keyDirty ? undefined : "Kosongkan kolom untuk menghapus."}
            >
              <div className="flex gap-2">
              <Input
                id="api_key"
                ref={keyRef}
                name={keyDirty ? "api_key" : undefined}
                type={keyShown ? "text" : "password"}
                defaultValue={props.apiKeyMasked}
                placeholder="Belum diisi"
                autoComplete="off"
                onChange={() => setKeyDirty(true)}
              />
                <Button
                  type="button"
                  onClick={revealKey}
                  className="shrink-0 px-3"
                >
                  {keyShown ? "Sembunyikan" : "Reveal"}
                </Button>
              </div>
            </Field>

            <Field
              label="Temperature"
              htmlFor="temperature"
              error={errors.temperature}
            >
              <Input
                id="temperature"
                name="temperature"
                type="number"
                step="0.1"
                min="0"
                max="2"
                defaultValue={props.temperature}
              />
            </Field>
            <Field
              label="Max tokens"
              htmlFor="max_tokens"
              error={errors.max_tokens}
            >
              <Input
                id="max_tokens"
                name="max_tokens"
                type="number"
                min="1"
                max="16000"
                defaultValue={props.maxTokens}
              />
            </Field>

            <div className="col-span-2">
              <Field
                label="System preamble"
                htmlFor="system_preamble"
                error={errors.system_preamble}
              >
                <Textarea
                  id="system_preamble"
                  name="system_preamble"
                  rows={4}
                  defaultValue={props.systemPreamble}
                />
              </Field>
            </div>
          </div>

          <div className="flex items-center gap-3 border-t border-border pt-4">
            <Button
              type="submit"
              formAction={testAction}
              disabled={testPending}
            >
              {testPending ? "Menguji..." : "Uji koneksi"}
            </Button>
            <p className="text-[13px] text-muted">
              Menguji pengaturan yang tersimpan.
            </p>
          </div>

          <div className="flex flex-col gap-4 border-t border-border pt-6">
            <div className="flex items-center justify-between gap-4">
              <h2>Embedding</h2>
              {!props.embConfigured ? (
                <Notice>Embedding belum disetel.</Notice>
              ) : (
                <Notice dot="#1d7a3e">Embedding aktif.</Notice>
              )}
            </div>
          <p className="text-[14px] text-muted">
            Dipakai untuk mengindeks berkas PDF/DOCX dan mengambil kutipan saat
            penilaian. Dimensi vector: {props.embDim}.
          </p>

          <div className="grid grid-cols-2 gap-4">
            <Field
              label="Alamat dasar embedding"
              htmlFor="emb_base_url"
              error={errors.emb_base_url}
            >
              <Input
                id="emb_base_url"
                name="emb_base_url"
                defaultValue={props.embBaseUrl}
                placeholder="https://..."
              />
            </Field>
            <Field
              label="Nama model embedding"
              htmlFor="emb_model_name"
              error={errors.emb_model_name}
            >
              <Input
                id="emb_model_name"
                name="emb_model_name"
                defaultValue={props.embModelName}
                placeholder="nama-model-embedding"
              />
            </Field>

            <div className="col-span-2">
              <Field label="API key embedding" htmlFor="emb_api_key">
                <div className="flex gap-2">
                  <Input
                    id="emb_api_key"
                    ref={embKeyRef}
                    name={embKeyDirty ? "emb_api_key" : undefined}
                    type={embKeyShown ? "text" : "password"}
                    defaultValue={props.embApiKeyMasked}
                    placeholder="Belum diisi"
                    autoComplete="off"
                    onChange={() => setEmbKeyDirty(true)}
                  />
                  <Button
                    type="button"
                    onClick={revealEmbKey}
                    className="shrink-0 px-3"
                  >
                    {embKeyShown ? "Sembunyikan" : "Reveal"}
                  </Button>
                </div>
              </Field>
            </div>
          </div>

          {errors.emb_api_key ? (
            <ErrorLine>{errors.emb_api_key}</ErrorLine>
          ) : null}
          </div>
        </Card>
      </form>
    </div>
  );
}
