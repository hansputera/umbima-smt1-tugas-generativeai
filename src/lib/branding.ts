import { cache } from "react";
import { q1 } from "@/db/pool";

export type Branding = {
  app_name: string;
  footer_text: string;
  logo_version: number;
  has_logo: boolean;
};

const SELECT_BRANDING = `SELECT app_name, footer_text, logo_version,
         (logo IS NOT NULL) AS has_logo
     FROM app_settings WHERE id = 1`;

export const getAppBranding = cache(async function getAppBranding(): Promise<Branding> {
  const row = await q1<Branding>(SELECT_BRANDING);
  if (row) return row;
  const inserted = await q1<Branding>(
    `INSERT INTO app_settings (id) VALUES (1)
     ON CONFLICT (id) DO NOTHING
     RETURNING app_name, footer_text, logo_version,
               (logo IS NOT NULL) AS has_logo`,
  );
  if (inserted) return inserted;
  const again = await q1<Branding>(SELECT_BRANDING);
  if (!again) throw new Error("app_settings tidak tersedia");
  return again;
});

export function footerOf(b: Branding): string {
  return b.footer_text.trim() || b.app_name;
}

export function logoSrc(b: Branding): string | null {
  return b.has_logo ? `/logo?v=${b.logo_version}` : null;
}
