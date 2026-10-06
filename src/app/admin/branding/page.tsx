import { footerOf, getAppBranding, logoSrc } from "@/lib/branding";
import { BrandingClient } from "./branding-client";

export const dynamic = "force-dynamic";

export default async function BrandingPage() {
  const b = await getAppBranding();
  return (
    <BrandingClient
      appName={b.app_name}
      footerText={b.footer_text}
      hasLogo={b.has_logo}
      logoSrc={logoSrc(b)}
      footerFallback={footerOf(b)}
    />
  );
}
