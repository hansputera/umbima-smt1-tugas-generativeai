"use client";

import { useActionState } from "react";
import Image from "next/image";
import { saveBranding, type BrandingState } from "./actions";
import { Button } from "@/components/ui/button";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Card, Notice, PageHeader } from "@/components/ui/misc";
import { Field, Input } from "@/components/ui/field";

export function BrandingClient(props: {
  appName: string;
  footerText: string;
  hasLogo: boolean;
  logoSrc: string | null;
  footerFallback: string;
}) {
  const [state, formAction, pending] = useActionState<BrandingState, FormData>(
    saveBranding,
    undefined,
  );
  const errors = state?.errors ?? {};

  return (
    <div className="flex flex-col gap-6">
      <Breadcrumb items={[{ label: "Aplikasi" }]} />
      <PageHeader
        title="Aplikasi"
        description="Nama aplikasi, teks footer, dan logo yang tampil di seluruh halaman."
        action={
          <Button
            type="submit"
            form="branding-form"
            variant="primary"
            disabled={pending}
          >
            {pending ? "Menyimpan..." : "Simpan"}
          </Button>
        }
      />

      {state?.info ? <Notice dot="#1d7a3e">{state.info}</Notice> : null}

      <Card className="p-6">
        <form
          id="branding-form"
          action={formAction}
          className="flex flex-col gap-4"
        >
          <div className="grid grid-cols-2 gap-4">
            <Field
              label="Nama aplikasi"
              htmlFor="b-name"
              error={errors.app_name}
              hint="Tampil di tab browser, navbar, dan breadcrumb."
            >
              <Input
                id="b-name"
                name="app_name"
                defaultValue={props.appName}
                maxLength={50}
              />
            </Field>
            <Field
              label="Teks footer"
              htmlFor="b-footer"
              error={errors.footer_text}
              hint={`Kosong = nama aplikasi (saat ini: ${props.footerFallback}).`}
            >
              <Input
                id="b-footer"
                name="footer_text"
                defaultValue={props.footerText}
                placeholder={props.appName}
                maxLength={120}
              />
            </Field>
          </div>

          <Field
            label="Logo"
            htmlFor="b-logo"
            error={errors.logo}
            hint="PNG, JPG, WebP, atau GIF. Maksimal 512 KB. Kosongkan untuk mempertahankan logo saat ini."
          >
            <input
              id="b-logo"
              name="logo"
              type="file"
              accept="image/png,image/jpeg,image/webp,image/gif"
              className="w-full cursor-pointer rounded border border-border bg-white px-2 py-1.5 text-[14px] text-ink file:mr-3 file:cursor-pointer file:rounded file:border file:border-border file:bg-canvas file:px-3 file:py-1 file:text-[14px] file:text-ink"
            />
          </Field>

          {props.hasLogo && props.logoSrc ? (
            <div className="flex items-center gap-4">
              <Image
                src={props.logoSrc}
                alt="Logo aplikasi saat ini"
                width={40}
                height={40}
                unoptimized
                className="size-10 rounded border border-border bg-white object-contain"
              />
              <label className="flex cursor-pointer items-center gap-2 text-[14px] text-ink">
                <input
                  type="checkbox"
                  name="remove_logo"
                  className="size-4 accent-accent"
                />
                Hapus logo
              </label>
            </div>
          ) : null}
        </form>
      </Card>
    </div>
  );
}
