import type { ReactNode } from "react";
import { Navbar, type NavItem } from "@/components/navbar";
import { BrandingProvider } from "@/components/branding-context";
import { footerOf, getAppBranding, logoSrc } from "@/lib/branding";

export async function AppShell({
  items,
  homeHref,
  userName,
  roleLabel,
  children,
}: {
  items: NavItem[];
  homeHref: string;
  userName: string;
  roleLabel: string;
  children: ReactNode;
}) {
  const branding = await getAppBranding();
  return (
    <div className="flex min-h-screen flex-col bg-canvas">
      <Navbar
        items={items}
        homeHref={homeHref}
        userName={userName}
        roleLabel={roleLabel}
        appName={branding.app_name}
        logoSrc={logoSrc(branding)}
      />
      <BrandingProvider appName={branding.app_name}>
        <main className="flex-1 px-6 py-6">{children}</main>
      </BrandingProvider>
      <footer className="flex items-center justify-between border-t border-border bg-white px-6 py-3 text-[13px] text-muted">
        <span>{footerOf(branding)}</span>
        <span>{roleLabel}</span>
      </footer>
    </div>
  );
}
