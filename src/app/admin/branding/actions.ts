"use server";

import { revalidatePath } from "next/cache";
import { q1 } from "@/db/pool";
import { getAppBranding } from "@/lib/branding";
import { requireRole } from "@/lib/session";

export type BrandingState =
  | { errors?: Record<string, string>; info?: string }
  | undefined;

const MAX_LOGO_BYTES = 512 * 1024;
const LOGO_TYPES = ["image/png", "image/jpeg", "image/webp", "image/gif"];

function str(value: FormDataEntryValue | null): string {
  return typeof value === "string" ? value.trim() : "";
}

export async function saveBranding(
  _prev: BrandingState,
  formData: FormData,
): Promise<BrandingState> {
  const admin = await requireRole("admin");
  await getAppBranding();

  const app_name = str(formData.get("app_name"));
  const footer_text = str(formData.get("footer_text"));
  const remove_logo = formData.get("remove_logo") === "on";

  const errors: Record<string, string> = {};
  if (!app_name) {
    errors.app_name = "Nama aplikasi wajib diisi.";
  } else if (app_name.length > 50) {
    errors.app_name = "Nama aplikasi maksimal 50 karakter.";
  }
  if (footer_text.length > 120) {
    errors.footer_text = "Teks footer maksimal 120 karakter.";
  }

  let logo: Buffer | null = null;
  let logoType: string | null = null;
  const file = formData.get("logo");
  if (file instanceof File && file.size > 0 && file.name.trim() !== "") {
    const type = file.type.toLowerCase();
    if (!LOGO_TYPES.includes(type)) {
      errors.logo = "Logo harus berformat PNG, JPG, WebP, atau GIF.";
    } else if (file.size > MAX_LOGO_BYTES) {
      errors.logo = "Ukuran logo maksimal 512 KB.";
    } else {
      logo = Buffer.from(await file.arrayBuffer());
      logoType = type;
    }
  }

  if (Object.keys(errors).length > 0) return { errors };

  if (logo && logoType) {
    await q1(
      `UPDATE app_settings
       SET app_name = $1, footer_text = $2, logo = $3, logo_type = $4,
           logo_version = logo_version + 1, updated_at = now(), updated_by = $5
       WHERE id = 1`,
      [app_name, footer_text, logo, logoType, admin.id],
    );
  } else if (remove_logo) {
    await q1(
      `UPDATE app_settings
       SET app_name = $1, footer_text = $2, logo = NULL, logo_type = NULL,
           logo_version = logo_version + 1, updated_at = now(), updated_by = $3
       WHERE id = 1`,
      [app_name, footer_text, admin.id],
    );
  } else {
    await q1(
      `UPDATE app_settings
       SET app_name = $1, footer_text = $2, updated_at = now(), updated_by = $3
       WHERE id = 1`,
      [app_name, footer_text, admin.id],
    );
  }

  revalidatePath("/", "layout");
  return { info: "Pengaturan aplikasi disimpan." };
}
